"""Voice mastering + BGM ducking + synthesized SFX -> final_mix.wav (48 kHz, 24-bit stereo, -14 LUFS)."""
import json, subprocess, wave, sys
import numpy as np

B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
A = B + 'work/audio/'
SR = 48000
INS_T, DLT = 719 / 30, 84 / 30
TOTAL = 206.6 + DLT
rng = np.random.default_rng(7)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2000:])
        raise SystemExit('ffmpeg failed')
    return r.stderr


def read_wav(path):
    w = wave.open(path)
    n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
    raw = np.frombuffer(w.readframes(n), dtype=np.uint8)
    assert sw == 3
    b = raw.reshape(-1, 3)
    x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
    x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(np.float64) / (1 << 23)
    return x.reshape(-1, ch)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    pcm = (x * (2 ** 23 - 1)).astype(np.int32)
    ch = pcm.shape[1]
    b = np.empty((pcm.shape[0], ch, 3), np.uint8)
    b[..., 0] = pcm & 255
    b[..., 1] = (pcm >> 8) & 255
    b[..., 2] = (pcm >> 16) & 255
    with wave.open(path, 'wb') as w:
        w.setnchannels(ch)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b.tobytes())


# ------------------------------------------------------------------ 1. voice
VOICE_CHAIN = ("highpass=f=90:poles=2,"
               f"arnndn=m={B}assets/rnn/bd.rnnn:mix=0.9,"
               "equalizer=f=230:t=q:w=1.0:g=-1.8,"
               "equalizer=f=3300:t=q:w=0.9:g=2.4,"
               "equalizer=f=6500:t=q:w=1.2:g=-1.2,"
               "treble=g=1.4:f=10000,"
               "deesser=i=0.30:m=0.5:f=0.5,"
               "acompressor=threshold=0.056:ratio=2.8:attack=6:release=130:knee=4:makeup=3.2,"
               "alimiter=limit=0.89:attack=3:release=60:level=false")
run(['ffmpeg', '-y', '-v', 'error', '-i', A + 'voice_edit.wav', '-af', VOICE_CHAIN, '-c:a', 'pcm_s24le', A + 'voice_proc.wav'])
voice = read_wav(A + 'voice_proc.wav')[:, 0]
VOICE_LAG = 616        # arnndn / limiter latency measured by cross-correlation against voice_edit.wav (12.8 ms)
voice = np.concatenate([voice[VOICE_LAG:], np.zeros(VOICE_LAG)])
print('voice processed:', len(voice) / SR, 's')

# ------------------------------------------------------------------ 2. music bed
MUSIC_SRC = B + 'stock/music/548.mp3'
run(['ffmpeg', '-y', '-v', 'error', '-i', MUSIC_SRC, '-t', f'{TOTAL}', '-ar', str(SR), '-ac', '2',
     '-af', "highpass=f=45,equalizer=f=450:t=q:w=0.8:g=-2.5,equalizer=f=2400:t=q:w=0.9:g=-3.5,"
            "afade=t=in:st=0:d=3.5,afade=t=out:st=205.4:d=4.0",
     '-c:a', 'pcm_s24le', A + 'music_raw.wav'])
music = read_wav(A + 'music_raw.wav')
N = int(TOTAL * SR)
if len(music) < N:
    music = np.pad(music, ((0, N - len(music)), (0, 0)))
music = music[:N]

# voice-driven ducking: smooth gain curve (fast down when he speaks, slow release)
def movavg(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0))
    k = n // 2
    idx = np.arange(len(x))
    lo = np.clip(idx - k, 0, len(x))
    hi = np.clip(idx + n - k, 0, len(x))
    return (c[hi] - c[lo]) / np.maximum(hi - lo, 1)


