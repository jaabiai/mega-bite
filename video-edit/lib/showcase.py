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

A.AURORA = [(0.0, EMBER_HI), (1.0, EMBER)]   # the logo sting's underline, in this look's colours
A.INK = INK
A.TEXT = PAPER

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
def pin_line(fr, t, ax, ay, tx, ty, alpha=1.0, dur=None):
    """Ember ring on the product joined by a thin leader to a fixed point (e.g. the edge of a diagram)."""
    if t < 0:
        return
    a = alpha * (1.0 if dur is None else 1 - ease_io(clamp01((t - (dur - 0.3)) / 0.3)))
    if a <= 0.01:
        return
    H, W = fr.shape[:2]
    k = ease_back(clamp01(t / 0.28))
    pulse = (t * 1.2) % 1.0
    lay = _rgba_layer(120, 120)
    d = ImageDraw.Draw(lay)
    c, r = 60, 13 * k
    if r > 1:
        d.ellipse([c - r, c - r, c + r, c + r], outline=EMBER + (255,), width=3)
        d.ellipse([c - 4.5 * k, c - 4.5 * k, c + 4.5 * k, c + 4.5 * k], fill=PAPER + (255,))
        rp = r + 22 * pulse
        d.ellipse([c - rp, c - rp, c + rp, c + rp], outline=EMBER + (int(150 * (1 - pulse)),), width=2)
    paste(fr, lay, int(ax - c), int(ay - c), a)
    kx = ease_io(clamp01((t - 0.15) / 0.35))
    if kx > 0:
        line = _rgba_layer(W, H)
        dl = ImageDraw.Draw(line)
        ang = math.atan2(ty - ay, tx - ax)
        p0 = (ax + 15 * math.cos(ang), ay + 15 * math.sin(ang))
        dl.line([p0, (lerp(p0[0], tx, kx), lerp(p0[1], ty, kx))], fill=EMBER + (255,), width=2)
        x0, x1 = int(max(min(p0[0], tx) - 4, 0)), int(min(max(p0[0], tx) + 4, W))
        y0, y1 = int(max(min(p0[1], ty) - 4, 0)), int(min(max(p0[1], ty) + 4, H))
        if x1 > x0 and y1 > y0:
            paste(fr, line.crop((x0, y0, x1, y1)), x0, y0, a)


def callout(fr, t, ax, ay, idx, label, sub=None, side="right", dist=(150, -70), alpha=1.0, size=30, dur=None,
            clip=None, xmax=None):
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
    cx0 = min(max(cx0, 24), (W if xmax is None else xmax) - cw - 24)
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
    _plate(fr, xx - 10, y - 6, wmax + 20, hh, a * k)
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
def spec_list(fr, t, items, x, y, size=30, dur=None, title=None, extra_h=0, extra_w=0):
    """Checklist that ticks in one item at a time (0.32 s apart)."""
    if t < 0:
        return
    a = 1.0 if dur is None else 1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35))
    ft = font("label", size)
    rows = [_txt_rgba(s.upper(), ft, PAPER, tracking=2)[0] for s in items]
    lh = int(size * 1.55)
    ti = _txt_rgba(title.upper(), font("label", int(size * 0.8)), EMBER, tracking=4)[0] if title else None
    wmax = max([r.width for r in rows] + ([ti.width] if ti else [])) + size * 1.4
    hh = lh * len(rows) + (ti.height + 12 if ti else 0) + (extra_h or 0)
    _plate(fr, x - 10, y - 6, wmax + 20 + (extra_w or 0), hh + 12, a * ease_out(clamp01(t / 0.4)))
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


# ---------------------------------------------------------------------------------------------- bar title
def bar_title(fr, t, idx, title, cx, cy, size=54, dur=2.6, total=None):
    """Big kinetic chapter title that lives in the top letterbox bar: ember index, then the name rising from a mask,
    an ember rule drawing under it.  Centred on (cx, cy)."""
    if t < 0 or t > dur:
        return 0.0
    a = 1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35))
    title = title.replace("\n", " ")
    ti, _ = _txt_rgba(title.upper(), font("display", size), PAPER, tracking=1.5)
    ki, _ = _txt_rgba(f"{idx:02d}", font("display6", int(size * 0.62)), EMBER, tracking=1)
    gap = int(size * 0.45)
    w = ki.width + gap + ti.width
    x0 = int(cx - w / 2)
    kk = ease_out(clamp01(t / 0.35))
    paste(fr, ki, x0, cy - ki.height / 2 + (1 - kk) * 14, a * kk)
    kt = ease_out(clamp01((t - 0.08) / 0.45))
    hv = int(ti.height * kt)
    if hv > 1:
        paste(fr, ti.crop((0, 0, ti.width, hv)), x0 + ki.width + gap, cy - ti.height / 2 + ti.height - hv, a)
    kr = ease_io(clamp01((t - 0.25) / 0.5))
    rw = int(w * kr)
    yy = int(cy + ti.height / 2 + 2)
    if rw > 2 and yy + 3 < fr.shape[0]:
        seg = fr[yy:yy + 3, int(cx - rw / 2):int(cx + rw / 2)]
        seg[:] = seg * (1 - a) + np.array(EMBER, np.float32) / 255 * a
    return a


