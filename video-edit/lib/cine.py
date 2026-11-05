"""V Create cinematic kit: letterbox, centred subtitles with a gold active word, chrome / gold Cinzel titles, logo bug +
logo sting, step HUD, spotlight + callout highlights, tap ripple, subscribe / like / comment / share CTAs, light-leak,
whip and dip transitions, bokeh backdrops, end card and reel outro.

Everything draws into float32 RGB frames (0..1) in output pixels.  Look: black + brushed chrome + champagne gold.
"""
import math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gfx import blend, blend_glow, glow_of, ease_io, ease_out, ease_back, clamp01, lerp, aa_shape, rrect, with_mask
from graphics import bell_icon, share_icon, check_icon, cursor_icon

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
LOGO_PATH = os.path.join(HERE, "..", "assets", "logo", "vcreate.png")

PAL = dict(gold=(217, 178, 107), gold_hi=(242, 213, 155), gold_lo=(160, 120, 62),
           silver=(226, 227, 231), steel=(150, 152, 158), ink=(8, 8, 9), panel=(20, 20, 22), text=(245, 245, 247))
NAME = "V CREATE"

# ---------------------------------------------------------------------------------------------- fonts / text
_FONTS = {}
_ROLES = {"display": ("Cinzel-VF.ttf", 800), "display_m": ("Cinzel-VF.ttf", 650),
          "cap": ("PlusJakartaSans-VF.ttf", 800), "bold": ("PlusJakartaSans-VF.ttf", 700),
          "semi": ("PlusJakartaSans-VF.ttf", 600), "med": ("PlusJakartaSans-VF.ttf", 500)}


def font(role, size):
    key = (role, int(round(size)))
    if key not in _FONTS:
        f, w = _ROLES[role]
        ft = ImageFont.truetype(os.path.join(FONT_DIR, f), key[1])
        ft.set_variation_by_axes([w])
        _FONTS[key] = ft
    return _FONTS[key]


def text_mask(txt, ft, tracking=0.0, pad=6):
    """L mask of a single line with letter tracking. Returns (mask, baseline_y)."""
    asc, desc = ft.getmetrics()
    widths = [ft.getlength(c) for c in txt]
    w = int(math.ceil(sum(widths) + tracking * max(len(txt) - 1, 0))) + 2 * pad
    h = asc + desc + 2 * pad
    m = Image.new("L", (max(w, 1), h), 0)
    d = ImageDraw.Draw(m)
    if tracking == 0:
        d.text((pad, pad + asc), txt, font=ft, fill=255, anchor="ls")
    else:
        x = pad
        for c, cw in zip(txt, widths):
            d.text((x, pad + asc), c, font=ft, fill=255, anchor="ls")
            x += cw + tracking
    return m, pad + asc


def _vgrad(h, stops):
    ys = np.linspace(0, 1, h, dtype=np.float32)
    pos = [p for p, _ in stops]
    return np.stack([np.interp(ys, pos, [c[k] for _, c in stops]) for k in range(3)], -1)


CHROME = [(0.0, (252, 252, 253)), (0.42, (205, 207, 212)), (0.52, (138, 140, 147)), (0.70, (196, 198, 203)), (1.0, (240, 240, 243))]
GOLD = [(0.0, (250, 226, 170)), (0.45, (222, 184, 112)), (0.55, (176, 134, 70)), (1.0, (238, 205, 140))]


def fill_mask(mask, stops=None, rgb=None, alpha=1.0):
    w, h = mask.size
    a = np.asarray(mask, np.float32) * alpha
    out = np.zeros((h, w, 4), np.uint8)
    if stops is not None:
        out[..., :3] = _vgrad(h, stops)[:, None, :].astype(np.uint8)
    else:
        out[..., :3] = rgb
    out[..., 3] = a.astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------------------------------------- logo
_LOGO = {}


def logo(size):
    size = int(size)
    if size not in _LOGO:
        im = Image.open(LOGO_PATH).convert("RGBA")
        bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        im = im.crop(bb)
        _LOGO[size] = im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)
    return _LOGO[size]


def draw_bug(fr, x, y, alpha=1.0, size=66, label=True):
    if alpha <= 0:
        return
    lg = logo(size)
    blend(fr, lg, x, y, alpha)
    if label:
        m, base = text_mask(NAME, font("display", size * 0.36), tracking=size * 0.075)
        blend(fr, fill_mask(m, CHROME), x + size + 14, y + size / 2 - base + size * 0.13, alpha)


_RAYS = {}


def _rays(r):
    if r not in _RAYS:
        n = 2 * r
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) - r
        ang = np.arctan2(yy, xx)
        d = np.hypot(xx, yy) / r
        streak = (0.5 + 0.5 * np.cos(ang * 18)) ** 6 * 0.8 + (0.5 + 0.5 * np.cos(ang * 7 + 1.3)) ** 10 * 0.6
        a = np.clip(streak * np.clip(1 - d, 0, 1) ** 1.6, 0, 1) * 0.55 + np.exp(-(d / 0.45) ** 2) * 0.35
        img = np.zeros((n, n, 4), np.uint8)
        img[..., :3] = PAL["gold_hi"]
        img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        _RAYS[r] = img
    return _RAYS[r]


