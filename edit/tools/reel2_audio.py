"""Reel v2 audio: the (louder) voice excerpts placed on the reel timeline + music slice + SFX, mixed with mix_audio.

The voice excerpts are cut at the deepest dip between two sentences (-44..-84 dB), so no click and no clipped word;
the pauses between excerpts are the recording's own (gated) silence.

usage: reel2_audio.py <scratch> <out.wav>
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
import reel2_plan as P  # noqa: E402

SR, FR = P.SR, P.FR
VOICE_FILE = os.environ.get("REEL_VOICE", "main_voice_loud.wav")    # main_voice_clear.wav = voice_clarity.py master
MUSIC_DB = float(os.environ.get("REEL_MUSIC_DB", "-17"))                    # music level under the speech
MASTER_CEILING = float(os.environ.get("REEL_CEILING", "0.891"))                 # master limiter ceiling (linear)
MUSIC_START = 25.0       # the "Welcome to Mega Byte" drop of the long video's bed -> the reel's hook lands on the drop


def fade(x, n_in=0, n_out=0, power=1.0):
    x = x.copy()
    if n_in:
        x[:n_in] *= (np.linspace(0, 1, n_in) ** power)[:, None]
    if n_out:
        x[-n_out:] *= (np.linspace(1, 0, n_out) ** power)[:, None]
    return x


def build_sfx(n, cues):
    buf = np.zeros((n, 2), np.float32)
    for c in cues:
        t, ty = c.get("t"), c["type"]
        g = c.get("gain", 0.3)
        if ty == "impact":
            ms.impact(buf, t, gain=g, big=c.get("big", False))
        elif ty == "whoosh":
            ms.whoosh(buf, t, c.get("dur", 0.5), c.get("up", True), g, c.get("pan", 0.0))
        elif ty == "pop":
            ms.pop(buf, t, g)
        elif ty == "swish":
            ms.swish(buf, t, c.get("dur", 0.4), g)
        elif ty == "tap":
            ms.tap(buf, t, g)
        elif ty == "toggle":
            ms.toggle(buf, t, g)
        elif ty == "chime":
            ms.chime(buf, t, g)
        elif ty == "riser":
            ms.riser(buf, c["t0"], c["t1"], gain=g, snare_roll=False)
    return buf


def main(scratch, out):
    L = P.load_layout()
    voice, sr = sf.read(f"{scratch}/audio/{VOICE_FILE}", dtype="float32")
    music, _ = sf.read(f"{scratch}/audio_gen/music_bed.wav", dtype="float32")
    assert sr == SR
    n = L["n_frames"] * FR
    v = np.zeros((n, 2), np.float32)
    for e in L["excerpts"]:
        seg = fade(voice[e["s0"]:e["s1"]], n_in=int(0.008 * SR), n_out=int(0.012 * SR))
        v[e["A"]:e["A"] + len(seg)] += seg
    m0 = int(MUSIC_START * SR)
    m = fade(music[m0:m0 + n], n_in=int(0.10 * SR), n_out=int(2.2 * SR), power=1.5)
    sfx = build_sfx(n, json.load(open(f"{EDIT}/data/{P.TAG}_sfx.json")))
    sfx = sfx / max(np.abs(sfx).max(), 1e-9) * 0.89
    d = f"{scratch}/{P.TAG}/audio"
    os.makedirs(d, exist_ok=True)
    sf.write(f"{d}/voice.wav", v, SR, subtype="FLOAT")
    sf.write(f"{d}/music.wav", m, SR, subtype="FLOAT")
    sf.write(f"{d}/sfx.wav", sfx, SR, subtype="FLOAT")
    mix_audio.main(f"{d}/voice.wav", f"{d}/music.wav", f"{d}/sfx.wav", f"{EDIT}/data/{P.TAG}_words.json", out,
                   boost_t=2.4, music_db=MUSIC_DB, ceiling=MASTER_CEILING)


if __name__ == "__main__":
    main(*sys.argv[1:3])