# ---------------------------------------------------------------------------------------------- chips / tags
def chip(fr, t, x, y, text, dur, size=24, dot=EMBER, icon=None):
    """Small glass pill with an ember dot: 'NOT SPONSORED · MY OWN EXPERIENCE'."""
    if t < 0 or t > dur:
        return
    a = ease_out(clamp01(t / 0.3)) * (1 - ease_io(clamp01((t - (dur - 0.3)) / 0.3)))
    ti, _ = _txt_rgba(text.upper(), font("label", size), PAPER, tracking=2.4)
    pad = int(size * 0.7)
    h = int(size * 1.9)
    w = ti.width + pad * 2 + int(size * 0.9)
    pill = _rgba_layer(w, h)
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=GLASS + (215,), outline=(84, 78, 72, 255), width=1)
    r = size * 0.24
    cyy = h / 2
    d.ellipse([pad - r, cyy - r, pad + r, cyy + r], fill=dot + (255,))
    pill.alpha_composite(ti, (pad + int(size * 0.7), int((h - ti.height) / 2)))
    paste(fr, pill, x + (1 - ease_out(clamp01(t / 0.35))) * -24, y, a)


def name_tag(fr, t, x, y, name, sub, dur, size=40):
    if t < 0 or t > dur:
        return
    a = 1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35))
    ni, _ = _txt_rgba(name.upper(), font("display", size), PAPER, tracking=1.5)
    si, _ = _txt_rgba(sub.upper(), font("label", int(size * 0.62)), EMBER, tracking=4)
    k1 = ease_out(clamp01(t / 0.45))
    kb = ease_io(clamp01(t / 0.35))
    bh = ni.height + si.height + 6
    fr[int(y):int(y + bh * kb), int(x):int(x + 4)] = np.array(EMBER, np.float32) / 255
    hv = int(ni.height * k1)
    if hv > 1:
        paste(fr, ni.crop((0, 0, ni.width, hv)), x + 16, y + ni.height - hv, a)
    paste(fr, si, x + 18, y + ni.height + 4, a * ease_out(clamp01((t - 0.25) / 0.4)))


# ---------------------------------------------------------------------------------------------- info cards
def _plate(fr, x, y, w, h, a, strength=0.70, blur=44):
    plate = np.zeros((int(h) + 2 * blur * 2, int(w) + 2 * blur * 2), np.float32)
    plate[blur * 2:-blur * 2, blur * 2:-blur * 2] = 1
    plate = cv2.GaussianBlur(plate, (0, 0), blur)
    y0, x0 = int(y) - blur * 2, int(x) - blur * 2
    H, W = fr.shape[:2]
    ys, xs = max(y0, 0), max(x0, 0)
    ye, xe = min(y0 + plate.shape[0], H), min(x0 + plate.shape[1], W)
    if ye <= ys or xe <= xs:
        return
    p = plate[ys - y0:ye - y0, xs - x0:xe - x0, None]
    fr[ys:ye, xs:xe] *= 1 - strength * a * p


def info_rows(fr, t, x, y, rows, dur, size=34, title=None, align="left"):
    """Stacked facts: [(big, small)], each big value in ember Unbounded, small label in Barlow; staggered rise."""
    if t < 0 or t > dur:
        return
    a = ease_out(clamp01(t / 0.35)) * (1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35)))
    items = []
    for big, small in rows:
        bi, _ = _txt_rgba(big, font("display", size), EMBER, tracking=0.5)
        si, _ = _txt_rgba(small.upper(), font("label", int(size * 0.62)), PAPER, tracking=2.6)
        items.append((bi, si))
    ti = _txt_rgba(title.upper(), font("label", int(size * 0.55)), MUTE, tracking=4)[0] if title else None
    lh = int(size * 2.25)
    wmax = max(max(b.width, s.width) for b, s in items)
    hh = lh * len(items) + (ti.height + 10 if ti else 0)
    xx = x if align == "left" else x - wmax
    _plate(fr, xx - 10, y - 6, wmax + 20, hh + 12, a)
    yy = y
    if ti:
        paste(fr, ti, xx, yy, a)
        yy += ti.height + 10
    for i, (bi, si) in enumerate(items):
        k = ease_out(clamp01((t - 0.15 - i * 0.22) / 0.4))
        paste(fr, bi, xx, yy + (1 - k) * 16, a * k)
        paste(fr, si, xx + 2, yy + bi.height - 2 + (1 - k) * 16, a * k)
        yy += lh


