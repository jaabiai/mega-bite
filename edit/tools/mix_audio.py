"""Final audio: the voice track from the main video (made louder by voice_loudness.py, never quieter) + synthesised music + SFX.

* music sits ~17 dB under the speech and swells a few dB in the pauses (speech-activity from the aligned words)
* SFX are mixed above the music, below the voice
* a transparent master limiter (-1 dBFS ceiling, 4 ms ramps) keeps the sum from clipping after AAC encoding
* the screen-recording audio is never used anywhere in this pipeline

usage: mix_audio.py <voice_loud.wav> <music_bed.wav> <sfx.wav> <words.json> <out.wav>
"""
import json
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

SR = 48000


def activity_env(words, n):
    """smooth 0..1 'someone is speaking' envelope at SR"""
    hz = 200
    m = np.zeros(int(n / SR * hz) + 2, np.float32)
    for w in words:
        a, b = int((w["start"] - 0.10) * hz), int((w["end"] + 0.18) * hz)
        m[max(a, 0):b] = 1
    # close pauses shorter than 0.45 s
    m = ndimage.binary_closing(m > 0.5, structure=np.ones(int(0.45 * hz))).astype(np.float32)
    # asymmetric smoothing: fast attack (duck), slow release (swell back)
    out = np.zeros_like(m)
    ka, kr = 1 - np.exp(-1 / (0.10 * hz)), 1 - np.exp(-1 / (0.65 * hz))
    y = 0.0
    for i, x in enumerate(m):
        y += (ka if x > y else kr) * (x - y)
        out[i] = y
    t = np.arange(n) / SR
    return np.interp(t, np.arange(len(out)) / hz, out).astype(np.float32)


def lookahead_limiter(x, ceiling=0.97, hold=0.005, smooth=0.004):
    """transparent peak guard: gain dips only around samples that would exceed `ceiling` (smooth 4 ms ramps)"""
    peak = np.abs(x).max(axis=1)
    r = np.maximum(0.0, 1.0 - ceiling / np.maximum(peak, 1e-9)).astype(np.float32)   # required reduction (0..1)
    if r.max() <= 0:
        return np.ones(len(x), np.float32)
    w = int(hold * SR)
    rh = ndimage.maximum_filter1d(r, size=2 * w + 1, mode="nearest")
    k = np.hanning(2 * int(smooth * SR) + 1).astype(np.float32)
    k /= k.sum()
    rs = signal.fftconvolve(rh, k, mode="same").astype(np.float32)
    return (1.0 - np.maximum(rs, 0)).astype(np.float32)


def main(voice_p, music_p, sfx_p, words_p, out_p, boost_t=27.4):
    voice, sr = sf.read(voice_p, dtype="float32")
    assert sr == SR and voice.ndim == 2
    n = len(voice)
    music, _ = sf.read(music_p, dtype="float32")
    sfx, _ = sf.read(sfx_p, dtype="float32")
    music, sfx = music[:n], sfx[:n]
    words = json.load(open(words_p))["words"]

    act = activity_env(words, n)
    # level references from the voice itself
    gate = act > 0.8
    v_rms = np.sqrt((voice[gate] ** 2).mean())
    m_rms = np.sqrt((music[gate] ** 2).mean())
    target_speech = v_rms * 10 ** (-17.0 / 20)       # music 17 dB below the speech
    base = target_speech / m_rms
    swell_db = 3.5
    gain_m = base * (10 ** (swell_db / 20 * (1 - act)))
    # "Welcome to Mega Byte" drop and the finale get a little extra weight
    t = np.arange(n) / SR
    if boost_t >= 0:
        gain_m = gain_m * (1 + 0.42 * np.clip(1 - np.abs(t - boost_t) / 2.4, 0, 1))
    sfx_gain = 10 ** (-8.0 / 20) / max(np.abs(sfx).max(), 1e-9)

    others = music * gain_m[:, None] + sfx * sfx_gain
    mix = voice + others
    gr = lookahead_limiter(mix, ceiling=0.891)       # -1 dBFS master ceiling (smooth 4 ms ramps)
    out = mix * gr[:, None]
    red_db = -20 * np.log10(np.maximum(gr, 1e-6))
    print(f"voice speech RMS {20 * np.log10(v_rms):.1f} dBFS | music target {20 * np.log10(target_speech):.1f} dBFS")
    print(f"master limiter: max {red_db.max():.2f} dB, >0.5 dB on {100 * (red_db > 0.5).mean():.4f}% of samples")
    print("pre-limiter peak", np.abs(mix).max(), "post", np.abs(out).max())
    sf.write(out_p, out, SR, subtype="PCM_24")


if __name__ == "__main__":
    main(*sys.argv[1:6], *([float(sys.argv[6])] if len(sys.argv) > 6 else []))
