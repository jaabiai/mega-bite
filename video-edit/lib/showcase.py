""""Showcase" look for V Create product videos: a cinematic product film.

The graded footage is the hero.  In 16:9 it plays full width inside a 2.39:1 letterbox; the bars carry everything that
is not the picture (logo bug and chapter label on top, subtitles at the bottom), so no text sits on the presenter or on
the product.  Features are pointed out with tracked callouts (an ember ring pinned to the product, a leader line and a
dark glass label).  In 9:16 the picture is a 4:5 window in the middle with a blurred, darkened extension of the same
frame above and below; the header and subtitles live there.

Palette from the product itself: graphite ink, warm paper white and the case's ember orange.  Type: Unbounded (titles),
Barlow Condensed (labels), Inter (subtitles); all SIL OFL.

Everything draws into float32 RGB frames (0..1) in output pixels.
"""
import math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cine as C
import aurora as A                     # Title3D; importing it sets the aurora theme, overridden below
from gfx import blend, ease_io, ease_out, ease_back, clamp01, lerp

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
DISPLAY = os.path.join(FONT_DIR, "Unbounded-800.ttf")

INK = (10, 11, 13)
GLASS = (16, 18, 21)
LINE = (52, 56, 62)
PAPER = (243, 239, 232)
MUTE = (150, 152, 156)
EMBER = (255, 106, 43)
EMBER_HI = (255, 170, 110)
SAGE = (157, 176, 163)
FACE_WHITE = ("v", [(0.0, (255, 255, 255)), (1.0, (222, 216, 206))])
FACE_EMBER = ("h", [(0.0, (255, 150, 80)), (1.0, (255, 84, 30))])
FACE_SAGE = ("v", [(0.0, (214, 228, 218)), (1.0, (150, 172, 158))])
SIDE = [(0.0, (60, 30, 18)), (0.5, (34, 22, 18)), (1.0, (18, 16, 16))]

C.set_theme(
    pal=dict(gold=EMBER, gold_hi=EMBER_HI, gold_lo=(190, 66, 20), silver=(236, 232, 226), steel=(120, 124, 130),
             ink=INK, panel=GLASS, text=PAPER),
    roles={"display": ("Unbounded-800.ttf", None), "display_m": ("Unbounded-600.ttf", None),
           "cap": ("Inter-800.ttf", None), "bold": ("Inter-700.ttf", None),
           "semi": ("Inter-600.ttf", None), "med": ("Inter-500.ttf", None)},
    accent=[(0.0, EMBER_HI), (0.5, EMBER), (1.0, (200, 70, 22))],
    chrome=[(0.0, (255, 255, 255)), (1.0, (222, 216, 206))],
    hot_fill=[(0.0, EMBER_HI), (1.0, EMBER)], leak=[1.0, 0.62, 0.36])

_F = {}
_FILES = {"display": "Unbounded-800.ttf", "display6": "Unbounded-600.ttf",
          "label": "BarlowCondensed-700.ttf", "label6": "BarlowCondensed-600.ttf", "label5": "BarlowCondensed-500.ttf",
          "cap": "Inter-600.ttf", "capb": "Inter-700.ttf", "heavy": "Inter-800.ttf", "med": "Inter-500.ttf"}


def font(role, size):
    key = (role, int(round(size)))
    if key not in _F:
        _F[key] = ImageFont.truetype(os.path.join(FONT_DIR, _FILES[role]), key[1])
    return _F[key]


def title3d(W, H, beats, box):
    return A.Title3D(W, H, beats, box=box, font=DISPLAY, faces={"white": FACE_WHITE, "accent": FACE_EMBER, "rec": FACE_SAGE},
                     side=SIDE, ink=INK, tint=(1.0, 0.62, 0.40), streak=(1.0, 0.80, 0.62),
                     glows=((0.22, 0.32, 0.55, EMBER, 0.18, 0.10, 0.0), (0.80, 0.68, 0.55, (255, 190, 140), 0.12, 0.08, 2.1),
                            (0.55, 0.12, 0.35, SAGE, 0.08, 0.12, 4.0)))


# ---------------------------------------------------------------------------------------------- primitives
def _rgba_layer(w, h):
    return Image.new("RGBA", (max(int(w), 1), max(int(h), 1)), (0, 0, 0, 0))


def paste(fr, img, x, y, alpha=1.0):
    """Blend a PIL RGBA image into a float frame at (x, y)."""
    if alpha <= 0.003:
        return
    blend(fr, img, x, y, alpha)


def tracked(txt, ft, tracking):
    m, base = C.text_mask(txt, ft, tracking=tracking, pad=4)
    return m, base