env = np.sqrt(movavg(voice ** 2, SR // 10))
env = np.pad(env, (0, max(0, N - len(env))))[:N]
speaking = (20 * np.log10(env + 1e-9) > -46).astype(np.float64)
speaking = movavg(speaking, int(0.25 * SR))          # bridge short gaps
speaking = (speaking > 0.3).astype(np.float64)
att, rel = 0.12, 0.7
g = np.zeros(N)
cur = 0.0
a_k, r_k = 1 - np.exp(-1 / (att * SR)), 1 - np.exp(-1 / (rel * SR))
# vectorised first-order smoother with different attack / release via two passes
sm = np.empty(N)
for i in range(0, N, SR):                       # chunked python loop (fast enough: 206 chunks)
    seg = speaking[i:i + SR]
    out = np.empty(len(seg))
    for j, s in enumerate(seg):
        cur += (a_k if s > cur else r_k) * (s - cur)
        out[j] = cur
    sm[i:i + SR] = out
DUCK_DB = -11.0
gain = 10 ** ((DUCK_DB * sm) / 20)
MUSIC_BASE_DB = -12.0
music = music * gain[:, None] * 10 ** (MUSIC_BASE_DB / 20)

# ------------------------------------------------------------------ 3. SFX (all synthesized here -> no licensing questions)
t_ax = lambda d: np.arange(int(d * SR)) / SR


def svf_bp(x, fc_curve, q=2.0):
    """Band-pass with a time-varying centre frequency (block-wise state variable filter)."""
    y = np.zeros_like(x)
    low = band = 0.0
    blk = 64
    for i in range(0, len(x), blk):
        f = 2 * np.sin(np.pi * min(fc_curve[min(i, len(fc_curve) - 1)], SR * 0.4) / SR)
        for j in range(i, min(i + blk, len(x))):
            high = x[j] - low - band / q
            band += f * high
            low += f * band
            y[j] = band
    return y


def whoosh(dur=0.6, f0=250, f1=5200, peak=0.16, up=True):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    fc = np.geomspace(f0, f1, n) if up else np.geomspace(f1, f0, n)
    y = svf_bp(noise, fc, 1.6)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2.2
    y *= env
    return y / (np.abs(y).max() + 1e-9) * peak


def pop(f0=1250, f1=380, dur=0.11, peak=0.16):
    t = t_ax(dur)
    ph = 2 * np.pi * np.cumsum(np.geomspace(f0, f1, len(t))) / SR
    y = np.sin(ph) * np.exp(-t * 34)
    y[:int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return y * peak


def thud(dur=0.55, peak=0.5):
    t = t_ax(dur)
    ph = 2 * np.pi * np.cumsum(np.geomspace(95, 42, len(t))) / SR
    y = np.sin(ph) * np.exp(-t * 8.5)
    nz = svf_bp(rng.standard_normal(len(t)), np.full(len(t), 900.0), 0.9) * np.exp(-t * 42)
    y = y + 0.12 * nz / (np.abs(nz).max() + 1e-9)
    return y / np.abs(y).max() * peak


def ding(f=1318.5, dur=0.9, peak=0.14):
    t = t_ax(dur)
    y = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 1.5 * t) + 0.2 * np.sin(2 * np.pi * f * 2.01 * t)) * np.exp(-t * 5.2)
    y[:int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return y / np.abs(y).max() * peak


def alert(peak=0.13):
    out = np.zeros(int(0.42 * SR))
    for k in range(2):
        t = t_ax(0.1)
        b = np.sin(2 * np.pi * 880 * t) * np.sin(np.linspace(0, np.pi, len(t))) ** 0.6
        out[int(k * 0.16 * SR):int(k * 0.16 * SR) + len(b)] += b
    return out * peak


def tick(peak=0.05):
    n = int(0.012 * SR)
    y = svf_bp(rng.standard_normal(n), np.full(n, 3200.0), 1.2) * np.exp(-np.arange(n) / (0.003 * SR))
    return y / (np.abs(y).max() + 1e-9) * peak


def click(peak=0.2):
    return tick(peak) * 1.0


def glitch(dur=0.28, peak=0.12):
    n = int(dur * SR)
    y = rng.standard_normal(n)
    gate = np.repeat(rng.random(n // 960 + 1) > 0.45, 960)[:n]
    y = svf_bp(y, np.full(n, 2400.0), 0.7) * gate
    return y / (np.abs(y).max() + 1e-9) * peak


def swipe():
    return whoosh(0.32, 500, 4200, 0.12)


sfx = np.zeros((N, 2))


def put(t, y, pan=0.0, gain_db=0.0, raw=False):
    if not raw and t >= INS_T - 1e-6:       # events written on the pre-insert timeline
        t += DLT
    i = int(t * SR)
    if i < 0 or i >= N:
        return
    y = y * 10 ** (gain_db / 20)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    n = min(len(y), N - i)
    sfx[i:i + n, 0] += y[:n] * l * 1.414
    sfx[i:i + n, 1] += y[:n] * r * 1.414


W = lambda t, **k: put(t, whoosh(**k), pan=0.0)
events = []
# hook + title
W(0.30, dur=0.55)
for t in (3.0,):
    put(t, pop(), 0.35)
for t in (3.45, 5.07, 6.15):
    put(t, tick(0.16), 0.3)
# cutaways
for t in (8.20, 12.35, 16.45):
    W(t - 0.1, dur=0.5)
for t in (9.0, 10.2, 11.1, 13.3, 14.3, 15.1):
    put(t, pop(1500, 520), 0.5, -3)
# question / never / stamp
put(21.0, pop(900, 300), 0.4)
put(22.78, thud(0.6, 0.5), 0)
put(22.95, thud(0.45, 0.3), 0.2)
# panam / data / maanam
for t in (27.45, 30.2, 32.85):
    put(t, pop(), 0.4)
# link trap
put(43.25, pop(), 0.4); put(45.4, click(0.3), 0.3); put(45.7, alert(), 0.3)
for t in (46.9, 48.4, 49.35, 50.35, 51.7):
    put(t, pop(1100, 360), 0.4)
for t in (56.9, 57.0, 57.85, 58.8, 61.0):
    put(t, pop(1300, 420), 0.4, -2)
put(66.5, thud(0.4, 0.28), 0.3); put(69.3, thud(0.4, 0.28), 0.5)
W(66.4, dur=0.4, peak=0.1)
# hacker / stolen
W(71.45, dur=0.5)
put(72.0, glitch(), 0, 0)
put(73.2, glitch(0.2), 0, -2)
W(74.95, dur=0.45)
for t in (75.65, 77.9, 80.8):
    put(t, pop(1000, 330), 0.3)
W(79.35, dur=0.4)
put(82.35, alert(), 0.3)
W(83.4, dur=0.45)
put(83.75, thud(0.45, 0.3), 0)
put(85.5, thud(0.45, 0.3), 0)
put(87.4, thud(0.55, 0.4), 0); put(87.55, alert(), 0)
put(91.5, ding(1568, 0.9, 0.12), 0.3)
put(96.65, pop(), 0.3); put(95.4, tick(0.12), 0.3)
put(100.9, pop(), 0.4); put(103.5, pop(900, 300), 0.4)
# step 1 + split
put(104.85, thud(0.5, 0.3), 0)
W(104.7, dur=0.6)
put(105.4, pop(), -0.3)
for t0, n in ((106.95, 31), (119.95, 17), (126.75, 17)):
    for k in range(n):
        put(t0 + k * (0.055 if t0 < 110 else 0.06), tick(0.045), 0.35)
put(109.35, pop(1400, 600), 0.2)
put(113.0, thud(0.5, 0.35), 0); put(113.1, alert(), 0.3)
put(115.35, pop(), -0.3); put(117.3, ding(1175, 0.7, 0.1), 0.3)
put(122.6, ding(), 0.3); put(128.0, ding(1568, 0.9, 0.13), 0.3)
put(130.8, pop(), 0.4); put(134.0, alert(), 0.3); put(134.05, thud(0.45, 0.3), 0)
# GPay demo
W(138.65, dur=0.55)
put(139.3, swipe(), 0.6)
for t in (140.45, 142.85, 147.15, 149.1):
    put(t, pop(1200, 400), -0.3)
put(142.15, pop(1700, 700), 0.5)
put(143.95, swipe(), 0.6)
put(145.0, pop(1500, 600), 0.6); put(147.0, pop(1500, 600), 0.6)
put(152.45, whoosh(0.5, 300, 4600), 0)
put(153.45, pop(700, 250), 0.2)
put(154.4, thud(0.7, 0.55), 0); put(154.62, thud(0.5, 0.3), 0.3)
# PhonePe demo
W(155.8, dur=0.5)
put(157.9, swipe(), 0.6); put(158.05, pop(), -0.3); put(159.0, pop(), -0.3); put(160.05, pop(), -0.3)
put(158.6, pop(1700, 700), 0.5); put(160.55, swipe(), 0.6)
for t in (161.3, 165.0):
    put(t, pop(1500, 600), 0.6)
put(164.2, ding(), -0.3); put(165.6, ding(1568, 0.9, 0.12), -0.3); put(167.9, pop(), -0.3)
put(171.15, ding(1568, 0.9, 0.13), 0.3)
# ashraddha
put(174.7, pop(), 0.4); put(175.5, pop(), 0.4)
for t in (176.92, 177.42):
    put(t, tick(0.14), 0.3)
put(177.92, thud(0.6, 0.45), 0); put(178.65, pop(800, 280), 0.4)
# checklist
put(182.0, pop(), 0.4); put(183.3, thud(0.4, 0.3), 0.3); put(185.1, thud(0.4, 0.3), 0.3); put(186.75, ding(1568, 0.9, 0.14), 0.3)
# share / subscribe
put(189.35, pop(), 0.4); put(190.3, pop(), 0.4)
for k in range(4):
    put(191.3 + k * 0.22, pop(1500 + 120 * k, 600), 0.3, -4)
put(196.65, pop(), 0.4); put(197.5, click(0.3), 0.3); put(197.7, ding(1760, 0.8, 0.12), 0.3)
# end card
W(199.35, dur=0.7, peak=0.2)
put(200.0, thud(0.8, 0.45), 0)
put(200.1, ding(1318.5, 1.6, 0.14), 0)
put(201.3, pop(1500, 600), 0.2, -4)

# welcome stinger (absolute timeline, no shift): riser -> hit on the logo -> shimmer
T0 = INS_T
put(T0 + 0.02, whoosh(0.5, 200, 6500, 0.22), 0.0, raw=True)
put(T0 + 0.50, thud(1.1, 0.62), 0, raw=True)
put(T0 + 0.50, ding(1318.5, 1.8, 0.16), 0, raw=True)
put(T0 + 0.52, ding(1975.5, 1.4, 0.09), 0.2, raw=True)
put(T0 + 1.34, whoosh(0.7, 800, 7000, 0.10), 0.0, raw=True)
put(T0 + 2.45, whoosh(0.35, 3000, 700, 0.10, up=False), 0.0, raw=True)

# ------------------------------------------------------------------ 4. mix + loudness
vox = np.zeros((N, 2))
v = voice[:N] if len(voice) >= N else np.pad(voice, (0, N - len(voice)))
vox[:, 0] = v
vox[:, 1] = v
mix = vox + music + sfx
pre = A + 'mix_pre.wav'
write_wav(pre, mix)
# two-pass loudnorm (linear) -> -14 LUFS, true peak <= -1.5 dBTP
stderr = run(['ffmpeg', '-hide_banner', '-nostats', '-i', pre, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'])
j = json.loads(stderr[stderr.rindex('{'):stderr.rindex('}') + 1])
print('pass 1:', {k: j[k] for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')})
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
      f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true:print_format=summary")
run(['ffmpeg', '-y', '-v', 'error', '-i', pre, '-af', af, '-ar', str(SR), '-c:a', 'pcm_s24le', A + 'final_mix.wav'])
st = run(['ffmpeg', '-hide_banner', '-nostats', '-i', A + 'final_mix.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'])
print([l.strip() for l in st.splitlines() if any(k in l for k in ('I:', 'LRA:', 'Peak:'))][-4:])
print('wrote final_mix.wav')
