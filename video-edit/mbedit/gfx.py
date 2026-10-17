"""2-D drawing primitives: premultiplied sprites, rounded masks, glow, highlights.

Frames are uint8 RGB numpy arrays (H, W, 3).  Sprites are dicts {pm: uint8 HxWx3 premultiplied RGB, a: uint8 HxW}.
"""
import functools
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import W, H, CYAN, BLUE, clamp


# ------------------------------------------------------------------ sprites
def sprite_from_rgba(arr):
    """uint8 RGBA (straight alpha) -> premultiplied sprite"""
    a = arr[..., 3]
    pm = (arr[..., :3].astype(np.uint16) * a[..., None] // 255).astype(np.uint8)
    return {"pm": pm, "a": a.copy()}


def sprite_from_png(path):
    return sprite_from_rgba(np.array(Image.open(path).convert("RGBA")))


def sprite_size(s):
    return s["a"].shape[1], s["a"].shape[0]


def scale_sprite(s, k, blur=0.0):
    w, h = sprite_size(s)
    nw, nh = max(1, int(round(w * k))), max(1, int(round(h * k)))
    interp = cv2.INTER_AREA if k < 1 else cv2.INTER_LINEAR
    pm = cv2.resize(s["pm"], (nw, nh), interpolation=interp)
    a = cv2.resize(s["a"], (nw, nh), interpolation=interp)
    if blur > 0:
        pm = cv2.GaussianBlur(pm, (0, 0), blur)
        a = cv2.GaussianBlur(a, (0, 0), blur)
    return {"pm": pm, "a": a}


def rotate_sprite(s, deg):
    if abs(deg) < 0.05:
        return s
    w, h = sprite_size(s)
    c, sn = abs(math.cos(math.radians(deg))), abs(math.sin(math.radians(deg)))
    nw, nh = int(w * c + h * sn) + 2, int(w * sn + h * c) + 2
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    pm = cv2.warpAffine(s["pm"], M, (nw, nh), flags=cv2.INTER_LINEAR)
    a = cv2.warpAffine(s["a"], M, (nw, nh), flags=cv2.INTER_LINEAR)
    return {"pm": pm, "a": a}


def blit(dst, s, x, y, opacity=1.0):
    """alpha-composite premultiplied sprite onto dst (in place) with top-left at (x, y)"""
    if opacity <= 0.003:
        return dst
    sh, sw = s["a"].shape
    x0, y0 = max(int(x), 0), max(int(y), 0)
    x1, y1 = min(int(x) + sw, dst.shape[1]), min(int(y) + sh, dst.shape[0])
    if x1 <= x0 or y1 <= y0:
        return dst
    sx0, sy0 = x0 - int(x), y0 - int(y)
    pm = s["pm"][sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
    a = s["a"][sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
    roi = dst[y0:y1, x0:x1]
    if opacity >= 0.999:
        inv = (255 - a)[..., None]
        out = pm.astype(np.uint16) * 255 + roi.astype(np.uint16) * inv
        roi[:] = ((out + 127) // 255).astype(np.uint8)
    else:
        af = (a.astype(np.float32) * (opacity / 255.0))[..., None]
        out = pm.astype(np.float32) * opacity + roi.astype(np.float32) * (1 - af)
        roi[:] = np.clip(out, 0, 255).astype(np.uint8)
    return dst


def draw_sprite(dst, s, cx, cy, scale=1.0, opacity=1.0, rot=0.0, anchor="c", blur=0.0):
    """draw sprite scaled/rotated around anchor. anchor: 'c' centre, 'b' bottom-centre, 'tl' top-left, 'l' left-centre"""
    if scale != 1.0 or blur > 0:
        s = scale_sprite(s, scale, blur)
    if rot:
        s = rotate_sprite(s, rot)
    w, h = sprite_size(s)
    if anchor == "c":
        x, y = cx - w / 2, cy - h / 2
    elif anchor == "b":
        x, y = cx - w / 2, cy - h
    elif anchor == "tl":
        x, y = cx, cy
    elif anchor == "l":
        x, y = cx, cy - h / 2
    elif anchor == "r":
        x, y = cx - w, cy - h / 2
    else:
        raise ValueError(anchor)
    return blit(dst, s, x, y, opacity)


# ------------------------------------------------------------------ masks / shapes
@functools.lru_cache(maxsize=256)
def rr_mask(w, h, r, ss=3):
    """anti-aliased rounded-rect mask, float32 0..1 (h, w)"""
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=r * ss, fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    return np.asarray(m, dtype=np.float32) / 255.0


def paste_rounded(dst, img, x, y, r, opacity=1.0):
    """paste RGB image (h,w,3) with rounded corners at (x,y) into dst"""
    h, w = img.shape[:2]
    m = rr_mask(w, h, r)
    a = (m * 255).astype(np.uint8)
    s = {"pm": (img.astype(np.uint16) * a[..., None] // 255).astype(np.uint8), "a": a}
    return blit(dst, s, x, y, opacity)


def solid_sprite(w, h, color, r=0, alpha=1.0):
    m = rr_mask(w, h, r) if r else np.ones((h, w), np.float32)
    a = (m * 255 * alpha).astype(np.uint8)
    col = np.array(color, np.uint8)[None, None, :]
    pm = (col.astype(np.uint16) * a[..., None] // 255).astype(np.uint8)
    return {"pm": pm, "a": a}


def glow_sprite(w, h, r, color, radius, strength=1.0, pad=None):
    """soft coloured glow around a rounded rect (sprite is (w+2pad) x (h+2pad))"""
    pad = pad or int(radius * 2.5)
    m = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
    m[pad:pad + h, pad:pad + w] = rr_mask(w, h, r)
    g = cv2.GaussianBlur(m, (0, 0), radius)
    a = np.clip(g * strength * 255, 0, 255).astype(np.uint8)
    col = np.array(color, np.uint8)[None, None, :]
    return {"pm": (col.astype(np.uint16) * a[..., None] // 255).astype(np.uint8), "a": a}, pad


def ring_sprite(w, h, r, thick, color, glow=14, glow_strength=1.0):
    """rounded-rect outline with outer glow, ready to blit; returns (sprite, pad)"""
    pad = int(glow * 3) + thick
    ss = 2
    big = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0)
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((pad * ss, pad * ss, (pad + w) * ss, (pad + h) * ss), radius=r * ss, outline=255, width=thick * ss)
    ring = np.asarray(big.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS), np.float32) / 255.0
    g = cv2.GaussianBlur(ring, (0, 0), glow) * glow_strength
    a = np.clip(np.maximum(ring, g * 0.9), 0, 1)
    col = np.array(color, np.float32)[None, None, :]
    # ring itself is a bit whiter than the glow
    core = np.clip(ring[..., None], 0, 1)
    rgb = col * (1 - 0.35 * core) + 255 * 0.35 * core
    pm = np.clip(rgb * a[..., None], 0, 255).astype(np.uint8)
    return {"pm": pm, "a": (a * 255).astype(np.uint8)}, pad


# ------------------------------------------------------------------ full-frame helpers
def vignette_gain(strength=0.45, power=2.2):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    g = 1 - strength * np.clip(d, 0, 1) ** power
    return cv2.merge([(g * 255).astype(np.uint8)] * 3)


VIG = vignette_gain()


def darken(img, k):
    """multiply frame by constant k (0..1)"""
    if k >= 0.999:
        return img
    return cv2.convertScaleAbs(img, alpha=k, beta=0)


def apply_gain_map(img, gain3):
    return cv2.multiply(img, gain3, scale=1 / 255.0)


@functools.lru_cache(maxsize=8)
def _left_shade(w):
    x = np.arange(W, dtype=np.float32)
    g = 1 - np.clip(1 - x / w, 0, 1) ** 1.5
    return g


def shade_side(img, side="left", width=900, strength=0.55):
    """darken one side of the frame with a smooth falloff (for title legibility)"""
    g = _left_shade(width)
    g = 1 - (1 - g) * strength
    if side == "right":
        g = g[::-1]
    gm = cv2.merge([np.tile((g * 255).astype(np.uint8), (H, 1))] * 3)
    return cv2.multiply(img, gm, scale=1 / 255.0)


def cover_resize(img, w=W, h=H, zoom=1.0, cx=0.5, cy=0.5):
    """scale `img` to cover (w,h), then zoom around (cx,cy) fractions; returns exactly (h,w,3)"""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih) * zoom
    cw, ch = w / s, h / s
    x0 = clamp(cx * iw - cw / 2, 0, iw - cw)
    y0 = clamp(cy * ih - ch / 2, 0, ih - ch)
    M = np.array([[s, 0, -x0 * s], [0, s, -y0 * s]], np.float32)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)


def crop_zoom(img, rect, out_w, out_h, interp=cv2.INTER_CUBIC):
    """crop float rect (x,y,w,h) out of img and resize to (out_w,out_h) (sub-pixel accurate)"""
    x, y, w, h = rect
    sx, sy = out_w / w, out_h / h
    M = np.array([[sx, 0, -x * sx], [0, sy, -y * sy]], np.float32)
    return cv2.warpAffine(img, M, (out_w, out_h), flags=interp, borderMode=cv2.BORDER_REPLICATE)


def blend(a, b, t):
    """cross-fade two frames, t=0 -> a, t=1 -> b"""
    if t <= 0.001:
        return a
    if t >= 0.999:
        return b
    return cv2.addWeighted(a, 1 - t, b, t, 0)


def box_blur_region(img, rect, sigma, feather=18):
    """blur a rect of img with soft edges (privacy blur)"""
    x, y, w, h = [int(v) for v in rect]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, img.shape[1]), min(y + h, img.shape[0])
    if x1 <= x0 or y1 <= y0:
        return img
    pad = int(sigma * 2)
    rx0, ry0, rx1, ry1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, img.shape[1]), min(y1 + pad, img.shape[0])
    roi = img[ry0:ry1, rx0:rx1]
    # downscale -> blur -> upscale is much faster than a full-res gaussian on a big region
    k = 4
    sm = cv2.resize(roi, (max(1, roi.shape[1] // k), max(1, roi.shape[0] // k)), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), sigma / k)
    bl = cv2.resize(sm, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_LINEAR)
    m = np.zeros(roi.shape[:2], np.float32)
    m[y0 - ry0:y1 - ry0, x0 - rx0:x1 - rx0] = 1.0
    if feather > 0:
        m = cv2.GaussianBlur(m, (0, 0), feather / 2.0)
        # keep the core fully blurred
        core = np.zeros_like(m)
        core[y0 - ry0 + feather:y1 - ry0 - feather, x0 - rx0 + feather:x1 - rx0 - feather] = 1.0
        m = np.maximum(m, core)
    out = roi.astype(np.float32) * (1 - m[..., None]) + bl.astype(np.float32) * m[..., None]
    img[ry0:ry1, rx0:rx1] = np.clip(out, 0, 255).astype(np.uint8)
    return img


# ------------------------------------------------------------------ text
_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


def text_sprite(text, path, size, fill=(255, 255, 255), stroke=0, stroke_fill=(0, 0, 0), shadow=(0, 6), shadow_blur=6,
                shadow_alpha=0.55, glow=None, glow_blur=18, pad=None, gradient=None, spacing=0):
    """render text into a premultiplied sprite.
    gradient: (top_rgb, bottom_rgb) vertical gradient fill instead of `fill`; glow: rgb for a soft outer glow"""
    f = font(path, size)
    pad = pad if pad is not None else int(size * 0.35) + stroke
    bbox = f.getbbox(text, stroke_width=stroke)
    asc, desc = f.getmetrics()
    tw = int(f.getlength(text)) + 2 * stroke
    w, h = tw + 2 * pad, asc + desc + 2 * pad
    ss = 1
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.text((pad, pad), text, font=f, fill=255, stroke_width=0)
    smask = Image.new("L", (w, h), 0)
    if stroke:
        ImageDraw.Draw(smask).text((pad, pad), text, font=f, fill=255, stroke_width=stroke)
    out = np.zeros((h, w, 4), np.float32)

    def over(layer_rgb, layer_a):
        a = layer_a[..., None]
        out[..., :3] = layer_rgb * a + out[..., :3] * (1 - a)
        out[..., 3:4] = a + out[..., 3:4] * (1 - a)

    m = np.asarray(mask, np.float32) / 255.0
    sm = np.asarray(smask, np.float32) / 255.0
    if glow is not None:
        g = cv2.GaussianBlur(np.maximum(m, sm), (0, 0), glow_blur)
        over(np.array(glow, np.float32)[None, None, :], np.clip(g * 1.6, 0, 1))
    if shadow and shadow_alpha > 0:
        base = np.maximum(m, sm)
        M = np.float32([[1, 0, shadow[0]], [0, 1, shadow[1]]])
        sh = cv2.warpAffine(base, M, (w, h))
        sh = cv2.GaussianBlur(sh, (0, 0), shadow_blur) if shadow_blur else sh
        over(np.zeros((1, 1, 3), np.float32), np.clip(sh * shadow_alpha, 0, 1))
    if stroke:
        over(np.array(stroke_fill, np.float32)[None, None, :], sm)
    if gradient is not None:
        top, bot = np.array(gradient[0], np.float32), np.array(gradient[1], np.float32)
        t = np.clip((np.arange(h, dtype=np.float32)[:, None] - pad) / max(asc + desc, 1), 0, 1)
        col = top[None, None, :] * (1 - t[..., None]) + bot[None, None, :] * t[..., None]
        col = np.broadcast_to(col, (h, w, 3))
        over(col, m)
    else:
        over(np.array(fill, np.float32)[None, None, :], m)
    a = np.clip(out[..., 3], 0, 1)
    pm = np.clip(out[..., :3], 0, 255).astype(np.uint8)      # `over` accumulates premultiplied colour
    return {"pm": pm, "a": (a * 255).astype(np.uint8)}


def text_width(text, path, size):
    return font(path, size).getlength(text)
