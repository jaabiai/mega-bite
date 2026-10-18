"""Reel audio: cut the (louder) voice at the two silent cut points, add the music bed segment and reel-specific SFX,
mix with mix_audio (voice first, music ~17 dB under, master limiter at -1 dBFS).

usage: reel_audio.py <scratch> <out.wav>
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
EDIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, EDIT)
import music_synth as ms  # noqa: E402
import mix_audio  # noqa: E402
import reel_plan as rp  # noqa: E402
import scenes  # noqa: E402

SR = 48000


def fade(x, n_in=0, n_out=0, power=1.0):
    x = x.copy()
    if n_in:
        x[:n_in] *= (np.linspace(0, 1, n_in) ** power)[:, None]
    if n_out:
        x[-n_out:] *= (np.linspace(1, 0, n_out) ** power)[:, None]
    return x


def build_sfx(n):
    buf = np.zeros((n, 2), np.float32)
    R = rp.r
    # hook
    ms.impact(buf, 0.22, gain=0.55, big=False)
    ms.whoosh(buf, 0.20, 0.55, True, 0.30)
    # B-roll cutaways: soft air whooshes in
    for c in rp.CUTS:
        ms.whoosh(buf, R(c["t0"]) + 0.02, 0.38, True, 0.20, 0.2)
    ms.whoosh(buf, R(rp.CUTS[2]["t1"]), 0.40, False, 0.18, -0.2)
    ms.whoosh(buf, R(rp.CUTS[5]["t1"]), 0.40, False, 0.18, -0.2)
    # title cards
    for t in (119.75, 123.20, 129.35, 154.95):
        ms.pop(buf, R(t) + 0.05, 0.16)
    # demo scene in/out + step cards + taps
    ms.whoosh(buf, R(rp.DEMO[0]) + 0.05, 0.55, True, 0.40)
    ms.whoosh(buf, R(rp.DEMO[1]), 0.50, False, 0.30)
    for t in (131.65, 133.45, 139.60, 144.30):
        ms.pop(buf, R(t) + 0.06, 0.22)
    for tp in scenes.S2["taps"]:
        ms.tap(buf, R(tp["t"]), 0.20, pan=0.1)
    ms.toggle(buf, R(152.10), 0.34)
    ms.pop(buf, R(151.00) + 0.06, 0.22)
    ms.chime(buf, R(152.12) + 0.04, 0.26)
    # result: riser into "ONLY YOUR VOICE", then impact
    ms.riser(buf, R(159.85), R(160.95), gain=0.34, snare_roll=False)
    ms.impact(buf, R(160.95), gain=0.55, big=False)
    # recap
    ms.pop(buf, R(165.90) + 0.1, 0.22)
    # end card
    ms.whoosh(buf, R(170.23) + 0.0, 0.55, True, 0.32)
    ms.tap(buf, 56.55, 0.34)
    ms.chime(buf, 56.58, 0.40)
    ms.chime(buf, 56.95, 0.20, pan=0.3)
    return buf


def main(scratch, out):
    voice, sr = sf.read(f"{scratch}/audio/main_voice_loud.wav", dtype="float32")
    music, _ = sf.read(f"{scratch}/audio_gen/music_bed.wav", dtype="float32")
    assert sr == SR
    s0 = int(round(rp.OFF * SR))
    s1 = int(round(rp.END_MAIN * SR))
    n_total = int(round(rp.N_FRAMES / rp.FPS * SR))
    v = np.zeros((n_total, 2), np.float32)
    seg = voice[s0:s1]
    v[:len(seg)] = fade(seg, n_in=int(0.04 * SR), n_out=int(0.03 * SR))
    m = fade(music[s0:s0 + n_total], n_in=int(0.30 * SR), n_out=int(2.0 * SR), power=1.5)
    sfx = build_sfx(n_total)
    sfx = sfx / max(np.abs(sfx).max(), 1e-9) * 0.89
    os.makedirs(f"{scratch}/reel/audio", exist_ok=True)
    sf.write(f"{scratch}/reel/audio/voice.wav", v, SR, subtype="FLOAT")
    sf.write(f"{scratch}/reel/audio/music.wav", m, SR, subtype="FLOAT")
    sf.write(f"{scratch}/reel/audio/sfx.wav", sfx, SR, subtype="FLOAT")
    mix_audio.main(f"{scratch}/reel/audio/voice.wav", f"{scratch}/reel/audio/music.wav", f"{scratch}/reel/audio/sfx.wav",
                   f"{EDIT}/data/reel_words.json", out, boost_t=-1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
