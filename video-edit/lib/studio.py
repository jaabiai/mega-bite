""""Studio" look for V Create: a broadcast-style explainer.  The picture sits in a rounded card (right side in 16:9, top
in 9:16) on a midnight backdrop with a faint grid; a sidebar / lower panel carries a live transcript-style caption block
(previous line dim, current line large with a teal word marker), the topic label, step numbers and prompts, so text is
never on the presenter.  Archivo Black + Manrope, teal / cyan accent with a recording-red dot motif.  The opening topic
is a full-screen extruded 3D title (aurora.Title3D re-skinned).

Everything draws into float32 RGB frames (0..1) in output pixels.
"""
import math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cine as C
import aurora as A                     # Title3D, prism transition; importing it sets the aurora theme, overridden below
from gfx import blend, ease_io, ease_out, ease_back, clamp01, lerp, rrect, aa_shape, with_mask

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
DISPLAY = os.path.join(FONT_DIR, "ArchivoBlack-Regular.ttf")

INK = (6, 10, 18)
PANEL = (13, 20, 34)
LINE = (34, 48, 70)
TEXT = (238, 244, 250)
MUTE = (132, 148, 170)
TEAL = (24, 226, 196)
CYAN = (86, 196, 255)
REC = (255, 82, 82)
ACCENT = [(0.0, TEAL), (1.0, CYAN)]
FACE_WHITE = ("v", [(0.0, (255, 255, 255)), (1.0, (206, 226, 244))])
FACE_TEAL = ("h", [(0.0, TEAL), (1.0, CYAN)])
FACE_REC = ("h", [(0.0, (255, 120, 96)), (1.0, REC)])
SIDE = [(0.0, (8, 70, 92)), (0.5, (10, 46, 96)), (1.0, (20, 30, 80))]

C.set_theme(
    pal=dict(gold=TEAL, gold_hi=(150, 255, 236), gold_lo=(10, 140, 120), silver=(220, 230, 240), steel=(110, 128, 150),
             ink=INK, panel=PANEL, text=TEXT),
    roles={"display": ("ArchivoBlack-Regular.ttf", None), "display_m": ("ArchivoBlack-Regular.ttf", None),
           "cap": ("Manrope-800.ttf", None), "bold": ("Manrope-700.ttf", None),
           "semi": ("Manrope-600.ttf", None), "med": ("Manrope-500.ttf", None)},
    accent=[(0.0, (160, 255, 238)), (0.5, TEAL), (1.0, (10, 160, 150))],
    chrome=[(0.0, (255, 255, 255)), (1.0, (206, 226, 244))],
    hot_fill=ACCENT, leak=[0.55, 1.0, 0.92])

_F = {}


def font(weight, size):
    key = (weight, int(round(size)))
    if key not in _F:
        name = "ArchivoBlack-Regular.ttf" if weight == "display" else f"Manrope-{weight}.ttf"
        _F[key] = ImageFont.truetype(os.path.join(FONT_DIR, name), key[1])
    return _F[key]


def ramp(n, stops):
    xs = np.linspace(0, 1, max(int(n), 1), dtype=np.float32)
    return np.stack([np.interp(xs, [p for p, _ in stops], [c[k] for _, c in stops]) for k in range(3)], -1)


def grad_fill(mask, stops, alpha=1.0):
    w, h = mask.size
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = ramp(w, stops)[None, :, :].astype(np.uint8)
    out[..., 3] = (np.asarray(mask, np.float32) * alpha).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def title3d(W, H, beats, box):
    return A.Title3D(W, H, beats, box=box, font=DISPLAY, faces={"white": FACE_WHITE, "accent": FACE_TEAL, "rec": FACE_REC},
                     side=SIDE, ink=INK, tint=(0.35, 1.0, 0.9), streak=(0.6, 1.0, 0.95),
                     glows=((0.20, 0.30, 0.55, TEAL, 0.20, 0.10, 0.0), (0.82, 0.70, 0.55, CYAN, 0.18, 0.08, 2.1),
                            (0.62, 0.12, 0.35, REC, 0.08, 0.12, 4.0)))


