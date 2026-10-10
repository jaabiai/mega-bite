"""Procedural silhouette art for the lyric video (crowd with flags, Jantar Mantar, chakra ring).
All art is drawn with PIL at 2x supersampling, returned as RGBA uint8 arrays."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 2  # supersample factor


def _canvas(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def _down(im, w, h):
    return im.resize((w, h), Image.LANCZOS)


def draw_person(d, x, base_y, s, rng, color, pole_list=None, raised=None):
    """One head-and-shoulders figure seen from behind/side. (x, base_y) = neck base in canvas px.
    All coordinates are multiplied by SS here."""
    k = SS
    hr = 17 * s * rng.uniform(0.92, 1.08)
    head_cy = base_y - 26 * s - hr * 0.2
    # shoulders / torso (rounded, extends to bottom)
    sw = 40 * s * rng.uniform(0.9, 1.15)
    top = base_y - 6 * s
    d.ellipse([(x - sw) * k, (top - 12 * s) * k, (x + sw) * k, (top + 46 * s) * k], fill=color)
    d.rectangle([(x - sw * 0.98) * k, (top + 14 * s) * k, (x + sw * 0.98) * k, (top + 4000) * k], fill=color)
    # neck
    d.rectangle([(x - 7 * s) * k, (head_cy + hr * 0.5) * k, (x + 7 * s) * k, (top + 4 * s) * k], fill=color)
    # head
    d.ellipse([(x - hr) * k, (head_cy - hr * 1.12) * k, (x + hr) * k, (head_cy + hr * 1.05) * k], fill=color)
    kind = rng.random()
    if kind < 0.14:   # turban
        d.ellipse([(x - hr * 1.25) * k, (head_cy - hr * 1.55) * k, (x + hr * 1.25) * k, (head_cy + hr * 0.15) * k], fill=color)
    elif kind < 0.26:  # topi (cap)
        d.polygon([((x - hr * 1.05) * k, (head_cy - hr * 0.55) * k), ((x + hr * 1.05) * k, (head_cy - hr * 0.55) * k),
                   ((x + hr * 0.8) * k, (head_cy - hr * 1.5) * k), ((x - hr * 0.8) * k, (head_cy - hr * 1.5) * k)], fill=color)
    elif kind < 0.42:  # bun / long hair
        d.ellipse([(x + hr * 0.2) * k, (head_cy - hr * 1.55) * k, (x + hr * 1.1) * k, (head_cy - hr * 0.6) * k], fill=color)
        d.rectangle([(x - hr * 0.9) * k, (head_cy - 0.2 * hr) * k, (x + hr * 0.9) * k, (head_cy + hr * 1.7) * k], fill=color)
    # raised arm (+ optional fist / flag pole)
    if raised is not None:
        ang, length, pole = raised
        ax, ay = x + (sw * 0.8 if ang >= 0 else -sw * 0.8), top + 4 * s
        rad = math.radians(ang)
        ex, ey = ax + math.sin(rad) * length * s, ay - math.cos(rad) * length * s
        d.line([(ax * k, ay * k), (ex * k, ey * k)], fill=color, width=int(13 * s * k))
        d.ellipse([(ex - 8 * s) * k, (ey - 8 * s) * k, (ex + 8 * s) * k, (ey + 8 * s) * k], fill=color)
        if pole:
            ph = pole * s
            d.line([(ex * k, (ey + 6 * s) * k), ((ex + math.sin(rad) * ph * 0.12) * k, (ey - ph) * k)], fill=color, width=max(2, int(3.4 * s * k)))
            if pole_list is not None:
                pole_list.append((ex + math.sin(rad) * ph * 0.12, ey - ph, s))


def crowd_strip(width, height, rows, seed=3):
    """rows: list of dict(scale, base, density, color(rgb), raised_prob, pole_prob).
    Returns (list of RGBA arrays per row, list of flag anchors per row)."""
    out, flags = [], []
    for ri, row in enumerate(rows):
        rng = random.Random(seed * 100 + ri)
        im = _canvas(width, height)
        d = ImageDraw.Draw(im)
        s = row["scale"]
        step = 62 * s * row["density"]
        x = -40 * s
        poles = []
        while x < width + 60:
            xx = x + rng.uniform(-0.25, 0.25) * step
            yy = row["base"] + rng.uniform(-10, 10) * s
            raised = None
            if rng.random() < row["raised_prob"]:
                ang = rng.uniform(-24, 24)
                pole = rng.uniform(150, 220) if rng.random() < row["pole_prob"] else 0
                raised = (ang, rng.uniform(62, 92), pole)
            draw_person(d, xx, yy, s, rng, row["color"] + (255,), poles, raised)
            x += step
        out.append(np.asarray(_down(im, width, height)))
        flags.append(poles)
    return out, flags


def flag_sprite(w=120, h=78, wave_phase=0.0, amp=5.0, saffron=(255, 135, 40), green=(24, 150, 60), tint=1.0):
    """Tricolor banner (saffron/white/green) with a sine ripple. Returns RGBA uint8."""
    ss = 3
    base = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    b = h * ss // 3
    d.rectangle([0, 0, w * ss, b], fill=saffron + (255,))
    d.rectangle([0, b, w * ss, 2 * b], fill=(244, 244, 238, 255))
    d.rectangle([0, 2 * b, w * ss, 3 * b], fill=green + (255,))
    # simple chakra
    cx, cy, r = w * ss // 2, h * ss // 2, int(b * 0.42)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(20, 40, 140, 255), width=max(2, ss))
    for i in range(24):
        a = math.radians(i * 15)
        d.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], fill=(20, 40, 140, 255), width=1)
    base = base.resize((w, h), Image.LANCZOS)
    a = np.asarray(base).copy()
    # ripple: shift each column vertically; shade by slope
    out = np.zeros((h + int(2 * amp) + 2, w, 4), np.uint8)
    for x in range(w):
        env = x / w  # more ripple away from the pole
        dy = amp * env * math.sin(x * 0.17 - wave_phase)
        slope = amp * env * 0.17 * math.cos(x * 0.17 - wave_phase)
        col = a[:, x].astype(np.float32)
        col[:, :3] *= np.clip(1.0 - slope * 0.35, 0.65, 1.15) * tint
        y0 = int(round(amp + 1 + dy))
        out[y0:y0 + h, x] = np.clip(col, 0, 255).astype(np.uint8)
    return out


def jantar_mantar(width=1500, height=520, color=(8, 9, 22)):
    """Silhouette: Samrat Yantra (stair-gnomon with chhatri + quadrant walls), Ram-Yantra drums,
    Jai Prakash bowl mounds. Ground line at the bottom of the canvas."""
    k = SS
    im = _canvas(width, height)
    d = ImageDraw.Draw(im)
    col = color + (255,)
    gy = height - 6  # ground y

    def poly(pts):
        d.polygon([(x * k, y * k) for x, y in pts], fill=col)

    # ---- Samrat Yantra (centre-right) ----
    bx, base_w, hgt = 760, 560, 400          # left x of base, base width, height at right edge
    rx = bx + base_w
    # main wedge: vertical edge on the right, hypotenuse (stairs) rising to the right
    top_x = rx - 70
    pts = [(bx, gy), (rx, gy), (rx, gy - hgt + 24), (top_x, gy - hgt)]
    # hypotenuse as a staircase
    n_steps = 34
    stair = []
    for i in range(n_steps + 1):
        t = i / n_steps
        x = bx + (top_x - bx) * t
        y = gy - (hgt) * t
        stair.append((x, y))
    shape = [(bx, gy)]
    for i in range(n_steps):
        x0, y0 = stair[i]
        x1, y1 = stair[i + 1]
        shape.append((x0, y0 - 1)); shape.append((x1, y0 - 1))
    shape += [(top_x, gy - hgt), (rx, gy - hgt + 24), (rx, gy)]
    poly(shape)
    # side parapet rails along the staircase (thin)
    d.line([(bx * k, gy * k), (top_x * k, (gy - hgt - 6) * k)], fill=col, width=int(5 * k))
    # chhatri on top: four posts + dome
    cx, cy = top_x + 24, gy - hgt - 4
    d.rectangle([(cx - 34) * k, (cy - 30) * k, (cx + 34) * k, (cy) * k], fill=col)
    d.pieslice([(cx - 36) * k, (cy - 64) * k, (cx + 36) * k, (cy + 8) * k], 180, 360, fill=col)
    d.rectangle([(cx - 3) * k, (cy - 86) * k, (cx + 3) * k, (cy - 60) * k], fill=col)
    # quadrant walls flanking the gnomon (stepped silhouettes)
    poly([(bx - 240, gy), (bx + 14, gy), (bx + 14, gy - 130), (bx - 40, gy - 105), (bx - 130, gy - 62), (bx - 240, gy - 22)])
    # right quadrant
    poly([(rx - 14, gy), (rx + 230, gy), (rx + 230, gy - 22), (rx + 120, gy - 62), (rx + 40, gy - 105), (rx - 14, gy - 130)])
    # ---- Ram Yantra drums (left): low circular walls with a central pillar ----
    for (cx_, w_, h_) in ((230, 250, 92), (500, 190, 74)):
        d.rectangle([(cx_ - w_ / 2) * k, (gy - h_) * k, (cx_ + w_ / 2) * k, gy * k], fill=col)
        d.rectangle([(cx_ - w_ / 2 - 6) * k, (gy - h_ - 7) * k, (cx_ + w_ / 2 + 6) * k, (gy - h_) * k], fill=col)
        d.rectangle([(cx_ - 5) * k, (gy - h_ - 62) * k, (cx_ + 5) * k, (gy - h_) * k], fill=col)   # central pillar
        d.ellipse([(cx_ - 9) * k, (gy - h_ - 72) * k, (cx_ + 9) * k, (gy - h_ - 54) * k], fill=col)
    # ---- Jai Prakash bowls / mounds (far right) ----
    for (cx_, rr) in ((1330, 120), (1130, 70)):
        d.pieslice([(cx_ - rr) * k, (gy - rr * 0.55) * k, (cx_ + rr) * k, (gy + rr * 0.55) * k], 180, 360, fill=col)
        d.rectangle([(cx_ - rr * 0.1) * k, (gy - rr * 0.78) * k, (cx_ + rr * 0.1) * k, (gy - rr * 0.5) * k], fill=col)
    # low boundary wall
    d.rectangle([0, (gy - 22) * k, width * k, gy * k + 40], fill=col)
    return np.asarray(_down(im, width, height))


def chakra_ring(size=900, color=(235, 235, 245), spokes=24, width_px=3):
    """Ashoka-chakra-like 24-spoke wheel, used as a thin decorative ring (RGBA)."""
    k = 2
    im = Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size * k / 2
    r = size * k * 0.46
    d.ellipse([c - r, c - r, c + r, c + r], outline=color + (255,), width=width_px * k)
    r2 = r * 0.12
    d.ellipse([c - r2, c - r2, c + r2, c + r2], fill=color + (255,))
    for i in range(spokes):
        a = math.radians(i * 360 / spokes)
        x0, y0 = c + r2 * math.cos(a), c + r2 * math.sin(a)
        x1, y1 = c + r * 0.93 * math.cos(a), c + r * 0.93 * math.sin(a)
        d.line([(x0, y0), (x1, y1)], fill=color + (255,), width=int(width_px * 0.7 * k))
        # small tip dots at the rim
        xd, yd = c + r * 0.985 * math.cos(a + math.radians(7.5)), c + r * 0.985 * math.sin(a + math.radians(7.5))
        dr = 3.2 * k
        d.ellipse([xd - dr, yd - dr, xd + dr, yd + dr], fill=color + (255,))
    return np.asarray(im.resize((size, size), Image.LANCZOS))


# ----------------------------------------------------------------------------------------
# Line-art emblems (RGBA, 260x260) used as lyric-relevant motifs
# ----------------------------------------------------------------------------------------
def _icon_canvas(size=260):
    k = 3
    im = Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im), k


def _fin(im, size):
    return im.resize((size, size), Image.LANCZOS)


def icon_vote_finger(size=260, ink=(112, 58, 196)):
    """Raised index finger with the indelible-ink mark on the nail (voting emblem)."""
    im, d, k = _icon_canvas(size)
    W = (255, 255, 255, 255)
    lw = 7 * k
    def rr(box, r, **kw):
        d.rounded_rectangle([c * k for c in box], r * k, **kw)
    rr((92, 40, 132, 150), 20, outline=W, width=lw)            # index finger
    rr((92, 40, 132, 84), 20, fill=ink + (255,), outline=W, width=lw)   # ink on the tip
    rr((136, 92, 168, 168), 15, outline=W, width=lw)           # middle (curled)
    rr((172, 104, 200, 172), 14, outline=W, width=lw)          # ring
    rr((204, 118, 228, 176), 12, outline=W, width=lw)          # little
    rr((58, 104, 96, 178), 18, outline=W, width=lw)            # thumb
    rr((66, 146, 224, 232), 26, outline=W, width=lw)           # palm / back of hand
    return _fin(im, size)


def icon_book(size=260):
    """Open book (the Constitution) with a small 24-spoke wheel."""
    im, d, k = _icon_canvas(size)
    W = (255, 255, 255, 255); S = (255, 153, 51, 255)
    lw = 7 * k
    L = [(130, 70), (130, 205), (40, 188), (34, 62)]
    R = [(130, 70), (130, 205), (220, 188), (226, 62)]
    d.polygon([(x * k, y * k) for x, y in L], outline=W, width=lw)
    d.polygon([(x * k, y * k) for x, y in R], outline=W, width=lw)
    for i in range(4):
        y0 = 100 + i * 20
        d.line([(52 * k, (y0 + 2) * k), (118 * k, (y0 + 8) * k)], fill=(255, 255, 255, 170), width=4 * k)
        d.line([(142 * k, (y0 + 8) * k), (208 * k, (y0 + 2) * k)], fill=(255, 255, 255, 170), width=4 * k)
    cx, cy, r = 130, 40, 22
    d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], outline=S, width=5 * k)
    for i in range(12):
        a = math.radians(i * 30)
        d.line([(cx * k, cy * k), ((cx + r * math.cos(a)) * k, (cy + r * math.sin(a)) * k)], fill=S, width=3 * k)
    return _fin(im, size)


def icon_scales(size=260):
    im, d, k = _icon_canvas(size)
    W = (255, 255, 255, 255); S = (255, 153, 51, 255)
    lw = 7 * k
    d.line([(130 * k, 50 * k), (130 * k, 215 * k)], fill=W, width=lw)
    d.line([(88 * k, 215 * k), (172 * k, 215 * k)], fill=W, width=lw)
    d.line([(46 * k, 78 * k), (214 * k, 78 * k)], fill=W, width=lw)
    d.ellipse([118 * k, 36 * k, 142 * k, 60 * k], outline=S, width=5 * k)
    for cx in (46, 214):
        d.line([(cx * k, 78 * k), ((cx - 34) * k, 150 * k)], fill=(255, 255, 255, 190), width=4 * k)
        d.line([(cx * k, 78 * k), ((cx + 34) * k, 150 * k)], fill=(255, 255, 255, 190), width=4 * k)
        d.pieslice([(cx - 40) * k, 110 * k, (cx + 40) * k, 190 * k], 0, 180, outline=W, width=lw)
        d.line([((cx - 40) * k, 150 * k), ((cx + 40) * k, 150 * k)], fill=W, width=lw)
    return _fin(im, size)


def icon_diya(size=260):
    """Clay lamp with flame (new-dawn / 'light the lamp')."""
    im, d, k = _icon_canvas(size)
    W = (255, 255, 255, 255); S = (255, 153, 51, 255); Y = (255, 214, 120, 255)
    lw = 7 * k
    d.pieslice([50 * k, 120 * k, 210 * k, 232 * k], 0, 180, outline=W, width=lw)
    d.line([(50 * k, 176 * k), (210 * k, 176 * k)], fill=W, width=lw)
    d.polygon([(205 * k, 150 * k), (238 * k, 140 * k), (212 * k, 168 * k)], outline=W, width=5 * k)   # spout
    flame = [(130, 38), (150, 76), (156, 104), (146, 126), (130, 134), (114, 126), (104, 104), (110, 78)]
    d.polygon([(x * k, y * k) for x, y in flame], fill=S)
    inner = [(130, 74), (141, 100), (137, 118), (130, 124), (123, 118), (119, 100)]
    d.polygon([(x * k, y * k) for x, y in inner], fill=Y)
    return _fin(im, size)
