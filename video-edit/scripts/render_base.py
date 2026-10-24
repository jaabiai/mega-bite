#!/usr/bin/env python3
"""Render the picture under the overlay: graded + framed presenter shots and B-roll.

The presenter footage keeps running under the phone scenes (the overlay covers it), so the
shot list in the EDL covers the whole timeline.  Every shot is rendered once into a cache
(<WORK>/base_segs) and the requested range is concatenated losslessly.

Usage: render_base.py OUT.mp4 [--from S] [--to S] [--layout wide|vertical]

Layouts: wide = 1920x1080.  vertical = 1080x1920 Reel: the presenter is cropped 9:16 out of the 4K frame
(face-centred); B-roll is shown as a full-width 16:9 band over a blurred, darkened copy of itself (a 1080p
clip cropped to 9:16 would be upscaled 1.8x and look soft).
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import GRADE, MAIN, WORK, sh  # noqa: E402
from edl import EDL, base_shots  # noqa: E402

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


def talk_filter(shot, dur, layout="wide"):
    z, cx, cy = shot["zoom"], shot["cx"], shot["cy"]
    pre = "setpts=PTS-STARTPTS"
    if layout == "vertical":                      # 9:16 window of the 3840x2160 frame, centred on the face
        h = int(2160 / z) // 2 * 2
        w = int(h * 9 / 16) // 2 * 2
        x0 = int(min(max(cx * 3840 - w / 2, 0), 3840 - w))
        y0 = int(min(max(cy * 2160 - h / 2, 0), 2160 - h))
        return f"{pre},crop={w}:{h}:{x0}:{y0},{push_chain(dur, shot.get('push', 0), 1080, 1920)},{GRADE}"
    if z > 1.0:
        w = 1 / z
        x0 = min(max(cx - w / 2, 0), 1 - w)
        y0 = min(max(cy - w / 2, 0), 1 - w)
        pre += f",crop=iw*{w:.5f}:ih*{w:.5f}:iw*{x0:.5f}:ih*{y0:.5f}"
    return f"{pre},{push_chain(dur, shot.get('push', 0))},{GRADE}"


def broll_filter(shot, dur):
    return (f"setpts=PTS-STARTPTS,fps={FPS},scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            f"{push_chain(dur, shot.get('push', 0))},{BROLL_GRADE}")


def broll_graph_vertical(shot, dur):
    """16:9 band (full width, 608 px tall) centred on a blurred copy of the clip; label [v]."""
    band = push_chain(dur, shot.get("push", 0), 1080, 608)
    return (f"[0:v]setpts=PTS-STARTPTS,fps={FPS},split=2[a][b];"
            f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=38,"
            f"eq=brightness=-0.20:saturation=1.15[bg];"
            f"[b]scale=1080:608:flags=lanczos,{band},{BROLL_GRADE}[fg];"
            f"[bg][fg]overlay=0:(H-h)/2:format=auto[v]")


def render_shot(shot, a, b, layout="wide"):
    """Render [a, b) of an EDL shot (a/b already clipped to the shot)."""
    n = round(b * FPS) - round(a * FPS)          # frame-exact, no drift across shots
    dur = n / FPS
    keyed = [shot, round(a, 3), round(b, 3), GRADE, BROLL_GRADE] + (["vertical"] if layout == "vertical" else [])
    key = hashlib.sha1(json.dumps(keyed, sort_keys=True).encode()).hexdigest()[:12]
    dst = os.path.join(SEGS, f"{key}.mp4")
    if os.path.exists(dst):
        return dst
    if shot["kind"] == "talk":
        sh(f'ffmpeg -v error -y -ss {a:.3f} -i "{MAIN}" -vf "{talk_filter(shot, dur, layout)}" -frames:v {n} {X264} "{dst}"')
    else:
        src, ss = os.path.join(BROLL, shot["clip"] + ".mp4"), shot["ss"] + (a - shot["start"])
        if layout == "vertical":
            sh(f'ffmpeg -v error -y -ss {ss:.3f} -i "{src}" -filter_complex "{broll_graph_vertical(shot, dur)}" -map "[v]" '
               f'-frames:v {n} {X264} "{dst}"')
        else:
            sh(f'ffmpeg -v error -y -ss {ss:.3f} -i "{src}" -vf "{broll_filter(shot, dur)}" -frames:v {n} {X264} "{dst}"')
    return dst


def main(out, t0, t1, layout="wide"):
    os.makedirs(SEGS, exist_ok=True)
    parts = []
    for shot in base_shots(layout):
        a, b = max(shot["start"], t0), min(shot["end"], t1)
        if b - a < 1 / FPS:
            continue
        parts.append(render_shot(shot, a, b, layout))
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
    ap.add_argument("--layout", default="wide", choices=["wide", "vertical"])
    a = ap.parse_args()
    main(a.out, a.t0, a.t1, a.layout)
