#!/usr/bin/env python3
"""Fit a fixed AssistiveTouch bubble as a radial translucent overlay, obs = m(r) * bg + b(r) per channel, from frames
where the background around the bubble is flat on some side (only those pixels are used).

usage: bubble_fit.py screen_sdr.mp4 spec.json out.npz [--preview out.jpg]
spec.json: {"fps": 30, "guess": [cx, cy], "r_max": 92,
            "frames": [{"t": 100.0, "keep": [[x0, y0, x1, y1], ...], "bg_box": [x0, y0, x1, y1]}, ...]}
`keep` boxes (full-frame px) select the pixels whose background is flat; `bg_box` is a patch of that same flat background
outside the bubble.  At least two frames with different background levels are needed.  The centre is refined on the
first frame from the bubble's outer edge.  The npz holds the un-mix maps over a box around the bubble (see screenprep).
"""
import argparse, json, subprocess
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("spec"); ap.add_argument("out")
ap.add_argument("--preview", default=None)
a = ap.parse_args()
spec = json.load(open(a.spec))
SW, SH = 1320, 2868


def grab(t):
    n = int(round(t * spec.get("fps", 30)))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"select=eq(n\\,{n})", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(SH, SW, 3).astype(np.float32)


frames = [(fr, grab(fr["t"])) for fr in spec["frames"]]
rmax = spec.get("r_max", 92)

# ---- centre from the outer edge on the first frame (bubble darker / lighter than the flat background) ----------
fr0, img0 = frames[0]
bg0 = np.median(img0[fr0["bg_box"][1]:fr0["bg_box"][3], fr0["bg_box"][0]:fr0["bg_box"][2]].reshape(-1, 3), axis=0)
gx, gy = spec["guess"]
pts = []
for x0, y0, x1, y1 in fr0["keep"]:
    sub = np.abs(img0[y0:y1, x0:x1] - bg0[None, None, :]).mean(-1) > 6
    for yy in range(sub.shape[0]):
        xs = np.nonzero(sub[yy])[0]
        if len(xs):
            pts.append((x0 + xs.max() + 0.5, y0 + yy))
    for xx in range(sub.shape[1]):
        ys = np.nonzero(sub[:, xx])[0]
        if len(ys):
            pts.append((x0 + xx, y0 + ys.min() - 0.5)); pts.append((x0 + xx, y0 + ys.max() + 0.5))
pts = np.array([p for p in pts if np.hypot(p[0] - gx, p[1] - gy) > 0.6 * rmax], np.float64)
A = np.c_[2 * pts[:, 0], 2 * pts[:, 1], np.ones(len(pts))]
sol, *_ = np.linalg.lstsq(A, (pts ** 2).sum(1), rcond=None)
cx, cy = sol[0], sol[1]
R = float(np.sqrt(sol[2] + cx * cx + cy * cy))
print(f"centre ({cx:.1f}, {cy:.1f})  radius {R:.1f}  from {len(pts)} edge points")

# ---- radial regression (closed form per radius bin), centre refined by a sub-pixel grid search ------------------
step = 0.25
samples = []
for fr, img in frames:
    bx = fr["bg_box"]
    bg = np.median(img[bx[1]:bx[3], bx[0]:bx[2]].reshape(-1, 3), axis=0)
    for x0, y0, x1, y1 in fr["keep"]:
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        samples.append((xx.ravel(), yy.ravel(), img[y0:y1, x0:x1].reshape(-1, 3), bg))
nb = int((R + 8) / step) + 1


