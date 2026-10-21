"""Voice mastering + BGM ducking + synthesized SFX -> work3/audio/final_mix.wav (48 kHz, 24-bit stereo, -14 LUFS) for the v3 edit."""
import json, subprocess, wave, sys
import numpy as np

B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
A = B + 'work3/audio/'
SR = 48000
SC = json.load(open(B + 'work3/scenes.json'))
TOTAL = SC['total']
WORDS = json.load(open(B + 'work3/words_srt.json'))['words']
CUES = {}
for w in WORDS:
    CUES.setdefault(w['cue'] + 1, []).append(w)
tw = lambda cue, k: CUES[cue][k - 1]['t0']
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


# ------------------------------------------------------------------ 1. voice (original recording, only cleaned + mastered)
VOICE_CHAIN = ("highpass=f=90:poles=2,"
               f"arnndn=m={B}assets/rnn/bd.rnnn:mix=0.9,"
               "equalizer=f=230:t=q:w=1.0:g=-1.8,"
               "equalizer=f=3300:t=q:w=0.9:g=2.4,"
               "equalizer=f=6500:t=q:w=1.2:g=-1.2,"
               "treble=g=1.4:f=10000,"
               "deesser=i=0.30:m=0.5:f=0.5,"
               "acompressor=threshold=0.056:ratio=2.8:attack=6:release=130:knee=4:makeup=3.2,"
               "alimiter=limit=0.89:attack=3:release=60:level=false")
run(['ffmpeg', '-y', '-v', 'error', '-i', A + 'voice_raw.wav', '-af', VOICE_CHAIN, '-c:a', 'pcm_s24le', A + 'voice_proc.wav'])
voice = read_wav(A + 'voice_proc.wav')[:, 0]
VOICE_LAG = 616        # arnndn / limiter latency measured by cross-correlation (12.8 ms)
voice = np.concatenate([voice[VOICE_LAG:], np.zeros(VOICE_LAG)])
print('voice processed:', len(voice) / SR, 's')

# ------------------------------------------------------------------ 2. music bed
MUSIC_SRC = B + 'stock/music/548.mp3'
run(['ffmpeg', '-y', '-v', 'error', '-i', MUSIC_SRC, '-t', f'{TOTAL}', '-ar', str(SR), '-ac', '2',
     '-af', f"highpass=f=45,equalizer=f=450:t=q:w=0.8:g=-2.5,equalizer=f=2400:t=q:w=0.9:g=-3.5,afade=t=in:st=0:d=3.5,afade=t=out:st={TOTAL - 4.5}:d=4.5",
     '-c:a', 'pcm_s24le', A + 'music_raw.wav'])
music = read_wav(A + 'music_raw.wav')
N = int(TOTAL * SR)
if len(music) < N:
    music = np.pad(music, ((0, N - len(music)), (0, 0)))
music = music[:N]


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
speaking = movavg(speaking, int(0.25 * SR))
speaking = (speaking > 0.3).astype(np.float64)
att, rel = 0.12, 0.7
cur = 0.0
a_k, r_k = 1 - np.exp(-1 / (att * SR)), 1 - np.exp(-1 / (rel * SR))
sm = np.empty(N)
for i in range(0, N, SR):
    seg = speaking[i:i + SR]
    out = np.empty(len(seg))
    for j, s in enumerate(seg):
        cur += (a_k if s > cur else r_k) * (s - cur)
        out[j] = cur
    sm[i:i + SR] = out
DUCK_DB = -11.0
gain = 10 ** ((DUCK_DB * sm) / 20)
MUSIC_BASE_DB = -11.0
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


sfx = np.zeros((N, 2))


def put(t, y, pan=0.0, gain_db=0.0):
    i = int(t * SR)
    if i < 0 or i >= N:
        return
    y = y * 10 ** (gain_db / 20)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    n = min(len(y), N - i)
    sfx[i:i + n, 0] += y[:n] * l * 1.414
    sfx[i:i + n, 1] += y[:n] * r * 1.414


# ---- scene transitions: one whoosh + soft thump per wipe (screen is covered at tc)
for s in SC['scenes']:
    for tc, on in ((s['t0'], s['wipeIn']), (s['t1'], s['wipeOut'])):
        if on:
            put(tc - 0.36, whoosh(0.72, 260, 5600, 0.17), 0.0)
            put(tc - 0.02, thud(0.35, 0.12), 0.0)
