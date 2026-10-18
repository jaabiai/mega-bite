"""Render the reel's B-roll cutaways as 1080x1920 / 30 fps clips of the exact planned length (Ken-Burns push-in,
graded to match the main footage).  usage: reel_broll.py <src_dir> <out_dir> [ids...]"""
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import reel_common as rc  # noqa: E402
from reel_plan import CUTS, CHAIN_PAD, FPS  # noqa: E402

GRADE = ("eq=contrast=1.07:saturation=1.06:gamma=0.98,"
         "curves=master='0/0 0.18/0.155 0.5/0.51 0.84/0.86 1/0.97',"
         "colorbalance=rs=-0.02:bs=0.035:rm=0.02:bm=-0.015:rh=0.03:bh=-0.03")


def render(c, src_dir, out):
    dur = (c["t1"] - c["t0"]) + (CHAIN_PAD if c["chain"] else 0.0)
    n = int(round(dur * FPS))
    path = f"{src_dir}/{c['id']}.mp4"
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    sw, sh = int(info[0]), int(info[1])
    portrait = sh > sw
    # decode at a size that keeps the push-in sharp: landscape -> 2400x1350 work frame, portrait -> native
    ww, wh = (sw, sh) if portrait else (2400, 1350)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{c['src_in']:.3f}", "-i", path, "-frames:v", str(n),
                            "-vf", f"fps={FPS},{GRADE},scale={ww}:{wh}:flags=lanczos", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "13",
                            "-g", "30", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", out], stdin=subprocess.PIPE)
    z0, z1 = c["zoom"]
    fs = ww * wh * 3
    last = None
    for i in range(n):
        buf = dec.stdout.read(fs)
        if len(buf) == fs:
            last = np.frombuffer(buf, np.uint8).reshape(wh, ww, 3)
        if last is None:
            break
        u = i / max(n - 1, 1)
        z = z0 + (z1 - z0) * (u * u * (3 - 2 * u) * 0.35 + u * 0.65)
        if portrait:
            img = rc.portrait_frame(last, zoom=z, grain_idx=i)
        else:
            img = rc.vertical_frame(last, c["cx"] * ww, z, grain_idx=i)
        enc.stdin.write(img.tobytes())
    enc.stdin.close()
    enc.wait()
    return out


if __name__ == "__main__":
    src, outd = sys.argv[1:3]
    only = set(int(x) for x in sys.argv[3:])
    os.makedirs(outd, exist_ok=True)
    for c in CUTS:
        if only and c["id"] not in only:
            continue
        print("done", render(c, src, f"{outd}/rcut_{c['id']}.mp4"), flush=True)
