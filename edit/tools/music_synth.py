"""Original (copyright-free) score + sound effects, synthesised in numpy and shaped to the video's structure.

Nothing here is sampled or taken from any library, so there is nothing a Content-ID system could match.

  music_synth.py <out_dir>      writes music_bed.wav and sfx.wav (stereo, 48 kHz, float32, same length as the video + tail)
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import scenes  # noqa: E402
import json  # noqa: E402

SR = 48000
BPM = 96.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
VIDEO_DUR = 263.0333
DUR = VIDEO_DUR + 4.0
N = int(DUR * SR)
rng = np.random.default_rng(7)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def stereo(n=N):
    return np.zeros((n, 2), np.float32)


def add(buf, sig, t0, gain=1.0, pan=0.0):
    """mix mono `sig` into stereo `buf` at time t0 (seconds) with equal-power pan (-1..1)"""
    i0 = int(t0 * SR)
    if i0 >= buf.shape[0] or i0 + len(sig) <= 0:
        return
    s0 = max(0, -i0)
    i0 = max(0, i0)
    seg = sig[s0:s0 + buf.shape[0] - i0]
    ang = (pan + 1) * np.pi / 4
    buf[i0:i0 + len(seg), 0] += (seg * gain * np.cos(ang)).astype(np.float32)
    buf[i0:i0 + len(seg), 1] += (seg * gain * np.sin(ang)).astype(np.float32)


def env_ad(n, a, d_tau):
    t = np.arange(n) / SR
    e = np.exp(-t / d_tau)
    if a > 0:
        e *= np.clip(t / a, 0, 1)
    return e


def lp(x, fc, order=4):
    return signal.sosfilt(signal.butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=4):
    return signal.sosfilt(signal.butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, f1, f2, order=3):
    return signal.sosfilt(signal.butter(order, [f1, f2], "band", fs=SR, output="sos"), x)


def reverb_ir(sec=2.4, damp=5500):
    n = int(sec * SR)
    t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], 1) * np.exp(-t / (sec / 5.5))[:, None]
    ir = np.stack([lp(ir[:, 0], damp), lp(ir[:, 1], damp)], 1)
    ir[:int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    return (ir / np.sqrt((ir ** 2).sum())).astype(np.float32)


def convolve_wet(x, ir):
    return np.stack([signal.fftconvolve(x[:, 0], ir[:, 0])[:len(x)], signal.fftconvolve(x[:, 1], ir[:, 1])[:len(x)]], 1)


# ---------------------------------------------------------------------------------- automation
def automation(points, n=N):
    """piecewise-linear (smoothed) level curve from [(t, v), ...]"""
    ts = np.array([p[0] for p in points])
    vs = np.array([p[1] for p in points])
    t = np.arange(n) / SR
    y = np.interp(t, ts, vs)
    k = int(0.35 * SR)
    ker = np.hanning(2 * k + 1)
    ker /= ker.sum()
    return np.convolve(np.pad(y, k, mode="edge"), ker, "valid")[:n].astype(np.float32)


# Section map (seconds on the main timeline) -> instrument levels.
#            t     pad  arp  bass kick hat  clap noise
SECTIONS = [
    (0.0,   .55, .00, .00, .00, .00, .00, 0),
    (3.0,   .60, .25, .00, .00, .00, .00, 0),
    (10.0,  .60, .45, .00, .00, .00, .00, 0),
    (14.0,  .62, .50, .00, .30, .20, .00, 0),
    (22.2,  .70, .65, .30, .40, .35, .00, 0),
    (25.2,  .80, .90, .95, .95, .75, .85, 0),    # drop on "Welcome to Mega Byte"
    (29.4,  .78, .90, .95, .95, .75, .85, 0),
    (30.6,  .50, .42, .48, .42, .18, .00, 0),    # screen-demo bed (S1)
    (58.0,  .50, .46, .50, .44, .22, .10, 0),
    (84.0,  .50, .50, .50, .46, .24, .12, 0),
    (108.0, .50, .40, .35, .30, .10, .00, 0),
    (113.0, .52, .30, .00, .00, .00, .00, 0),    # talking head, calmer
    (115.0, .40, .18, .00, .00, .00, .00, .55),  # noise story: tension
    (129.2, .45, .20, .00, .00, .00, .00, .20),
    (130.2, .55, .40, .40, .30, .10, .00, 0),
    (132.0, .52, .50, .50, .46, .24, .08, 0),    # screen-demo bed (S2)
    (154.0, .55, .55, .55, .50, .28, .12, 0),
    (163.0, .60, .60, .50, .50, .30, .40, 0),
    (165.9, .70, .75, .75, .75, .55, .55, 0),    # feature 03 lifts
    (172.5, .55, .50, .50, .46, .22, .10, 0),    # physical shots: steady
    (234.0, .50, .40, .30, .25, .10, .00, 0),
    (241.0, .55, .45, .35, .30, .14, .00, 0),
    (245.2, .70, .70, .70, .70, .45, .50, 0),    # CTA lift
    (253.0, .60, .55, .45, .45, .25, .20, 0),
    (258.5, .60, .50, .30, .20, .10, .00, 0),
    (263.0, .00, .00, .00, .00, .00, .00, 0),
]
INSTR = ["pad", "arp", "bass", "kick", "hat", "clap", "noise"]


def levels():
    out = {}
    for i, name in enumerate(INSTR):
        out[name] = automation([(s[0], s[1 + i]) for s in SECTIONS])
    return out


# ---------------------------------------------------------------------------------- instruments
CHORDS = [  # A minor: i - VI - III - VII (2 bars each)
    dict(root=33, notes=[57, 60, 64, 69, 72]),   # Am  (A1 bass; A3 C4 E4 A4 C5)
    dict(root=29, notes=[53, 57, 60, 65, 69]),   # F
    dict(root=36, notes=[55, 60, 64, 67, 72]),   # C
    dict(root=31, notes=[55, 59, 62, 67, 71]),   # G
]


def chord_at(bar):
    return CHORDS[(bar // 2) % 4]


def render_pad():
    buf = stereo()
    nbars = int(DUR / BAR) + 2
    for b in range(0, nbars, 2):
        ch = chord_at(b)
        t0 = b * BAR
        seg_len = 2 * BAR + 2.0
        n = int(seg_len * SR)
        t = np.arange(n) / SR
        lr = [np.zeros(n), np.zeros(n)]
        for k, m in enumerate(ch["notes"][:4]):
            f = mtof(m)
            for ch_i, dets in enumerate(([-9, 0, 8], [-6, 3, 11])):
                for d in dets:
                    lr[ch_i] += signal.sawtooth(2 * np.pi * f * 2 ** (d / 1200) * t + rng.uniform(0, 6.28))
        env = np.clip(t / 0.9, 0, 1) * np.where(t < 2 * BAR, 1, np.clip(1 - (t - 2 * BAR) / 2.0, 0, 1))
        for c in (0, 1):
            x = lp(lr[c] * env, 1500 + 900 * np.sin(2 * np.pi * (t0 + t) / 19.0), 2) if False else lp(lr[c] * env, 1400, 4)
            buf[int(t0 * SR):int(t0 * SR) + n, c] += (x[:max(0, N - int(t0 * SR))] * 0.035)[:max(0, N - int(t0 * SR))]
    return buf


def pluck(f, n, tau=0.16, bright=3600):
    t = np.arange(n) / SR
    x = signal.sawtooth(2 * np.pi * f * t) * 0.6 + signal.square(2 * np.pi * f * 1.003 * t) * 0.4
    return lp(x * np.exp(-t / tau), bright, 2)


def render_arp():
    buf = stereo()
    step = BEAT / 2  # 8th notes
    pattern = [0, 2, 1, 3, 2, 4, 3, 1]
    total = int(DUR / step)
    n = int(0.7 * SR)
    for i in range(total):
        t0 = i * step
        bar = int(t0 // BAR)
        ch = chord_at(bar)
        m = ch["notes"][pattern[i % 8] % len(ch["notes"])] + (12 if pattern[i % 8] >= 3 else 0)
        pan = -0.55 if i % 2 == 0 else 0.55
        add(buf, pluck(mtof(m), n), t0, 0.07 * (1.15 if i % 4 == 0 else 0.85), pan)
    # ping-pong delay (dotted 8th)
    d = int(BEAT * 0.75 * SR)
    wet = np.zeros_like(buf)
    for k, g in enumerate((0.38, 0.22, 0.12), start=1):
        wet[d * k:, 0] += buf[:-d * k, 1] * g if k % 2 else buf[:-d * k, 0] * g
        wet[d * k:, 1] += buf[:-d * k, 0] * g if k % 2 else buf[:-d * k, 1] * g
    return buf + wet


def render_bass():
    buf = stereo()
    nbars = int(DUR / BAR) + 1
    hits = [0.0, 1.5, 2.5, 3.0]  # beats inside a bar
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    for b in range(nbars):
        ch = chord_at(b)
        f = mtof(ch["root"] + 12)
        for hb in hits:
            x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * signal.sawtooth(2 * np.pi * f * t)
            x = lp(x, 700, 2) * env_ad(n, 0.006, 0.28)
            add(buf, x, b * BAR + hb * BEAT, 0.34, 0.0)
    return buf


def render_kick():
    buf = stereo()
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 42 + 95 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    k = np.sin(ph) * np.exp(-t / 0.16) + 0.4 * np.exp(-t / 0.004) * rng.standard_normal(n) * 0.2
    for i in range(int(DUR / BEAT)):
        add(buf, k, i * BEAT, 0.62)
    return buf


def render_hat():
    buf = stereo()
    n = int(0.25 * SR)
    noise = hp(rng.standard_normal(n), 7000, 4)
    closed = noise * env_ad(n, 0.0, 0.025)
    open_ = noise * env_ad(n, 0.0, 0.09)
    for i in range(int(DUR / (BEAT / 2))):
        t0 = i * BEAT / 2
        if i % 2 == 1:
            add(buf, open_, t0, 0.07, 0.25)
        else:
            add(buf, closed, t0, 0.04 if i % 4 else 0.05, -0.25)
        if i % 2 == 0:  # ghost 16th
            add(buf, closed, t0 + BEAT / 4, 0.022, 0.1)
    return buf


def render_clap():
    buf = stereo()
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 1100, 6500) * env_ad(n, 0.0, 0.11)
    x += 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    for bar in range(int(DUR / BAR) + 1):
        for b in (1, 3):
            add(buf, x, bar * BAR + b * BEAT, 0.20, 0.0)
    return buf


def render_noise():
    n = N
    x = rng.standard_normal(n)
    x = bp(x, 300, 1100, 2)
    t = np.arange(n) / SR
    pulse = 0.5 + 0.5 * np.sin(2 * np.pi * t / (BEAT * 2))
    x = x * (0.4 + 0.6 * pulse)
    out = np.stack([x, np.roll(x, 311)], 1) * 0.05
    return out.astype(np.float32)


# ---------------------------------------------------------------------------------- fx / sfx
def sweep_noise(dur, f0, f1, width=0.55, amp_shape="bell"):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    f, tt, Z = signal.stft(x, SR, nperseg=1024, noverlap=768)
    centers = np.geomspace(f0, f1, Z.shape[1])
    lf = np.log(np.maximum(f, 20))[:, None]
    mask = np.exp(-((lf - np.log(centers)[None, :]) ** 2) / (2 * width ** 2))
    _, y = signal.istft(Z * mask, SR, nperseg=1024, noverlap=768)
    y = y[:n]
    y = np.pad(y, (0, n - len(y)))
    u = np.linspace(0, 1, n)
    env = np.sin(np.pi * u) ** 1.6 if amp_shape == "bell" else u ** 2.2
    y = y * env
    return y / (np.abs(y).max() + 1e-9)


def whoosh(buf, t, dur=0.55, up=True, gain=0.5, pan=0.0):
    f0, f1 = (300, 5200) if up else (5200, 300)
    add(buf, sweep_noise(dur, f0, f1), t - dur * 0.35, gain, pan)


def impact(buf, t, gain=0.8, big=True):
    n = int(2.2 * SR)
    tt = np.arange(n) / SR
    f = 38 + 55 * np.exp(-tt / 0.12)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (0.9 if big else 0.45))
    crack = lp(rng.standard_normal(n), 2500, 2) * np.exp(-tt / 0.12) * 0.5
    x = boom + crack
    add(buf, x, t, gain)
    # reverse swell leading in
    m = int(0.55 * SR)
    sw = hp(rng.standard_normal(m), 600, 2) * (np.linspace(0, 1, m) ** 3)
    add(buf, sw, t - 0.55, 0.18 * gain)


def riser(buf, t0, t1, gain=0.5, snare_roll=True):
    dur = t1 - t0
    n = int(dur * SR)
    x = sweep_noise(dur, 250, 9000, width=0.7, amp_shape="ramp")
    tt = np.arange(n) / SR
    tone = np.sin(2 * np.pi * np.cumsum(180 * (2 ** (3 * tt / dur))) / SR) * (tt / dur) ** 2 * 0.25
    add(buf, x + tone, t0, gain)
    if snare_roll:
        m = int(0.18 * SR)
        s = bp(rng.standard_normal(m), 1500, 6500) * env_ad(m, 0, 0.05)
        t = t0
        interval = BEAT / 2
        while t < t1 - 0.05:
            add(buf, s, t, 0.12 * (0.4 + 0.6 * (t - t0) / dur), 0.0)
            interval = max(0.045, interval * 0.86)
            t += interval


def tap(buf, t, gain=0.20, pan=0.0):
    n = int(0.12 * SR)
    tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1450 * tt) * np.exp(-tt / 0.018) + 0.5 * np.sin(2 * np.pi * 2900 * tt) * np.exp(-tt / 0.01)
    x += lp(rng.standard_normal(n), 3000, 2) * np.exp(-tt / 0.004) * 0.4
    add(buf, x, t, gain, pan)


def pop(buf, t, gain=0.35, pan=0.0):
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    f = 380 + 700 * (1 - np.exp(-tt / 0.03))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.07)
    sp = (np.sin(2 * np.pi * 2637 * tt) + np.sin(2 * np.pi * 3322 * tt) * 0.6) * np.exp(-tt / 0.12) * 0.3
    add(buf, x + sp, t, gain, pan)


def chime(buf, t, gain=0.3, pan=0.0):
    n = int(1.6 * SR)
    tt = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt / d) for f, a, d in
            ((1318.5, 1.0, 0.55), (1760.0, 0.6, 0.45), (2637.0, 0.4, 0.3), (3951.0, 0.2, 0.2)))
    add(buf, x * 0.25, t, gain, pan)


def toggle(buf, t, gain=0.30):
    n = int(0.25 * SR)
    tt = np.arange(n) / SR
    f = 520 + 520 * np.clip(tt / 0.09, 0, 1)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.08)
    x += np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt / 0.01) * 0.4
    add(buf, x, t, gain)


def swish(buf, t, dur=0.3, gain=0.22, pan=0.0):
    add(buf, sweep_noise(dur, 900, 3800, width=0.5), t - 0.05, gain, pan)


def build_sfx():
    buf = stereo()
    tl = json.load(open(f"{HERE}/../data/timeline.json"))
    ev = tl["events"]
    # --- stinger
    riser(buf, 22.3, 25.3, gain=0.55)
    impact(buf, 25.3, gain=0.9)
    whoosh(buf, 25.15, 0.7, True, 0.35)
    whoosh(buf, 28.4, 0.7, False, 0.30, 0.3)   # logo flies to the corner
    # --- scene transitions
    for s in (scenes.S1, scenes.S2):
        whoosh(buf, s["t0"] + 0.1, 0.55, True, 0.42)
        whoosh(buf, s["t1"], 0.55, False, 0.36)
        for tp in s["taps"]:
            tap(buf, tp["t"], 0.16, pan=0.1)
        for sw in s["swipes"]:
            swish(buf, sw["t0"] + 0.1, 0.5, 0.2)
    toggle(buf, 77.55)
    toggle(buf, 152.10)
    # --- feature cards / hero titles
    for e in ev:
        if e["type"] == "hero":
            whoosh(buf, e["t0"] + 0.05, 0.4, True, 0.22)
        elif e["type"] == "scene":
            whoosh(buf, e["show_card_from"], 0.45, True, 0.22, -0.4)
        elif e["type"] == "badge":
            pop(buf, e["t0"] + 0.1, 0.22)
        elif e["type"] == "chip":
            tap(buf, e["t0"] + 0.05, 0.12)
        elif e["type"] == "recap":
            for it in e["items"]:
                pop(buf, it[2], 0.28)
        elif e["type"] in ("cta_like", "cta_share"):
            pop(buf, e["at"], 0.4)
            whoosh(buf, e["t0"] + 0.1, 0.35, True, 0.2)
        elif e["type"] == "cta_trio":
            whoosh(buf, e["t0"] + 0.1, 0.35, True, 0.2)
            for a in e["at"]:
                pop(buf, a, 0.38)
        elif e["type"] == "cta_sub":
            whoosh(buf, e["t0"] + 0.1, 0.35, True, 0.2)
            tap(buf, e["at"], 0.35)
            chime(buf, e["at"] + 0.05, 0.38)
    # --- small impacts / risers at story beats
    riser(buf, 126.9, 129.7, gain=0.30, snare_roll=False)
    impact(buf, 129.7, gain=0.45, big=False)
    riser(buf, 162.3, 165.9, gain=0.40)
    impact(buf, 165.9, gain=0.65)
    riser(buf, 243.0, 245.3, gain=0.30, snare_roll=False)
    impact(buf, 262.35, gain=0.35, big=False)
    # --- b-roll cutaways: soft air whooshes in/out
    for a, b in BROLL_TIMES:
        whoosh(buf, a, 0.4, True, 0.20, 0.2)
        whoosh(buf, b, 0.4, False, 0.16, -0.2)
    return buf


BROLL_TIMES = [  # (start, end) of full-screen cutaways -- kept in sync with edit/broll.py
]
try:
    from broll import CUTAWAYS  # noqa: E402
    BROLL_TIMES = [(c["t0"], c["t1"]) for c in CUTAWAYS]
except Exception:  # noqa: BLE001
    pass


# ---------------------------------------------------------------------------------- mix-down of the score
def build_music():
    lv = levels()
    pad, arp, bass, kick = render_pad(), render_arp(), render_bass(), render_kick()
    hat, clap, noise = render_hat(), render_clap(), render_noise()
    # kick side-chain pump on pad / arp / bass
    kenv = np.zeros(N, np.float32)
    tt = np.arange(int(BEAT * SR)) / SR
    shape = np.exp(-tt / 0.11).astype(np.float32)
    for i in range(int(DUR / BEAT)):
        i0 = int(i * BEAT * SR)
        seg = min(len(shape), N - i0)
        kenv[i0:i0 + seg] = np.maximum(kenv[i0:i0 + seg], shape[:seg])
    duck = (1 - 0.32 * kenv * np.minimum(1, lv["kick"] * 2.2))[:, None]
    ir = reverb_ir()
    wet_in = (pad * lv["pad"][:, None] + arp * lv["arp"][:, None])
    wet = convolve_wet(wet_in, ir)
    mix = (pad * lv["pad"][:, None] * 0.9 + arp * lv["arp"][:, None] * 0.8 + bass * lv["bass"][:, None]) * duck
    mix += kick * lv["kick"][:, None] + hat * lv["hat"][:, None] + clap * lv["clap"][:, None] + noise * lv["noise"][:, None]
    mix += wet * 0.55
    # tone: remove sub rumble, small dip in the speech-presence band so the voice stays clear
    sos = signal.butter(2, 38, "high", fs=SR, output="sos")
    mix = signal.sosfilt(sos, mix, axis=0)
    f0, q, gdb = 2400.0, 0.9, -3.5
    A = 10 ** (gdb / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]
    mix = signal.lfilter(b, a, mix, axis=0)
    # global fade-out on the last 3.2 s
    fade = np.ones(N, np.float32)
    k0, k1 = int((VIDEO_DUR - 3.2) * SR), int(VIDEO_DUR * SR)
    fade[k0:k1] = np.linspace(1, 0, k1 - k0) ** 1.5
    fade[k1:] = 0
    mix = mix * fade[:, None]
    return mix.astype(np.float32)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    m = build_music()
    pk = np.abs(m).max()
    m = m / pk * 0.89          # headroom; final level is set in the mixer relative to the voice
    sf.write(f"{out_dir}/music_bed.wav", m, SR, subtype="FLOAT")
    fx = build_sfx()
    fx = fx / max(np.abs(fx).max(), 1e-9) * 0.89
    sf.write(f"{out_dir}/sfx.wav", fx, SR, subtype="FLOAT")
    print("music peak before norm", round(float(pk), 3), "| sfx events done")


if __name__ == "__main__":
    main(sys.argv[1])