def draw_sting(fr, t, cx, cy, size=330, bug=(40, 26, 66), dur=2.9):
    """Logo reveal: darken, gold rays, logo scales in, a shine sweeps the chrome, name settles, logo flies to the bug."""
    if t < 0 or t > dur:
        return
    H, W = fr.shape[:2]
    a_in = ease_out(t / 0.35)
    fly = ease_io((t - (dur - 0.75)) / 0.7)
    dark = 0.62 * a_in * (1 - fly)
    fr *= (1 - dark)
    # rays
    r = int(size * 1.35)
    rays = _rays(r)
    M = cv2.getRotationMatrix2D((r, r), t * 9.0, 1.0)
    rr = cv2.warpAffine(rays, M, (2 * r, 2 * r), flags=cv2.INTER_LINEAR)
    blend(fr, Image.fromarray(rr, "RGBA"), cx - r, cy - r, 0.85 * a_in * (1 - fly))
    # logo with a moving shine
    sc = lerp(0.72, 1.0, ease_back(t / 0.55)) if t < 0.55 else 1.0
    s = size * sc
    s = lerp(s, bug[2], fly)
    lx = lerp(cx - s / 2, bug[0], fly)
    ly = lerp(cy - s / 2 - size * 0.12, bug[1], fly)
    lg = logo(max(int(s), 8)).copy()
    k = (t - 0.55) / 0.8
    if 0 < k < 1:
        w_, h_ = lg.size
        yy, xx = np.mgrid[0:h_, 0:w_].astype(np.float32)
        band = np.exp(-(((xx + yy * 0.6) / (w_ * 1.6) - (k * 1.4 - 0.2)) / 0.06) ** 2)
        arr = np.asarray(lg, np.float32)
        arr[..., :3] = np.clip(arr[..., :3] + band[..., None] * 140, 0, 255)
        lg = Image.fromarray(arr.astype(np.uint8), "RGBA")
    blend(fr, lg, lx, ly, clamp01(t / 0.25))
    # name
    ta = ease_out((t - 0.35) / 0.6) * (1 - ease_io((t - (dur - 0.9)) / 0.35))
    if ta > 0:
        tr = lerp(34, 16, ease_out((t - 0.35) / 1.0))
        m, base = text_mask(NAME, font("display", size * 0.19), tracking=tr)
        blend(fr, fill_mask(m, CHROME), cx - m.width / 2, cy + size * 0.48, ta)
        lw = int(m.width * 0.7 * ease_out((t - 0.6) / 0.6))
        if lw > 2:
            line = Image.new("RGBA", (lw, 3), PAL["gold"] + (255,))
            blend(fr, line, cx - lw / 2, cy + size * 0.48 + m.height + 6, ta)


# ---------------------------------------------------------------------------------------------- letterbox / backdrops
def letterbox(fr, h, line=True):
    if h <= 0:
        return
    h = int(round(h))
    fr[:h] = 0.0
    fr[-h:] = 0.0
    if line:
        fr[h:h + 1] = fr[h:h + 1] * 0.82 + 0.18 * np.array(PAL["steel"], np.float32) / 255
        fr[-h - 1:-h] = fr[-h - 1:-h] * 0.82 + 0.18 * np.array(PAL["steel"], np.float32) / 255


def bokeh_bg(w, h, seed=4, centre=(0.62, 0.48)):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((xx / w - centre[0]) * (w / h), yy / h - centre[1])
    base = np.clip(1 - d / 0.95, 0, 1) ** 1.6
    img = np.zeros((h, w, 3), np.float32)
    img += np.array([7, 7, 8], np.float32) / 255
    img += base[..., None] * np.array([34, 30, 26], np.float32) / 255
    layer = np.zeros((h, w, 3), np.float32)
    for _ in range(46):
        r = rng.uniform(0.012, 0.055) * w
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        col = np.array(PAL["gold_hi"] if rng.random() < 0.65 else PAL["silver"], np.float32) / 255
        a = rng.uniform(0.05, 0.16)
        cv2.circle(layer, (int(x), int(y)), int(r), (col * a).tolist(), -1, lineType=cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), w * 0.004)
    img = 1 - (1 - img) * (1 - layer)
    streak = np.exp(-(((xx / w) - (yy / h) * 0.55 - 0.18) / 0.16) ** 2) * 0.05
    img += streak[..., None] * np.array([1.0, 0.92, 0.78], np.float32)
    return np.clip(img, 0, 1).astype(np.float32)


