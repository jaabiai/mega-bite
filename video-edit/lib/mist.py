""""Mist" style kit: a moody thriller-film look for talking-head tech explainers.

Pairs with grade_moody.MoodyGrader (green, misty, desaturated).  Type: Big Shoulders Display (film-title condensed
headlines, 3D title), Albert Sans (captions, labels) and JetBrains Mono (kickers, chapter numbers), all OFL.
Colour: bone white text, one blood-red accent, moss and fog greys.  Captions reveal word by word in film-subtitle
style (key words in red).  App demos use a split frame: device on a dark misty field on the left, the presenter in a
tall panel on the right, so the speaker is never covered.  Cuts are film-burn dissolves.
"""
import math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gfx import ease_io, ease_out, ease_back, clamp01, lerp, blend
import text3d as T3

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")

BONE = (234, 229, 216)
INK = (8, 12, 10)
RED = (214, 58, 44)
MOSS = (132, 156, 124)
FOG = (176, 186, 178)
REDF = np.array(RED, np.float32) / 255
BONEF = np.array(BONE, np.float32) / 255

FILES = {"display": "BigShouldersDisplay-900.ttf", "display8": "BigShouldersDisplay-800.ttf", "text": "AlbertSans-600.ttf",
         "text7": "AlbertSans-700.ttf", "text8": "AlbertSans-800.ttf", "mono": "JetBrainsMono-700.ttf", "mono5": "JetBrainsMono-500.ttf"}
_F = {}


def font(kind, size):
    key = (kind, int(size))
    if key not in _F:
        _F[key] = ImageFont.truetype(os.path.join(FONT_DIR, FILES[kind]), int(size))
    return _F[key]


def fpath(kind):
    return os.path.join(FONT_DIR, FILES[kind])


# ---------------------------------------------------------------------------------------------- shading
def side_shade(W, H, reel, strength=0.55):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if reel:
        k = np.clip(1 - yy / (H * 0.40), 0, 1) ** 1.3 * strength
    else:
        k = np.clip(1 - xx / (W * 0.52), 0, 1) ** 1.2 * strength
        k = k + np.clip(1 - (H - yy) / (H * 0.30), 0, 1) ** 2 * 0.25 * np.clip(1 - xx / (W * 0.65), 0, 1)
    k = np.clip(k, 0, 0.8)[..., None]
    tint = np.array([0.80, 1.0, 0.92], np.float32)                  # the shade leans green-black, not neutral grey
    return (1 - k * tint).astype(np.float32)


# ---------------------------------------------------------------------------------------------- text
def _shadow(img, r=8, a=0.7):
    al = img.split()[3].filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * a))
    sh = Image.new("RGBA", img.size, INK + (0,))
    sh.putalpha(al)
    return Image.alpha_composite(sh, img)


_T = {}