def _txt_rgba(txt, ft, rgb, tracking=0.0, alpha=1.0):
    m, base = tracked(txt, ft, tracking)
    out = Image.new("RGBA", m.size, rgb + (0,))
    out.putalpha(m.point(lambda v: int(v * alpha)))
    return out, base


# ---------------------------------------------------------------------------------------------- letterbox / bars
def bar_h(W, H, ratio=2.39):
    return max(0, int(round((H - W / ratio) / 2)))


def letterbox(fr, h, line_alpha=0.55):
    """Black cinema bars of height h (top and bottom) with a faint warm hairline on the picture edge."""
    if h <= 0:
        return
    H = fr.shape[0]
    fr[:h] = np.array(INK, np.float32) / 255
    fr[H - h:] = np.array(INK, np.float32) / 255
    c = np.array((70, 52, 42), np.float32) / 255 * line_alpha
    fr[h:h + 1] = fr[h:h + 1] * (1 - line_alpha) + c
    fr[H - h - 1:H - h] = fr[H - h - 1:H - h] * (1 - line_alpha) + c


def draw_header(fr, x, y, idx, total, name, alpha=1.0, size=24, right=None, progress=None, width=None):
    """Chapter label in the top bar: '02 / 05   LENS PROTECTION' (index in ember), optional progress hairline."""
    if alpha <= 0.01:
        return
    ftn = font("label", size)
    ftl = font("label6", size)
    num = f"{idx:02d}"
    a1, _ = _txt_rgba(num, ftn, EMBER, tracking=2)
    a2, _ = _txt_rgba(f"/ {total:02d}", ftl, MUTE, tracking=2)
    a3, _ = _txt_rgba(name.upper(), ftn, PAPER, tracking=3.2)
    w = a1.width + 6 + a2.width + 22 + a3.width
    x0 = (right - w) if right is not None else x
    paste(fr, a1, x0, y, alpha)
    paste(fr, a2, x0 + a1.width + 6, y, alpha)
    paste(fr, a3, x0 + a1.width + 6 + a2.width + 22, y, alpha)
    if progress is not None and width:
        yy = int(y + a1.height + 8)
        x1 = int(x0 + w)
        seg = fr[yy:yy + 2, int(x0):x1]
        seg[:] = seg * (1 - 0.35 * alpha) + np.array(LINE, np.float32) / 255 * 0.35 * alpha
        xe = int(x0 + (x1 - x0) * clamp01(progress))
        seg = fr[yy:yy + 2, int(x0):xe]
        seg[:] = seg * (1 - alpha) + np.array(EMBER, np.float32) / 255 * alpha


def draw_bug(fr, x, y, alpha=1.0, size=44):
    C.draw_bug(fr, x, y, alpha, size=size)


# ---------------------------------------------------------------------------------------------- subtitles
def _wrap(words, ft, max_w, space):
    lines, cur, cw = [], [], 0.0
    for i, w in enumerate(words):
        ww = ft.getlength(w)
        if cur and cw + space + ww > max_w:
            lines.append(cur)
            cur, cw = [], 0.0
        cur.append(i)
        cw += (space if len(cur) > 1 else 0) + ww
    if cur:
        lines.append(cur)
    return lines


def subtitle(words, act, age, size, max_w, lines_max=2):
    """Cinema subtitle block (RGBA): the whole line in paper white, the spoken word lifted to full white with a gliding
    ember underline.  Returns (img, w, h)."""
    ft = font("cap", size)
    space = ft.getlength(" ")
    lines = _wrap(words, ft, max_w, space)[:lines_max]
    asc, desc = ft.getmetrics()
    lh = int(size * 1.34)
    widths = [sum(ft.getlength(words[i]) for i in ln) + space * (len(ln) - 1) for ln in lines]
    W = int(max(widths) + 24) if widths else 10
    Hh = lh * len(lines) + 16
    img = _rgba_layer(W, Hh)
    d = ImageDraw.Draw(img)
    sh = _rgba_layer(W, Hh)
    ds = ImageDraw.Draw(sh)
    ul = None
    for li, ln in enumerate(lines):
        x = (W - widths[li]) / 2
        y = 6 + li * lh + asc
        for i in ln:
            w = words[i]
            col = (255, 255, 255, 255) if i == act else (PAPER[0], PAPER[1], PAPER[2], 232 if i < act or act < 0 else 205)
            ds.text((x, y + 2), w, font=ft, fill=(0, 0, 0, 200), anchor="ls")
            d.text((x, y), w, font=ft, fill=col, anchor="ls")
            if i == act:
                ul = (x, y + desc * 0.55, ft.getlength(w))
            x += ft.getlength(w) + space
    out = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3)), img)
    if ul is not None:
        k = ease_out(clamp01(age / 0.22))
        x0, yy, ww = ul
        dd = ImageDraw.Draw(out)
        cx = x0 + ww / 2
        half = ww / 2 * k
        dd.rounded_rectangle([cx - half, yy, cx + half, yy + max(2, size * 0.075)], radius=2, fill=EMBER + (255,))
    return out


