"""Render the picture layers (shots) of reel v2 as 1080x1920 / 30 fps clips.

 spk / orig : frames of the graded base video, 9:16 layout (tracked speaker crop or fixed crop for the phone shots),
              frozen once the narration of the excerpt is over, optional blur/dim tail for the end card
 scene      : vertical iPhone demo for a main-timeline window (S1 miss-call reminder, S2 voice isolation)
 broll      : Mixkit stock clip, graded, slow push-in
Every shot can bake a push-in entrance (the chapter transition) into its first frames.

usage: reel2_shots.py <scratch> <shots.json> [shot ids ...]
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import reel_common as rc  # noqa: E402

FPS = 30
W, H = 1080, 1920
GRADE = ("eq=contrast=1.07:saturation=1.06:gamma=0.98,"
         "curves=master='0/0 0.18/0.155 0.5/0.51 0.84/0.86 1/0.97',"
         "colorbalance=rs=-0.02:bs=0.035:rm=0.02:bm=-0.015:rh=0.03:bh=-0.03")


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def entrance(img, k, spec):
    """push-in: the new shot starts 16 % enlarged and settles (baked into the first `fade` frames)"""
    n = max(spec.get("fade", 0), 1)
    if spec.get("entrance") != "zoom" or k >= n:
        return img
    s = 1 + 0.16 * (1 - ease_out(k / n))
    M = np.array([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def encoder(out):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "13", "-g", "30",
                             "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                             "-color_trc", "bt709", out], stdin=subprocess.PIPE)


def total_frames(spec):
    return spec["F1"] - spec["F0"] + spec["ext"]


# ---------------------------------------------------------------------------------------------- footage
def read_base(base, f0, n):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{f0 / FPS:.5f}", "-i", base, "-frames:v", str(n),
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    fs = 1920 * 1080 * 3
    while True:
        buf = p.stdout.read(fs)
        if len(buf) < fs:
            return
        yield np.frombuffer(buf, np.uint8).reshape(1080, 1920, 3)


def render_footage(spec, scratch, out):
    hx = np.load(f"{scratch}/work/headx_full.npy")
    hx = np.clip(ndimage.gaussian_filter1d(hx, 30, mode="nearest"), 380, 1540)
    total, nominal = total_frames(spec), spec["F1"] - spec["F0"]
    src_n, f0 = spec["src_n"], spec["src_f0"]
    z0, z1 = spec["zoom"]
    enc = encoder(out)
    frames = read_base(f"{scratch}/base/base.mp4", f0, src_n)
    last = None
    for n in range(total):
        if n < src_n:
            fr = next(frames, None)
            if fr is not None:
                last = fr
        fr = last
        idx = min(n, src_n - 1)
        z = z0 + (z1 - z0) * smooth(min(n / max(nominal - 1, 1), 1.0))
        cx = hx[min(f0 + idx, len(hx) - 1)] if spec.get("tracked") else spec["cx"]
        dark = 1.0
        tail = None
        if spec.get("tail") and n >= src_n:
            u = (n - src_n + 1) / max(total - src_n, 1)
            dark, tail = 1 - 0.55 * u, 22 * u
        img = rc.vertical_frame(fr, cx, z, grain_idx=spec["F0"] + n, dark=dark, fg_dy=spec.get("fg_dy", 0))
        if tail and tail > 0.5:
            img = cv2.GaussianBlur(img, (0, 0), tail)
        enc.stdin.write(np.ascontiguousarray(entrance(img, n, spec)).tobytes())
    enc.stdin.close()
    enc.wait()


# ---------------------------------------------------------------------------------------------- b-roll
def render_broll(spec, scratch, out):
    total, nominal = total_frames(spec), spec["F1"] - spec["F0"]
    path = f"{scratch}/broll/hd/{spec['clip']}.mp4"
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    sw, sh = int(info[0]), int(info[1])
    portrait = sh > sw
    ww, wh = (sw, sh) if portrait else (2400, 1350)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{spec['src_in']:.3f}", "-i", path, "-frames:v", str(total),
                            "-vf", f"fps={FPS},{GRADE},scale={ww}:{wh}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = encoder(out)
    z0, z1 = spec["zoom"]
    fs = ww * wh * 3
    last = None
    for n in range(total):
        buf = dec.stdout.read(fs)
        if len(buf) == fs:
            last = np.frombuffer(buf, np.uint8).reshape(wh, ww, 3)
        if last is None:
            break
        u = min(n / max(nominal - 1, 1), 1.0)
        z = z0 + (z1 - z0) * (u * u * (3 - 2 * u) * 0.35 + u * 0.65)
        if portrait:
            img = rc.portrait_frame(last, zoom=z, grain_idx=spec["F0"] + n)
        else:
            img = rc.vertical_frame(last, spec["cx"] * ww, z, grain_idx=spec["F0"] + n)
        enc.stdin.write(np.ascontiguousarray(entrance(img, n, spec)).tobytes())
    enc.stdin.close()
    enc.wait()


# ---------------------------------------------------------------------------------------------- iPhone demo
def render_scene(spec, scratch, out):
    import reel_scene as rs
    total = total_frames(spec)
    m0 = spec["m0"]
    cam = [tuple(k) for k in spec["camera"]]
    sc = rs.window_scene(spec["scene"], m0, m0 + total / FPS, cam, [dict(f) for f in spec.get("focus_extra", [])])
    sc.N = total
    enc = encoder(out)
    for n, img in enumerate(sc.frames()):
        enc.stdin.write(np.ascontiguousarray(entrance(img, n, spec)).tobytes())
    enc.stdin.close()
    enc.wait()


RENDER = {"spk": render_footage, "orig": render_footage, "broll": render_broll, "scene": render_scene}


def main(scratch, shots_json, *ids):
    shots = json.load(open(shots_json))
    os.makedirs(f"{scratch}/reel2/shots", exist_ok=True)
    for s in shots:
        if ids and s["id"] not in ids:
            continue
        out = f"{scratch}/reel2/shots/{s['id']}.mp4"
        RENDER[s["kind"]](s, scratch, out)
        print("done", s["id"], total_frames(s), "frames", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
