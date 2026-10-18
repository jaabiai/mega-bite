"""Reel v2: find the exact cut points (samples) of every narration excerpt and the speaker's x-position track.

* cut points sit on the quietest 2 ms window of the gap between two sentences (every gap of this recording drops to
  -44..-84 dB, so a cut there is inaudible);
* head-x track: centroid of the person matte (top 36 % of the frame) for every frame of the main video.

usage: reel2_cuts.py <voice.wav> <matte_full.mkv> <out_cuts.json> <out_headx.npy>
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
EDIT = os.path.dirname(HERE)
sys.path.insert(0, EDIT)
from reel2_plan import EXCERPTS  # noqa: E402

SR = 48000
HOP = int(0.002 * SR)


def env(m, t0, t1):
    t0 = max(t0, 0.0)
    a, b = int(t0 * SR), int(t1 * SR)
    n = (b - a) // HOP
    x = m[a:a + n * HOP].reshape(n, HOP)
    return a / SR + np.arange(n) * HOP / SR, 20 * np.log10(np.sqrt((x ** 2).mean(axis=1)) + 1e-9)


def headx(matte, out):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", matte, "-vf", "scale=320:180,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float32) / 255
    head = a[:, :65, :]
    w = head.sum(axis=1)
    cx = (w * np.arange(320)).sum(axis=1) / np.maximum(w.sum(axis=1), 1e-6) * 6
    np.save(out, cx)
    return cx


def main(voice_p, matte_p, out_json, out_npy):
    v, sr = sf.read(voice_p, dtype="float32")
    assert sr == SR
    m = v.mean(axis=1)
    W = json.load(open(f"{EDIT}/data/words_aligned.json"))["words"]
    cuts = {}
    for ex in EXCERPTS:
        cs = ex["cues"]
        ws = [w for w in W if w["cue"] in cs]
        a, b = ws[0]["start"], ws[-1]["end"]
        prev = [w for w in W if w["cue"] < cs[0]]
        nxt = [w for w in W if w["cue"] > cs[-1]]
        pe = prev[-1]["end"] if prev else a - 0.3
        ns = nxt[0]["start"] if nxt else b + 0.3
        t, r = env(m, min(pe, a) - 0.05, a + 0.06)
        i = int(np.argmin(r))
        t2, r2 = env(m, b - 0.06, max(ns, b) + 0.05)
        j = int(np.argmin(r2))
        s0, s1 = int(round(t[i] * SR)), int(round(t2[j] * SR))
        cuts[ex["id"]] = {"s0": s0, "s1": s1, "min_db_start": round(float(r[i]), 1), "min_db_end": round(float(r2[j]), 1),
                          "first_word": ws[0]["start"], "last_word_end": ws[-1]["end"]}
        print(f"{ex['id']:8s} cut {s0 / SR:8.3f} -> {s1 / SR:8.3f}  ({(s1 - s0) / SR:5.2f} s)  dips {r[i]:6.1f} / {r2[j]:6.1f} dB")
    json.dump(cuts, open(out_json, "w"), indent=1)
    cx = headx(matte_p, out_npy)
    print("head-x track", cx.shape, "mean %.0f" % cx.mean())


if __name__ == "__main__":
    main(*sys.argv[1:5])
