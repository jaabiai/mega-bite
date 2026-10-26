#!/usr/bin/env python3
"""OCR sweep of the finished video: flags any frame where an e-mail address / account name is still legible.

usage: qa_privacy.py video.mp4 [--t0 20 --t1 92 --step 0.2]
"""
import argparse, re, subprocess
import numpy as np
from rapidocr_onnxruntime import RapidOCR

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--t0", type=float, default=20.0)
ap.add_argument("--t1", type=float, default=92.0)
ap.add_argument("--step", type=float, default=0.2)
args = ap.parse_args()
W, H = 1920, 1080
PAT = re.compile(r"@|gmail|\.com|raabso|jabir|varikkodan|ibbc|hameed|belly|laughs|megabyte1|jafareasy|mysrh|jaabi|newses", re.I)
ocr = RapidOCR()
hits = 0
n = int(round((args.t1 - args.t0) / args.step))
fps = 1.0 / args.step
p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(args.t0), "-t", str(args.t1 - args.t0), "-i", args.video,
                      "-vf", f"fps={fps}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
i = 0
while True:
    buf = p.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)[:, 700:]          # phone area only (captions are English text we wrote)
    res, _ = ocr(fr)
    t = args.t0 + i * args.step
    for box, text, conf in (res or []):
        if PAT.search(text):
            hits += 1
            print(f"t={t:6.2f}  conf={float(conf):.2f}  '{text}'", flush=True)
    i += 1
print(f"scanned {i} frames, {hits} suspicious text hits")
