"""Shared 9:16 layout helpers for the reel.

Layout (1080x1920):
  * the picture is a 2:3 crop of the 16:9 frame scaled to 1080x1620 and placed at y=220 (feathered edges)
  * behind it: the same footage, cover-scaled, heavily blurred and darkened (classic "blurred fill")
  * soft dark gradients top and bottom keep the hook text and the captions readable
  * a touch of animated film grain on top
Portrait sources are used full-bleed.
"""
import cv2
import numpy as np

CW, CH = 1080, 1920
FG_H, FG_Y = 1620, 220
FPS = 30

_RNG = np.random.default_rng(11)
_GRAIN = [(_RNG.standard_normal((CH, CW)).astype(np.float32) * 2.6) for _ in range(6)]


def _feather():
    a = np.ones(FG_H, np.float32)
    top, bot = 110, 150
    a[:top] = np.sin(np.linspace(0, np.pi / 2, top)) ** 2
    a[-bot:] = np.cos(np.linspace(0, np.pi / 2, bot)) ** 2
    return a[:, None, None]


FEATHER = _feather()


def _gradients():
    y = np.arange(CH, dtype=np.float32)
    top = np.clip(1 - y / 470, 0, 1) ** 1.6 * 0.62
    bot = np.clip((y - 1130) / 790, 0, 1) ** 1.5 * 0.78
    g = np.clip(top + bot, 0, 0.9)[:, None, None]
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    d = np.hypot((xx - CW / 2) / (CW / 2), (yy - CH / 2) / (CH / 2))
    vig = (1 - 0.26 * np.clip(d - 0.55, 0, 1) ** 1.4)[..., None]
    return g, vig.astype(np.float32)


GRAD, VIG = _gradients()
NAVY = np.array([8, 9, 16], np.float32)


def crop_scale(src, x_center, y_center, crop_h, out_w, out_h):
    """sub-pixel crop (crop_h source rows tall, aspect = out_w/out_h) centred at (x_center, y_center) -> out_w x out_h"""
    s = out_h / crop_h
    x0 = x_center - out_w / s / 2
    y0 = y_center - crop_h / 2
    M = np.array([[s, 0, -x0 * s], [0, s, -y0 * s]], np.float32)
    return cv2.warpAffine(src, M, (out_w, out_h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)


def blurred_fill(src, x_center, y_center, crop_h):
    """cover-scale (9:16) of the same footage, blurred and darkened"""
    small = crop_scale(src, x_center, y_center, crop_h, 270, 480)
    small = cv2.GaussianBlur(small, (0, 0), 7)
    big = cv2.resize(small, (CW, CH), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    return big * 0.40 + NAVY * 0.10


def vertical_frame(src, x_center, zoom=1.0, y_center=None, grain_idx=0, dark=1.0, fg_dy=0):
    """landscape source (any size) -> finished 1080x1920 frame (uint8 RGB).
    fg_dy moves the picture up (<0) / down (>0), e.g. to lift a phone that sits at the bottom of the shot."""
    h = src.shape[0]
    yc = h / 2 if y_center is None else y_center
    crop_h = h / zoom
    fg = crop_scale(src, x_center, yc, crop_h, CW, FG_H).astype(np.float32)
    bg = blurred_fill(src, x_center, yc, min(crop_h * 1.0, h))
    out = bg.copy()
    y0 = FG_Y + int(fg_dy)
    a0, a1 = max(y0, 0), min(y0 + FG_H, CH)
    reg = out[a0:a1]
    fe = FEATHER[a0 - y0:a1 - y0]
    reg[:] = reg * (1 - fe) + fg[a0 - y0:a1 - y0] * fe
    out = out * (1 - GRAD) + NAVY * GRAD
    out *= VIG
    out += _GRAIN[grain_idx % len(_GRAIN)][..., None]
    if dark != 1.0:
        out *= dark
    return np.clip(out, 0, 255).astype(np.uint8)


def portrait_frame(src, x_center=None, zoom=1.0, grain_idx=0):
    """portrait source (e.g. 1080x1920) -> full-bleed 1080x1920 frame"""
    h, w = src.shape[:2]
    xc = w / 2 if x_center is None else x_center
    crop_h = min(h / zoom, w / zoom * CH / CW)
    img = crop_scale(src, xc, h / 2, crop_h, CW, CH).astype(np.float32)
    img = img * (1 - GRAD * 0.8) + NAVY * GRAD * 0.8
    img *= VIG
    img += _GRAIN[grain_idx % len(_GRAIN)][..., None]
    return np.clip(img, 0, 255).astype(np.uint8)