# ---- jump cuts that stay on screen (speaker visible): a very light swish
hidden = [(s['t0'], s['t1']) for s in SC['scenes']]
for c in json.load(open(B + 'work3/cuts.json'))['cuts']:
    t = c / 30
    if not any(a0 - 0.3 <= t <= a1 + 0.3 for a0, a1 in hidden):
        put(t - 0.06, whoosh(0.28, 600, 3800, 0.045), 0.0)

# ---- left-column headline chips
for t in (0.25, 0.55, 21.45, tw(7, 3), 46.9, tw(15, 1), tw(15, 4), tw(15, 7), 78.95, 105.3, tw(31, 2), tw(31, 8), 130.8, tw(38, 1), tw(38, 4), tw(38, 8), tw(39, 8), 164.0):
    put(t, pop(1300, 460, 0.1, 0.13), -0.5)
# ---- key-point scenes
# wa
put(2.55, pop(), 0.5); put(tw(1, 8) - 0.05, pop(1600, 600), 0.3); put(tw(2, 2) - 0.05, pop(1600, 600), 0.3); put(tw(2, 5) - 0.05, pop(1600, 600), 0.3)
put(tw(1, 8), tick(0.12), 0.5); put(6.9, tick(0.12), 0.5); put(7.1, alert(), 0.0)
# b-roll
for t in (8.37, 9.0, 10.2, 11.1, 12.37, 13.3, 14.3, 15.0):
    put(t, pop(1200, 420), 0.4)
# never
put(tw(6, 3) - 0.12, pop(900, 300), 0.4)
put(tw(6, 4) + 0.18, thud(0.6, 0.55), 0.0); put(tw(6, 4) + 0.18, glitch(0.2, 0.1), 0.0)
put(tw(6, 4) + 0.5, thud(0.45, 0.35), 0.2)
# loss
put(tw(8, 2) - 0.1, pop(), 0.4); put(tw(8, 9) - 0.1, pop(), 0.4); put(tw(9, 4) - 0.1, pop(), 0.4); put(tw(9, 4) + 0.3, thud(0.5, 0.35), 0.0)
# link
put(36.2, pop(), 0.4); put(tw(11, 4) - 0.1, pop(1700, 700), 0.5)
put(tw(12, 3) + 0.1, click(0.35), 0.3); put(38.82, alert(), 0.0); put(38.82, thud(0.6, 0.5), 0.0)
for t in (40.6, 41.94, 42.9):
    put(t, pop(900, 300), 0.4); put(t, glitch(0.18, 0.09), 0.0, -2)
# rules
for t in (tw(18, 2) - 0.1, tw(18, 7) - 0.1, 62.9, tw(19, 2) - 0.1, tw(19, 5) - 0.1, 69.8, tw(21, 6) - 0.1, tw(21, 8) - 0.1, 75.4, tw(22, 3) - 0.1):
    put(t, pop(1200, 420), 0.4)
put(tw(18, 7) + 0.4, thud(0.4, 0.25), 0.3)
put(tw(20, 6) - 0.05, thud(0.6, 0.5), 0.0); put(tw(20, 6) - 0.05, alert(), 0.0)
put(tw(21, 10) - 0.1, ding(1568, 0.9, 0.14), 0.3)
# domain
put(82.5, pop(), 0.4); put(tw(24, 2) - 0.1, pop(), 0.4); put(tw(24, 5) - 0.2, pop(1100, 360), 0.4)
for i in range(31):
    put(tw(24, 5) + 0.25 + i * 0.045, tick(0.045), 0.35)