def lens_card(fr, t, x, y, dur, size=30, align="left"):
    """'Why I skip a lens protector': a lens with an extra glass layer, the haze it adds, and the takeaway."""
    if t < 0 or t > dur:
        return
    a = ease_out(clamp01(t / 0.35)) * (1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35)))
    l1w = font("display", int(size * 0.9)).getlength("CAMERA QUALITY") + 12
    W0, H0 = int(size * 2.4 + size * 1.8 + size * 1.1 + l1w + 10), int(size * 7.4)
    xx = x if align == "left" else x - W0
    _plate(fr, xx, y, W0, H0, a)
    lay = _rgba_layer(W0, H0)
    d = ImageDraw.Draw(lay)
    ti, _ = _txt_rgba("LENS PROTECTOR?", font("label", int(size * 0.9)), EMBER, tracking=3)
    lay.alpha_composite(ti, (0, 0))
    # icon: lens + glass layer sliding on top
    cx, cy, r = size * 2.4, ti.height + size * 2.9, size * 1.8
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(26, 28, 32, 255), outline=(190, 186, 180, 255), width=3)
    d.ellipse([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], fill=(8, 10, 14, 255), outline=(90, 96, 110, 255), width=2)
    d.ellipse([cx - r * 0.22, cy - r * 0.42, cx + r * 0.05, cy - r * 0.18], fill=(150, 170, 200, 200))
    kg = ease_out(clamp01((t - 0.4) / 0.5))
    gy = cy - r * 1.25 + (1 - kg) * -size * 1.2
    d.rounded_rectangle([cx - r * 1.15, gy, cx + r * 1.15, gy + size * 0.32], radius=4, fill=(200, 230, 255, int(150 * kg)),
                        outline=(230, 245, 255, int(220 * kg)), width=1)
    if kg > 0.6:                      # haze over the lens once the glass is on
        hz = _rgba_layer(int(r * 2.2), int(r * 2.2))
        ImageDraw.Draw(hz).ellipse([0, 0, r * 2.2 - 1, r * 2.2 - 1], fill=(220, 225, 235, int(70 * (kg - 0.6) / 0.4)))
        lay.alpha_composite(hz.filter(ImageFilter.GaussianBlur(6)), (int(cx - r * 1.1), int(cy - r * 1.1)))
    tx = int(cx + r + size * 1.1)
    l1, _ = _txt_rgba("EXTRA GLASS", font("display", int(size * 0.9)), PAPER)
    l2, _ = _txt_rgba("CAN COST YOU", font("label", int(size * 0.8)), MUTE, tracking=2)
    l3, _ = _txt_rgba("CAMERA QUALITY", font("display", int(size * 0.9)), PAPER)
    k2 = ease_out(clamp01((t - 0.7) / 0.4))
    yy = int(ti.height + size * 1.1)
    for im in (l1, l2, l3):
        lay.alpha_composite(im, (tx, yy))
        yy += im.height + 2
    paste(fr, lay.crop((0, 0, W0, H0)), xx, y, a)
    if k2 < 1:                         # reveal the text block with a wipe
        pass