def film_grain(fr, amount, rng):
    if amount <= 0:
        return fr
    h, w = fr.shape[:2]
    g = rng.standard_normal((h // 2, w // 2)).astype(np.float32)
    g = cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR)[..., None] * amount
    l = fr.mean(-1, keepdims=True)
    fr += g * (0.35 + 0.65 * (1 - np.abs(l - 0.5) * 2))
    return fr


# ---------------------------------------------------------------------------------------------- captions
def caption_layer(words, act, age, size, max_w, lines_max=2):
    """Centred subtitle block: spoken words white, active word gold (pop + glow), upcoming words dim."""
    ft = font("cap", size)
    sp = ft.getlength(" ")
    widths = [ft.getlength(w) for w in words]
    lines, cur, cw = [], [], 0.0
    for i, w in enumerate(widths):
        need = w if not cur else cw + sp + w
        if cur and need > max_w and len(lines) < lines_max - 1:
            lines.append(cur)
            cur, cw = [i], w
        else:
            cur.append(i)
            cw = need
    lines.append(cur)
    asc, desc = ft.getmetrics()
    lh = int((asc + desc) * 1.08)
    pad = int(size * 0.6)
    W_ = int(max(sum(widths[i] for i in L) + sp * (len(L) - 1) for L in lines)) + 2 * pad
    H_ = lh * len(lines) + 2 * pad
    base = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    shadow = Image.new("L", (W_, H_), 0)
    d, dg, ds = ImageDraw.Draw(base), ImageDraw.Draw(glow), ImageDraw.Draw(shadow)
    pop = 1.0 + 0.04 * max(0.0, 1 - age / 0.18)
    for li, L in enumerate(lines):
        lw = sum(widths[i] for i in L) + sp * (len(L) - 1)
        x = (W_ - lw) / 2
        y = pad + li * lh + asc
        for i in L:
            w = words[i]
            if i == act:
                f2 = font("cap", size * pop) if pop > 1.001 else ft
                dx = (f2.getlength(w) - widths[i]) / 2
                dg.text((x - dx, y + (size * pop - size) * 0.35), w, font=f2, fill=PAL["gold"] + (230,), anchor="ls")
                ds.text((x - dx, y + 3), w, font=f2, fill=200, anchor="ls")
                d.text((x - dx, y + (size * pop - size) * 0.35), w, font=f2, fill=PAL["gold_hi"] + (255,), anchor="ls")
            else:
                col = PAL["text"] + ((255,) if i < act else (110,))
                ds.text((x, y + 3), w, font=ft, fill=200 if i < act else 90, anchor="ls")
                d.text((x, y), w, font=ft, fill=col, anchor="ls")
            x += widths[i] + sp
    out = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    sh = shadow.filter(ImageFilter.GaussianBlur(size * 0.10))
    out.alpha_composite(with_mask((W_, H_), (0, 0, 0), sh, 0.85))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size * 0.28)))
    out.alpha_composite(base)
    return out


def draw_caption(fr, words, act, age, cx, cy, size, max_w, alpha=1.0, rise=0.0, lines_max=2):
    if alpha <= 0:
        return
    img = caption_layer(words, act, age, size, max_w, lines_max)
    blend(fr, img, cx - img.width / 2, cy - img.height / 2 + rise, alpha)


# ---------------------------------------------------------------------------------------------- titles / HUD
def draw_title(fr, t, lines, x, y, size=78, dur=3.4, align="left"):
    """Trailer title: tracking settles, line 1 chrome, line 2 gold, gold rule draws under. t since start."""
    if t < 0 or t > dur:
        return
    out = 1 - ease_io((t - (dur - 0.45)) / 0.45)
    yy = y
    for i, (txt, gold) in enumerate(lines):
        ti = t - 0.18 * i
        a = ease_out(ti / 0.5) * out
        if a <= 0:
            yy += size * 1.12
            continue
        tr = lerp(size * 0.32, size * 0.06, ease_out(ti / 1.1))
        m, base = text_mask(txt, font("display", size), tracking=tr)
        xx = x if align == "left" else x - m.width / 2
        blend(fr, fill_mask(m, GOLD if gold else CHROME), xx, yy - base, a)
        yy += size * 1.12
    lw = int(size * 4.2 * ease_out((t - 0.55) / 0.8))
    if lw > 2:
        xx = x if align == "left" else x - lw / 2
        blend(fr, Image.new("RGBA", (lw, 4), PAL["gold"] + (255,)), xx + 6, yy - size * 0.55, out)


def draw_kicker(fr, txt, x, y, alpha=1.0, size=18, rgb=None):
    m, base = text_mask(txt.upper(), font("bold", size), tracking=size * 0.22)
    blend(fr, fill_mask(m, rgb=rgb or PAL["gold"]), x, y - base, alpha)
    return m.width


def draw_step(fr, n, total, label, alpha, x_right, y, size=26):
    """Top-right HUD: 'STEP 02 / 05', the step name, a segmented progress rule."""
    if alpha <= 0:
        return
    k = f"STEP {n:02d} / {total:02d}"
    mk, bk = text_mask(k, font("bold", size * 0.62), tracking=size * 0.16)
    ml, bl = text_mask(label, font("bold", size), tracking=0)
    w = max(mk.width, ml.width)
    blend(fr, fill_mask(mk, rgb=PAL["gold"]), x_right - mk.width, y - bk, alpha)
    blend(fr, fill_mask(ml, rgb=PAL["text"]), x_right - ml.width, y + size * 0.42 - bl + size * 0.62, alpha)
    seg, gap = 30, 6
    tot_w = total * seg + (total - 1) * gap
    x0 = x_right - tot_w - 6
    yb = int(y + size * 1.85)
    for i in range(total):
        col = PAL["gold"] if i < n else PAL["steel"]
        a = 1.0 if i < n else 0.45
        bar = Image.new("RGBA", (seg, 3), col + (255,))
        blend(fr, bar, x0 + i * (seg + gap), yb, alpha * a)


