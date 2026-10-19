"""Cut the speaker out of a graded base frame for a thumbnail: <base frame> + <full-res alpha> -> RGBA PNG.

* alpha: soft threshold, 1 px erosion (drops the blurred-background fringe), light feather
* picture: mild local contrast + sharpening (the frame is shown at ~1x, a little punch helps at thumbnail size)

usage: thumb_prep.py <base.mp4> <alpha_dir> <out_dir> <frame> [frame ...]
"""
import os
import subprocess
import sys

import cv2
import numpy as np

FPS = 30


def main(base, alpha_dir, out_dir, *frames):
    os.makedirs(out_dir, exist_ok=True)
    for n in map(int, frames):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{n / FPS:.5f}", "-i", base, "-frames:v", "1", "-f", "rawvideo",
                              "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        img = np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3).copy()
        a = cv2.imread(f"{alpha_dir}/alpha_{n:05d}.png", cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
        a = np.clip((a - 0.06) / 0.88, 0, 1)
        a = cv2.erode(a, np.ones((3, 3), np.uint8), iterations=1)
        a = cv2.GaussianBlur(a, (0, 0), 0.9)
        # local contrast on luminance, then unsharp
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(6, 6)).apply(lab[:, :, 0])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        blur = cv2.GaussianBlur(img, (0, 0), 1.6)
        img = cv2.addWeighted(img, 1.55, blur, -0.55, 0)
        ys, xs = np.where(a > 0.05)
        x0, x1, y0, y1 = max(xs.min() - 8, 0), min(xs.max() + 8, 1919), max(ys.min() - 8, 0), 1079
        rgba = np.dstack([img, (a * 255 + 0.5).astype(np.uint8)])[y0:y1 + 1, x0:x1 + 1]
        cv2.imwrite(f"{out_dir}/person_{n:05d}.png", rgba)
        print(n, "crop", (x0, y0, x1, y1), "->", rgba.shape, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