# ---------------------------------------------------------------------------------------------- tracked callout
def callout(fr, t, ax, ay, idx, label, sub=None, side="right", dist=(150, -70), alpha=1.0, size=30, dur=None,
            clip=None):
    """Pinned feature callout.  (ax, ay) = anchor on the product in frame pixels, t = seconds since the callout began.
    The ring pops (0-0.25 s), the leader draws (0.15-0.45 s), the card wipes in (0.35-0.7 s); `dur` fades it out over
    its last 0.3 s.  clip = (y0, y1) keeps the card inside the picture area."""
    if t < 0 or alpha <= 0.01:
        return
    a = alpha
    if dur is not None:
        a *= 1 - ease_io(clamp01((t - (dur - 0.3)) / 0.3))
    if a <= 0.01:
        return
    H, W = fr.shape[:2]
    # ring
    k = ease_back(clamp01(t / 0.28))
    r = 13 * k
    pulse = (t * 1.2) % 1.0
    lay = _rgba_layer(120, 120)
    d = ImageDraw.Draw(lay)
    c = 60
    if r > 1:
        d.ellipse([c - r, c - r, c + r, c + r], outline=EMBER + (255,), width=3)
        d.ellipse([c - 4.5 * k, c - 4.5 * k, c + 4.5 * k, c + 4.5 * k], fill=PAPER + (255,))
        rp = r + 22 * pulse
        d.ellipse([c - rp, c - rp, c + rp, c + rp], outline=EMBER + (int(150 * (1 - pulse)),), width=2)
    paste(fr, lay, int(ax - c), int(ay - c), a)
    # leader: diagonal then horizontal
    sgn = 1 if side == "right" else -1
    ex, ey = ax + sgn * dist[0], ay + dist[1]
    if clip is not None:
        ey = min(max(ey, clip[0] + 40), clip[1] - 60)
    kx = ease_io(clamp01((t - 0.15) / 0.30))
    pts = [(ax + sgn * 14 * 0.7, ay - 14 * 0.7 if dist[1] < 0 else ay + 14 * 0.7), (ex, ey)]
    # card
    ft = font("label", size)
    fs = font("med", int(size * 0.62))
    num = f"{idx:02d}"
    t_num, _ = _txt_rgba(num, font("label", int(size * 0.8)), EMBER, tracking=1)
    t_lab, _ = _txt_rgba(label.upper(), ft, PAPER, tracking=2.0)
    t_sub = None
    if sub:
        t_sub, _ = _txt_rgba(sub, fs, (210, 206, 200), tracking=0.2)
    pad = int(size * 0.55)
    cw = pad + t_num.width + int(size * 0.45) + max(t_lab.width, t_sub.width if t_sub else 0) + pad
    chh = pad + t_lab.height + (t_sub.height + 2 if t_sub else 0) + pad - 6
    cx0 = ex + (10 if sgn > 0 else -10 - cw)
    cx0 = min(max(cx0, 24), W - cw - 24)
    cy0 = ey - chh / 2
    if clip is not None:
        cy0 = min(max(cy0, clip[0] + 14), clip[1] - chh - 14)
    lx1 = cx0 if sgn > 0 else cx0 + cw
    line = _rgba_layer(W, H)
    dl = ImageDraw.Draw(line)
    p0 = pts[0]
    p1 = (lerp(p0[0], ex, kx), lerp(p0[1], ey, kx))
    dl.line([p0, p1], fill=EMBER + (255,), width=2)
    if kx >= 1:
        kh = ease_io(clamp01((t - 0.42) / 0.16))
        dl.line([(ex, ey), (lerp(ex, lx1, kh), ey)], fill=EMBER + (255,), width=2)
    xs = [p0[0], ex, lx1]
    ys = [p0[1], ey]
    bx0, bx1 = int(max(min(xs) - 4, 0)), int(min(max(xs) + 4, W))
    by0, by1 = int(max(min(ys) - 4, 0)), int(min(max(ys) + 4, H))
    if bx1 > bx0 and by1 > by0:
        paste(fr, line.crop((bx0, by0, bx1, by1)), bx0, by0, a)
    kc = ease_out(clamp01((t - 0.36) / 0.34))
    if kc <= 0:
        return
    card = _rgba_layer(cw, chh)
    dc = ImageDraw.Draw(card)
    dc.rounded_rectangle([0, 0, cw - 1, chh - 1], radius=6, fill=GLASS + (226,), outline=(70, 66, 62, 255), width=1)
    dc.rectangle([0, 0, 3, chh - 1], fill=EMBER + (255,))
    card.alpha_composite(t_num, (pad, pad - 2))
    xl = pad + t_num.width + int(size * 0.45)
    card.alpha_composite(t_lab, (xl, pad - 4))
    if t_sub:
        card.alpha_composite(t_sub, (xl, pad - 4 + t_lab.height))
    wv = int(cw * kc)
    if wv < 2:
        return
    if sgn > 0:
        card = card.crop((0, 0, wv, chh))
        paste(fr, card, int(cx0), int(cy0), a)
    else:
        card = card.crop((cw - wv, 0, cw, chh))
        paste(fr, card, int(cx0 + cw - wv), int(cy0), a)


