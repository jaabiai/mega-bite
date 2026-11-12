#!/usr/bin/env python3
"""Track hand-picked points on a moving object (e.g. a product held to the camera) so labels can stay pinned to it.

usage: track_points.py VIDEO SPEC.json OUT.json [--w 960]

SPEC.json: [{"name": "lens", "t0": 30.2, "t1": 34.0, "x": 0.41, "y": 0.62}, ...]   (x, y normalised to the frame)
OUT.json:  {"fps": 30, "points": {"lens": {"t0": .., "xy": [[x, y, ok], ...]}}}   one entry per frame from t0 to t1

Pyramidal Lucas-Kanade on a small patch of features around the seed point; each frame the patch is re-seeded from
good features near the tracked centre, a forward-backward check drops bad tracks and the centre moves by the median
flow.  When too few features survive, the point holds its last position and ok = 0.
"""
import argparse, json, subprocess
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("spec")
ap.add_argument("out")
ap.add_argument("--w", type=int, default=960)
ap.add_argument("--fps", type=float, default=30.0)
args = ap.parse_args()

spec = json.load(open(args.spec))
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", args.video], capture_output=True, text=True).stdout.strip().split(",")
SW, SH = int(probe[0]), int(probe[1])
W = args.w
H = int(round(W * SH / SW / 2) * 2)
LK = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))


def frames(t0, t1):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", args.video, "-t", f"{t1 - t0:.3f}",
                          "-vf", f"fps={args.fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W)
    p.wait()


def seed(gray, c, r):
    m = np.zeros_like(gray)
    cv2.circle(m, (int(c[0]), int(c[1])), int(r), 255, -1)
    pts = cv2.goodFeaturesToTrack(gray, maxCorners=60, qualityLevel=0.01, minDistance=4, mask=m)
    return pts


out = {"fps": args.fps, "points": {}}
for s in spec:
    c = np.array([s["x"] * W, s["y"] * H], np.float32)
    r = s.get("r", 0.05) * W
    xy, prev, pts = [], None, None
    for g in frames(s["t0"], s["t1"]):
        ok = 1
        if prev is None:
            pts = seed(g, c, r)
        else:
            if pts is None or len(pts) < 6:
                pts = seed(prev, c, r)
            if pts is not None and len(pts) >= 4:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None, **LK)
                back, st2, _ = cv2.calcOpticalFlowPyrLK(g, prev, nxt, None, **LK)
                fb = np.linalg.norm((pts - back).reshape(-1, 2), axis=1)
                good = (st.ravel() == 1) & (st2.ravel() == 1) & (fb < 1.0)
                if good.sum() >= 4:
                    d = (nxt - pts).reshape(-1, 2)[good]
                    c = c + np.median(d, axis=0)
                    pts = seed(g, c, r)
                else:
                    ok, pts = 0, None
            else:
                ok = 0
        c = np.clip(c, [0, 0], [W - 1, H - 1])
        xy.append([round(float(c[0] / W), 4), round(float(c[1] / H), 4), ok])
        prev = g
    out["points"][s["name"]] = {"t0": s["t0"], "xy": xy}
    lost = sum(1 for v in xy if not v[2])
    print(f"{s['name']}: {len(xy)} frames, {lost} lost", flush=True)
json.dump(out, open(args.out, "w"))