# ---------------------------------------------------------------------------------------------- backdrop / card
def backdrop(w, h):
    """Midnight field, faint 60 px grid, teal glow low-left and cyan glow top-right, vignette (float RGB)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    img = np.zeros((h, w, 3), np.float32) + np.array(INK, np.float32) / 255
    for bx, by, br, col, a in ((0.10, 0.95, 0.60, TEAL, 0.16), (0.95, 0.05, 0.55, CYAN, 0.12)):
        d = np.hypot((u - bx) * w / h, v - by) / br
        img += (np.exp(-d * d * 2.0) * a)[..., None] * np.array(col, np.float32) / 255
    step = 60
    grid = ((xx % step) < 1.2) | ((yy % step) < 1.2)
    img += grid[..., None] * 0.022
    vig = 1 - 0.35 * np.clip(np.hypot(u - 0.5, v - 0.5) / 0.75 - 0.3, 0, 1)
    return np.clip(img * vig[..., None], 0, 1).astype(np.float32)


class Card:
    """Rounded picture card at (x, y, w, h) with a hairline teal border, an outer glow and a soft shadow."""

    def __init__(self, W, H, x, y, w, h, r=26):
        self.x, self.y, self.w, self.h, self.r = x, y, w, h, r
        m = aa_shape((w, h), lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=r * s, fill=255))
        self.mask = (np.asarray(m, np.float32) / 255.0)[..., None]
        ring = aa_shape((w + 40, h + 40), lambda d, s: d.rounded_rectangle([20 * s, 20 * s, (w + 20) * s - 1, (h + 20) * s - 1],
                                                                           radius=r * s, outline=255, width=int(2 * s)))
        rim = np.asarray(ring, np.float32) / 255.0
        grad = ramp(w + 40, ACCENT)[None, :, :] / 255.0
        self.rim = (rim[..., None] * 0.75, grad)
        sh = np.zeros((H, W), np.float32)
        sh[y + 18:y + h + 18, x:x + w] = self.mask[..., 0]
        glow = np.zeros((H, W), np.float32)
        glow[y:y + h, x:x + w] = self.mask[..., 0]
        self.shadow = cv2.GaussianBlur(sh, (0, 0), 22)[..., None] * 0.55
        self.glow = (cv2.GaussianBlur(glow, (0, 0), 30) - glow * 0.0)[..., None] * 0.10

    def compose(self, fr, pic):
        fr *= 1 - self.shadow
        fr[:] = 1 - (1 - fr) * (1 - self.glow * np.array(TEAL, np.float32) / 255)
        reg = fr[self.y:self.y + self.h, self.x:self.x + self.w]
        reg[:] = reg * (1 - self.mask) + pic * self.mask
        a, grad = self.rim
        x0, y0 = self.x - 20, self.y - 20
        reg2 = fr[y0:y0 + self.h + 40, x0:x0 + self.w + 40]
        reg2[:] = reg2 * (1 - a) + grad * a


# ---------------------------------------------------------------------------------------------- bug / labels
def draw_bug(fr, x, y, alpha=1.0, size=56, label="V CREATE"):
    if alpha <= 0:
        return
    blend(fr, C.logo(size), x, y, alpha)
    f = font(800, size * 0.34)
    tr = size * 0.09
    wd = sum(f.getlength(c) for c in label) + tr * (len(label) - 1)
    lay = Image.new("RGBA", (int(wd) + 8, int(size * 0.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    xx = 2
    for c in label:
        d.text((xx, lay.height / 2), c, font=f, fill=TEXT + (255,), anchor="lm")
        xx += f.getlength(c) + tr
    blend(fr, lay, x + size + 14, y + size / 2 - lay.height / 2, alpha)


def rec_dot(fr, cx, cy, r, t, alpha=1.0):
    """Recording-red dot with a slow pulse ring."""
    if alpha <= 0:
        return
    n = int(r * 6)
    lay = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    k = (t % 1.6) / 1.6
    rr = r * (1 + 1.6 * k)
    d.ellipse((n / 2 - rr, n / 2 - rr, n / 2 + rr, n / 2 + rr), outline=REC + (int(160 * (1 - k)),), width=max(2, int(r * 0.25)))
    d.ellipse((n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r), fill=REC + (255,))
    blend(fr, lay, cx - n / 2, cy - n / 2, alpha)


def draw_topic(fr, x, y, kicker, title, alpha=1.0, width=520, size=40, t=0.0):
    """Topic label: red REC dot + small kicker, then the topic in Archivo Black, wrapped to `width`."""
    if alpha <= 0:
        return y
    rec_dot(fr, x + 9, y + 10, 8, t, alpha)
    fk = font(800, 20)
    lay = Image.new("RGBA", (width, 34), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((0, 17), kicker.upper(), font=fk, fill=TEAL + (255,), anchor="lm")
    blend(fr, lay, x + 28, y - 7, alpha)
    ft = font("display", size)
    words, lines, cur = title.split(), [], ""
    for wd in words:
        nxt = (cur + " " + wd).strip()
        if ft.getlength(nxt) > width and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = nxt
    lines.append(cur)
    yy = y + 40
    for ln in lines:
        lay = Image.new("RGBA", (width + 10, int(size * 1.35)), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((0, size * 0.1), ln, font=ft, fill=TEXT + (255,))
        blend(fr, lay, x, yy, alpha)
        yy += size * 1.18
    return yy


def draw_rule(fr, x, y, w, alpha=1.0):
    if alpha <= 0:
        return
    m = Image.new("L", (int(w), 3), 255)
    blend(fr, grad_fill(m, ACCENT), x, y, alpha * 0.9)


# ---------------------------------------------------------------------------------------------- transcript captions
def _wrap(words, ft, max_w):
    sp = ft.getlength(" ")
    lines, cur, cw = [], [], 0.0
    for i, w in enumerate(words):
        wl = ft.getlength(w)
        need = wl if not cur else cw + sp + wl
        if cur and need > max_w:
            lines.append(cur)
            cur, cw = [i], wl
        else:
            cur.append(i)
            cw = need
    if cur:
        lines.append(cur)
    return lines


def caption_block(prev_words, words, act, age, size, max_w, align="left", alpha_prev=1.0):
    """Transcript block: the previous line small and dim above, the current line large; spoken words white, the current
    word teal on a soft teal marker, upcoming words dim."""
    ft, fp = font(800, size), font(600, size * 0.56)
    sp = ft.getlength(" ")
    lines = _wrap(words, ft, max_w)
    plines = _wrap(prev_words, fp, max_w)[-2:] if prev_words else []
    asc, desc = ft.getmetrics()
    lh = int((asc + desc) * 1.08)
    pasc, pdesc = fp.getmetrics()
    plh = int((pasc + pdesc) * 1.15)
    H_ = plh * len(plines) + (int(size * 0.35) if plines else 0) + lh * len(lines) + 20
    W_ = int(max_w + 40)
    img = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 6
    for L in plines:
        txt = " ".join(prev_words[i] for i in L)
        x = 10 if align == "left" else (W_ - fp.getlength(txt)) / 2
        d.text((x, y + pasc), txt, font=fp, fill=MUTE + (int(200 * alpha_prev),), anchor="ls")
        y += plh
    if plines:
        y += int(size * 0.35)
    k = ease_out(age / 0.16)
    for L in lines:
        lw = sum(ft.getlength(words[i]) for i in L) + sp * (len(L) - 1)
        x = 10 if align == "left" else (W_ - lw) / 2
        for i in L:
            wl = ft.getlength(words[i])
            if i == act:
                pad = size * 0.14
                mk = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ImageDraw.Draw(mk).rounded_rectangle([x - pad, y + size * 0.10, x + wl + pad, y + lh - size * 0.02],
                                                     radius=size * 0.18, fill=TEAL + (int(46 * k),))
                img.alpha_composite(mk)
                d = ImageDraw.Draw(img)
                d.text((x, y + asc), words[i], font=ft, fill=tuple(int(lerp(TEXT[c], TEAL[c], k)) for c in range(3)) + (255,), anchor="ls")
            else:
                d.text((x, y + asc), words[i], font=ft, fill=TEXT + ((255,) if i < act else (105,)), anchor="ls")
            x += wl + sp
        y += lh
    return img


# ---------------------------------------------------------------------------------------------- step block
def draw_step(fr, x, y, n, total, label, alpha, size=30, width=520):
    """Big teal step number, 'STEP n OF N' kicker, the step name and a progress bar (sidebar)."""
    if alpha <= 0:
        return
    fn = font("display", size * 2.6)
    num = f"{n:02d}"
    m = Image.new("L", (int(fn.getlength(num)) + 10, int(size * 3.2)), 0)
    ImageDraw.Draw(m).text((0, 0), num, font=fn, fill=255)
    blend(fr, grad_fill(m, ACCENT), x + (1 - alpha) * -20, y, alpha)
    nx = x + m.width + 18
    lay = Image.new("RGBA", (width, int(size * 4.2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((0, size * 0.55), f"STEP {n} OF {total}", font=font(800, size * 0.58), fill=MUTE + (255,), anchor="lm")
    ft = font(800, size)
    words, lines, cur = label.split(), [], ""
    for wd in words:
        nxt = (cur + " " + wd).strip()
        if ft.getlength(nxt) > width - (nx - x) - 10 and cur:
            lines.append(cur); cur = wd
        else:
            cur = nxt
    lines.append(cur)
    yy = size * 1.15
    for ln in lines[:2]:
        d.text((0, yy), ln, font=ft, fill=TEXT + (255,))
        yy += size * 1.2
    blend(fr, lay, nx, y + size * 0.15, alpha)
    seg, gap = 34, 6
    for i in range(total):
        bar = Image.new("RGBA", (seg, 5), (TEAL if i < n else LINE) + (255,))
        blend(fr, bar, x + i * (seg + gap), y + size * 3.4, alpha)


# ---------------------------------------------------------------------------------------------- transitions
def push(fr, p, direction=1):
    """Card-content push: the frame slides with a short motion blur around a cut (p in [-1, 1])."""
    if p <= -1 or p >= 1:
        return fr
    k = math.exp(-(p / 0.40) ** 2)
    if k < 0.03:
        return fr
    H, W = fr.shape[:2]
    n = int(1 + 120 * k)
    out = cv2.blur(fr, (n | 1, 1)) if n >= 3 else fr
    shift = -direction * p * 90 * k
    M = np.array([[1, 0, shift], [0, 1, 0]], np.float32)
    return cv2.warpAffine(out, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def scan(fr, p):
    """A thin teal scan line passes down the frame, brightening what it crosses."""
    if p <= -1 or p >= 1:
        return fr
    H, W = fr.shape[:2]
    k = math.exp(-(p / 0.5) ** 2)
    y = (0.5 + 0.6 * p) * H
    ys = np.arange(H, dtype=np.float32)
    band = (np.exp(-((ys - y) / (H * 0.012)) ** 2) * 0.9 + np.exp(-((ys - y) / (H * 0.08)) ** 2) * 0.18)[:, None, None] * k
    fr[:] = 1 - (1 - fr) * (1 - band * np.array([0.45, 1.0, 0.92], np.float32))
    return fr


def prism(fr, p):
    return A.prism(fr, p)
