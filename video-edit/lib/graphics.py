"""Branded motion graphics: logo bug, step chip, hook title, search+lock scene, CTAs, end card, ring, tap, wipe."""
import math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter
from brand import hex2rgb
from caption import font
from gfx import *
import scene as scene_mod

# ---------------------------------------------------------------------------------------------- logo
LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "logo", "logo.png")
_logo = None


def logo_image():
    """Real channel logo if supplied (assets/logo/logo.png, RGBA) else None -> placeholder mark is drawn."""
    global _logo
    if _logo is None:
        _logo = Image.open(LOGO_PATH).convert("RGBA") if os.path.exists(LOGO_PATH) else False
    return _logo or None


def mark(size, pal, S=1.0):
    """Square brand mark layer (diameter = size px)."""
    lg = logo_image()
    d = int(size)
    if lg is not None:
        return lg.resize((d, int(d * lg.height / lg.width)), Image.LANCZOS)
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    m = aa_shape((d, d), lambda dr, s: dr.ellipse((0, 0, d * s - 1, d * s - 1), fill=255))
    img = with_mask((d, d), acc, m)
    dr = ImageDraw.Draw(img)
    f = font("title", d * 0.40)
    tw = f.getlength("MB")
    dr.text(((d - tw) / 2, d * 0.28), "MB", font=f, fill=dark + (255,))
    return img


def draw_logo_bug(fr, S, pal, alpha=1.0):
    h = int(60 * S)
    m = mark(h, pal, S)
    show_word = logo_image() is None
    f = font("title", 30 * S)
    label = "MEGA BYTE"
    tw = f.getlength(label) if show_word else 0
    padx, pady = 14 * S, 10 * S
    W_ = int(padx * 2 + m.width + (14 * S + tw if show_word else 0))
    H_ = int(max(m.height, h) + pady * 2)
    base = rrect((W_, H_), (0, 0, W_ - 1, H_ - 1), H_ / 2, (6, 8, 7), 0.45)
    base.alpha_composite(m, (int(padx), int((H_ - m.height) / 2)))
    if show_word:
        ImageDraw.Draw(base).text((padx + m.width + 14 * S, H_ / 2 - 22 * S), label, font=f, fill=(255, 255, 255, 240))
    blend(fr, base, 56 * S, 40 * S, alpha)


# ---------------------------------------------------------------------------------------------- step chip
def draw_step_chip(fr, S, pal, n, total, label, x=96, y=400, alpha=1.0, slide=0.0):
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    fl, fb = font("label", 30 * S), font("title", 20 * S)
    tag = f"STEP {n}"
    tagw = fb.getlength(tag)
    padx = 16 * S
    W_ = int(padx * 2 + tagw + 18 * S + fl.getlength(label) + 26 * S)
    H_ = int(58 * S + 22 * S)
    base = rrect((W_, H_), (0, 0, W_ - 1, 56 * S), 28 * S, (8, 11, 9), 0.78, outline=acc + (110,), width=1.5 * S)
    badge = rrect((W_, H_), (8 * S, 9 * S, 8 * S + tagw + 2 * padx - 6 * S, 47 * S), 19 * S, acc, 1.0)
    base = Image.alpha_composite(base, badge)
    d = ImageDraw.Draw(base)
    d.text((8 * S + padx - 3 * S, 14 * S), tag, font=fb, fill=dark + (255,))
    d.text((8 * S + tagw + 2 * padx - 6 * S + 16 * S, 10 * S), label, font=fl, fill=(255, 255, 255, 255))
    # progress segments
    seg_w, gap = 34 * S, 7 * S
    for i in range(total):
        x0 = 8 * S + i * (seg_w + gap)
        col = acc + (255,) if i < n else (255, 255, 255, 60)
        d.rounded_rectangle((x0, 66 * S, x0 + seg_w, 71 * S), radius=3 * S, fill=col)
    blend(fr, base, x * S + slide * S, y * S, alpha)


