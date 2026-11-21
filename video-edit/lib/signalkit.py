""""Signal" style kit: a cinematic, keynote-grade explainer look.

The picture runs full-bleed with a cinematic grade; a soft graphite shade on the free side of the frame carries
everything else.  Type is Geist (headlines, captions), Geist Mono (labels) and Instrument Serif Italic for the words
that matter.  One accent: electric lime.  Tips are counted with a numbered ring that fills from the first word of a
tip to its last.  All OFL fonts in assets/fonts.
"""
import math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gfx import ease_io, ease_out, ease_back, clamp01, lerp, blend
import text3d as T3

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")

INK = (10, 12, 14)
LIME = (198, 255, 61)
LIME_D = (120, 168, 20)
WHITE = (246, 247, 243)
MUTE = (160, 166, 160)
GRAPH = (22, 25, 28)
LIMEF = np.array(LIME, np.float32) / 255
INKF = np.array(INK, np.float32) / 255

_F = {}
FILES = {"black": "Geist-900.ttf", "bold": "Geist-800.ttf", "semi": "Geist-700.ttf", "text": "Geist-600.ttf",
         "mono": "GeistMono-700.ttf", "mono5": "GeistMono-500.ttf", "serif": "InstrumentSerif-Italic.ttf"}


def font(kind, size):
    key = (kind, int(size))
    if key not in _F:
        _F[key] = ImageFont.truetype(os.path.join(FONT_DIR, FILES[kind]), int(size))
    return _F[key]


def fpath(kind):
    return os.path.join(FONT_DIR, FILES[kind])