def label(txt, kind, size, rgb=BONE, tracking=0.0, shadow=True):
    key = (txt, kind, size, rgb, tracking, shadow)
    if key in _T:
        return _T[key]
    ft = font(kind, size)
    pad = 22
    w = int(sum(ft.getlength(c) for c in txt) + tracking * size * max(len(txt) - 1, 0)) + 2 * pad
    asc, desc = ft.getmetrics()
    img = Image.new("RGBA", (w, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for c in txt:
        d.text((x, pad), c, font=ft, fill=tuple(rgb) + (255,))
        x += ft.getlength(c) + tracking * size
    if shadow:
        img = _shadow(img, max(size // 7, 4), 0.65)
    img.pad = pad
    _T[key] = img
    return img


def put(fr, img, x, y, alpha=1.0, anchor="lt"):
    p = getattr(img, "pad", 0)
    w, h = img.width - 2 * p, img.height - 2 * p
    if anchor[0] == "c":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    blend(fr, img, x - p, y - p, alpha)


def reveal(fr, img, x, y, k, alpha=1.0, anchor="lt", blur=True):
    """Text rises out of a mask line; a little motion blur while it moves (film-title reveal)."""
    if k <= 0.001 or alpha <= 0.01:
        return
    p = getattr(img, "pad", 0)
    w, h = img.width, img.height
    e = ease_out(k)
    off = int((1 - e) * (h - 2 * p) * 0.85)
    src = img
    if blur and e < 0.95:
        src = img.filter(ImageFilter.GaussianBlur((1 - e) * 3))
    sub = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sub.paste(src.crop((0, 0, w, h - off)), (0, off))
    m = np.zeros((h, w), np.float32)
    m[: h - p + 6] = 1
    a = np.asarray(sub.split()[3], np.float32) * m
    sub.putalpha(Image.fromarray(a.astype(np.uint8)))
    sub.pad = p
    put(fr, sub, x, y, alpha * min(1, e * 1.5), anchor)


# ---------------------------------------------------------------------------------------------- captions
def caption_img(words, act, age, keys, size, max_w, lines_max=2):
    """Film-subtitle captions: the layout is fixed for the whole chunk; words appear as they are spoken (a quick fade and
    rise), key words set in red Albert Sans ExtraBold; a thin red rule runs down the left edge of the block."""
    ft, fk = font("text", size), font("text8", size)
    space = ft.getlength(" ")
    meas = [(fk if i in keys else ft).getlength(w) for i, w in enumerate(words)]
    lines, cur, cw = [], [], 0.0
    for i in range(len(words)):
        if cur and cw + space + meas[i] > max_w:
            lines.append(cur); cur, cw = [], 0.0
        cur.append(i); cw += (space if len(cur) > 1 else 0) + meas[i]
    if cur:
        lines.append(cur)
    if len(lines) > lines_max:
        li = next((k for k, ln in enumerate(lines) if act in ln), 0)
        s0 = min(max(li - lines_max + 1, 0), len(lines) - lines_max)
        lines = lines[s0:s0 + lines_max]
    lh = int(size * 1.28)
    pad, rule = 26, 22
    tw = max(sum(meas[i] for i in ln) + space * (len(ln) - 1) for ln in lines)
    W_, H_ = int(tw + 2 * pad + rule), int(lh * len(lines) + 2 * pad)
    k = 2
    img = Image.new("RGBA", (W_ * k, H_ * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ftk, fkk = font("text", size * k), font("text8", size * k)
    d.rectangle([pad * k, (pad + size * 0.12) * k, (pad + 4) * k, (pad + lh * len(lines) - size * 0.22) * k], fill=RED + (235,))
    for li, ln in enumerate(lines):
        x = pad + rule
        y = pad + li * lh
        for i in ln:
            if i > act + 0:
                x += meas[i] + space
                continue
            a = 1.0 if i < act else ease_out(age / 0.18)
            dy = (1 - a) * size * 0.25
            col = RED if i in keys else BONE
            d.text((x * k, (y + dy) * k), words[i], font=fkk if i in keys else ftk, fill=tuple(col) + (int(255 * a),))
            x += meas[i] + space
    img = img.resize((W_, H_), Image.LANCZOS)
    img = _shadow(img, 10, 0.85)
    img.pad = pad
    return img


# ---------------------------------------------------------------------------------------------- chapter slate
def chapter(fr, t, dur, n, title, x, y, size=58):
    if t < 0 or t > dur + 0.4:
        return
    a = 1 - ease_io((t - dur) / 0.4)
    kick = label(f"CHAPTER {n:02d}", "mono", 20, RED, tracking=0.25)
    reveal(fr, kick, x, y, clamp01(t / 0.35), a)
    tt = label(title.upper(), "display", size, BONE, tracking=0.02)
    reveal(fr, tt, x, y + 30, clamp01((t - 0.1) / 0.45), a)
    wln = (tt.width - 2 * tt.pad) * ease_out((t - 0.3) / 0.6)
    if wln > 2:
        H, W = fr.shape[:2]
        yy = int(y + 30 + size * 1.08)
        x0, x1 = int(x), int(min(x + wln, W))
        fr[yy:yy + 3, x0:x1] = fr[yy:yy + 3, x0:x1] * (1 - a) + REDF * a


def _greedy(words, ft, max_w):
    out, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and ft.getlength(t) > max_w:
            out.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        out.append(cur)
    return out


def wrap(text, kind, size, max_w):
    """Greedy wrap to max_w, then balanced: the narrowest width that still needs the same number of lines (no orphans)."""
    ft = font(kind, size)
    words = text.split()
    best = _greedy(words, ft, max_w)
    n = len(best)
    if n > 1:
        w = max_w
        while w > 80:
            w -= 8
            trial = _greedy(words, ft, w)
            if len(trial) > n:
                break
            best = trial
    return best


def key_line(fr, t, dur, text, x, y, size=46, max_w=None, kicker="NOTE"):
    """A key phrase: mono kicker 'NOTE' + bone phrase (wrapped to max_w) with a red underline under the last line."""
    if t < 0 or t > dur + 0.35:
        return
    a = 1 - ease_io((t - dur) / 0.35)
    kick = label(kicker, "mono", 18 if size < 50 else 22, FOG, tracking=0.3)
    reveal(fr, kick, x, y, clamp01(t / 0.3), a)
    lines = wrap(text, "text8", size, max_w) if max_w else [text]
    lh = size * 1.16
    wmax = 0
    for k, ln in enumerate(lines):
        tt = label(ln, "text8", size, BONE)
        reveal(fr, tt, x, y + 28 + k * lh, clamp01((t - 0.08 - 0.06 * k) / 0.4), a)
        wmax = max(wmax, tt.width - 2 * tt.pad)
    wln = wmax * ease_out((t - 0.25) / 0.5)
    if wln > 2:
        H, W = fr.shape[:2]
        yy = int(y + 28 + (len(lines) - 1) * lh + size * 1.12)
        fr[yy:yy + 3, int(x):int(min(x + wln, W))] = fr[yy:yy + 3, int(x):int(min(x + wln, W))] * (1 - a) + REDF * a


# ---------------------------------------------------------------------------------------------- phone marks
def spotlight(fr, rect, a, radius=20, dim=0.6):
    if a <= 0.01:
        return
    H, W = fr.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    m = np.zeros((H // 2, W // 2), np.float32)
    cv2.rectangle(m, (x0 // 2, y0 // 2), (x1 // 2, y1 // 2), 1.0, -1)
    m = cv2.resize(cv2.GaussianBlur(m, (0, 0), radius / 2), (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    fr *= 1 - dim * a * (1 - m)


def brackets(fr, rect, t, a=1.0, width=4):
    """Red corner brackets that close in on the rect, plus a hairline box."""
    if a <= 0.01:
        return
    H, W = fr.shape[:2]
    x0, y0, x1, y1 = rect
    g = ease_out(t / 0.35)
    off = (1 - g) * 26
    L = max(min((x1 - x0), (y1 - y0)) * 0.35, 14)
    col = tuple(float(c) for c in REDF)
    pts = []
    for (cx, cy, sx, sy) in ((x0 - off, y0 - off, 1, 1), (x1 + off, y0 - off, -1, 1), (x0 - off, y1 + off, 1, -1), (x1 + off, y1 + off, -1, -1)):
        pts.append([(cx + sx * L, cy), (cx, cy), (cx, cy + sy * L)])
    k = 4
    bx0, by0 = int(max(x0 - 40, 0)), int(max(y0 - 40, 0))
    bx1, by1 = int(min(x1 + 40, W)), int(min(y1 + 40, H))
    if bx1 <= bx0 or by1 <= by0:
        return
    m = np.zeros(((by1 - by0) * k, (bx1 - bx0) * k), np.uint8)
    for p3 in pts:
        arr = ((np.array(p3) - [bx0, by0]) * k).astype(np.int32)
        cv2.polylines(m, [arr], False, 255, int(width * k), cv2.LINE_AA)
    hair = np.zeros_like(m)
    cv2.rectangle(hair, (int((x0 - bx0) * k), int((y0 - by0) * k)), (int((x1 - bx0) * k), int((y1 - by0) * k)), 255, int(1.5 * k), cv2.LINE_AA)
    mm = cv2.resize(m, (bx1 - bx0, by1 - by0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * a
    hh = cv2.resize(hair, (bx1 - bx0, by1 - by0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * a * 0.6 * g
    reg = fr[by0:by1, bx0:bx1]
    reg[:] = reg * (1 - hh) + BONEF * hh
    reg[:] = reg * (1 - mm) + REDF * mm


def tag(fr, rect, text, t, a=1.0, side="right", size=26, xmin=10, xmax=None, below=True):
    """Mono label on a dark plate joined to the rect by a short red line (below the rect, or skipped when below=False,
    if neither side has room)."""
    if a <= 0.01 or not text:
        return
    H, W = fr.shape[:2]
    xmax = xmax or W
    x0, y0, x1, y1 = rect
    lab = label(text.upper(), "mono", size, BONE, tracking=0.08)
    lw = lab.width - 2 * lab.pad
    cy = (y0 + y1) / 2
    fits_r = x1 + 60 + lw + 20 < xmax
    fits_l = x0 - 60 - lw - 20 > xmin
    if side == "right" and not fits_r and fits_l:
        side = "left"
    elif side == "left" and not fits_l and fits_r:
        side = "right"
    elif not fits_r and not fits_l:
        if not below:
            return
        reveal(fr, lab, min(max((x0 + x1) / 2 - lw / 2, xmin + 6), xmax - lw - 6), y1 + 18, clamp01((t - 0.1) / 0.35), a)
        return
    g = ease_out(t / 0.3)
    sx = x1 + 6 if side == "right" else x0 - 6
    ex = sx + (50 if side == "right" else -50) * g
    yy = int(cy)
    xa, xb = int(min(sx, ex)), int(max(sx, ex))
    if xb > xa:
        fr[yy - 1:yy + 2, max(xa, 0):min(xb, W)] = fr[yy - 1:yy + 2, max(xa, 0):min(xb, W)] * (1 - a) + REDF * a
    tx = sx + 62 if side == "right" else sx - 62 - lw
    # plate
    ph = size + 18
    px0, px1 = int(tx - 12), int(tx + lw + 12)
    py0, py1 = int(cy - ph / 2), int(cy + ph / 2)
    px0, px1 = max(px0, 0), min(px1, W)
    if px1 > px0:
        k = clamp01((t - 0.12) / 0.3) * a
        fr[py0:py1, px0:px1] = fr[py0:py1, px0:px1] * (1 - 0.72 * k) + np.array(INK, np.float32) / 255 * 0.72 * k
    reveal(fr, lab, tx, cy - size * 0.62, clamp01((t - 0.12) / 0.35), a)


def tap(fr, x, y, t):
    if t < -0.1 or t > 0.9:
        return
    H, W = fr.shape[:2]
    R = 64
    x0, y0 = int(x - R), int(y - R)
    if x0 < 0 or y0 < 0 or x0 + 2 * R > W or y0 + 2 * R > H:
        return
    k = 4
    m1 = np.zeros((2 * R * k, 2 * R * k), np.uint8)
    m2 = np.zeros_like(m1)
    press = ease_out((t + 0.1) / 0.1) * (1 - ease_io((t - 0.28) / 0.3))
    cv2.circle(m1, (R * k, R * k), int(15 * k), 255, -1, cv2.LINE_AA)
    if t > 0:
        cv2.circle(m2, (R * k, R * k), int((18 + 40 * ease_out(t / 0.6)) * k), 255, int(3 * k), cv2.LINE_AA)
    reg = fr[y0:y0 + 2 * R, x0:x0 + 2 * R]
    for m, col, al in ((m1, BONE, 0.6 * press), (m2, RED, 0.95 * (1 - clamp01(t / 0.9)))):
        mm = cv2.resize(m, (2 * R, 2 * R), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * al
        reg[:] = reg * (1 - mm) + np.array(col, np.float32) / 255 * mm


# ---------------------------------------------------------------------------------------------- logo / prompts
_BUG = {}


def logo_bug(size, path):
    key = (size, path)
    if key in _BUG:
        return _BUG[key]
    lg = Image.open(path).convert("RGBA")
    bb = lg.split()[3].getbbox() or (0, 0, lg.width, lg.height)
    lg = lg.crop(bb)
    s = max(lg.size)
    sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sq.paste(lg, ((s - lg.width) // 2, (s - lg.height) // 2))
    out = sq.resize((size, size), Image.LANCZOS)
    pad = 14
    img = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    img.paste(out, (pad, pad), out)
    img = _shadow(img, 8, 0.6)
    _BUG[key] = img
    return img


def cta(fr, kind, t, x, y, scale=1.0, dur=3.3):
    """Hairline bone pill with an icon; a click fills it red ('SUBSCRIBED', 'SHARED', ...)."""
    import pop
    if t < 0 or t > dur + 0.4:
        return
    spec = {"subscribe": ("SUBSCRIBE", "SUBSCRIBED", pop.ic_bell), "like": ("LIKE", "LIKED", pop.ic_thumb),
            "share": ("SHARE", "SHARED", pop.ic_share), "comment": ("COMMENT", "COMMENT", pop.ic_chat),
            "follow": ("FOLLOW", "FOLLOWING", pop.ic_star)}[kind]
    t_click = 1.2
    done = t >= t_click
    txt = spec[1] if done else spec[0]
    h = int(68 * scale)
    ft = font("mono", int(26 * scale))
    w = int(sum(ft.getlength(c) for c in txt) + 0.12 * 26 * scale * len(txt) + h * 1.5)
    k = 3
    img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if done:
        d.rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=h * k // 2, fill=RED + (255,))
    else:
        d.rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=h * k // 2, fill=INK + (150,), outline=BONE + (230,), width=2 * k)
    spec[2](d, h * 0.30 * k, h * 0.5 * k, h * 0.52 * k, BONE)
    xx = h * 0.95 * k
    for c in txt:
        d.text((xx, h * 0.5 * k), c, font=font("mono", int(26 * scale) * k), fill=BONE + (255,), anchor="lm")
        xx += font("mono", int(26 * scale) * k).getlength(c) + 0.12 * 26 * scale * k
    img = img.resize((w, h), Image.LANCZOS)
    k_in, k_out = ease_out(t / 0.45), ease_io((t - dur) / 0.4)
    a = clamp01(t / 0.2) * (1 - k_out)
    blend(fr, img, x + (1 - k_in) * -30 + k_out * -30, y - h / 2, a)


# ---------------------------------------------------------------------------------------------- transitions
def burn_mix(a, b, p):
    """Film-burn dissolve: a warm light leak sweeps across while a crossfades into b (p 0..1)."""
    H, W = a.shape[:2]
    e = ease_io(p)
    bump = math.sin(math.pi * clamp01(p))
    out = a * (1 - e) + b * e
    xx = np.linspace(0, 1, W // 8, dtype=np.float32)[None, :]
    yy = np.linspace(0, 1, H // 8, dtype=np.float32)[:, None]
    cx = lerp(-0.2, 1.2, e)
    g = np.exp(-(((xx - cx) / 0.28) ** 2 + ((yy - 0.45) / 0.9) ** 2)) * bump
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    leak = np.array([1.0, 0.55, 0.30], np.float32)
    return np.clip(1 - (1 - out) * (1 - g * 0.55 * leak), 0, 1)


# ---------------------------------------------------------------------------------------------- 3D title
class MistTitle:
    """Extruded Big Shoulders title set in the free column (never over the presenter): bone face with a red accent line,
    moss-black sides, a slow turn toward the speaker; a mono kicker above, a sub-line below."""

    def __init__(self, W, H, beats, cx, cy, box):
        self.W, self.H, self.cx, self.cy = W, H, cx, cy
        fp = fpath("display")
        faces = {"bone": ("v", [(0.0, (250, 247, 238)), (0.6, BONE), (1.0, (196, 190, 176))]),
                 "red": ("v", [(0.0, (240, 96, 76)), (0.6, RED), (1.0, (150, 36, 28))])}
        side = [(0.0, (20, 28, 24)), (0.5, (44, 58, 50)), (1.0, (16, 22, 18))]
        self.beats = []
        for b in beats:
            t0, t1, lines = b[:3]
            o = b[3] if len(b) > 3 else {}
            ln = [(txt, faces[st], rel) for txt, st, rel in lines]
            bw, bh = o.get("box", box)
            size = T3.fit_size(ln, fp, W * bw, H * bh, line_gap=0.86, tracking=0.01)
            blk = T3.Block(ln, fp, size, side, depth=0.14, layers=20, line_gap=0.86, tracking=0.01)
            self.beats.append((t0, t1, blk, o))

    def span(self):
        return self.beats[0][0], self.beats[-1][1]

    def draw(self, fr, t):
        W, H = self.W, self.H
        for bi, (t0, t1, blk, o) in enumerate(self.beats):
            last = bi == len(self.beats) - 1
            if not (t0 - 0.05 <= t < t1 + (0.4 if last else 0.02)):
                continue
            tt, dur = t - t0, t1 - t0
            k_in = ease_out(tt / 0.7)
            k_out = ease_io((tt - dur) / 0.4) if last else ease_io((tt - (dur - 0.2)) / 0.2)
            yaw = lerp(32, 12, k_in) - 4 * clamp01(tt / max(dur, 0.01)) - 30 * k_out
            pitch = lerp(10, 3, k_in)
            scale = lerp(0.86, 1.0, ease_out(tt / 0.8)) * (1 + 0.02 * clamp01(tt / max(dur, 0.01)))
            alpha = clamp01((tt + 0.05) / 0.25) * (1 - k_out)
            cx, cy = W * self.cx, H * self.cy
            sw = (tt - 0.6) / 1.0
            lay = blk.render(W, H, yaw=yaw, pitch=pitch, scale=scale, cx=cx, cy=cy, sweep=sw if 0 < sw < 1 else None, alpha=alpha)
            T3.shadow_and_glow(fr, lay, shadow=0.65 * alpha, glow=0.10 * alpha, offset=(0, int(H * 0.018)), tint=(1.0, 0.4, 0.3))
            T3.composite(fr, lay)
            bh, bw = blk.h * scale, blk.w * scale
            if o.get("kicker"):
                kk = label(o["kicker"], "mono", int(H * (0.023 if W > H else 0.016)), RED, tracking=0.24)
                reveal(fr, kk, cx, cy - bh / 2 - H * 0.045, clamp01((tt - 0.2) / 0.4), alpha, "ct")
            if o.get("sub"):
                st = label(o["sub"], "text", int(H * (0.034 if W > H else 0.024)), FOG)
                reveal(fr, st, cx, cy + bh / 2 + H * 0.012, clamp01((tt - 0.4) / 0.5), alpha, "ct")