# ---------------------------------------------------------------------------------------------- hook title
def draw_title(fr, S, pal, t):
    """Animated hook title, t = seconds since the title started (total ~3.2 s)."""
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    lines = [("LOCK YOUR GOOGLE", False), ("SEARCH HISTORY", True)]
    f = font("title", 62 * S)
    fk = font("title", 22 * S)
    out_a = 1.0 - ease_io((t - 2.85) / 0.35)
    x, y0 = 96 * S, 232 * S
    # kicker
    ka = ease_out(t / 0.35) * out_a
    kw = fk.getlength("TECH TIP") + 36 * S
    k = rrect((int(kw), int(40 * S)), (0, 0, kw - 1, 38 * S), 19 * S, acc, 1.0)
    ImageDraw.Draw(k).text((18 * S, 6 * S), "TECH TIP", font=fk, fill=dark + (255,))
    blend(fr, k, x, y0 - 62 * S + (1 - ease_out(t / 0.35)) * 18 * S, ka)
    # accent bar
    bar_h = 2 * 74 * S
    bh = bar_h * ease_out((t - 0.1) / 0.5)
    bar = rrect((int(10 * S), int(max(bar_h, 4))), (0, 0, 9 * S, max(bh, 1)), 4 * S, acc, 1.0)
    blend(fr, bar, x - 24 * S, y0 + 6 * S, out_a)
    for i, (txt, hot) in enumerate(lines):
        ti = (t - 0.18 - 0.14 * i) / 0.45
        a = ease_out(ti) * out_a
        if a <= 0:
            continue
        w = int(f.getlength(txt)) + int(30 * S)
        h = int(100 * S)
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        sh = Image.new("L", (w, h), 0)
        ImageDraw.Draw(sh).text((6 * S, 8 * S), txt, font=f, fill=200)
        sh = sh.filter(ImageFilter.GaussianBlur(8 * S))
        sl = np.zeros((h, w, 4), np.uint8); sl[..., 3] = np.asarray(sh)
        layer = Image.alpha_composite(layer, Image.fromarray(sl, "RGBA"))
        ImageDraw.Draw(layer).text((6 * S, 8 * S), txt, font=f, fill=(acc if hot else (255, 255, 255)) + (255,))
        blend(fr, layer, x - 6 * S, y0 + i * 74 * S + (1 - ease_out(ti)) * 34 * S, a)


# ---------------------------------------------------------------------------------------------- icons
def lock_icon(size, rgb, body_rgb=None, open_amt=0.0, keyhole=(10, 13, 11)):
    """Padlock layer. open_amt 1 = shackle lifted & opened, 0 = closed."""
    s = int(size)
    W_, H_ = s, int(s * 1.25)
    ss = 3
    img = Image.new("L", (W_ * ss, H_ * ss), 0)
    d = ImageDraw.Draw(img)
    bw, bh = 0.86 * s, 0.62 * s
    bx0, by0 = (s - bw) / 2, H_ - bh - 0.04 * s
    th = 0.115 * s
    r_out = 0.30 * s
    cx = s / 2
    lift = open_amt * 0.20 * s
    top = by0 - 0.40 * s - lift
    # shackle: U shape
    d.arc([(cx - r_out) * ss, top * ss, (cx + r_out) * ss, (top + 2 * r_out) * ss], 180, 360, fill=255, width=int(th * ss))
    left_x = cx - r_out + th / 2
    right_x = cx + r_out - th / 2
    y_mid = top + r_out
    d.rectangle([(left_x - th / 2) * ss, y_mid * ss, (left_x + th / 2) * ss, (by0 + 0.05 * s) * ss], fill=255)
    right_end = (by0 + 0.05 * s) if open_amt < 0.05 else (y_mid + 0.12 * s)
    d.rectangle([(right_x - th / 2) * ss, y_mid * ss, (right_x + th / 2) * ss, right_end * ss], fill=255)
    shackle = img.resize((W_, H_), Image.LANCZOS)
    lay = with_mask((W_, H_), rgb, shackle)
    body_m = aa_shape((W_, H_), lambda dr, s_: dr.rounded_rectangle([bx0 * s_, by0 * s_, (bx0 + bw) * s_, (by0 + bh) * s_], radius=0.13 * s * s_, fill=255))
    lay = Image.alpha_composite(lay, with_mask((W_, H_), body_rgb or rgb, body_m))
    # keyhole
    kh = aa_shape((W_, H_), lambda dr, s_: (dr.ellipse([(cx - 0.065 * s) * s_, (by0 + 0.17 * s) * s_, (cx + 0.065 * s) * s_, (by0 + 0.30 * s) * s_], fill=255),
                                          dr.polygon([((cx - 0.035 * s) * s_, (by0 + 0.27 * s) * s_), ((cx + 0.035 * s) * s_, (by0 + 0.27 * s) * s_), ((cx + 0.05 * s) * s_, (by0 + 0.44 * s) * s_), ((cx - 0.05 * s) * s_, (by0 + 0.44 * s) * s_)], fill=255)))
    lay = Image.alpha_composite(lay, with_mask((W_, H_), keyhole, kh))
    return lay


