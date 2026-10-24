#!/usr/bin/env python3
"""EDL + word timings -> timeline.json for the overlay engine (render/overlay.html).

Usage: build_timeline.py OUT.json [--upto SECONDS]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LOGO, ROOT, WORK, url  # noqa: E402
from edl import EDL  # noqa: E402

FPS = 30
FRAMES = os.path.join(WORK, "frames")


def find_word(words, text, after):
    for w in words:
        if w["start"] >= after and text.lower() in w["text"].lower():
            return w
    raise KeyError(text)


def build(upto=None):
    words = json.load(open(os.path.join(ROOT, "captions/words.json")))["words"]
    end = EDL["end_card"]
    total = round(end["start"] + end["length"], 3) if end else EDL["main_duration"]

    blocks = []
    for b in EDL["blocks"]:
        subs, prev_last = [], None
        for s in b["subs"]:
            n = sum(round((n1 - n0) * FPS) for n0, n1, _, _ in s["src"]) + 3
            d = os.path.join(FRAMES, s["id"])
            sub = {
                "id": s["id"], "start": s["n0"], "end": s["n1"], "count": n,
                "frames": url(os.path.join(d, "%05d.jpg")),
                "title": s.get("title"), "zoom": s.get("zoom"), "hl": s.get("hl"),
                "fadeIn": 0.22,
            }
            if prev_last:
                sub["prevFrame"] = prev_last
            prev_last = url(os.path.join(d, f"{n:05d}.jpg"))
            subs.append(sub)
        blocks.append({"id": b["id"], "start": b["start"], "end": b["end"], "exit": .5, "subs": subs})

    cta = []
    for c in EDL["cta"]:
        if c["type"] == "subscribe":
            w = find_word(words, c["word"], c["after"])
            start = round(w["start"] - c["clickAt"] + .1, 3)
            cta.append({"type": "subscribe", "start": start, "end": round(start + c["len"], 3),
                        "y": c["y"], "clickAt": c["clickAt"]})
        else:
            cta.append(dict(c))

    tl = {
        "fps": FPS, "duration": total, "logo": url(LOGO),
        "words": words, "blocks": blocks, "titles": EDL["titles"],
        "cta": cta, "toasts": EDL["toasts"],
        "end": {"start": end["start"], "captionsOff": end["start"] - .05, "lines": end["lines"]} if end else None,
    }
    if upto is not None:
        tl["duration"] = upto
        if tl["end"]:
            tl["end"]["start"] = max(tl["end"]["start"], upto + 1)   # never show the end card in a partial render
    return tl


if __name__ == "__main__":
    out = sys.argv[1]
    upto = float(sys.argv[sys.argv.index("--upto") + 1]) if "--upto" in sys.argv else None
    tl = build(upto)
    json.dump(tl, open(out, "w"))
    print(f"timeline: {tl['duration']}s, {len(tl['words'])} caption chunks, {len(tl['blocks'])} phone blocks, "
          f"{len(tl['cta'])} CTA events -> {out}")
