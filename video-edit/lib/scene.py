"""Branded backgrounds for the screen-recording scenes."""
import numpy as np
from PIL import Image, ImageFilter
from brand import hex2rgb


def background(w, h, pal, glow_center=(0.72, 0.5), glow_r=0.55, seed=3):
    c0, c1, ac = (np.array(hex2rgb(pal[k]), np.float32) for k in ("bg0", "bg1", "accent"))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = xx / w, yy / h
    t = np.clip(0.65 * xn + 0.35 * yn, 0, 1)[..., None]
    img = c0 * (1 - t) + c1 * t
    # accent glow behind the phone
    gx, gy = glow_center
    d = np.sqrt(((xn - gx) * w / h) ** 2 + (yn - gy) ** 2) / glow_r
    glow = np.exp(-(d ** 2) * 2.2)[..., None]
    img = img + glow * ac * 0.24
    # secondary soft glow bottom-left
    ac2 = np.array(hex2rgb(pal["accent2"]), np.float32)
    d2 = np.sqrt(((xn - 0.05) * w / h) ** 2 + (yn - 1.05) ** 2) / 0.6
    img = img + (np.exp(-(d2 ** 2) * 2.0))[..., None] * ac2 * 0.07
    # soft diagonal light beam through the phone area
    beam = np.exp(-(((xn - 0.62) - (yn - 0.5) * 0.55) / 0.11) ** 2)[..., None]
    img = img + beam * ac * 0.045
    # fine dot grid
    step = max(18, h // 36)
    grid = ((xx % step < 1.6) & (yy % step < 1.6)).astype(np.float32)[..., None]
    fade = np.clip(1.2 - np.sqrt(((xn - 0.5) * 1.3) ** 2 + (yn - 0.5) ** 2) * 1.2, 0, 1)[..., None]
    img = img + grid * fade * 0.05 * 255 * 0.35
    rng = np.random.default_rng(seed)
    img = img + rng.standard_normal((h, w, 1)).astype(np.float32) * 1.4
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def drop_shadow(size, mask, blur, offset=(0, 30), opacity=0.55):
    """RGBA shadow layer from an L mask."""
    w, h = size
    sh = Image.new("L", (w, h), 0)
    sh.paste(mask, offset)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    a = (np.array(sh, np.float32) * opacity).astype(np.uint8)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., 3] = a
    return Image.fromarray(out, "RGBA")
