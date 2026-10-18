"""Render every B-roll cutaway to a 1920x1080 / 30 fps clip of exactly the planned length.

 * graded to sit with the main footage (contrast, warm highlights, vignette)
 * slow push-in (sub-pixel, no jitter)
 * portrait clips are placed on a blurred, darkened fill with a rounded amber-edged frame
usage: prep_broll.py <src_dir> <out_dir>
"""
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from broll import CUTAWAYS  # noqa: E402

W, H, FPS = 1920, 1080, 30
GRADE = ("eq=contrast=1.07:saturation=1.06:gamma=0.98,"
         "curves=master='0/0 0.18/0.155 0.5/0.51 0.84/0.86 1/0.97',"
         "colorbalance=rs=-0.02:bs=0.035:rm=0.02:bm=-0.015:rh=0.03:bh=-0.03")


def rounded(w, h, r, ss=3):
    m = np.zeros((h * ss, w * ss), np.uint8)
    cv2.rectangle(m, (r * ss, 0), (w * ss - r * ss, h * ss), 255, -1)
    cv2.rectangle(m, (0, r * ss), (w * ss, h * ss - r * ss), 255, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (cx * ss, cy * ss), r * ss, 255, -1, cv2.LINE_AA)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255


VIG = None


def vignette():
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
        VIG = (1 - 0.30 * np.clip(d - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
    return VIG


def decode(path, src_in, n, vf):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{src_in:.3f}", "-i", path, "-frames:v", str(n),
           "-vf", f"fps={FPS},{vf}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)


def render(c, src_dir, out):
    n = int(round((c["t1"] - c["t0"]) * FPS))
    path = f"{src_dir}/{c['id']}.mp4"
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    sw, sh = int(info[0]), int(info[1])
    portrait = sh > sw
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "13",
                            "-g", "30", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", out], stdin=subprocess.PIPE)
    z0, z1 = c["zoom"]
    if not portrait:
        # work at 2112x1188 so the push-in never upsamples a lot
        ww, wh = 2112, 1188
        dec = decode(path, c["src_in"], n, f"{GRADE},scale={ww}:{wh}:flags=lanczos")
        fs = ww * wh * 3
        for i in range(n):
            buf = dec.stdout.read(fs)
            if len(buf) < fs:
                break
            fr = np.frombuffer(buf, np.uint8).reshape(wh, ww, 3)
            z = (z0 + (z1 - z0) * i / max(n - 1, 1)) * (W / ww)
            M = np.array([[z, 0, W / 2 - z * ww / 2], [0, z, H / 2 - z * wh / 2]], np.float32)
            img = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            img = (img.astype(np.float32) * vignette()).clip(0, 255).astype(np.uint8)
            enc.stdin.write(img.tobytes())
    else:
        fw, fh = 608, 1080  # foreground frame (portrait)
        dec = decode(path, c["src_in"], n, f"{GRADE},scale={fw + 40}:{int((fw + 40) * sh / sw)}:flags=lanczos")
        pw = fw + 40
        ph = int(pw * sh / sw)
        fs = pw * ph * 3
        mask = rounded(fw, fh, 38)
        for i in range(n):
            buf = dec.stdout.read(fs)
            if len(buf) < fs:
                break
            fr = np.frombuffer(buf, np.uint8).reshape(ph, pw, 3)
            # blurred fill
            big = cv2.resize(fr, (W, int(W * ph / pw)), interpolation=cv2.INTER_AREA)
            y0 = (big.shape[0] - H) // 2
            bg = cv2.GaussianBlur(big[y0:y0 + H], (0, 0), 28).astype(np.float32) * 0.42
            z = (z0 + (z1 - z0) * i / max(n - 1, 1)) * (fw / pw)
            M = np.array([[z, 0, fw / 2 - z * pw / 2], [0, z, fh / 2 - z * ph / 2]], np.float32)
            fg = cv2.warpAffine(fr, M, (fw, fh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
            x0 = (W - fw) // 2
            out_img = bg.copy()
            # soft shadow + amber rim
            sh_ = np.zeros((H, W, 1), np.float32)
            sh_[:, x0:x0 + fw] = mask
            sh_ = cv2.GaussianBlur(sh_, (0, 0), 22)[..., None] if sh_.ndim == 2 else cv2.GaussianBlur(sh_[..., 0], (0, 0), 22)[..., None]
            out_img *= (1 - 0.55 * sh_)
            rim = (mask - cv2.erode(mask[..., 0], np.ones((7, 7), np.uint8))[..., None]).clip(0, 1)
            reg = out_img[:, x0:x0 + fw]
            reg[:] = reg * (1 - mask) + fg * mask
            reg[:] = reg * (1 - rim * 0.9) + np.array([255, 184, 28], np.float32) * rim * 0.9
            out_img *= vignette()
            enc.stdin.write(out_img.clip(0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    return out


if __name__ == "__main__":
    src, outd = sys.argv[1:3]
    os.makedirs(outd, exist_ok=True)
    only = set(int(x) for x in sys.argv[3:])
    for c in CUTAWAYS:
        if only and c["id"] not in only:
            continue
        o = f"{outd}/cut_{c['id']}.mp4"
        render(c, src, o)
        print("done", o, flush=True)
