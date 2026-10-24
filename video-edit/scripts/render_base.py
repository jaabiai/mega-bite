#!/usr/bin/env python3
"""Render the picture under the overlay: graded + framed presenter shots and B-roll.

The presenter footage keeps running under the phone scenes (the overlay covers it), so the
shot list in the EDL covers the whole timeline.  Every shot is rendered once into a cache
(<WORK>/base_segs) and the requested range is concatenated losslessly.

Usage: render_base.py OUT.mp4 [--from S] [--to S]
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import GRADE, MAIN, WORK, sh  # noqa: E402
from edl import EDL  # noqa: E402

FPS = 30
SEGS = os.path.join(WORK, "base_segs")
BROLL = os.path.join(WORK, "broll")
X264 = "-c:v libx264 -preset veryfast -crf 12 -pix_fmt yuv420p -r 30 -an -movflags +faststart"

# stock footage grade: calm it down so it sits with the presenter shots (slightly cooler/darker)
BROLL_GRADE = ("eq=saturation=0.92:contrast=1.06:brightness=-0.03,"
               "curves=all='0/0 0.12/0.10 0.5/0.52 0.88/0.88 1/0.96',unsharp=5:5:0.4:5:5:0.0")


def push_chain(dur, push, base_w=1920, base_h=1080):
    """Slow punch-in: scale up by `push` over the shot, then centre-crop back to 1080p."""
    if push <= 0:
        return f"scale={base_w}:{base_h}:flags=lanczos"
    d = max(dur, .1)
    return (f"scale=w='trunc({base_w}*(1+{push}*t/{d:.3f})/2)*2':h='trunc({base_h}*(1+{push}*t/{d:.3f})/2)*2':"
            f"eval=frame:flags=bicubic,crop={base_w}:{base_h}:(iw-{base_w})/2:(ih-{base_h})/2")


def talk_filter(shot, dur):
    z, cx, cy = shot["zoom"], shot["cx"], shot["cy"]
    pre = "setpts=PTS-STARTPTS"
    if z > 1.0:
        w = 1 / z
        x0 = min(max(cx - w / 2, 0), 1 - w)
        y0 = min(max(cy - w / 2, 0), 1 - w)
        pre += f",crop=iw*{w:.5f}:ih*{w:.5f}:iw*{x0:.5f}:ih*{y0:.5f}"
    return f"{pre},{push_chain(dur, shot.get('push', 0))},{GRADE}"


def broll_filter(shot, dur):
    return (f"setpts=PTS-STARTPTS,fps={FPS},scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            f"{push_chain(dur, shot.get('push', 0))},{BROLL_GRADE}")


def render_shot(shot, a, b):
    """Render [a, b) of an EDL shot (a/b already clipped to the shot)."""
    n = round(b * FPS) - round(a * FPS)          # frame-exact, no drift across shots
    dur = n / FPS
    key = hashlib.sha1(json.dumps([shot, round(a, 3), round(b, 3), GRADE, BROLL_GRADE], sort_keys=True).encode()).hexdigest()[:12]
    dst = os.path.join(SEGS, f"{key}.mp4")
    if os.path.exists(dst):
        return dst
    if shot["kind"] == "talk":
        src, ss, vf = MAIN, a, talk_filter(shot, dur)
    else:
        src, ss, vf = os.path.join(BROLL, shot["clip"] + ".mp4"), shot["ss"] + (a - shot["start"]), broll_filter(shot, dur)
    sh(f'ffmpeg -v error -y -ss {ss:.3f} -i "{src}" -vf "{vf}" -frames:v {n} {X264} "{dst}"')
    return dst


def main(out, t0, t1):
    os.makedirs(SEGS, exist_ok=True)
    parts = []
    for shot in EDL["base"]:
        a, b = max(shot["start"], t0), min(shot["end"], t1)
        if b - a < 1 / FPS:
            continue
        parts.append(render_shot(shot, a, b))
    lst = out + ".txt"
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    # padding after the last spoken frame (end card) is added in compose.py
    sh(f'ffmpeg -v error -y -f concat -safe 0 -i "{lst}" -c copy "{out}"')
    print(f"base {t0}-{t1}s: {len(parts)} shots -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=EDL["main_duration"])
    a = ap.parse_args()
    main(a.out, a.t0, a.t1)