# ---------------------------------------------------------------------------------------------- feature title
def feature_title(fr, t, idx, title, x, y, size=58, dur=2.8, align="left", kicker=None):
    """Kinetic chapter title inside the picture: small ember index + kicker, big title rising out of a mask."""
    if t < 0 or t > dur:
        return
    a = 1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35))
    k = ease_out(clamp01(t / 0.55))
    ft = font("display", size)
    lines = title.split("\n")
    imgs = [_txt_rgba(l.upper(), ft, PAPER, tracking=1.0)[0] for l in lines]
    kick = f"{idx:02d}" + (f"  ·  {kicker.upper()}" if kicker else "")
    ki, _ = _txt_rgba(kick, font("label", int(size * 0.42)), EMBER, tracking=3)
    wmax = max(i.width for i in imgs + [ki])
    xx = x if align == "left" else x - wmax
    # soft shadow plate for legibility
    hh = ki.height + sum(i.height for i in imgs) + 10
    plate = np.zeros((hh + 80, wmax + 160, 1), np.float32)
    plate[40:-40, 80:-80] = 1
    plate = cv2.GaussianBlur(plate, (0, 0), 30)[..., None]
    sub = fr[max(int(y) - 40, 0):max(int(y) - 40, 0) + plate.shape[0], max(int(xx) - 80, 0):max(int(xx) - 80, 0) + plate.shape[1]]
    pp = plate[:sub.shape[0], :sub.shape[1]]
    sub[:] = sub * (1 - 0.45 * a * k * pp)
    paste(fr, ki, xx, y, a * k)
    yy = y + ki.height + 4
    for li, im in enumerate(imgs):
        kl = ease_out(clamp01((t - 0.08 - li * 0.08) / 0.5))
        hv = int(im.height * kl)
        if hv > 1:
            crop = im.crop((0, 0, im.width, hv))
            paste(fr, crop, xx, yy + im.height - hv, a)
        yy += im.height - int(size * 0.12)
    # ember rule
    kr = ease_io(clamp01((t - 0.3) / 0.5))
    rw = int(min(wmax, 140) * kr)
    if rw > 2:
        fr[int(yy + 10):int(yy + 14), int(xx):int(xx + rw)] = np.array(EMBER, np.float32) / 255 * a + \
            fr[int(yy + 10):int(yy + 14), int(xx):int(xx + rw)] * (1 - a)