def fit(cx, cy):
    S = np.zeros((5, nb, 3))
    for xx, yy, ob, bg in samples:
        k = np.minimum((np.hypot(xx - cx, yy - cy) / step).astype(int), nb - 1)
        for c in range(3):
            x = np.full(len(k), bg[c]); y = ob[:, c]
            S[0, :, c] += np.bincount(k, minlength=nb)
            S[1, :, c] += np.bincount(k, x, nb); S[2, :, c] += np.bincount(k, y, nb)
            S[3, :, c] += np.bincount(k, x * x, nb); S[4, :, c] += np.bincount(k, x * y, nb)
    n, sx, sy, sxx, sxy = S
    det = n * sxx - sx * sx
    ok = det > n * n * 400                                    # needs two clearly different background levels in the bin
    m = np.where(ok, (n * sxy - sx * sy) / np.where(ok, det, 1), 1.0)
    b = np.where(ok, (sy - m * sx) / np.where(n > 0, n, 1), 0.0)
    for c in range(3):
        idx = np.arange(nb)
        m[:, c] = np.interp(idx, idx[ok[:, c]], m[ok[:, c], c]); b[:, c] = np.interp(idx, idx[ok[:, c]], b[ok[:, c], c])
    err = 0.0
    for xx, yy, ob, bg in samples:
        k = np.minimum((np.hypot(xx - cx, yy - cy) / step).astype(int), nb - 1)
        err += ((ob - (m[k] * bg[None, :] + b[k])) ** 2).sum()
    return m.astype(np.float32), b.astype(np.float32), err


best = None
for dx in np.arange(-2.0, 2.01, 0.5):
    for dy in np.arange(-2.0, 2.01, 0.5):
        e = fit(cx + dx, cy + dy)[2]
        if best is None or e < best[0]:
            best = (e, cx + dx, cy + dy)
c0x, c0y = best[1], best[2]
for dx in np.arange(-0.5, 0.51, 0.125):
    for dy in np.arange(-0.5, 0.51, 0.125):
        e = fit(c0x + dx, c0y + dy)[2]
        if e < best[0]:
            best = (e, c0x + dx, c0y + dy)
cx, cy = best[1], best[2]
m_prof, b_prof, err = fit(cx, cy)
print(f"refined centre ({cx:.3f}, {cy:.3f})  rms residual {np.sqrt(err / sum(len(s[0]) * 3 for s in samples)):.2f}")
m_prof = np.clip(m_prof, 0.3, 1.0)
edge = int((R + 4) / step)
m_prof[edge:] = 1.0
b_prof[edge:] = 0.0
print("m at r=0,20,40,60,80:", [np.round(m_prof[int(r / step)], 3).tolist() for r in (0, 20, 40, 60, 80)])
print("b at r=0,20,40,60,80:", [np.round(b_prof[int(r / step)], 1).tolist() for r in (0, 20, 40, 60, 80)])

pad = int(R + 8)
X0, Y0 = int(max(cx - pad, 0)), int(max(cy - pad, 0))
X1, Y1 = int(min(cx + pad, SW)), int(min(cy + pad, SH))
yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
rr = np.hypot(xx - cx, yy - cy) / step
ar = np.arange(nb, dtype=np.float32)
oma = np.stack([np.interp(rr, ar, m_prof[:, c]) for c in range(3)], -1).astype(np.float32)
aC = np.stack([np.interp(rr, ar, b_prof[:, c]) for c in range(3)], -1).astype(np.float32)
np.savez_compressed(a.out, oma=oma, aC=aC, box=np.array([X0, Y0, X1, Y1]), centre=np.array([cx, cy, R]))
print("wrote", a.out)

if a.preview:
    tiles = []
    for fr, img in frames + [({"t": t}, grab(t)) for t in spec.get("check", [])]:
        roi = img[Y0 - 30:Y1 + 30, X0 - 30:X1 + 30].copy()
        cl = img.copy()
        cl[Y0:Y1, X0:X1] = np.clip((cl[Y0:Y1, X0:X1] - aC) / oma, 0, 255)
        tiles.append(np.vstack([roi, cl[Y0 - 30:Y1 + 30, X0 - 30:X1 + 30]]))
    cv2.imwrite(a.preview, cv2.cvtColor(np.hstack(tiles).astype(np.uint8), cv2.COLOR_RGB2BGR))