def magnifier(size, rgb, width):
    s = int(size)
    def fn(d, ss):
        d.ellipse([0.06 * s * ss, 0.06 * s * ss, 0.66 * s * ss, 0.66 * s * ss], outline=255, width=int(width * ss))
        d.line([0.58 * s * ss, 0.58 * s * ss, 0.92 * s * ss, 0.92 * s * ss], fill=255, width=int(width * 1.15 * ss))
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def bell_icon(size, rgb, angle=0.0):
    s = int(size)
    def fn(d, ss):
        k = s * ss
        d.ellipse([0.22 * k, 0.10 * k, 0.78 * k, 0.60 * k], fill=255)
        d.polygon([(0.22 * k, 0.40 * k), (0.78 * k, 0.40 * k), (0.88 * k, 0.74 * k), (0.12 * k, 0.74 * k)], fill=255)
        d.rounded_rectangle([0.10 * k, 0.70 * k, 0.90 * k, 0.78 * k], radius=0.04 * k, fill=255)
        d.ellipse([0.41 * k, 0.80 * k, 0.59 * k, 0.98 * k], fill=255)
        d.ellipse([0.44 * k, 0.02 * k, 0.56 * k, 0.14 * k], fill=255)
    img = with_mask((s, s), rgb, aa_shape((s, s), fn))
    return img.rotate(angle, resample=Image.BICUBIC, center=(s / 2, s * 0.12))


def share_icon(size, rgb):
    s = int(size)
    def fn(d, ss):
        k = s * ss
        pts = [(0.78 * k, 0.20 * k), (0.22 * k, 0.50 * k), (0.78 * k, 0.80 * k)]
        w = int(0.07 * k)
        d.line([pts[0], pts[1]], fill=255, width=w)
        d.line([pts[1], pts[2]], fill=255, width=w)
        for (x, y) in pts:
            r = 0.15 * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def check_icon(size, rgb, width):
    s = int(size)
    def fn(d, ss):
        k = s * ss
        d.line([(0.18 * k, 0.55 * k), (0.42 * k, 0.78 * k), (0.84 * k, 0.26 * k)], fill=255, width=int(width * ss), joint="curve")
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def cursor_icon(size):
    s = int(size)
    def fn(d, ss):
        k = s * ss
        d.polygon([(0.14 * k, 0.06 * k), (0.14 * k, 0.80 * k), (0.34 * k, 0.62 * k), (0.48 * k, 0.94 * k), (0.62 * k, 0.88 * k), (0.48 * k, 0.57 * k), (0.76 * k, 0.55 * k)], fill=255)
    m = aa_shape((s, s), fn)
    dark = with_mask((s, s), (10, 13, 11), m.filter(ImageFilter.MaxFilter(5)))
    return Image.alpha_composite(dark, with_mask((s, s), (255, 255, 255), m))