# ---------------------------------------------------------------------------------------------- price card
def price_card(fr, t, x, y, mrp, price, note=None, size=1.0, dur=None, align="left"):
    """'MRP ₹1,999' struck through, then the price counting up in ember: '₹520 onwards'."""
    if t < 0:
        return
    a = 1.0 if dur is None else 1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35))
    k = ease_out(clamp01(t / 0.45))
    lab, _ = _txt_rgba("MRP", font("label", int(26 * size)), MUTE, tracking=3)
    mrp_i, _ = _txt_rgba(mrp, font("display6", int(40 * size)), (200, 196, 190))
    cnt = clamp01((t - 0.55) / 0.9)
    digits = "".join(ch for ch in price if ch.isdigit())
    shown = price
    if digits:
        val = int(round(int(digits) * ease_out(cnt)))
        shown = price.replace(digits, f"{val}")
    pr_i, _ = _txt_rgba(shown, font("display", int(84 * size)), EMBER)
    note_i = _txt_rgba(note.upper(), font("label", int(28 * size)), PAPER, tracking=3)[0] if note else None
    wmax = max(lab.width + 12 + mrp_i.width, pr_i.width, note_i.width if note_i else 0)
    xx = x if align == "left" else x - wmax
    hh = mrp_i.height + pr_i.height + (note_i.height if note_i else 0) + 20
    plate = np.zeros((hh + 100, wmax + 200, 1), np.float32)
    plate[50:-50, 100:-100] = 1
    plate = cv2.GaussianBlur(plate, (0, 0), 36)[..., None]
    y0, x0 = max(int(y) - 50, 0), max(int(xx) - 100, 0)
    sub = fr[y0:y0 + plate.shape[0], x0:x0 + plate.shape[1]]
    sub[:] = sub * (1 - 0.55 * a * k * plate[:sub.shape[0], :sub.shape[1]])
    paste(fr, lab, xx, y + 10, a * k)
    paste(fr, mrp_i, xx + lab.width + 12, y, a * k)
    ks = ease_io(clamp01((t - 0.35) / 0.3))
    if ks > 0:
        sy = int(y + mrp_i.height * 0.55)
        sx0 = int(xx + lab.width + 12)
        sx1 = int(sx0 + mrp_i.width * ks)
        fr[sy:sy + 3, sx0:sx1] = fr[sy:sy + 3, sx0:sx1] * (1 - a) + np.array(EMBER, np.float32) / 255 * a
    kp = ease_out(clamp01((t - 0.5) / 0.4))
    paste(fr, pr_i, xx, y + mrp_i.height + 4 + (1 - kp) * 20, a * kp)
    if note_i:
        kn = ease_out(clamp01((t - 1.2) / 0.4))
        paste(fr, note_i, xx + 4, y + mrp_i.height + pr_i.height + 2, a * kn)


# ---------------------------------------------------------------------------------------------- spec list
def spec_list(fr, t, items, x, y, size=30, dur=None, title=None):
    """Checklist that ticks in one item at a time (0.32 s apart)."""
    if t < 0:
        return
    a = 1.0 if dur is None else 1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35))
    ft = font("label", size)
    rows = [_txt_rgba(s.upper(), ft, PAPER, tracking=2)[0] for s in items]
    lh = int(size * 1.55)
    ti = _txt_rgba(title.upper(), font("label", int(size * 0.8)), EMBER, tracking=4)[0] if title else None
    wmax = max([r.width for r in rows] + ([ti.width] if ti else [])) + size * 1.4
    hh = lh * len(rows) + (ti.height + 12 if ti else 0)
    plate = np.zeros((hh + 100, int(wmax) + 200, 1), np.float32)
    plate[50:-50, 100:-100] = 1
    plate = cv2.GaussianBlur(plate, (0, 0), 36)[..., None]
    y0, x0 = max(int(y) - 50, 0), max(int(x) - 100, 0)
    sub = fr[y0:y0 + plate.shape[0], x0:x0 + plate.shape[1]]
    sub[:] = sub * (1 - 0.55 * a * ease_out(clamp01(t / 0.4)) * plate[:sub.shape[0], :sub.shape[1]])
    yy = y
    if ti:
        paste(fr, ti, x, yy, a * ease_out(clamp01(t / 0.4)))
        yy += ti.height + 12
    for i, r in enumerate(rows):
        k = ease_out(clamp01((t - 0.25 - i * 0.32) / 0.35))
        if k <= 0:
            break
        tick = _rgba_layer(size, size)
        dt = ImageDraw.Draw(tick)
        dt.rounded_rectangle([1, 1, size - 2, size - 2], radius=5, fill=EMBER + (255,))
        s = size
        dt.line([(s * 0.26, s * 0.52), (s * 0.43, s * 0.68), (s * 0.74, s * 0.33)], fill=INK + (255,), width=max(3, int(s * 0.12)))
        paste(fr, tick, x, yy + (lh - size) / 2 - 2 + (1 - k) * 10, a * k)
        paste(fr, r, x + size * 1.4, yy + (lh - r.height) / 2 + (1 - k) * 10, a * k)
        yy += lh


# ---------------------------------------------------------------------------------------------- reel backdrop
def reel_extension(pic, W, H, win):
    """Blurred, darkened, slightly desaturated fill of the full 9:16 frame from the picture itself (float RGB)."""
    x0, y0, w, h = win
    small = cv2.resize(pic, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    big = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
    g = big.mean(-1, keepdims=True)
    big = (big * 0.55 + g * 0.45) * 0.42
    return big.astype(np.float32)


# ---------------------------------------------------------------------------------------------- transitions
def flash(fr, p):
    return C.flash(fr, p)


def whip(fr, p, direction=1):
    return C.whip(fr, p, direction)
