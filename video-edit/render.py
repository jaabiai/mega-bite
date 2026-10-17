#!/usr/bin/env python3
"""Render driver.

  python render.py preview 5 47.5 ...        -> JPEG stills in $MB_WORK/preview/
  python render.py clip 44 52 out.mp4        -> silent test clip of a time range
  python render.py full [--workers 4]        -> full video (silent) in $MB_WORK/render/video.mp4
"""
import multiprocessing as mp
import os
import subprocess
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mbedit.common import WORK, FPS, NF, W, H          # noqa: E402

OUT = os.path.join(WORK, "render")


def _setup():
    import edl
    from mbedit.scenes import Ctx
    return edl.build(), Ctx()


def encoder(path, crf=18, preset="medium", threads=0):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-color_range", "tv", "-x264-params", "keyint=60:min-keyint=60:scenecut=0",
           "-threads", str(threads), "-movflags", "+faststart", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def preview(times):
    tl, ctx = _setup()
    os.makedirs(os.path.join(OUT, "../preview"), exist_ok=True)
    for t in times:
        i = int(round(float(t) * FPS))
        t0 = time.time()
        f = tl.frame(ctx, i)
        p = os.path.join(WORK, "preview", f"f_{float(t):07.2f}.jpg")
        cv2.imwrite(p, cv2.cvtColor(f, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{t}s -> {p}  ({(time.time()-t0)*1000:.0f} ms)", flush=True)
    ctx.close()


def sheet(times, name="sheet", cols=2, w=960):
    tl, ctx = _setup()
    tiles = []
    for t in times:
        i = int(round(float(t) * FPS))
        f = tl.frame(ctx, i)
        small = cv2.resize(f, (w, int(w * H / W)), interpolation=cv2.INTER_AREA)
        cv2.putText(small, f"{float(t):.2f}s", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2, cv2.LINE_AA)
        tiles.append(small)
    ctx.close()
    rows = []
    for k in range(0, len(tiles), cols):
        r = tiles[k:k + cols]
        while len(r) < cols:
            r.append(np.zeros_like(tiles[0]))
        rows.append(np.concatenate(r, 1))
    out = os.path.join(WORK, "preview", name + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cv2.imwrite(out, cv2.cvtColor(np.concatenate(rows, 0), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(out)


def render_range(a, b, path, crf=18, preset="medium", threads=0, quiet=False):
    tl, ctx = _setup()
    enc = encoder(path, crf, preset, threads)
    t0 = time.time()
    for i in range(a, b):
        enc.stdin.write(tl.frame(ctx, i).tobytes())
        if not quiet and (i - a) % 150 == 0:
            el = time.time() - t0
            print(f"[{a}-{b}] frame {i-a}/{b-a}  {(i-a+1)/max(el,1e-6):.2f} fps", flush=True)
    enc.stdin.close()
    enc.wait()
    ctx.close()


def clip(t0, t1, out):
    render_range(int(round(t0 * FPS)), int(round(t1 * FPS)), out, crf=20, preset="veryfast", threads=1)


def full(workers=4, crf=18, preset="medium", only=None):
    os.makedirs(OUT, exist_ok=True)
    per = (NF + workers - 1) // workers
    # chunk boundaries on whole seconds (60 frames) so every chunk starts on a keyframe boundary
    per = ((per + 59) // 60) * 60
    jobs = []
    for k in range(workers):
        a, b = k * per, min((k + 1) * per, NF)
        if a >= b:
            continue
        p = os.path.join(OUT, f"chunk_{k}.mp4")
        jobs.append((a, b, p))
    procs = [mp.Process(target=render_range, args=(a, b, p, crf, preset, 1)) for k, (a, b, p) in enumerate(jobs) if only is None or k in only]
    for pr in procs:
        pr.start()
    for pr in procs:
        pr.join()
    lst = os.path.join(OUT, "chunks.txt")
    with open(lst, "w") as f:
        for _, _, p in jobs:
            f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(OUT, "video.mp4")], check=True)
    print("done ->", os.path.join(OUT, "video.mp4"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "preview":
        preview(sys.argv[2:])
    elif cmd == "sheet":
        name = sys.argv[2]
        sheet([float(x) for x in sys.argv[3:]], name)
    elif cmd == "clip":
        clip(float(sys.argv[2]), float(sys.argv[3]), sys.argv[4])
    elif cmd == "full":
        w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
        only = [int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")] if "--only" in sys.argv else None
        full(workers=w, only=only)
