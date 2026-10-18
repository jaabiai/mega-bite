"""Reel speaker layer: tracked 9:16 crop of the graded base video for the reel's source range, plus a frozen,
progressively blurred/dimmed tail for the end card.

usage:
  reel_base.py render <base.mp4> <headx.npy> <out.mp4>
  reel_base.py still  <base.mp4> <headx.npy> <outdir> t1 t2 ...      (reel seconds)
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_common as rc  # noqa: E402

SRC0_F = 3445          # first source frame of the reel (114.8333 s)
SRC1_F = 5118          # last source frame + 1 (170.600 s)
TAIL_F = 52            # frames after the last word (1.733 s)
N_VOICE = SRC1_F - SRC0_F
N_TOTAL = N_VOICE + TAIL_F
W, H = 1920, 1080


def track(headx_path):
    hx = np.load(headx_path)[:N_VOICE + 5]
    hx = np.pad(hx, (0, max(0, N_VOICE - len(hx))), mode="edge")[:N_VOICE]
    hx = ndimage.gaussian_filter1d(hx, 40, mode="nearest")          # 1.3 s smoothing -> a slow, "operated" pan
    return np.clip(hx, 380, 1540)


def zoom_at(n):
    """slow push-in 1.00 -> 1.07 across the reel with a tiny ease"""
    u = n / (N_TOTAL - 1)
    return 1.0 + 0.07 * (u * u * (3 - 2 * u) * 0.5 + u * 0.5)


def read_frames(base, f0, n):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{f0 / 30:.5f}", "-i", base, "-frames:v", str(n),
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    fs = W * H * 3
    while True:
        buf = p.stdout.read(fs)
        if len(buf) < fs:
            return
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)


def render(base, headx, out):
    hx = track(headx)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                            "-r", "30", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-g", "30",
                            "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", out], stdin=subprocess.PIPE)
    last = None
    n = 0
    for fr in read_frames(base, SRC0_F, N_VOICE):
        img = rc.vertical_frame(fr, hx[n], zoom_at(n), grain_idx=n)
        enc.stdin.write(img.tobytes())
        last = (fr, hx[n])
        n += 1
        if n % 150 == 0:
            print(f"speaker {n}/{N_TOTAL}", flush=True)
    assert n == N_VOICE, n
    fr, x = last
    for k in range(TAIL_F):
        u = (k + 1) / TAIL_F
        img = rc.vertical_frame(fr, x, zoom_at(N_VOICE + k), grain_idx=N_VOICE + k, dark=1 - 0.55 * u)
        sig = 22 * u
        if sig > 0.5:
            img = cv2.GaussianBlur(img, (0, 0), sig)
        enc.stdin.write(img.tobytes())
    enc.stdin.close()
    enc.wait()
    print("done", out, N_TOTAL, "frames")


def still(base, headx, outdir, times):
    os.makedirs(outdir, exist_ok=True)
    hx = track(headx)
    for t in times:
        n = int(round(t * 30))
        k = min(n, N_VOICE - 1)
        fr = next(read_frames(base, SRC0_F + k, 1))
        img = rc.vertical_frame(fr, hx[k], zoom_at(n), grain_idx=n)
        cv2.imwrite(f"{outdir}/spk_{t:06.2f}.png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    if sys.argv[1] == "render":
        render(*sys.argv[2:5])
    else:
        still(sys.argv[2], sys.argv[3], sys.argv[4], [float(x) for x in sys.argv[5:]])
