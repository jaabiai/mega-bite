"""Spectrogram review sheets: every line start (red, with id) + bar lines (white) over the vocal range."""
import os
import sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from specplot import plot, T

def make(timing_path, out_prefix, seg=20.0, pxs=96, fmax=4500, ends=True):
    d = json.load(open(timing_path, encoding="utf-8"))
    g = json.load(open(T + "work/beatgrid.json"))
    marks = []
    for l in d["lines"]:
        marks.append((l["start"], (255, 70, 70), l["id"]))
        if ends and l.get("end") is not None:
            marks.append((l["end"], (80, 200, 255), ""))
    t = 0.0; i = 0
    while t < 267.2:
        plot(t, min(267.2, t + seg), marks, f"{out_prefix}_{i:02d}.png", fmax=fmax, pxs=pxs, H=330, grid=(g["period"], g["phase"]))
        t += seg; i += 1
    return i

if __name__ == "__main__":
    print(make(sys.argv[1], sys.argv[2]))