# ---------------------------------------------------------------------------------------------- search + lock scene
def render_search_lock(t, S, pal, bg_img):
    """t seconds since scene start (4.0 s). Returns float32 RGB frame."""
    W_, H_ = bg_img.size
    fr = np.asarray(bg_img.convert("RGB"), np.float32) / 255.0
    fr = fr.copy()
    acc = hex2rgb(pal["accent"])
    cx = 1290 * S
    # --- search bar
    bw, bh = 800 * S, 112 * S
    bx, by = cx - bw / 2, 560 * S
    p_in = ease_out(t / 0.45)
    bar = Image.new("RGBA", (int(bw + 120 * S), int(bh + 120 * S)), (0, 0, 0, 0))
    box = (60 * S, 60 * S, 60 * S + bw, 60 * S + bh)
    locked = t > 2.55
    glow_col = acc if locked else (255, 255, 255)
    g = rrect(bar.size, box, bh / 2, glow_col, 0.0 + (0.55 if locked else 0.18))
    _gb = glow_of(g, 22 * S, 1.0)
    bar.alpha_composite(_gb.crop((_gb.pad, _gb.pad, _gb.pad + bar.width, _gb.pad + bar.height)))
    bar = Image.alpha_composite(bar, rrect(bar.size, box, bh / 2, (22, 28, 24), 0.82, outline=acc + (230 if locked else 150,), width=2.5 * S))
    d = ImageDraw.Draw(bar)
    mg = magnifier(54 * S, (220, 226, 222), 5.5 * S)
    bar.alpha_composite(mg, (int(60 * S + 34 * S), int(60 * S + bh / 2 - 27 * S)))
    f = font("body", 40 * S)
    text = "search history"
    n_chars = int(clamp01((t - 0.75) / 1.1) * len(text))
    shown = text[:n_chars]
    if locked:
        shown = "•" * len(text)
    caret = (int(t * 2.2) % 2 == 0) and not locked
    d.text((60 * S + 112 * S, 60 * S + bh / 2 - 29 * S), shown + ("|" if caret else ""), font=f, fill=(240, 244, 241, 255))
    blend(fr, bar, bx - 60 * S + (1 - p_in) * 80 * S, by - 60 * S, p_in)
    # --- padlock
    open_amt = 1.0 - ease_back((t - 2.2) / 0.35) if t > 2.2 else 1.0
    open_amt = max(open_amt, 0.0)
    ls = 250 * S
    lock = lock_icon(ls, (238, 242, 239), body_rgb=acc if t > 2.5 else (238, 242, 239), open_amt=open_amt)
    drop = (1 - ease_out(t / 0.6)) * -90 * S
    glow = glow_of(lock, 26 * S, 1.2)
    lx, ly = cx - lock.width / 2, 250 * S - 10 * S + drop
    blend_glow(fr, glow, lx, ly, 0.25 + (0.6 if locked else 0.0))
    shake = math.sin((t - 2.5) * 60) * 5 * S * max(0.0, 1 - (t - 2.5) / 0.35) if 2.5 < t < 2.85 else 0.0
    blend(fr, lock, lx + shake, ly, ease_out(t / 0.4))
    # --- lock-in pulse ring
    if 2.5 < t < 3.4:
        r = (t - 2.5) / 0.9
        rad = (110 + 250 * ease_out(r)) * S
        ring = Image.new("RGBA", (int(rad * 2 + 20 * S), int(rad * 2 + 20 * S)), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((10 * S, 10 * S, 10 * S + rad * 2, 10 * S + rad * 2), outline=acc + (int(220 * (1 - r)),), width=int(6 * S))
        blend(fr, ring, cx - ring.width / 2, 250 * S + ls * 0.55 - ring.height / 2)
    # --- LOCKED pill
    if t > 2.75:
        a = ease_out((t - 2.75) / 0.3)
        pf = font("title", 34 * S)
        txt = "LOCKED"
        pw, ph = int(pf.getlength(txt) + 96 * S), int(64 * S)
        pill = rrect((pw, ph), (0, 0, pw - 1, ph - 1), ph / 2, acc, 1.0)
        dd = ImageDraw.Draw(pill)
        dd.ellipse((24 * S, ph / 2 - 8 * S, 40 * S, ph / 2 + 8 * S), fill=hex2rgb(pal["on_accent"]) + (255,))
        dd.text((54 * S, 10 * S), txt, font=pf, fill=hex2rgb(pal["on_accent"]) + (255,))
        blend(fr, pill, cx - pw / 2, by + bh + 36 * S + (1 - a) * 20 * S, a)
    return fr


# ---------------------------------------------------------------------------------------------- CTAs
def draw_subscribe(fr, S, pal, t, x=96, y=860):
    """t = seconds since CTA start (3.0 s total). Click happens at t=1.15."""
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    p_in = ease_back(t / 0.5)
    out = ease_io((t - 2.65) / 0.35)
    if t < 0 or out >= 1:
        return
    clicked = t >= 1.15
    press = 1.0 - 0.07 * math.exp(-((t - 1.15) / 0.07) ** 2) if t > 0.95 else 1.0
    f = font("title", 34 * S)
    label = "SUBSCRIBED" if clicked else "SUBSCRIBE"
    w, h = int(f.getlength("SUBSCRIBED") + 190 * S), int(84 * S)
    box = (20 * S, 14 * S, w - 20 * S, h - 14 * S)
    sz = (w, h)
    if clicked:
        pill = rrect(sz, box, (h - 28 * S) / 2, (16, 21, 18), 0.92, outline=acc + (255,), width=3 * S)
    else:
        pill = rrect(sz, box, (h - 28 * S) / 2, acc, 1.0)
    d = ImageDraw.Draw(pill)
    col = (acc if clicked else dark) + (255,)
    d.text((54 * S, 20 * S), label, font=f, fill=col)
    # bell
    ang = 0.0
    if t > 1.2:
        ang = math.sin((t - 1.2) * 28) * 24 * max(0.0, 1 - (t - 1.2) / 1.1)
    bell = bell_icon(40 * S, acc if clicked else dark, ang)
    pill.alpha_composite(bell, (int(w - 20 * S - 28 * S - bell.width + 2 * S), int(h / 2 - bell.height / 2 + 1 * S)))
    if clicked:
        ck = check_icon(34 * S, acc, 5 * S)
        pill.alpha_composite(ck, (int(24 * S), int(h / 2 - ck.height / 2)))
    sc = press
    if sc != 1.0:
        pill = pill.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
    gl = glow_of(pill, 16 * S, 1.0)
    px = x * S + (1 - p_in) * -(w + 80 * S) - out * (w + 80 * S) + (w - pill.width) / 2
    py = y * S + (h - pill.height) / 2
    blend_glow(fr, gl, px, py, 0.5 if not clicked else 0.35)
    blend(fr, pill, px, py)
    # cursor travelling to the button
    if 0.55 < t < 1.9:
        k = ease_io((t - 0.55) / 0.6)
        cur = cursor_icon(46 * S)
        cxp = lerp(px + w * 0.95, px + w * 0.62, k)
        cyp = lerp(py + h * 1.9, py + h * 0.52, k)
        a = 1.0 if t < 1.55 else 1 - ease_io((t - 1.55) / 0.3)
        blend(fr, cur, cxp, cyp, a)
    if clicked and t < 1.9:
        r = (t - 1.15) / 0.75
        rad = (30 + 70 * ease_out(r)) * S
        ring = Image.new("RGBA", (int(rad * 2 + 12), int(rad * 2 + 12)), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((6, 6, 6 + rad * 2, 6 + rad * 2), outline=acc + (int(230 * (1 - r)),), width=max(2, int(4 * S)))
        blend(fr, ring, px + w * 0.62 - ring.width / 2 + 40 * S, py + h * 0.52 - ring.height / 2)


def draw_share(fr, S, pal, t, x=96, y=860):
    """t since CTA start (3.4 s). Tap at t=1.0."""
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    p_in = ease_back(t / 0.5)
    out = ease_io((t - 3.0) / 0.35)
    if t < 0 or out >= 1:
        return
    f = font("title", 34 * S)
    w, h = int(f.getlength("SHARE") + 180 * S), int(84 * S)
    box = (20 * S, 14 * S, w - 20 * S, h - 14 * S)
    hot = t >= 1.0
    pill = rrect((w, h), box, (h - 28 * S) / 2, acc if hot else (16, 21, 18), 1.0 if hot else 0.92,
                 outline=acc + (255,), width=3 * S)
    d = ImageDraw.Draw(pill)
    d.text((100 * S, 20 * S), "SHARE", font=f, fill=(dark if hot else acc) + (255,))
    ic = share_icon(48 * S, dark if hot else acc)
    pill.alpha_composite(ic, (int(40 * S), int(h / 2 - ic.height / 2)))
    sc = 1.0 - 0.07 * math.exp(-((t - 1.0) / 0.08) ** 2)
    if sc != 1.0:
        pill = pill.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
    px = x * S + (1 - p_in) * -(w + 80 * S) - out * (w + 80 * S) + (w - pill.width) / 2
    py = y * S + (h - pill.height) / 2
    blend_glow(fr, glow_of(pill, 16 * S, 1.0), px, py, 0.4)
    blend(fr, pill, px, py)
    if 1.0 < t < 1.9:
        r = (t - 1.0) / 0.9
        for k in range(3):
            rr = clamp01(r - k * 0.12)
            if rr <= 0:
                continue
            rad = (28 + 85 * ease_out(rr)) * S
            ring = Image.new("RGBA", (int(rad * 2 + 12), int(rad * 2 + 12)), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((6, 6, 6 + rad * 2, 6 + rad * 2), outline=acc + (int(200 * (1 - rr)),), width=max(2, int(3 * S)))
            blend(fr, ring, px + 64 * S - ring.width / 2, py + h / 2 - ring.height / 2)


# ---------------------------------------------------------------------------------------------- end card
def render_end_card(t, S, pal, bg_img):
    W_, H_ = bg_img.size
    fr = np.asarray(bg_img.convert("RGB"), np.float32) / 255.0
    fr = fr.copy()
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    # left column
    lg = mark(150 * S, pal, S)
    a0 = ease_out(t / 0.5)
    blend_glow(fr, glow_of(lg, 20 * S, 1.0), 120 * S, 190 * S + (1 - a0) * 30 * S, 0.5 * a0)
    blend(fr, lg, 120 * S, 190 * S + (1 - a0) * 30 * S, a0)
    f1, f2, f3 = font("title", 74 * S), font("title", 74 * S), font("label", 32 * S)
    for i, (txt, col, y) in enumerate((("Thanks for", (255, 255, 255), 380), ("watching!", acc, 462))):
        a = ease_out((t - 0.25 - 0.12 * i) / 0.5)
        layer = Image.new("RGBA", (int(f1.getlength(txt)) + int(40 * S), int(110 * S)), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((8 * S, 6 * S), txt, font=f1, fill=col + (255,))
        blend(fr, layer, 112 * S, y * S + (1 - a) * 26 * S, a)
    a = ease_out((t - 0.8) / 0.5)
    sub = Image.new("RGBA", (int(900 * S), int(150 * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(sub)
    d.text((8 * S, 0), "Subscribe to MEGA BYTE for more", font=f3, fill=(214, 220, 216, 255))
    d.text((8 * S, 46 * S), "tech tips, AI tools and updates.", font=f3, fill=(214, 220, 216, 255))
    blend(fr, sub, 112 * S, 600 * S + (1 - a) * 20 * S, a)
    # right-hand panels (YouTube end-screen slots)
    for i, (px, py, pw, ph, lab) in enumerate(((1010, 150, 760, 428, "WATCH NEXT"), (1010, 610, 360, 260, "SUBSCRIBE"))):
        a = ease_out((t - 0.5 - 0.15 * i) / 0.5)
        w, h = int(pw * S), int(ph * S)
        pn = rrect((w + 40, h + 40), (20, 20, 20 + w, 20 + h), 26 * S, (255, 255, 255), 0.05, outline=acc + (150,), width=2.5 * S)
        pf = font("title", 22 * S)
        ImageDraw.Draw(pn).text((20 + 26 * S, 20 + 20 * S), lab, font=pf, fill=acc + (230,))
        blend(fr, pn, px * S - 20, py * S - 20 + (1 - a) * 30 * S, a)
    return fr


# ---------------------------------------------------------------------------------------------- ring + tap
def draw_ring(fr, S, pal, rect, t, alpha=1.0):
    """rect=(x0,y0,x1,y1) in output px. t = seconds since the ring appeared (drives pulse)."""
    acc = hex2rgb(pal["accent"])
    x0, y0, x1, y1 = rect
    pad = 10 * S
    w, h = int(x1 - x0 + 2 * pad + 60 * S), int(y1 - y0 + 2 * pad + 60 * S)
    if w < 4 or h < 4:
        return
    pulse = 1.0 + 0.018 * math.sin(t * 2 * math.pi * 1.5)
    ox, oy = 30 * S, 30 * S
    cx, cy = ox + pad + (x1 - x0) / 2, oy + pad + (y1 - y0) / 2
    bw, bh = (x1 - x0 + 2 * pad) * pulse, (y1 - y0 + 2 * pad) * pulse
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    rad = min(26 * S, bh / 2)
    layer = rrect((w, h), box, rad, acc, 0.10, outline=acc + (255,), width=5 * S)
    gl = glow_of(rrect((w, h), box, rad, acc, 0.0, outline=acc + (255,), width=9 * S), 12 * S, 1.6)
    blend_glow(fr, gl, x0 - pad - ox, y0 - pad - oy, 0.9 * alpha)
    blend(fr, layer, x0 - pad - ox, y0 - pad - oy, alpha)


def draw_tap(fr, S, pal, x, y, t):
    """Touch indicator at (x, y) px; t = seconds relative to the tap moment (-0.25 .. +0.8)."""
    acc = hex2rgb(pal["accent"])
    if t < -0.30 or t > 0.85:
        return
    if t < 0:                                   # finger approaching: dot grows in
        k = ease_out((t + 0.30) / 0.30)
        r = 26 * S * (0.6 + 0.4 * k)
        a = 0.75 * k
    else:
        r = 26 * S * (1.0 - 0.25 * math.exp(-(t / 0.1) ** 2))
        a = 0.75 * (1 - ease_io((t - 0.12) / 0.2))
    if a > 0.01:
        d = int(r * 2 + 40 * S)
        dot = Image.new("RGBA", (d, d), (0, 0, 0, 0))
        m = aa_shape((d, d), lambda dr, s: dr.ellipse([(d / 2 - r) * s, (d / 2 - r) * s, (d / 2 + r) * s, (d / 2 + r) * s], fill=255))
        dot = with_mask((d, d), (255, 255, 255), m, 0.85)
        blend_glow(fr, glow_of(dot, 8 * S, 1.0), x - d / 2, y - d / 2, a)
        blend(fr, dot, x - d / 2, y - d / 2, a)
    if t >= 0:
        for k in range(2):
            rr = clamp01((t - 0.05 * k) / 0.7)
            if rr <= 0 or rr >= 1:
                continue
            rad = (24 + 86 * ease_out(rr)) * S
            sz = int(rad * 2 + 16 * S)
            ring = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((8 * S, 8 * S, 8 * S + rad * 2, 8 * S + rad * 2), outline=acc + (int(240 * (1 - rr)),), width=max(2, int(5 * S * (1 - rr * 0.5))))
            blend(fr, ring, x - sz / 2, y - sz / 2)


# ---------------------------------------------------------------------------------------------- transitions
def apply_wipe(fr, p, pal, S=1.0):
    """Lime band sweeping left -> right. p in 0..1 (band fully covers the frame at p=0.5)."""
    H_, W_ = fr.shape[:2]
    acc = np.array(hex2rgb(pal["accent"]), np.float32) / 255.0
    dark = np.array(hex2rgb(pal["bg0"]), np.float32) / 255.0
    band_w = 1.45 * W_
    x1 = -0.12 * W_ + p * (2.85 * W_)
    x0 = x1 - band_w
    skew = math.tan(math.radians(14))
    yy = (np.arange(H_, dtype=np.float32) - H_ / 2)[:, None] * skew
    xx = np.arange(W_, dtype=np.float32)[None, :] - yy
    edge = 2.5 * S
    m = np.clip((xx - x0) / edge, 0, 1) * np.clip((x1 - xx) / edge, 0, 1)
    # colour: lime body with a darker trailing stripe and a brighter leading edge
    u = np.clip((xx - x0) / band_w, 0, 1)
    col = acc[None, None, :] * (0.92 + 0.08 * u[..., None])
    stripe = np.exp(-(((xx - (x0 + 0.045 * band_w)) / (0.012 * band_w)) ** 2))[..., None]
    col = col * (1 - 0.85 * stripe) + dark[None, None, :] * 0.85 * stripe
    lead = np.exp(-(((xx - (x1 - 0.02 * band_w)) / (0.01 * band_w)) ** 2))[..., None]
    col = np.clip(col + lead * 0.25, 0, 1)
    fr[:] = fr * (1 - m[..., None]) + col * m[..., None]
    return fr


def zoom_punch(fr, amount):
    """Quick push-in with a touch of motion blur. amount 0..~0.3."""
    if amount <= 0.002:
        return fr
    H_, W_ = fr.shape[:2]
    s = 1.0 + amount
    M = np.array([[s, 0, (1 - s) * W_ / 2], [0, s, (1 - s) * H_ / 2]], np.float32)
    out = cv2.warpAffine(fr, M, (W_, H_), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    k = int(1 + amount * 40) | 1
    if k > 1:
        out = cv2.GaussianBlur(out, (k, 1), 0)
    return out
