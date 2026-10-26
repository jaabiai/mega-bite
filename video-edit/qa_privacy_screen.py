#!/usr/bin/env python3
"""OCR sweep over the *cleaned* screen recording (every frame at 30 fps, half resolution).

usage: qa_privacy_screen.py screen_clean60.mp4 --s0 8 --t0 21 --t1 40     (s0 = recording time of the file's first frame)
"""
import argparse, re, subprocess
import numpy as np
from rapidocr_onnxruntime import RapidOCR

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--s0", type=float, default=8.0)
ap.add_argument("--t0", type=float, required=True)
ap.add_argument("--t1", type=float, required=True)
args = ap.parse_args()
W, H = 660, 1434
PAT = re.compile(r"@|gmail|\.com|raabso|jabir|varikkodan|ibbc|hameed|belly|laughs|megabyte1|jafareasy|mysrh|jaabi|newses", re.I)
ocr = RapidOCR()
p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(args.t0 - args.s0), "-t", str(args.t1 - args.t0), "-i", args.video,
                      "-vf", f"fps=30,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
i = hits = 0
while True:
    buf = p.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    res, _ = ocr(np.frombuffer(buf, np.uint8).reshape(H, W, 3))
    for box, text, conf in (res or []):
        if PAT.search(text):
            hits += 1
            print(f"S={args.t0 + i / 30:7.2f}  conf={float(conf):.2f}  '{text}'", flush=True)
    i += 1
print(f"scanned {i} frames, {hits} suspicious hits")
