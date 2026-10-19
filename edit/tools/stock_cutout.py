"""Cut the person out of a licence-free stock photo (RVM matte, single image) -> RGBA PNG for the thumbnail page.

RVM is a video matting model: the still is fed `warm` times so its recurrent state settles, the last alpha is used.
Alpha: soft threshold + 1 px erosion + light feather; colour: despill of the old backdrop colour on semi-transparent edges.

usage: stock_cutout.py <photo.jpg> <rvm.onnx> <out.png> [warm=8] [despill=none|teal|blue] [keep_polygon]

keep_polygon: on a black-backdrop photo the matte mistakes a dark object (the black phone) for backdrop; the polygon
("x,y;x,y;..." in full-res pixels) is forced opaque.
"""
import sys

import cv2
import numpy as np
import onnxruntime as ort


def main(photo, model, out_path, warm=8, despill="none", lumakey=""):
    img = cv2.imread(photo)
    h, w = img.shape[:2]
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    t = (rgb.astype(np.float16) / 255).transpose(2, 0, 1)[None]
    st = [np.zeros((1, 1, 1, 1), np.float16) for _ in range(4)]
    ds = np.array([0.4 if max(h, w) > 1400 else 0.6], np.float32)
    pha = None
    for _ in range(int(warm)):
        _, pha, *st = sess.run(None, {"src": t, "r1i": st[0], "r2i": st[1], "r3i": st[2], "r4i": st[3], "downsample_ratio": ds})
    a = np.clip(pha[0, 0].astype(np.float32), 0, 1)
    a = np.clip((a - 0.05) / 0.90, 0, 1)
    a = cv2.erode(a, np.ones((3, 3), np.uint8), iterations=1)
    a = cv2.GaussianBlur(a, (0, 0), 0.8)
    pix = img.astype(np.float32)
    if lumakey:                       # polygon "x,y;x,y;..." (full-res px) kept fully opaque (dark phone on a black backdrop)
        pts = np.array([[int(v) for v in pt.split(",")] for pt in lumakey.split(";")], np.int32)
        m = np.zeros((h, w), np.float32)
        cv2.fillPoly(m, [pts], 1.0)
        m = cv2.GaussianBlur(m, (0, 0), 1.2)
        a = np.maximum(a, m)
    if despill != "none":
        edge = ((a > 0.02) & (a < 0.98)).astype(np.float32)
        edge = np.clip(cv2.GaussianBlur(cv2.dilate(edge, np.ones((9, 9), np.uint8)), (0, 0), 3.0) * 1.6, 0, 1)[:, :, None]
        b, g, r = pix[:, :, 0], pix[:, :, 1], pix[:, :, 2]
        if despill == "teal":                       # backdrop was teal: clamp blue/green to the red level on the edge
            g2, b2 = np.minimum(g, r * 1.05 + 6), np.minimum(b, r * 1.05 + 6)
        else:
            g2, b2 = g, np.minimum(b, np.maximum(r, g) * 1.05 + 6)
        e = edge[:, :, 0]
        pix = np.dstack([b * (1 - e) + b2 * e, g * (1 - e) + g2 * e, r])
    ys, xs = np.where(a > 0.05)
    x0, x1, y0, y1 = max(xs.min() - 6, 0), min(xs.max() + 6, w - 1), max(ys.min() - 6, 0), min(ys.max() + 6, h - 1)
    rgba = np.dstack([np.clip(pix, 0, 255).astype(np.uint8), (a * 255 + 0.5).astype(np.uint8)])[y0:y1 + 1, x0:x1 + 1]
    cv2.imwrite(out_path, rgba)
    print(out_path, rgba.shape, "crop", (x0, y0, x1, y1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], *(sys.argv[4:7]))
