"""Make the ORIGINAL voice louder (the only change made to the voice track in the whole pipeline).

chain:  soft-knee compressor (evens out the loud words)  ->  make-up gain  ->  look-ahead peak limiter (-1 dBFS)
Stereo-linked (one gain curve for both channels) so the picture of the voice does not move.

usage: voice_loudness.py <in.wav> <out.wav> [makeup_db=5.8] [threshold_db=-22] [ratio=2.0] [ceiling_dbfs=-1]
"""
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

SR = 48000
HOP = 48  # 1 ms gain-computer resolution


def compressor_gain_db(x, thr, ratio, knee=8.0, attack=0.030, release=0.250, win_ms=40):
    """per-sample gain in dB (<= 0). RMS detector (40 ms) on 1 ms frames, asymmetric smoothing.
    RMS (not peak) detection keeps the compressor gentle: it evens out loud words but leaves the short
    consonant peaks to the limiter, which is what keeps speech natural at higher loudness."""
    n = len(x)
    nf = n // HOP
    ms = (x[:nf * HOP] ** 2).mean(axis=1).reshape(nf, HOP).mean(axis=1)
    ms = ndimage.uniform_filter1d(ms, win_ms, mode="nearest")
    lvl = 10 * np.log10(np.maximum(ms, 1e-12))
    over = lvl - thr
    gr = np.zeros(nf)
    # soft knee static curve (reduction in dB, negative)
    hi = over > knee / 2
    mid = np.abs(over) <= knee / 2
    gr[hi] = (1 / ratio - 1) * over[hi]
    gr[mid] = (1 / ratio - 1) * (over[mid] + knee / 2) ** 2 / (2 * knee)
    ka = 1 - np.exp(-1 / (attack * 1000))
    kr = 1 - np.exp(-1 / (release * 1000))
    y = np.zeros(nf)
    s = 0.0
    for i in range(nf):                      # s is the (negative) applied reduction
        t = gr[i]
        s += (ka if t < s else kr) * (t - s)
        y[i] = s
    t_frames = (np.arange(nf) + 0.5) * HOP
    return np.interp(np.arange(n), t_frames, y)


def limiter_gain(x, ceiling, hold=0.005, smooth=0.004):
    """per-sample gain (<= 1) so that |x|*gain <= ceiling; smooth Hann ramps around the offending peaks"""
    peak = np.abs(x).max(axis=1)
    r = np.maximum(0.0, 1.0 - ceiling / np.maximum(peak, 1e-9))
    if r.max() <= 0:
        return np.ones(len(x))
    w = int(hold * SR)
    rh = ndimage.maximum_filter1d(r, size=2 * w + 1, mode="nearest")
    k = np.hanning(2 * int(smooth * SR) + 1)
    k /= k.sum()
    rs = signal.fftconvolve(rh, k, mode="same")
    # the smoothing can undershoot the needed reduction at the peak -> take the max of both
    rs = np.maximum(rs, 0)
    g = 1.0 - rs
    g = np.minimum(g, ceiling / np.maximum(peak, 1e-9))   # hard guarantee
    return g


def process(x, makeup_db=5.8, thr=-22.0, ratio=2.0, ceiling_db=-1.0):
    gr = compressor_gain_db(x, thr, ratio)
    y = x * (10 ** ((gr + makeup_db) / 20))[:, None]
    ceiling = 10 ** (ceiling_db / 20)
    lg = limiter_gain(y, ceiling)
    out = y * lg[:, None]
    stats = dict(comp_max_db=float(-gr.min()), comp_mean_active_db=float(-gr[gr < -0.5].mean()) if (gr < -0.5).any() else 0.0,
                 lim_max_db=float(-20 * np.log10(lg.min())), lim_active_pct=float(100 * (lg < 0.995).mean()))
    return out.astype(np.float32), stats


if __name__ == "__main__":
    inp, outp = sys.argv[1:3]
    mk = float(sys.argv[3]) if len(sys.argv) > 3 else 5.8
    thr = float(sys.argv[4]) if len(sys.argv) > 4 else -22.0
    ratio = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
    ceil = float(sys.argv[6]) if len(sys.argv) > 6 else -1.0
    x, sr = sf.read(inp, dtype="float64")
    assert sr == SR and x.ndim == 2
    y, st = process(x, mk, thr, ratio, ceil)
    sf.write(outp, y, SR, subtype="PCM_24")
    print(f"makeup {mk} dB thr {thr} ratio {ratio} -> compressor max {st['comp_max_db']:.1f} dB, "
          f"limiter max {st['lim_max_db']:.2f} dB on {st['lim_active_pct']:.3f}% of samples")
