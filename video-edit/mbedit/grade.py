"""Colour grade + smooth background blur for the talking-head footage.

All functions work on uint8 RGB numpy frames (H, W, 3) and a float32 person matte (H, W) in 0..1.
Everything heavy is done with cv2 uint8 ops / LUTs so a 1080p frame costs ~60-80 ms.
"""
import numpy as np
import cv2

H, W = 1080, 1920
_x = np.arange(256, dtype=np.float32) / 255.0


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- LUTs
def _curve(lift=0.015, contrast=0.16, hi_roll=0.10, gamma=1.0):
    """Filmic-ish S-curve with lifted blacks and a gentle highlight shoulder (0..1 -> 0..1)."""
    y = _x ** gamma
    s = y + contrast * (y - 0.5) * (1 - np.abs(2 * y - 1) ** 1.6)
    s = np.where(s > 0.80, 0.80 + (s - 0.80) * (1 - hi_roll * _smoothstep(0.8, 1.0, s) * 4), s)
    s = lift + s * (1 - lift)
    return np.clip(s, 0, 1)


def _tone(curve, shadow, high):
    """per-channel colour balance: add `shadow` (in 1/255) to shadows and `high` to highlights, by the channel's own value"""
    ws = 1 - _smoothstep(0.0, 0.55, curve)
    wh = _smoothstep(0.45, 1.0, curve)
    return np.clip(curve + (shadow * ws + high * wh) / 255.0, 0, 1)


def _lut_rgb(r, g, b):
    return np.stack([np.clip(r * 255 + 0.5, 0, 255), np.clip(g * 255 + 0.5, 0, 255), np.clip(b * 255 + 0.5, 0, 255)], -1).astype(np.uint8)


# Presenter look: brighter face, a touch of contrast, warm-neutral skin, slightly teal shadows
_base = _curve(lift=0.012, contrast=0.18, hi_roll=0.03, gamma=0.88)
FG_LUT = _lut_rgb(_tone(_base, -4, 5), _tone(_base, 2, 2), _tone(_base * 1.012, 8, -4))
# Background look: darker, cooler, lower contrast (pushes the blur back, harmonises with the blue brand colours)
_bgc = _curve(lift=0.02, contrast=0.12, hi_roll=0.30, gamma=1.02) * 0.97
BG_LUT = _lut_rgb(_bgc * 0.97, _bgc, np.clip(_bgc * 1.04, 0, 1))


def apply_lut(img, lut):
    out = np.empty_like(img)
    for c in range(3):
        out[..., c] = cv2.LUT(img[..., c], lut[:, c].copy())
    return out


def saturate(img, k):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    hsv[..., 1] = cv2.convertScaleAbs(hsv[..., 1], alpha=k)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def sharpen(img, amount=0.35, sigma=1.6):
    b = cv2.GaussianBlur(img, (0, 0), sigma)
    return cv2.addWeighted(img, 1 + amount, b, -amount, 0)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_v = 1.0 - 0.20 * np.clip((((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.66)) ** 2) - 0.25, 0, 1.2) ** 1.2
VIG_FULL = cv2.merge([(_v * 255).astype(np.uint8)] * 3)              # uint8 gain map (255 = unchanged)
VIG_SOFT = cv2.merge([(255 - (255 - _v * 255) * 0.7).astype(np.uint8)] * 3)


def vignette(img, soft=True):
    return cv2.multiply(img, VIG_SOFT if soft else VIG_FULL, scale=1 / 255.0)


# ---------------------------------------------------------------- matte handling
def _keep_zone():
    """soft 'keep sharp' zone at the bottom of the frame (phone / hands held close to the camera)"""
    top = _smoothstep(840, 905, _yy)
    left = _smoothstep(40, 170, _xx)
    right = 1 - _smoothstep(1330, 1470, _xx)
    return (top * left * right).astype(np.float32)


KEEP = _keep_zone()


def refine_matte(alpha, keep=1.0):
    """alpha float32 0..1 -> slightly choked + feathered alpha, unioned with the keep-sharp zone (strength `keep` 0..1)"""
    a = np.clip((alpha - 0.06) / 0.88, 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 1.0)
    if keep > 0.01:
        a = np.maximum(a, KEEP * keep)
    return a


def blurred_background_small(img, alpha, sigma_q=4.0):
    """Background-only (normalised convolution) blur at 1/4 res, float32 -> no colour bleed from the subject."""
    sh, sw = H // 4, W // 4
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA).astype(np.float32)
    a_s = cv2.resize(alpha, (sw, sh), interpolation=cv2.INTER_AREA)
    a_s = cv2.dilate(a_s, np.ones((5, 5), np.uint8))
    w = (1.0 - np.clip(a_s * 1.6, 0, 1))
    small = np.minimum(small, 208.0)                       # tame blown highlights so they don't bloom
    w3 = w[..., None]
    num = cv2.GaussianBlur(small * w3, (0, 0), sigma_q)
    den = cv2.GaussianBlur(w, (0, 0), sigma_q)[..., None]
    bg = num / np.maximum(den, 1e-3)
    wide = cv2.GaussianBlur(small, (0, 0), sigma_q * 3)
    conf = np.clip(den * 4, 0, 1)
    return bg * conf + wide * (1 - conf)


def grade_frame(rgb, alpha_raw, blur=True, sigma_q=4.0, keep=1.0):
    """Full treatment for one main-video frame. Returns uint8 RGB."""
    a = refine_matte(alpha_raw, keep)
    fg = apply_lut(rgb, FG_LUT)
    fg = saturate(fg, 1.12)
    fg = sharpen(fg, 0.30, 1.4)
    if not blur:
        return vignette(fg)
    # background: blur small -> grade small -> upscale
    bgs = np.clip(blurred_background_small(rgb, a, sigma_q), 0, 255).astype(np.uint8)
    bgs = saturate(apply_lut(bgs, BG_LUT), 1.05)
    bg = cv2.resize(bgs, (W, H), interpolation=cv2.INTER_CUBIC)
    a8 = np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)
    # decontaminate the foreground colour in the thin edge band only: F = (I - (1-a) B) / a
    ys, xs = np.nonzero((a8 > 5) & (a8 < 250))
    if len(ys):
        al = a[ys, xs][:, None]
        F = fg[ys, xs].astype(np.float32)
        B = bg[ys, xs].astype(np.float32)
        est = (F - (1 - al) * B) / np.maximum(al, 0.25)
        fg[ys, xs] = np.clip(0.6 * est + 0.4 * F, 0, 255).astype(np.uint8)
    a3 = cv2.merge([a8, a8, a8])
    out = cv2.add(cv2.multiply(fg, a3, scale=1 / 255.0), cv2.multiply(bg, cv2.bitwise_not(a3), scale=1 / 255.0))
    return vignette(out)
