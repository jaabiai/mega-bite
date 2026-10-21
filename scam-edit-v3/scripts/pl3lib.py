import numpy as np, cv2
cv2.setNumThreads(2)


def nconv(rgb, w, sig):
    num = cv2.GaussianBlur(rgb * w[..., None], (0, 0), sig)
    den = cv2.GaussianBlur(w, (0, 0), sig)
    return num / np.maximum(den, 1e-4)[..., None], den


def person_layer(rgb, a, lo=0.10, hi=0.90, erode=1):
    """rgb float32 HxWx3 (0..1), a float32 HxW matte -> straight colour F (edge colours extended from the solid interior) and tightened alpha."""
    H, W = a.shape
    a = np.clip((a - lo) / (hi - lo), 0, 1)
    if erode:
        a = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * erode + 1, 2 * erode + 1)))
        a = cv2.GaussianBlur(a, (0, 0), 0.8)
    rs = cv2.resize(rgb, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    as_ = cv2.resize(a, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    solid = (as_ > 0.97).astype(np.uint8)
    solid = cv2.erode(solid, np.ones((5, 5), np.uint8))          # stay away from the edge band
    fi, den = nconv(rs, solid.astype(np.float32), 4.0)
    m = np.clip(den * 8, 0, 1)[..., None]
    fi = fi * m + cv2.GaussianBlur(rs, (0, 0), 8.0) * (1 - m)
    fi = cv2.resize(fi, (W, H), interpolation=cv2.INTER_LINEAR)
    # edge pixels clearly brighter than the solid colour next to them are old wall, not hair -> drop their alpha
    lum = lambda c: 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]
    k = np.clip((lum(rgb) - lum(fi) - 0.10) / 0.20, 0, 1)
    k = cv2.GaussianBlur(k, (0, 0), 1.0)
    a = a * (1 - k * (1 - np.clip((a - 0.97) / 0.03, 0, 1)))
    t = np.clip((a - 0.90) / 0.09, 0, 1)[..., None]
    t = t * t * (3 - 2 * t)
    F = fi * (1 - t) + rgb * t
    return np.clip(F, 0, 1), a
