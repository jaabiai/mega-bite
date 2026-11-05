#!/usr/bin/env python3
"""Track the presenter's face (centre x, y as fractions of the frame) with OpenCV's YuNet face detector.

usage: face_track.py main.mp4 yunet.onnx out.json [--step 0.25]      (YuNet: opencv_zoo face_detection_yunet_2023mar.onnx)
Writes {"t": [...], "x": [...], "y": [...]} smoothed with a slow follow so a crop driven by it moves like a camera operator.
"""
import argparse, json, subprocess
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("model"); ap.add_argument("out")
ap.add_argument("--step", type=float, default=0.25)
a = ap.parse_args()
w, h = 640, 360
det_ = cv2.FaceDetectorYN.create(a.model, "", (w, h), 0.6, 0.3, 5000)
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"fps={1 / a.step},scale={w}:{h}", "-f", "rawvideo",
                      "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
ts, xs, ys = [], [], []
i = 0
while True:
    buf = p.stdout.read(w * h * 3)
    if len(buf) < w * h * 3:
        break
    img = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    _, faces = det_.detect(img)
    t = i * a.step
    if faces is not None and len(faces):
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4]
        ts.append(t); xs.append(float((x + fw / 2) / w)); ys.append(float((y + fh / 2) / h))
    i += 1
ts, xs, ys = np.array(ts), np.array(xs), np.array(ys)
grid = np.arange(0, i * a.step, a.step)
gx, gy = np.interp(grid, ts, xs), np.interp(grid, ts, ys)
# median filter then a gentle two-way exponential follow (about 0.8 s)
def smooth(v, k=7, alpha=0.25):
    pad = np.pad(v, k // 2, mode="edge")
    med = np.array([np.median(pad[j:j + k]) for j in range(len(v))])
    f = med.copy()
    for j in range(1, len(f)):
        f[j] = f[j - 1] + alpha * (f[j] - f[j - 1])
    b = f.copy()
    for j in range(len(b) - 2, -1, -1):
        b[j] = b[j + 1] + alpha * (b[j] - b[j + 1])
    return b
json.dump({"t": grid.round(3).tolist(), "x": smooth(gx).round(4).tolist(), "y": smooth(gy).round(4).tolist()}, open(a.out, "w"))
print("detections", len(ts), "of", i, "x range", round(float(xs.min()), 3), round(float(xs.max()), 3), "median", round(float(np.median(xs)), 3))