def draw_chip(fr, txt, cx, y, alpha=1.0, size=17):
    if alpha <= 0:
        return
    f = font("semi", size)
    tw = f.getlength(txt)
    w, h = int(tw + size * 2.2), int(size * 2.0)
    pill = rrect((w, h), (0, 0, w - 1, h - 1), h / 2, PAL["panel"], 0.82, outline=PAL["steel"] + (120,), width=1.5)
    ImageDraw.Draw(pill).text((w / 2, h / 2), txt, font=f, fill=PAL["silver"] + (230,), anchor="mm")
    blend(fr, pill, cx - w / 2, y, alpha)


# ---------------------------------------------------------------------------------------------- spotlight / callout / tap
_SPOT = {}


def spotlight(fr, rect, a, radius=26, dim=0.62):
    """Darken everything but a feathered rounded rect (output px)."""
    if a <= 0:
        return
    H, W = fr.shape[:2]
    x0, y0, x1, y1 = rect
    q = 4
    m = np.zeros((H // q + 1, W // q + 1), np.float32)
    cv2.rectangle(m, (int(x0 / q + radius / q), int(y0 / q)), (int(x1 / q - radius / q), int(y1 / q)), 1.0, -1)
    cv2.rectangle(m, (int(x0 / q), int(y0 / q + radius / q)), (int(x1 / q), int(y1 / q - radius / q)), 1.0, -1)
    for cx_, cy_ in ((x0 + radius, y0 + radius), (x1 - radius, y0 + radius), (x0 + radius, y1 - radius), (x1 - radius, y1 - radius)):
        cv2.circle(m, (int(cx_ / q), int(cy_ / q)), int(radius / q), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), 3.0)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[:H, :W, None]
    fr *= 1 - dim * a * (1 - m)


def draw_frame_box(fr, rect, t, a=1.0, radius=24, width=3.0):
    """Gold rounded outline with a soft glow, scaling in from 1.06."""
    if a <= 0:
        return
    x0, y0, x1, y1 = rect
    s = lerp(1.06, 1.0, ease_out(t / 0.35))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * s, (y1 - y0) * s
    pad = 26
    W_, H_ = int(w + 2 * pad), int(h + 2 * pad)
    box = (pad, pad, pad + w, pad + h)
    glow = rrect((W_, H_), box, radius, PAL["gold"], 0.0, outline=PAL["gold"] + (200,), width=width * 3)
    g = glow.filter(ImageFilter.GaussianBlur(10))
    ring = rrect((W_, H_), box, radius, PAL["gold"], 0.0, outline=PAL["gold_hi"] + (255,), width=width)
    blend(fr, g, cx - W_ / 2, cy - H_ / 2, a * 0.8)
    blend(fr, ring, cx - W_ / 2, cy - H_ / 2, a)


def draw_callout(fr, rect, text, t, a=1.0, side="auto", size=26, min_x=40, max_x=None, left_edge=None):
    """Label pill beside a highlighted rect, joined by a thin gold leader line ending in a dot."""
    if a <= 0 or not text:
        return
    H, W = fr.shape[:2]
    max_x = W - 40 if max_x is None else max_x
    x0, y0, x1, y1 = rect
    f = font("bold", size)
    tw = f.getlength(text)
    pw, ph = int(tw + size * 1.6), int(size * 2.1)
    gap = 70
    if side == "auto":
        side = "left" if x0 - gap - pw >= min_x else "right"
    cy = (y0 + y1) / 2
    if side == "left":
        px, ex = x0 - gap - pw, x0
    else:
        px, ex = x1 + gap, x1
    if side == "left" and left_edge is not None:            # keep the pill off the phone body when there is room
        px = min(px, max(left_edge - pw, min_x))
    px = min(max(px, min_x), max_x - pw)
    k = ease_out(t / 0.45)
    slide = (1 - k) * (24 if side == "left" else -24)
    pill = rrect((pw, ph), (0, 0, pw - 1, ph - 1), ph / 2, PAL["panel"], 0.92, outline=PAL["gold"] + (255,), width=2)
    ImageDraw.Draw(pill).text((pw / 2, ph / 2), text, font=f, fill=PAL["text"] + (255,), anchor="mm")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    sx = px + pw if side == "left" else px
    lx = lerp(sx, ex, k)
    d.line([(sx + slide, cy), (lx + slide * 0, cy)], fill=PAL["gold"] + (230,), width=2)
    if k > 0.95:
        d.ellipse((ex - 6, cy - 6, ex + 6, cy + 6), fill=PAL["gold_hi"] + (255,))
    blend(fr, lay, 0, 0, a)
    blend(fr, pill, px + slide, cy - ph / 2, a * k)


def draw_tap(fr, x, y, t):
    if t < -0.3 or t > 0.95:
        return
    if t < 0:
        a = ease_out((t + 0.3) / 0.3)
        r = 20
        dot = aa_shape((60, 60), lambda d, s: d.ellipse([(30 - r) * s, (30 - r) * s, (30 + r) * s, (30 + r) * s], fill=255))
        blend(fr, with_mask((60, 60), (255, 255, 255), dot, 0.85), x - 30, y - 30, a)
        return
    for k, delay in enumerate((0.0, 0.16)):
        tt = t - delay
        if tt < 0:
            continue
        p = clamp01(tt / 0.75)
        rad = 22 + 70 * ease_out(p)
        n = int(rad * 2 + 16)
        ring = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((8, 8, 8 + rad * 2, 8 + rad * 2), outline=PAL["gold_hi"] + (int(255 * (1 - p)),), width=4)
        blend(fr, ring, x - n / 2, y - n / 2)
    a = 1 - ease_io(t / 0.4)
    if a > 0:
        r = 18
        dot = aa_shape((60, 60), lambda d, s: d.ellipse([(30 - r) * s, (30 - r) * s, (30 + r) * s, (30 + r) * s], fill=255))
        blend(fr, with_mask((60, 60), PAL["gold_hi"], dot, 0.9), x - 30, y - 30, a)


# ---------------------------------------------------------------------------------------------- icons
def thumb_icon(size, rgb):
    s = int(size)

    def fn(d, ss):
        k = s * ss
        d.rounded_rectangle([0.08 * k, 0.44 * k, 0.28 * k, 0.92 * k], radius=0.04 * k, fill=255)            # cuff
        d.polygon([(0.34 * k, 0.46 * k), (0.52 * k, 0.12 * k), (0.62 * k, 0.10 * k), (0.66 * k, 0.20 * k),
                   (0.60 * k, 0.40 * k), (0.88 * k, 0.40 * k), (0.94 * k, 0.48 * k), (0.86 * k, 0.86 * k),
                   (0.78 * k, 0.92 * k), (0.34 * k, 0.92 * k)], fill=255)
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def bubble_icon(size, rgb):
    s = int(size)

    def fn(d, ss):
        k = s * ss
        d.rounded_rectangle([0.08 * k, 0.14 * k, 0.92 * k, 0.72 * k], radius=0.16 * k, fill=255)
        d.polygon([(0.26 * k, 0.70 * k), (0.22 * k, 0.92 * k), (0.46 * k, 0.70 * k)], fill=255)
        for cx in (0.32, 0.50, 0.68):
            d.ellipse([(cx - 0.055) * k, 0.38 * k, (cx + 0.055) * k, 0.49 * k], fill=0)
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def play_icon(size, rgb, inner):
    s = int(size)
    img = rrect((s, int(s * 0.72)), (0, 0, s - 1, int(s * 0.72) - 1), s * 0.18, rgb, 1.0)

    def fn(d, ss):
        k = s * ss
        d.polygon([(0.40 * k, 0.20 * k), (0.40 * k, 0.52 * k), (0.66 * k, 0.36 * k)], fill=255)
    img.alpha_composite(with_mask((s, int(s * 0.72)), inner, aa_shape((s, int(s * 0.72)), fn)))
    return img


# ---------------------------------------------------------------------------------------------- CTAs
def _pill(w, h, hot):
    if hot:
        p = rrect((w, h), (0, 0, w - 1, h - 1), h / 2, PAL["gold"], 1.0)
        # brushed gold: vertical gradient over the fill
        a = np.asarray(p, np.float32)
        a[..., :3] = _vgrad(h, GOLD)[:, None, :]
        return Image.fromarray(a.astype(np.uint8), "RGBA")
    return rrect((w, h), (0, 0, w - 1, h - 1), h / 2, PAL["panel"], 0.88, outline=PAL["silver"] + (150,), width=2)


def _cursor(fr, t, t0, t_click, start, end):
    if t < t0 or t > t_click + 0.55:
        return
    k = ease_io((t - t0) / max(t_click - t0, 0.01))
    x, y = lerp(start[0], end[0], k), lerp(start[1], end[1], k)
    a = 1 - ease_io((t - (t_click + 0.25)) / 0.3)
    press = 0.9 if abs(t - t_click) < 0.08 else 1.0
    c = cursor_icon(int(44 * press))
    blend(fr, c, x, y, a)


def cta_subscribe(fr, t, x, y, dur=3.4, scale=1.0):
    """Dark glass pill (play icon + SUBSCRIBE) -> cursor click at 1.2 s -> gold SUBSCRIBED + ringing bell."""
    if t < 0 or t > dur:
        return
    s = scale
    p_in = ease_back(t / 0.5)
    out = ease_io((t - (dur - 0.35)) / 0.35)
    a = clamp01(t / 0.25) * (1 - out)
    hot = t >= 1.2
    f = font("bold", 30 * s)
    label = "SUBSCRIBED" if hot else "SUBSCRIBE"
    h = int(78 * s)
    w = int(f.getlength("SUBSCRIBED") + 150 * s)
    pill = _pill(w, h, hot)
    ink = PAL["ink"] if hot else PAL["text"]
    if hot:
        ck = check_icon(int(40 * s), PAL["ink"], 6 * s)
        pill.alpha_composite(ck, (int(26 * s), int(h / 2 - ck.height / 2)))
    else:
        ic = play_icon(int(46 * s), PAL["gold"], PAL["ink"])
        pill.alpha_composite(ic, (int(22 * s), int(h / 2 - ic.height / 2)))
    ImageDraw.Draw(pill).text((int(84 * s), h / 2), label, font=f, fill=ink + (255,), anchor="lm")
    press = 1.0 - 0.06 * math.exp(-((t - 1.2) / 0.07) ** 2)
    if press != 1.0:
        pill = pill.resize((int(w * press), int(h * press)), Image.LANCZOS)
    px = x + (1 - p_in) * -60 * s + (w - pill.width) / 2
    py = y + (h - pill.height) / 2
    if hot:
        blend_glow(fr, glow_of(pill, 18 * s, 1.0), px, py, 0.55 * a)
    blend(fr, pill, px, py, a)
    # bell in its own circle
    bx = x + w + 16 * s
    circ = rrect((h, h), (0, 0, h - 1, h - 1), h / 2, PAL["panel"], 0.88, outline=PAL["gold"] + (255 if hot else 120,), width=2)
    ang = math.sin((t - 1.35) * 26) * 26 * max(0.0, 1 - (t - 1.35) / 1.2) if t > 1.35 else 0.0
    bell = bell_icon(int(40 * s), PAL["gold_hi"] if hot else PAL["silver"], ang)
    circ.alpha_composite(bell, (int(h / 2 - bell.width / 2), int(h / 2 - bell.height / 2)))
    ba = ease_back((t - 0.25) / 0.45)
    blend(fr, circ, bx, y + (1 - clamp01(ba)) * 12 * s, a * clamp01(ba))
    _cursor(fr, t, 0.45, 1.2, (x + w * 1.1, y + h * 2.2), (x + w * 0.62, y + h * 0.5))
    if hot and t < 2.0:
        r = (t - 1.2) / 0.8
        rad = (40 + 90 * ease_out(r)) * s
        n = int(rad * 2 + 12)
        ring = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((6, 6, 6 + rad * 2, 6 + rad * 2), outline=PAL["gold_hi"] + (int(220 * (1 - r)),), width=max(2, int(4 * s)))
        blend(fr, ring, x + w * 0.62 - n / 2, y + h / 2 - n / 2)


def _icon_pill(fr, t, x, y, icon_fn, label, hot_at, dur, scale=1.0, burst=False):
    if t < 0 or t > dur:
        return 0
    s = scale
    p_in = ease_back(t / 0.45)
    out = ease_io((t - (dur - 0.35)) / 0.35)
    a = clamp01(t / 0.2) * (1 - out)
    hot = t >= hot_at
    f = font("bold", 28 * s)
    h = int(74 * s)
    w = int(f.getlength(label) + 120 * s)
    pill = _pill(w, h, hot)
    ink = PAL["ink"] if hot else PAL["text"]
    ic = icon_fn(int(40 * s), PAL["ink"] if hot else PAL["gold"])
    pill.alpha_composite(ic, (int(24 * s), int(h / 2 - ic.height / 2)))
    ImageDraw.Draw(pill).text((int(76 * s), h / 2), label, font=f, fill=ink + (255,), anchor="lm")
    pop = 1.0 + 0.08 * math.exp(-((t - hot_at) / 0.08) ** 2)
    if pop != 1.0:
        pill = pill.resize((int(w * pop), int(h * pop)), Image.LANCZOS)
    px = x + (1 - p_in) * -50 * s + (w - pill.width) / 2
    py = y + (h - pill.height) / 2
    if hot:
        blend_glow(fr, glow_of(pill, 16 * s, 1.0), px, py, 0.5 * a)
    blend(fr, pill, px, py, a)
    if burst and hot and t < hot_at + 0.7:
        r = (t - hot_at) / 0.7
        lay = Image.new("RGBA", (int(200 * s), int(200 * s)), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        c = 100 * s
        for i in range(10):
            ang = i / 10 * 2 * math.pi
            r0, r1 = (30 + 40 * r) * s, (44 + 60 * r) * s
            d.line([(c + r0 * math.cos(ang), c + r0 * math.sin(ang)), (c + r1 * math.cos(ang), c + r1 * math.sin(ang))],
                   fill=PAL["gold_hi"] + (int(255 * (1 - r)),), width=max(2, int(4 * s)))
        blend(fr, lay, x + 44 * s - c, y + h / 2 - c)
    return w


def cta_like(fr, t, x, y, dur=2.4, scale=1.0):
    return _icon_pill(fr, t, x, y, thumb_icon, "LIKE", 0.8, dur, scale, burst=True)


def cta_comment(fr, t, x, y, dur=3.0, scale=1.0, label="COMMENT YOUR DOUBTS"):
    return _icon_pill(fr, t, x, y, bubble_icon, label, 0.9, dur, scale)


def cta_share(fr, t, x, y, dur=3.0, scale=1.0):
    return _icon_pill(fr, t, x, y, share_icon, "SHARE", 1.0, dur, scale)


def cta_engage(fr, t, x, y, dur=4.6, scale=1.0, vertical=False, grid=False):
    """LIKE, COMMENT, SHARE popping one after another, then SUBSCRIBE (one row, a column, or a 2x2 grid)."""
    if t < 0 or t > dur:
        return
    s = scale
    step = 88 * s
    if grid:
        wl = int(font("bold", 28 * s).getlength("LIKE") + 120 * s)
        ws = int(font("bold", 28 * s).getlength("SHARE") + 120 * s)
        cta_like(fr, t, x, y, dur, s)
        cta_comment(fr, t - 0.35, x + wl + 16 * s, y, dur - 0.35, s, label="COMMENT")
        cta_share(fr, t - 0.7, x, y + step, dur - 0.7, s)
        cta_subscribe(fr, t - 1.05, x + ws + 16 * s, y + step - 2 * s, dur - 1.05, s * 0.95)
        return
    if vertical:
        cta_like(fr, t, x, y, dur, s)
        cta_comment(fr, t - 0.35, x, y + step, dur - 0.35, s, label="COMMENT")
        cta_share(fr, t - 0.7, x, y + 2 * step, dur - 0.7, s)
        cta_subscribe(fr, t - 1.05, x, y + 3 * step, dur - 1.05, s)
        return
    w1 = cta_like(fr, t, x, y, dur, s) or int(font("bold", 28 * s).getlength("LIKE") + 120 * s)
    w2 = cta_comment(fr, t - 0.35, x + w1 + 16 * s, y, dur - 0.35, s, label="COMMENT") or int(font("bold", 28 * s).getlength("COMMENT") + 120 * s)
    w3 = cta_share(fr, t - 0.7, x + w1 + w2 + 32 * s, y, dur - 0.7, s) or int(font("bold", 28 * s).getlength("SHARE") + 120 * s)
    cta_subscribe(fr, t - 1.05, x + w1 + w2 + w3 + 48 * s, y - 2 * s, dur - 1.05, s * 0.95)


# ---------------------------------------------------------------------------------------------- transitions
def flash(fr, p):
    """Light leak around a cut: p in [-1, 1], 0 = the cut. Warm gold bloom sweeping left -> right plus an exposure lift."""
    if p <= -1 or p >= 1:
        return fr
    H, W = fr.shape[:2]
    k = math.exp(-(p / 0.42) ** 2)
    q = 8
    yy, xx = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
    cx = (0.5 + 0.55 * p) * W / q
    blob = np.exp(-(((xx - cx) / (0.30 * W / q)) ** 2 + ((yy - 0.45 * H / q) / (0.75 * H / q)) ** 2))
    blob = cv2.resize(blob, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    warm = np.array([1.0, 0.80, 0.52], np.float32)
    fr[:] = 1 - (1 - fr) * (1 - np.clip(blob * k * 0.95, 0, 1) * warm)
    fr[:] = np.clip(fr * (1 + 0.35 * k), 0, 1)
    return fr


def whip(fr, p, direction=1):
    """Horizontal whip-pan blur around a cut (p in [-1, 1])."""
    if p <= -1 or p >= 1:
        return fr
    k = math.exp(-(p / 0.38) ** 2)
    n = int(1 + 180 * k)
    if n < 3:
        return fr
    out = cv2.blur(fr, (n | 1, 1))
    shift = -direction * p * 120 * k
    M = np.array([[1, 0, shift], [0, 1, 0]], np.float32)
    out = cv2.warpAffine(out, M, (fr.shape[1], fr.shape[0]), borderMode=cv2.BORDER_REFLECT)
    return out


def dip(fr, p):
    if p <= -1 or p >= 1:
        return fr
    return fr * (1 - math.exp(-(p / 0.45) ** 2))


# ---------------------------------------------------------------------------------------------- end screens
def render_end(t, W, H, bg, subtitle="THANKS FOR WATCHING"):
    """16:9 end card. Left: logo, name, thanks, subscribe button. Right: two empty slots for YouTube end-screen elements."""
    fr = bg.copy()
    a = ease_out(t / 0.6)
    lg = logo(250)
    blend(fr, lg, 230, 300 + (1 - a) * 20, a)
    m, base = text_mask(NAME, font("display", 64), tracking=14)
    blend(fr, fill_mask(m, CHROME), 230 + 125 - m.width / 2, 600 - base + 40, ease_out((t - 0.2) / 0.6))
    draw_kicker(fr, subtitle, 230 + 125 - text_mask(subtitle.upper(), font("bold", 20), tracking=4.4)[0].width / 2, 718,
                ease_out((t - 0.4) / 0.6), size=20)
    cta_subscribe(fr, max(t - 0.6, 0) + 1.25 if t > 0.6 else -1, 155, 790, dur=1e9)
    for i, (lbl, y0) in enumerate((("WATCH NEXT", 250), ("MORE FROM V CREATE", 600))):
        ai = ease_out((t - 0.3 - 0.15 * i) / 0.6)
        w, h = 760, 300
        box = rrect((w, h), (0, 0, w - 1, h - 1), 20, PAL["panel"], 0.35, outline=PAL["gold"] + (170,), width=2)
        blend(fr, box, 1040, y0 - 40 + (1 - ai) * 20, ai)
        draw_kicker(fr, lbl, 1060, y0 - 64, ai, size=18)
    return fr


def render_reel_outro(t, W, H, bg):
    fr = bg.copy()
    a = ease_out(t / 0.5)
    lg = logo(300)
    blend(fr, lg, W / 2 - 150, 560 + (1 - a) * 24, a)
    m, base = text_mask(NAME, font("display", 70), tracking=16)
    blend(fr, fill_mask(m, CHROME), W / 2 - m.width / 2, 930 - base, ease_out((t - 0.2) / 0.5))
    k = "FOLLOW FOR MORE"
    mk, bk = text_mask(k, font("bold", 26), tracking=6)
    blend(fr, fill_mask(mk, rgb=PAL["gold"]), W / 2 - mk.width / 2, 1010 - bk, ease_out((t - 0.35) / 0.5))
    cta_subscribe(fr, (t - 0.5) + 1.25 if t > 0.5 else -1, W / 2 - 250, 1080, dur=1e9)
    return fr


# ---------------------------------------------------------------------------------------------- deadline graphic
def render_deadline(t, W, H, bg, month="DECEMBER", day="31", kicker="DEADLINE", note="FREE UNTIL THEN"):
    """Calendar page: month band, a big Cinzel day number, a gold ring drawn around it, kicker above, note below."""
    fr = bg.copy()
    reel = H > W
    cx, cy = W / 2, H * (0.40 if reel else 0.50)
    pw, ph = (600, 680) if reel else (520, 590)
    a = ease_out(t / 0.5)
    k = ease_back(t / 0.6)
    page = rrect((pw, ph), (0, 0, pw - 1, ph - 1), 34, (238, 236, 232), 1.0)
    band = rrect((pw, int(ph * 0.24)), (0, 0, pw - 1, int(ph * 0.24) + 40), 34, (24, 24, 26), 1.0)
    page.alpha_composite(band.crop((0, 0, pw, int(ph * 0.24))), (0, 0))
    d = ImageDraw.Draw(page)
    d.text((pw / 2, ph * 0.12), month, font=font("display", ph * 0.085), fill=PAL["gold_hi"] + (255,), anchor="mm")
    d.text((pw / 2, ph * 0.60), day, font=font("display", ph * 0.46), fill=(24, 24, 26, 255), anchor="mm")
    for i in range(2):
        yy = ph * 0.05
        d.ellipse((pw * (0.28 + 0.36 * i) - 14, -6, pw * (0.28 + 0.36 * i) + 14, 30), fill=(150, 152, 158, 255))
    sc = lerp(0.85, 1.0, clamp01(k))
    pg = page.resize((int(pw * sc), int(ph * sc)), Image.LANCZOS) if sc != 1 else page
    shadow = rrect((pg.width + 80, pg.height + 80), (40, 60, pg.width + 40, pg.height + 60), 40, (0, 0, 0), 0.55).filter(ImageFilter.GaussianBlur(24))
    blend(fr, shadow, cx - pg.width / 2 - 40, cy - pg.height / 2 - 40, a)
    blend(fr, pg, cx - pg.width / 2, cy - pg.height / 2, a)
    # gold ring drawn around the day
    p = ease_io((t - 0.7) / 0.7)
    if p > 0:
        R = ph * 0.30
        lay = Image.new("RGBA", (int(R * 2 + 40), int(R * 2 + 40)), (0, 0, 0, 0))
        ImageDraw.Draw(lay).arc((20, 20, 20 + R * 2, 20 + R * 1.85), -100, -100 + 370 * p, fill=PAL["gold"] + (255,), width=12)
        blend_glow(fr, glow_of(lay, 10, 1.2), cx - lay.width / 2, cy + ph * 0.10 - lay.height / 2, 0.6)
        blend(fr, lay, cx - lay.width / 2, cy + ph * 0.10 - lay.height / 2)
    ka = ease_out((t - 0.3) / 0.5)
    mk, bk = text_mask(kicker, font("bold", 30 if reel else 26), tracking=10)
    blend(fr, fill_mask(mk, rgb=PAL["gold"]), cx - mk.width / 2, cy - ph / 2 - 70 - bk, ka)
    na = ease_out((t - 1.2) / 0.5)
    mn, bn = text_mask(note, font("display", 46 if reel else 40), tracking=8)
    blend(fr, fill_mask(mn, CHROME), cx - mn.width / 2, cy + ph / 2 + 90 - bn, na)
    return fr
