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
ap.add_argument("--size", default="1920x1080", help="WxH of the video (use 1080x1920 for the reel)")
ap.add_argument("--pattern", default=None, help="regex of private strings (default: the Google-history video's e-mails / names)")
ap.add_argument("--list", action="store_true", help="print every distinct OCR text instead of only matches")
ap.add_argument("--crop-x", type=int, default=700, help="ignore the left part (our own captions) – 0 for the reel")
args = ap.parse_args()
W, H = (int(v) for v in args.size.split("x"))
PAT = re.compile(args.pattern or r"@|gmail|\.com|raabso|jabir|varikkodan|ibbc|hameed|belly|laughs|megabyte1|jafareasy|mysrh|jaabi|newses", re.I)
seen = set()
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
    fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)[:, args.crop_x:]          # phone area only (captions are English text we wrote)
    res, _ = ocr(fr)
    t = args.t0 + i * args.step
    for box, text, conf in (res or []):
        if args.list and text not in seen:
            seen.add(text)
            print(f"t={t:6.2f}  '{text}'", flush=True)
        if PAT.search(text):
            hits += 1
            print(f"t={t:6.2f}  conf={float(conf):.2f}  '{text}'", flush=True)
    i += 1
print(f"scanned {i} frames, {hits} suspicious text hits")
