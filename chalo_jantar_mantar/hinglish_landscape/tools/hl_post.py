"""Post-processing (bloom, anamorphic streaks, filmic grade, vignette, dither) and shot-to-shot transitions on float RGB images."""
import math
import numpy as np
from PIL import Image

from hl_common import *
import hl_scenes as SC

_VIG = {}
_NOISE = None


def vignette_mask(strength):
    key = round(strength, 2)
    if key not in _VIG:
        y, x = np.mgrid[0:WH, 0:WW].astype(np.float32)
        nx, ny = (x / WW - 0.5) * 2.0, (y / WH - 0.5) * 2.0
        r2 = (nx * nx * 0.85 + ny * ny * 1.15)
        _VIG[key] = np.clip(1.0 - strength * np.clip(r2, 0, 2.2) ** 1.25 * 0.5, 0.0, 1.0)[..., None].astype(np.float32)
    return _VIG[key]


def box_blur_h(a, k):
    """Horizontal box blur of width k via cumulative sums (a: h,w,3)."""
    k = max(1, int(k) | 1)
    pad = k // 2
    p = np.pad(a, ((0, 0), (pad + 1, pad), (0, 0)), mode="edge")
    c = np.cumsum(p, axis=1, dtype=np.float32)
    return (c[:, k:, :] - c[:, :-k, :]) / k


def _down(a, f):
    h, w = a.shape[:2]
    return a[:h // f * f, :w // f * f].reshape(h // f, f, w // f, f, 3).mean(axis=(1, 3))


def bloom(img, thresh=0.72, gain=0.30, streak=0.0, streak_len=41):
    """Multi-scale bloom + optional anamorphic streak, computed at 1/4 resolution and upscaled once."""
    q = _down(img, 4)                                          # 180 x 320
    hi = np.clip(q - thresh, 0, None)
    h2 = resize_f(_down(hi, 2), hi.shape[1], hi.shape[0], Image.BICUBIC)
    h4 = resize_f(_down(hi, 4), hi.shape[1], hi.shape[0], Image.BICUBIC)
    h8 = resize_f(_down(hi, 8), hi.shape[1], hi.shape[0], Image.BICUBIC)
    comb = (hi * 0.30 + h2 * 0.45 + h4 * 0.40 + h8 * 0.35) * gain * 3.0
    if streak > 0:
        hi2 = np.clip(q - (thresh + 0.15), 0, None)
        st = box_blur_h(box_blur_h(hi2, streak_len), streak_len)
        comb = comb + st * streak * C3(0.55, 0.75, 1.0) * 4.0
    return img + resize_f(comb, WW, WH, Image.BICUBIC)


def C3(r, g, b):
    return np.array([r, g, b], np.float32)


def aces(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)


def grade(img, g):
    """g: dict(exp, sat, contrast, shadow=(r,g,b), shadow_amt, high=(r,g,b), vig, fade, tint=(r,g,b))"""
    x = img * g.get("exp", 1.0)
    if "tint" in g:
        x = x * np.asarray(g["tint"], np.float32)
    x = aces(x)
    lum = (x @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    sat = g.get("sat", 1.0)
    x = lum + (x - lum) * sat
    sh = np.asarray(g.get("shadow", (0.0, 0.0, 0.0)), np.float32)
    x = x + sh * g.get("shadow_amt", 0.0) * (1 - lum) ** 2
    hi = np.asarray(g.get("high", (1.0, 1.0, 1.0)), np.float32)
    x = x * (1 + (hi - 1) * g.get("high_amt", 1.0) * lum)
    c = g.get("contrast", 1.0)
    if c != 1.0:
        x = 0.5 + (x - 0.5) * c
    f = g.get("fade", 0.0)
    if f:
        x = x * (1 - f) + f * 0.5 * np.asarray(g.get("fade_col", (0.4, 0.45, 0.6)), np.float32)
    x = x * vignette_mask(g.get("vig", 0.7))
    return np.clip(x, 0, 1)


def chroma(img, px):
    if px <= 0:
        return img
    out = img.copy()
    out[:, px:, 0] = img[:, :-px, 0]
    out[:, :-px, 2] = img[:, px:, 2]
    return out


def to_uint8_dither(x, rng):
    """Float 0..1 -> uint8 with triangular dither (kills banding in dark gradients)."""
    global _NOISE
    if _NOISE is None:
        r = np.random.RandomState(5)
        _NOISE = [((r.rand(WH, WW, 1) + r.rand(WH, WW, 1)) - 1.0).astype(np.float32) for _ in range(6)]
    n = _NOISE[int(rng) % len(_NOISE)]
    return np.clip(x * 255.0 + 0.5 + n * 0.9, 0, 255).astype(np.uint8)


def upscale(u8):
    return np.array(Image.fromarray(u8, "RGB").resize((W, H), Image.LANCZOS))


# ----------------------------------------------------------------------------------------------------------------------
# transitions (a, b float images at working res; p in 0..1)
# ----------------------------------------------------------------------------------------------------------------------
def transition(a, b, kind, p, t):
    p = clamp(p)
    if kind == "dissolve":
        k = smooth(p)
        return a * (1 - k) + b * k
    if kind == "flash":
        k = smooth(p)
        out = a * (1 - k) + b * k
        bump = math.exp(-((p - 0.5) / 0.16) ** 2)
        return out + bump * C3(1.0, 0.82, 0.55) * 0.9
    if kind == "dip":
        if p < 0.5:
            return a * (1 - smooth(p * 2))
        return b * smooth((p - 0.5) * 2)
    if kind == "smoke":
        n = SC.tex("s1").sample(t * 20, 0, WW // 2, WH // 2, 1.4)
        n2 = SC.tex("s2").sample(t * 11 + 50, 30, WW // 2, WH // 2, 2.6)
        nn = resize_f(0.6 * n + 0.4 * n2, WW, WH, Image.BILINEAR)
        thr = lerp(-0.15, 1.15, smooth(p))
        e = 0.14
        m = smoothstep(thr + e, thr - e, nn)[..., None]
        edge = np.exp(-((nn - thr) / (e * 0.8)) ** 2)[..., None]
        out = a * (1 - m) + b * m
        return out + edge * C3(1.0, 0.55, 0.18) * 0.55 * math.sin(math.pi * clamp(p))
    if kind == "whip":
        d = int(smooth(p) * WW)
        out = np.empty_like(a)
        if d <= 0:
            out[:] = a
        elif d >= WW:
            out[:] = b
        else:
            out[:, :WW - d] = a[:, d:]
            out[:, WW - d:] = b[:, :d]
        amt = math.sin(math.pi * p)
        if amt > 0.05:
            out = box_blur_h(out, 1 + int(amt * 90))
            out *= 1.0 + 0.25 * amt
        return out
    raise ValueError(kind)
