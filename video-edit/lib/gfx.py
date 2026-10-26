"""Small drawing/compositing helpers shared by the graphics modules (all coordinates in px of the output frame)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_io(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_back(x, s=1.70158):
    x = clamp01(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def blend(fr, img, x, y, opacity=1.0):
    """Alpha-composite an RGBA PIL image (straight alpha) onto float32 RGB frame `fr` (0..1) in place."""
    if opacity <= 0:
        return
    H, W = fr.shape[:2]
    x, y = int(round(x)), int(round(y))
    w, h = img.size
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    a = np.asarray(img.crop((x0 - x, y0 - y, x1 - x, y1 - y)), dtype=np.float32) / 255.0
    al = a[..., 3:4] * opacity
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - al) + a[..., :3] * al


def aa_shape(size, fn, ss=3):
    """Anti-aliased L mask: fn(draw, ss) draws white shapes on a supersampled canvas."""
    w, h = size
    m = Image.new("L", (int(w * ss), int(h * ss)), 0)
    fn(ImageDraw.Draw(m), ss)
    return m.resize((int(w), int(h)), Image.LANCZOS)


def solid(size, rgb, alpha=255):
    return Image.new("RGBA", size, tuple(rgb) + (alpha,))


def with_mask(size, rgb, mask, alpha=1.0):
    img = solid(size, rgb, 255)
    a = np.asarray(mask, np.float32) * alpha
    img.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    return img


def rrect(size, box, radius, rgb, alpha=1.0, outline=None, width=0, ss=3):
    """Anti-aliased rounded rectangle layer (RGBA) with optional outline colour."""
    w, h = size
    def fill(d, s):
        d.rounded_rectangle([c * s for c in box], radius=radius * s, fill=255)
    m = aa_shape(size, fill, ss)
    img = with_mask(size, rgb, m, alpha)
    if outline is not None and width > 0:
        def ring(d, s):
            d.rounded_rectangle([c * s for c in box], radius=radius * s, outline=255, width=int(width * s))
        mo = aa_shape(size, ring, ss)
        img = Image.alpha_composite(img, with_mask(size, outline[:3], mo, (outline[3] / 255.0) if len(outline) > 3 else 1.0))
    return img


def glow_of(img, sigma, gain=1.0):
    """Blurred copy of an RGBA layer, for soft glows. The result is padded by `pad` px on every side
    (img.pad); position it at (x - pad, y - pad) – use blend_glow()."""
    pad = int(sigma * 3) + 2
    canvas = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), tuple(img.getpixel((0, 0))[:3]) + (0,))
    canvas.paste(img, (pad, pad))
    g = canvas.filter(ImageFilter.GaussianBlur(sigma))
    if gain != 1.0:
        a = np.array(g)
        a[..., 3] = np.clip(a[..., 3].astype(np.float32) * gain, 0, 255).astype(np.uint8)
        g = Image.fromarray(a, "RGBA")
    g.pad = pad
    return g


def blend_glow(fr, g, x, y, opacity=1.0):
    blend(fr, g, x - g.pad, y - g.pad, opacity)


def lerp(a, b, t):
    return a + (b - a) * t