def lip_diagram(fr, t, x, y, dur, w=560, align="left", size=26):
    """Side-view schematic: the phone settles onto a table and the case's raised lip (ember) touches first, so the lens
    bump hangs above the surface with a visible gap."""
    if t < 0 or t > dur:
        return
    a = ease_out(clamp01(t / 0.35)) * (1 - ease_io(clamp01((t - (dur - 0.35)) / 0.35)))
    h = int(w * 0.44)
    xx = x if align == "left" else x - w
    _plate(fr, xx, y, w, h, a)
    ss = 2
    lay = _rgba_layer(w * ss, h * ss)
    d = ImageDraw.Draw(lay)
    S_ = lambda v: v * ss
    ti, _ = _txt_rgba("RAISED CAMERA LIP", font("label", size), EMBER, tracking=3)
    table_y = h * 0.76
    d.line([(S_(6), S_(table_y)), (S_(w - 6), S_(table_y))], fill=(176, 172, 166, 255), width=S_(2))
    for k in range(16):
        x0 = 12 + k * (w - 24) / 16
        d.line([(S_(x0), S_(table_y + 3)), (S_(x0 - 11), S_(table_y + 14))], fill=(104, 100, 96, 255), width=S_(1))
    drop = ease_out(clamp01((t - 0.15) / 0.75))
    lift = (1 - drop) * h * 0.22
    lip_h, bump_h, slab = h * 0.20, h * 0.05, h * 0.16
    px0, px1 = w * 0.05, w * 0.95
    body_bot = table_y - lip_h - lift
    d.rounded_rectangle([S_(px0), S_(body_bot - slab), S_(px1), S_(body_bot)], radius=S_(12), fill=(116, 132, 122, 255),
                        outline=(200, 214, 204, 255), width=S_(2))
    cx0, cx1 = w * 0.12, w * 0.40
    d.rectangle([S_(cx0), S_(body_bot), S_(cx1), S_(body_bot + bump_h)], fill=(52, 54, 58, 255))
    for k in range(2):
        lx = cx0 + (cx1 - cx0) * (0.30 + 0.40 * k)
        d.ellipse([S_(lx - 16), S_(body_bot + bump_h * 0.1), S_(lx + 16), S_(body_bot + bump_h * 1.3)], fill=(18, 20, 24, 255),
                  outline=(150, 160, 180, 255), width=S_(1))
    for xa, xb in ((cx0 - 15, cx0 - 2), (cx1 + 2, cx1 + 15)):
        d.rounded_rectangle([S_(xa), S_(body_bot), S_(xb), S_(body_bot + lip_h)], radius=S_(3), fill=EMBER + (255,))
    kg = ease_out(clamp01((t - 1.0) / 0.5))
    gx = (cx0 + cx1) / 2
    if kg > 0:
        y_a, y_b = body_bot + bump_h * 1.3 + 2, table_y - 2
        col = PAPER + (int(255 * kg),)
        d.line([(S_(gx), S_(y_a + 6)), (S_(gx), S_(y_b - 6))], fill=col, width=S_(2))
        d.polygon([(S_(gx), S_(y_a)), (S_(gx - 6), S_(y_a + 9)), (S_(gx + 6), S_(y_a + 9))], fill=col)
        d.polygon([(S_(gx), S_(y_b)), (S_(gx - 6), S_(y_b - 9)), (S_(gx + 6), S_(y_b - 9))], fill=col)
    img = lay.resize((w, h), Image.LANCZOS)
    img.alpha_composite(ti, (6, 2))
    if kg > 0:
        g1, _ = _txt_rgba("GAP", font("label", int(size * 0.95)), PAPER, tracking=2)
        g2, _ = _txt_rgba("THE LENS NEVER TOUCHES THE TABLE", font("label6", int(size * 0.72)), (206, 202, 196), tracking=1.4)
        lab = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lab.alpha_composite(g1, (int(cx1 + 26), int(table_y - lip_h / 2 - g1.height / 2 - lift)))
        lab.alpha_composite(g2, (int(w - g2.width - 6), int(h - g2.height - 2)))
        arr = np.asarray(lab).copy()
        arr[..., 3] = (arr[..., 3] * kg).astype(np.uint8)
        img.alpha_composite(Image.fromarray(arr, "RGBA"))
    paste(fr, img, xx, y, a)


def heat_waves(fr, t, ax, ay, dur, scale=1.0):
    """Warm air rising off a vent: three wavy ember wisps drifting up and fading."""
    if t < 0 or t > dur:
        return
    a = ease_out(clamp01(t / 0.4)) * (1 - ease_io(clamp01((t - (dur - 0.4)) / 0.4)))
    w, h = int(120 * scale), int(190 * scale)
    lay = _rgba_layer(w, h)
    d = ImageDraw.Draw(lay)
    for k in range(3):
        ph = (t * 0.9 + k / 3.0) % 1.0
        xo = w * (0.28 + 0.22 * k)
        pts = []
        for i in range(24):
            v = i / 23
            yy = h * (1 - v) - ph * h * 0.35
            xx = xo + math.sin(v * 6.0 + t * 5 + k) * 9 * scale * (0.4 + v)
            pts.append((xx, yy))
        al = int(235 * (1 - ph) * a)
        d.line(pts, fill=EMBER_HI + (al,), width=max(3, int(5 * scale)), joint="curve")
    lay = lay.filter(ImageFilter.GaussianBlur(1.6))
    paste(fr, lay, ax - w / 2, ay - h + 10 * scale, 1.0)