# ---------------------------------------------------------------------------------------------- shades
def side_shade(W, H, reel, strength=0.62):
    """Multiplicative shade (HxWx1) darkening the free side: the left ~45 % in 16:9, the top ~40 % in 9:16."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if reel:
        d = np.clip(1 - yy / (H * 0.42), 0, 1)
        k = d ** 1.4 * strength + np.clip(1 - (H - yy) / (H * 0.16), 0, 1) ** 2 * 0.35
    else:
        d = np.clip(1 - xx / (W * 0.50), 0, 1)
        k = d ** 1.25 * strength + np.clip(1 - (H - yy) / (H * 0.32), 0, 1) ** 2 * 0.28 * np.clip(1 - xx / (W * 0.7), 0, 1)
    return (1 - np.clip(k, 0, 0.82))[..., None].astype(np.float32)


# ---------------------------------------------------------------------------------------------- text helpers
def _shadowed(img, radius=10, alpha=0.55):
    """Add a soft dark shadow under an RGBA text layer (keeps the size, so pad the layer beforehand)."""
    a = img.split()[3].filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: int(v * alpha))
    sh = Image.new("RGBA", img.size, INK + (0,))
    sh.putalpha(a)
    return Image.alpha_composite(sh, img)


def text_img(txt, kind, size, rgb=WHITE, tracking=0.0, shadow=True, pad=24):
    ft = font(kind, size)
    w = int(sum(ft.getlength(c) for c in txt) + tracking * size * max(len(txt) - 1, 0)) + 2 * pad
    asc, desc = ft.getmetrics()
    h = asc + desc + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for c in txt:
        d.text((x, pad), c, font=ft, fill=tuple(rgb) + (255,))
        x += ft.getlength(c) + tracking * size
    if shadow:
        img = _shadowed(img, radius=max(size // 6, 4), alpha=0.6)
    img.pad = pad
    return img


_TXT = {}


def label(txt, kind, size, rgb=WHITE, tracking=0.0, shadow=True):
    key = (txt, kind, size, rgb, tracking, shadow)
    if key not in _TXT:
        _TXT[key] = text_img(txt, kind, size, rgb, tracking, shadow)
    return _TXT[key]


def put(fr, img, x, y, alpha=1.0, anchor="lt"):
    """Place a text image so its text box (without padding) starts at (x, y).  anchor: lt | ct | rt | lm."""
    p = getattr(img, "pad", 0)
    w, h = img.width - 2 * p, img.height - 2 * p
    if anchor[0] == "c":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    blend(fr, img, x - p, y - p, alpha)


def reveal(fr, img, x, y, k, alpha=1.0, anchor="lt"):
    """Masked rise: the text slides up out of an invisible line (k 0 -> 1)."""
    if k <= 0.001 or alpha <= 0.01:
        return
    p = getattr(img, "pad", 0)
    w, h = img.width, img.height
    off = int((1 - ease_out(k)) * (h - 2 * p) * 0.9)
    crop = img.crop((0, 0, w, h - off))
    crop.pad = p
    sub = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sub.paste(crop, (0, off))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rectangle([0, 0, w, h - p + 6], fill=255)
    sub.putalpha(Image.fromarray((np.asarray(sub.split()[3], np.float32) * np.asarray(m, np.float32) / 255).astype(np.uint8)))
    sub.pad = p
    put(fr, sub, x, y, alpha, anchor)


# ---------------------------------------------------------------------------------------------- captions
def caption_img(words, act, age, keys, size, max_w, lines_max=2, align="left"):
    """Karaoke caption: words already spoken in white, the current one white with a lime underline that grows, words
    still to come in faded white; key words (indices in `keys`) set in lime Instrument Serif Italic.  PIL RGBA."""
    ft = font("semi", size)
    fk = font("serif", int(size * 1.16))
    space = ft.getlength(" ")
    meas = [(fk if i in keys else ft).getlength(w) for i, w in enumerate(words)]
    lines, cur, cw = [], [], 0.0
    for i, w in enumerate(words):
        if cur and cw + space + meas[i] > max_w:
            lines.append(cur); cur, cw = [], 0.0
        cur.append(i); cw += (space if len(cur) > 1 else 0) + meas[i]
    if cur:
        lines.append(cur)
    if len(lines) > lines_max:
        li = next((k for k, ln in enumerate(lines) if act in ln), 0)
        s0 = min(max(li - lines_max + 1, 0), len(lines) - lines_max)
        lines = lines[s0:s0 + lines_max]
    lh = int(size * 1.30)
    pad = 26
    tw = max(sum(meas[i] for i in ln) + space * (len(ln) - 1) for ln in lines)
    W_, H_ = int(tw + 2 * pad), int(lh * len(lines) + 2 * pad)
    k = 2
    img = Image.new("RGBA", (W_ * k, H_ * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ftk, fkk = font("semi", size * k), font("serif", int(size * 1.16) * k)
    asc = ft.getmetrics()[0]
    for li, ln in enumerate(lines):
        lw = sum(meas[i] for i in ln) + space * (len(ln) - 1)
        x = pad + ((tw - lw) / 2 if align == "center" else 0)
        y = pad + li * lh
        for i in ln:
            key = i in keys
            f_ = fkk if key else ftk
            col = LIME if key else WHITE
            a = 255 if i <= act else 96
            dy = -size * 0.10 if key else 0
            d.text((x * k, (y + dy) * k), words[i], font=f_, fill=tuple(col) + (a,))
            if i == act and not key:
                g = ease_out(age / 0.16)
                d.rounded_rectangle([x * k, (y + asc + size * 0.16) * k, (x + meas[i] * g) * k, (y + asc + size * 0.16 + 4) * k],
                                    radius=2 * k, fill=LIME + (255,))
            x += meas[i] + space
    img = img.resize((W_, H_), Image.LANCZOS)
    img = _shadowed(img, radius=9, alpha=0.75)
    img.pad = pad
    return img


# ---------------------------------------------------------------------------------------------- tip counter
_RING = {}


def ring_img(r, width, progress, track_a=0.22, glow=False):
    """Antialiased progress ring (PIL RGBA, size 2r+pad): faint white track, lime arc from 12 o'clock clockwise."""
    key = (r, width, round(progress, 3), glow)
    if key in _RING:
        return _RING[key]
    k = 4
    pad = 16
    S = 2 * (r + pad)
    img = Image.new("RGBA", (S * k, S * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = [pad * k, pad * k, (S - pad) * k, (S - pad) * k]
    d.ellipse(box, outline=WHITE + (int(255 * track_a),), width=width * k)
    if progress > 0.002:
        end = -90 + 360 * min(progress, 1.0)
        d.arc(box, -90, end, fill=LIME + (255,), width=width * k)
        # round caps
        for ang in (-90, end):
            a = math.radians(ang)
            cx = S * k / 2 + (r - width / 2) * k * math.cos(a)
            cy = S * k / 2 + (r - width / 2) * k * math.sin(a)
            d.ellipse([cx - width * k / 2, cy - width * k / 2, cx + width * k / 2, cy + width * k / 2], fill=LIME + (255,))
    out = img.resize((S, S), Image.LANCZOS)
    if glow:
        g = out.filter(ImageFilter.GaussianBlur(8))
        out = Image.alpha_composite(g, out)
    if len(_RING) > 600:
        _RING.clear()
    _RING[key] = out
    return out


def tip_counter(fr, cx, cy, n, progress, title, t_in, t_out=None, r=54, title_size=34, reel=False):
    """Numbered ring (cx, cy centre) that fills with `progress`, kicker 'TIP 0n' and the tip title to its right.
    t_in: seconds since the tip began (entry animation); t_out: seconds since it ended (exit), None while running."""
    k_in = ease_out(t_in / 0.5)
    a = clamp01(t_in / 0.25)
    if t_out is not None:
        a *= 1 - ease_io((t_out - 0.6) / 0.35)
    if a <= 0.01:
        return
    done_flash = math.exp(-((t_out - 0.15) / 0.18) ** 2) if t_out is not None and t_out > 0 else 0.0
    rg = ring_img(r, 6, progress if t_out is None else 1.0, glow=done_flash > 0.05)
    s = lerp(0.6, 1.0, ease_back(clamp01(t_in / 0.45), 1.6)) * (1 + 0.08 * done_flash)
    if abs(s - 1) > 1e-3:
        rg = rg.resize((max(int(rg.width * s), 2), max(int(rg.height * s), 2)), Image.BICUBIC)
    # dark disc behind the ring for legibility
    disc = Image.new("RGBA", rg.size, (0, 0, 0, 0))
    rr = (rg.width / 2) - 16 * s
    ImageDraw.Draw(disc).ellipse([rg.width / 2 - rr, rg.height / 2 - rr, rg.width / 2 + rr, rg.height / 2 + rr], fill=INK + (150,))
    blend(fr, disc, cx - rg.width / 2, cy - rg.height / 2, a)
    blend(fr, rg, cx - rg.width / 2, cy - rg.height / 2, a)
    num = label(str(n), "black", int(r * 1.18), WHITE if done_flash < 0.5 else LIME, shadow=False)
    put(fr, num, cx, cy - r * 0.02, a * min(1, k_in * 1.4), "cm")
    # labels
    x = cx + r + 26
    kick = label(f"TIP 0{n}" if n < 10 else f"TIP {n}", "mono", 22 if not reel else 24, LIME, tracking=0.18)
    reveal(fr, kick, x, cy - r * 0.62, clamp01((t_in - 0.12) / 0.4), a)
    if title:
        tt = label(title, "semi", title_size, WHITE)
        reveal(fr, tt, x, cy - r * 0.10, clamp01((t_in - 0.22) / 0.45), a)


# ---------------------------------------------------------------------------------------------- tip card
def tip_card(fr, t, dur, n, title, sub=None, reel=False):
    """Full-frame tip opener over the (already dimmed) frame: a big numeral inside a ring that sweeps once, the kicker
    and the tip title in serif italic."""
    H, W = fr.shape[:2]
    if t < 0 or t > dur + 0.3:
        return
    k_out = ease_io((t - dur) / 0.3)
    a = clamp01(t / 0.2) * (1 - k_out)
    cx, cy = (W / 2, H * 0.40) if reel else (W * 0.5, H * 0.42)
    R = int(min(W, H) * (0.20 if reel else 0.19))
    prog = ease_io(clamp01((t - 0.1) / (dur * 0.7)))
    rg = ring_img(R, 10, prog, track_a=0.18, glow=True)
    s = lerp(0.85, 1.0, ease_out(t / 0.6)) * (1 + 0.12 * k_out)
    rg2 = rg.resize((int(rg.width * s), int(rg.height * s)), Image.BICUBIC)
    blend(fr, rg2, cx - rg2.width / 2, cy - rg2.height / 2, a)
    num = label(f"{n:02d}", "black", int(R * 1.05), WHITE, tracking=-0.02)
    reveal(fr, num, cx, cy - R * 0.55, clamp01((t - 0.05) / 0.45), a, "ct")
    kick = label(f"TIP {n:02d}  /  02", "mono", 26 if not reel else 30, LIME, tracking=0.2)
    ty = cy + R + (60 if not reel else 70)
    reveal(fr, kick, cx, ty, clamp01((t - 0.2) / 0.4), a, "ct")
    tt = label(title, "serif", 86 if not reel else 84, WHITE)
    reveal(fr, tt, cx, ty + 46, clamp01((t - 0.32) / 0.5), a, "ct")
    if sub:
        st = label(sub, "text", 30 if not reel else 34, MUTE)
        reveal(fr, st, cx, ty + 46 + (118 if not reel else 112), clamp01((t - 0.45) / 0.5), a, "ct")


# ---------------------------------------------------------------------------------------------- key point
def key_point(fr, t, dur, text, x, y, size=64, kicker="KEY POINT", max_w=None):
    """Key phrase in lime serif italic with a mono kicker and an underline that sweeps in."""
    if t < 0 or t > dur + 0.35:
        return
    k_out = ease_io((t - dur) / 0.35)
    a = 1 - k_out
    kk = label(kicker, "mono", 20, MUTE, tracking=0.22)
    reveal(fr, kk, x, y, clamp01(t / 0.35), a)
    tt = label(text, "serif", size, LIME)
    reveal(fr, tt, x, y + 34, clamp01((t - 0.08) / 0.45), a)
    w = (tt.width - 2 * tt.pad) * ease_out((t - 0.25) / 0.5)
    if w > 2:
        H, W = fr.shape[:2]
        y0 = int(y + 34 + size * 1.05)
        x0, x1 = int(x), int(min(x + w, W))
        fr[y0:y0 + 3, x0:x1] = fr[y0:y0 + 3, x0:x1] * (1 - 0.9 * a) + LIMEF * 0.9 * a


# ---------------------------------------------------------------------------------------------- phone marks
def spotlight(fr, rect, a, radius=22, dim=0.55):
    if a <= 0.01:
        return
    H, W = fr.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    m = np.zeros((H // 2, W // 2), np.float32)
    cv2.rectangle(m, (x0 // 2, y0 // 2), (x1 // 2, y1 // 2), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), radius / 2)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    fr *= 1 - dim * a * (1 - m)


def frame_box(fr, rect, t, a=1.0, radius=18, width=4):
    """Lime rounded outline that draws around the rect (corner brackets first, then the full box)."""
    if a <= 0.01:
        return
    H, W = fr.shape[:2]
    x0, y0, x1, y1 = rect
    pad = 30
    bx0, by0 = int(max(x0 - pad, 0)), int(max(y0 - pad, 0))
    bx1, by1 = int(min(x1 + pad, W)), int(min(y1 + pad, H))
    if bx1 <= bx0 or by1 <= by0:
        return
    k = 3
    img = Image.new("L", ((bx1 - bx0) * k, (by1 - by0) * k), 0)
    d = ImageDraw.Draw(img)
    g = ease_out(t / 0.35)
    s = lerp(1.08, 1.0, g)
    cx, cy = (x0 + x1) / 2 - bx0, (y0 + y1) / 2 - by0
    hw, hh = (x1 - x0) / 2 * s, (y1 - y0) / 2 * s
    d.rounded_rectangle([(cx - hw) * k, (cy - hh) * k, (cx + hw) * k, (cy + hh) * k], radius=radius * k, outline=255, width=width * k)
    m = np.asarray(img.resize((bx1 - bx0, by1 - by0), Image.LANCZOS), np.float32)[..., None] / 255 * a * clamp01(t / 0.15)
    reg = fr[by0:by1, bx0:bx1]
    reg[:] = reg * (1 - m) + LIMEF * m


def tap(fr, x, y, t):
    if t < -0.12 or t > 0.9:
        return
    H, W = fr.shape[:2]
    R = 64
    x0, y0 = int(x - R), int(y - R)
    if x0 < 0 or y0 < 0 or x0 + 2 * R > W or y0 + 2 * R > H:
        return
    k = 4
    m1 = np.zeros((2 * R * k, 2 * R * k), np.uint8)
    m2 = np.zeros_like(m1)
    press = ease_out((t + 0.12) / 0.12) * (1 - ease_io((t - 0.3) / 0.3))
    cv2.circle(m1, (R * k, R * k), int(17 * k), 255, -1, cv2.LINE_AA)
    if t > 0:
        cv2.circle(m2, (R * k, R * k), int((20 + 40 * ease_out(t / 0.6)) * k), 255, int(3 * k), cv2.LINE_AA)
    reg = fr[y0:y0 + 2 * R, x0:x0 + 2 * R]
    for m, col, al in ((m1, WHITE, 0.55 * press), (m2, LIME, 0.95 * (1 - clamp01(t / 0.9)))):
        mm = cv2.resize(m, (2 * R, 2 * R), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * al
        reg[:] = reg * (1 - mm) + np.array(col, np.float32) / 255 * mm


def callout(fr, rect, text, t, a=1.0, side="right", size=30, max_x=None):
    """Leader line from the rect edge to a lime-dot label."""
    if a <= 0.01:
        return
    H, W = fr.shape[:2]
    x0, y0, x1, y1 = rect
    cy = (y0 + y1) / 2
    lab = label(text, "semi", size, WHITE)
    lw = lab.width - 2 * lab.pad
    W_lim = max_x or W
    fits_r = x1 + 70 + 18 + lw <= W_lim - 10
    fits_l = x0 - 70 - 18 - lw >= 10
    if side == "right" and not fits_r and fits_l:
        side = "left"
    elif side == "left" and not fits_l and fits_r:
        side = "right"
    elif not fits_r and not fits_l:                      # neither side: put the label just under the rect
        g = ease_out(t / 0.35)
        reveal(fr, lab, min(max((x0 + x1) / 2 - lw / 2, 12), W_lim - lw - 12), y1 + 14, clamp01((t - 0.1) / 0.35), a)
        return
    if side == "right":
        sx, ex = x1 + 8, x1 + 70
    else:
        sx, ex = x0 - 8, x0 - 70
    g = ease_out(t / 0.35)
    ex_ = lerp(sx, ex, g)
    yy = int(cy)
    xa, xb = int(min(sx, ex_)), int(max(sx, ex_))
    if xb > xa:
        fr[yy - 1:yy + 2, max(xa, 0):min(xb, W)] = fr[yy - 1:yy + 2, max(xa, 0):min(xb, W)] * (1 - a) + LIMEF * a
    cv2.circle(fr, (int(ex_), yy), 6, tuple(float(c) for c in LIMEF), -1, cv2.LINE_AA)
    tx = ex + 18 if side == "right" else ex - 18 - lw
    reveal(fr, lab, tx, cy - size * 0.62, clamp01((t - 0.15) / 0.35), a)


# ---------------------------------------------------------------------------------------------- logo / CTA
_BUG = {}


def logo_bug(size, path):
    key = (size, path)
    if key in _BUG:
        return _BUG[key]
    lg = Image.open(path).convert("RGBA")
    bb = lg.split()[3].getbbox() or (0, 0, lg.width, lg.height)
    lg = lg.crop(bb)
    side = max(lg.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(lg, ((side - lg.width) // 2, (side - lg.height) // 2))
    out = sq.resize((size, size), Image.LANCZOS)
    pad = 14
    img = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    img.paste(out, (pad, pad), out)
    img = _shadowed(img, radius=8, alpha=0.6)
    _BUG[key] = img
    return img


def _pill(w, h, fill, alpha, outline=None):
    k = 3
    img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=h * k // 2, fill=tuple(fill) + (int(255 * alpha),),
                        outline=(tuple(outline) + (255,)) if outline else None, width=2 * k if outline else 0)
    return img.resize((w, h), Image.LANCZOS)


def cta(fr, kind, t, x, y, scale=1.0, dur=3.3):
    """Glass pill with an icon: slides in, a click turns it lime ('SUBSCRIBED', 'LIKED', ...), slides out."""
    import pop
    if t < 0 or t > dur + 0.4:
        return
    spec = {"subscribe": ("Subscribe", "Subscribed", pop.ic_bell), "like": ("Like", "Liked", pop.ic_thumb),
            "share": ("Share", "Shared", pop.ic_share), "comment": ("Comment", "Comment", pop.ic_chat),
            "follow": ("Follow", "Following", pop.ic_star)}[kind]
    t_click = 1.2
    done = t >= t_click
    txt = spec[1] if done else spec[0]
    size = int(34 * scale)
    h = int(76 * scale)
    ft = font("semi", size)
    w = int(ft.getlength(txt) + h * 1.55 + 24 * scale)
    pill = _pill(w, h, LIME if done else (18, 20, 22), 1.0 if done else 0.78, None if done else (90, 96, 92))
    d = ImageDraw.Draw(pill)
    k = 3
    ic = Image.new("RGBA", (h * k, h * k), (0, 0, 0, 0))
    spec[2](ImageDraw.Draw(ic), h * 0.30 * k, h * 0.5 * k, h * 0.56 * k, INK if done else LIME)
    ic = ic.resize((h, h), Image.LANCZOS)
    pill.alpha_composite(ic, (int(h * 0.08), 0))
    d.text((h * 0.95, h / 2), txt, font=ft, fill=tuple(INK if done else WHITE) + (255,), anchor="lm")
    k_in = ease_out(t / 0.45)
    k_out = ease_io((t - dur) / 0.4)
    a = clamp01(t / 0.2) * (1 - k_out)
    bump = 1 + 0.07 * math.exp(-((t - t_click - 0.05) / 0.08) ** 2)
    if abs(bump - 1) > 1e-3:
        pill = pill.resize((int(pill.width * bump), int(pill.height * bump)), Image.BICUBIC)
    ox = (1 - k_in) * -40 + k_out * -40
    blend(fr, pill, x + ox, y - pill.height / 2, a)
    if t_click <= t <= t_click + 0.6:
        tt = (t - t_click) / 0.6
        cxp, cyp = x + w * 0.78, y
        r = 12 + 46 * ease_out(tt)
        ring = ring_img(int(r), 3, 1.0, track_a=0.0)
        blend(fr, ring, cxp - ring.width / 2, cyp - ring.height / 2, (1 - tt) * a)


# ---------------------------------------------------------------------------------------------- transitions
def blur_mix(a, b, p):
    """Crossfade a -> b through a lens-blur push (p 0..1)."""
    H, W = a.shape[:2]
    e = ease_io(p)
    def push(img, s, sig):
        M = np.array([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]], np.float32)
        out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if sig > 0.6:
            small = cv2.resize(out, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), sig / 4)
            out = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
        return out
    bump = math.sin(math.pi * e)
    A = push(a, 1 + 0.06 * e, 26 * bump)
    B = push(b, 1.06 - 0.06 * e, 26 * bump)
    out = A * (1 - e) + B * e
    return out * (1 - 0.10 * bump)


# ---------------------------------------------------------------------------------------------- 3D title
class SignalTitle:
    """Opening: extruded Geist Black block (silver face, graphite sides, lime rim light) that turns in over the dimmed
    picture, a serif-italic line under it and a mono kicker over it.  beats: [(t0, t1, lines, opts)]."""

    def __init__(self, W, H, beats, box=(0.78, 0.36)):
        self.W, self.H = W, H
        self.beats = []
        fp = fpath("black")
        silver = ("v", [(0.0, (255, 255, 255)), (0.55, (222, 226, 224)), (1.0, (168, 176, 172))])
        lime = ("v", [(0.0, (226, 255, 150)), (0.6, LIME), (1.0, (150, 210, 30))])
        faces = {"silver": silver, "lime": lime}
        side = [(0.0, (34, 38, 40)), (0.5, (64, 72, 70)), (1.0, (26, 30, 32))]
        for i, b in enumerate(beats):
            t0, t1, lines = b[:3]
            o = b[3] if len(b) > 3 else {}
            bw, bh = o.get("box", box)
            ln = [(txt, faces[st], rel) for txt, st, rel in lines]
            size = T3.fit_size(ln, fp, W * bw, H * bh, line_gap=0.9, tracking=-0.01)
            blk = T3.Block(ln, fp, size, side, depth=0.16, layers=22, line_gap=0.9, tracking=-0.01)
            self.beats.append((t0, t1, blk, o, -1 if i % 2 else 1))

    def span(self):
        return self.beats[0][0], self.beats[-1][1]

    def draw(self, fr, t):
        W, H = self.W, self.H
        for bi, (t0, t1, blk, o, dr) in enumerate(self.beats):
            last = bi == len(self.beats) - 1
            if not (t0 - 0.05 <= t < t1 + (0.35 if last else 0.02)):
                continue
            tt = t - t0
            dur = t1 - t0
            k_in = ease_out(tt / 0.6)
            k_out = ease_io((tt - dur) / 0.35) if last else ease_io((tt - (dur - 0.2)) / 0.2)
            yaw = dr * (lerp(-38, -7, k_in) + 9 * clamp01(tt / max(dur, 0.01))) + dr * 40 * k_out
            pitch = lerp(14, 4, k_in)
            scale = lerp(0.78, 1.0, ease_out(tt / 0.7)) * (1 + 0.025 * clamp01(tt / max(dur, 0.01))) * (1 + 0.25 * k_out)
            alpha = clamp01((tt + 0.05) / 0.2) * (1 - k_out)
            cy = H * o.get("cy", 0.47)
            sw = (tt - 0.5) / 0.9
            lay = blk.render(W, H, yaw=yaw, pitch=pitch, scale=scale, cx=W / 2, cy=cy, sweep=sw if 0 < sw < 1 else None, alpha=alpha)
            T3.shadow_and_glow(fr, lay, shadow=0.6 * alpha, glow=0.22 * alpha, offset=(0, int(H * 0.02)), tint=(0.78, 1.0, 0.24))
            T3.composite(fr, lay)
            bh = blk.h * scale
            if o.get("kicker"):
                kk = label(o["kicker"], "mono", int(H * (0.022 if W > H else 0.016)), LIME, tracking=0.24)
                reveal(fr, kk, W / 2, cy - bh / 2 - H * 0.05, clamp01((tt - 0.15) / 0.4), alpha, "ct")
            if o.get("sub"):
                st = label(o["sub"], "serif", int(H * (0.068 if W > H else 0.040)), WHITE)
                reveal(fr, st, W / 2, cy + bh / 2 + H * 0.005, clamp01((tt - 0.35) / 0.5), alpha, "ct")
