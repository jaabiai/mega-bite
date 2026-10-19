"""Voice clarity master: a voice that stays loud and clear on PHONE speakers / earbuds, not only on a meter.

Why: the recording is very bass-heavy (a deep voice + proximity effect in the car): ~83 % of the speech energy sits below
500 Hz and only ~7 % above 1 kHz. A phone speaker cannot reproduce that low band, so a track that measures loud
(LUFS counts the bass) still sounds quiet and muffled there. The fix is spectral, then level:

  1. high-pass 85 Hz                    (rumble / road noise: costs headroom, adds no loudness a listener hears)
  2. bell -5 dB @ 170 Hz, -2 dB @ 320   (the boom that masks the words)
  3. bell +4.5 dB @ 2.8 kHz, +3 dB @ 5 kHz, shelf +2 dB @ 9 kHz   (consonants = intelligibility = perceived loudness)
  4. slow RMS compressor (evens out loud / soft words)  +  fast compressor (cuts the short peaks = crest factor)
  5. make-up gain  ->  soft clipper above -6 dBFS (rounds the last few dB of peaks)  ->  look-ahead limiter (-2 dBFS)

Because the boom is gone the peaks are lower, so the same -1 dBFS ceiling carries a much higher RMS.
Stereo-linked processing; the original is never made quieter anywhere in the speech band.

usage: voice_clarity.py <in.wav> <out.wav> [makeup_db=16]
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_loudness as vl  # noqa: E402

SR = 48000


def _rbj(kind, f0, gain_db, q):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2 * q)
    if kind == "peak":
        b = [1 + al * a, -2 * cw, 1 - al * a]
        d = [1 + al / a, -2 * cw, 1 - al / a]
    elif kind == "hshelf":
        sq = 2 * np.sqrt(a) * al
        b = [a * ((a + 1) + (a - 1) * cw + sq), -2 * a * ((a - 1) + (a + 1) * cw), a * ((a + 1) + (a - 1) * cw - sq)]
        d = [(a + 1) - (a - 1) * cw + sq, 2 * ((a - 1) - (a + 1) * cw), (a + 1) - (a - 1) * cw - sq]
    else:
        raise ValueError(kind)
    return signal.tf2sos(np.array(b) / d[0], np.array(d) / d[0])


def eq_sos():
    parts = [signal.butter(4, 85, "highpass", fs=SR, output="sos"),
             _rbj("peak", 170, -5.0, 0.9),
             _rbj("peak", 320, -2.0, 0.9),
             _rbj("peak", 2800, 4.5, 0.9),
             _rbj("peak", 5000, 3.0, 1.0),
             _rbj("hshelf", 9000, 2.0, 0.7)]
    return np.vstack(parts)


def softclip(y, knee_db):
    t = 10 ** (knee_db / 20)
    a = np.abs(y)
    over = a > t
    out = y.copy()
    out[over] = np.sign(y[over]) * (t + (1 - t) * np.tanh((a[over] - t) / (1 - t)))
    return out


def process(x, makeup_db=16.0, knee_db=-6.0, ceiling_db=-2.0):
    y = signal.sosfilt(eq_sos(), x, axis=0)
    g1 = vl.compressor_gain_db(y, -27.0, 2.2, release=0.25, win_ms=40)
    y = y * (10 ** (g1 / 20))[:, None]
    g2 = vl.compressor_gain_db(y, -26.0, 4.0, attack=0.003, release=0.10, win_ms=6, knee=6.0)
    y = y * (10 ** ((g2 + makeup_db) / 20))[:, None]
    clipped = float(100 * (np.abs(y) > 10 ** (knee_db / 20)).mean())
    y = softclip(y, knee_db)
    lg = vl.limiter_gain(y, 10 ** (ceiling_db / 20))
    return (y * lg[:, None]).astype(np.float32), dict(softclip_pct=clipped, lim_max_db=float(-20 * np.log10(lg.min())),
                                                      lim_active_pct=float(100 * (lg < 0.94).mean()))


if __name__ == "__main__":
    inp, outp = sys.argv[1:3]
    mk = float(sys.argv[3]) if len(sys.argv) > 3 else 16.0
    x, sr = sf.read(inp, dtype="float64")
    assert sr == SR and x.ndim == 2
    y, st = process(x, mk)
    sf.write(outp, y, SR, subtype="PCM_24")
    print(f"makeup {mk} dB -> soft-clipped {st['softclip_pct']:.1f}% of samples, limiter max {st['lim_max_db']:.2f} dB "
          f"(>0.5 dB on {st['lim_active_pct']:.1f}%)")