put(tw(24, 10) - 0.1, pop(1500, 600), 0.2)
put(tw(25, 5) - 0.1, thud(0.45, 0.3), 0.0); put(tw(25, 5) - 0.1, alert(), 0.0)
put(tw(26, 4) - 0.1, pop(900, 300), 0.4); put(tw(26, 5), thud(0.4, 0.3), 0.0)
put(tw(27, 3) - 0.1, ding(1318.5, 0.9, 0.14), 0.3)
# official
put(96.7, pop(), 0.4); put(tw(28, 5) - 0.15, pop(1100, 360), 0.4); put(tw(28, 5) + 0.1, ding(1568, 0.8, 0.12), 0.3)
put(tw(29, 3) - 0.15, pop(1100, 360), 0.4); put(tw(29, 3) + 0.1, ding(1568, 0.8, 0.12), 0.3); put(tw(29, 6), ding(1760, 1.0, 0.14), 0.3)
# gpay
put(113.95, pop(), 0.4); put(tw(32, 1) - 0.1, pop(), 0.4); put(tw(32, 6) - 0.2, swipe(), 0.6); put(tw(32, 6) - 0.1, pop(), -0.3)
put(tw(33, 4) - 0.1, swipe(), 0.6); put(tw(33, 4) - 0.1, pop(), -0.3); put(tw(34, 5) - 0.1, pop(), -0.3); put(tw(34, 5) + 0.1, ding(1568, 0.9, 0.14), -0.3)
put(tw(35, 7) - 0.1, thud(0.5, 0.35), 0.0); put(tw(35, 7) - 0.1, alert(), 0.0)
put(tw(36, 4) - 0.05, thud(0.8, 0.6), 0.0); put(tw(36, 4) + 0.18, thud(0.5, 0.35), 0.2); put(tw(36, 4) + 0.2, alert(), 0.0)
# careful
put(146.4, pop(), 0.4); put(tw(41, 5) - 0.2, pop(), 0.4)
for i in range(18):
    put(tw(41, 6) + i * 0.07, tick(0.05), 0.3)
put(tw(41, 6) + 1.25, thud(0.7, 0.5), 0.0); put(tw(42, 3) - 0.1, pop(900, 300), 0.4)
# recap / share
for t in (151.75, tw(43, 3) - 0.1, tw(44, 5) - 0.1, tw(44, 7) + 0.2):
    put(t, pop(1200, 420), 0.4)
put(tw(44, 7) + 0.7, ding(1568, 0.9, 0.14), 0.3)
put(tw(45, 1) - 0.2, pop(), 0.4); put(tw(45, 3), click(0.25), 0.3); put(tw(45, 3) + 0.1, ding(1760, 0.8, 0.12), 0.3)
put(tw(46, 1) - 0.1, pop(), 0.4)
for k in range(4):
    put(tw(46, 2) + k * 0.2, pop(1500 + 120 * k, 600), 0.3, -4)
# subscribe + end
put(tw(48, 2) - 0.3, pop(), 0.4); put(tw(48, 4) + 0.05, click(0.35), 0.3); put(tw(48, 4) + 0.25, ding(1760, 0.9, 0.14), 0.3)
put(tw(48, 6) - 0.1, pop(), 0.4)
put(170.62, whoosh(0.7, 300, 5200, 0.2), 0.0)
put(170.95, thud(0.9, 0.5), 0.0); put(170.95, ding(1318.5, 1.8, 0.15), 0.0); put(171.1, ding(1975.5, 1.4, 0.09), 0.2)
put(172.1, pop(1500, 600), 0.2, -4)

# ------------------------------------------------------------------ 4. mix + loudness
vox = np.zeros((N, 2))
v = voice[:N] if len(voice) >= N else np.pad(voice, (0, N - len(voice)))
vox[:, 0] = v
vox[:, 1] = v
mix = vox + music + sfx
pre = A + 'mix_pre.wav'
write_wav(pre, mix)
stderr = run(['ffmpeg', '-hide_banner', '-nostats', '-i', pre, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'])
j = json.loads(stderr[stderr.rindex('{'):stderr.rindex('}') + 1])
print('pass 1:', {k: j[k] for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')})
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
      f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true:print_format=summary")
run(['ffmpeg', '-y', '-v', 'error', '-i', pre, '-af', af, '-ar', str(SR), '-c:a', 'pcm_s24le', A + 'final_mix.wav'])
st = run(['ffmpeg', '-hide_banner', '-nostats', '-i', A + 'final_mix.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'])
print([l.strip() for l in st.splitlines() if any(k in l for k in ('I:', 'LRA:', 'Peak:'))][-4:])
print('wrote final_mix.wav')
