"""Procedural silhouette sprites for the landscape backgrounds (masks at the 1280x720 working resolution).

Each generator returns 'L' masks (uint8, 0..255).  Scenes colour them per frame (haze / rim light), so the same mask can sit in a
cold dawn or a red protest dusk.  The crowd/flag/Jantar-Mantar drawing code from the earlier portrait build (tools/art.py) is re-used
read-only; everything else is new.
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "tools")))      # existing project tools (read-only import)
import art                                                                            # noqa: E402  (existing art.py, unmodified)
from hl_common import WW, WH                                                          # noqa: E402

SS = 2


def _canvas(w, h):
    return Image.new("L", (int(w * SS), int(h * SS)), 0)


def _down(im, w, h):
    return im.resize((int(w), int(h)), Image.LANCZOS)


def noise1d(n, spacing, seed):
    rs = np.random.RandomState(seed)
    nodes = rs.rand(int(n / spacing) + 4)
    xs = np.arange(n) / float(spacing)
    i = np.floor(xs).astype(int)
    f = xs - i
    w = f * f * (3 - 2 * f)
    return nodes[i] * (1 - w) + nodes[i + 1] * w


def ridge(n, base, amp, seed, octaves=6, rough=0.52, first=380, ridged=0.0):
    prof = np.zeros(n)
    a = 1.0
    tot = 0.0
    for o in range(octaves):
        nz = noise1d(n, max(3.0, first / (2 ** o)), seed * 31 + o)
        if ridged > 0:                                   # ridged multifractal -> sharper peaks and notches
            nz = (1 - ridged) * nz + ridged * (1.0 - np.abs(2 * nz - 1))
        prof += a * nz
        tot += a
        a *= rough
    prof /= tot
    return base - (prof - 0.5) * 2 * amp                 # y of the ridge top (smaller = higher on screen)


def mountain_mask(Wm, Hm, base, amp, seed, sharp=0.52, first=380, ridged=0.5):
    """Mask (Hm,Wm) uint8 filled below a fractal ridge line."""
    top = ridge(Wm, base, amp, seed, rough=sharp, first=first, ridged=ridged)
    Y = np.arange(Hm)[:, None]
    cov = np.clip(Y - top[None, :] + 0.5, 0, 1)
    return (cov * 255).astype(np.uint8)


def rim_of(mask, dx, dy, blur=1.4, gain=2.2):
    """Edge light: pixels of the mask whose neighbour toward the light (dx,dy) is empty."""
    m = np.asarray(mask, np.float32) / 255.0
    sh = np.roll(np.roll(m, -dy, axis=0), -dx, axis=1)
    r = np.clip(m - sh, 0, 1) * gain
    im = Image.fromarray((np.clip(r, 0, 1) * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im)


# ----------------------------------------------------------------------------------------------------------------------
# monuments (drawn into an SS-scaled draw context, coordinates in working pixels)
# ----------------------------------------------------------------------------------------------------------------------
def _rect(d, x0, y0, x1, y1, v=255):
    d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=v)


def _poly(d, pts, v=255):
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=v)


def _dome(d, cx, base, r, h=None, v=255):
    h = r if h is None else h
    d.pieslice([(cx - r) * SS, (base - h) * SS, (cx + r) * SS, (base + h) * SS], 180, 360, fill=v)


def _onion(d, cx, base, r, v=255):
    """Onion dome with finial."""
    pts = []
    for a in np.linspace(math.pi, 0, 30):
        k = math.sin(a)
        rr = r * (1 + 0.28 * math.sin(a * 2 if a < math.pi / 2 else a))      # bulge
        pts.append((cx + rr * math.cos(a), base - r * 1.25 * k))
    pts.append((cx, base - r * 1.9))
    _poly(d, pts, v)
    _rect(d, cx - 1, base - r * 2.5, cx + 1, base - r * 1.7, v)
    _rect(d, cx - r * 0.95, base - 3, cx + r * 0.95, base, v)


def india_gate(d, cx, base, s, canvas=None):
    w, h = 62 * s, 96 * s
    _rect(d, cx - w * 0.78, base - 6 * s, cx + w * 0.78, base)                      # plinth
    _rect(d, cx - w * 0.68, base - 12 * s, cx + w * 0.68, base - 6 * s)
    _rect(d, cx - w / 2, base - h, cx + w / 2, base - 12 * s)                       # body
    _rect(d, cx - w * 0.58, base - h - 5 * s, cx + w * 0.58, base - h)              # cornice
    _rect(d, cx - w * 0.44, base - h - 9 * s, cx + w * 0.44, base - h - 5 * s)
    _rect(d, cx - w * 0.26, base - h - 12 * s, cx + w * 0.26, base - h - 9 * s)
    # arch opening (carve with 0)
    aw = w * 0.30
    d.pieslice([(cx - aw) * SS, (base - 68 * s) * SS, (cx + aw) * SS, (base - 68 * s + 2 * aw) * SS], 180, 360, fill=0)
    d.rectangle([(cx - aw) * SS, (base - 68 * s + aw) * SS, (cx + aw) * SS, (base - 12 * s) * SS], fill=0)


def red_fort(d, x0, x1, base, s, canvas=None):
    wall_h = 40 * s
    _rect(d, x0, base - wall_h, x1, base)
    n = int((x1 - x0) / (7 * s))
    for i in range(n):                                                               # merlons
        xx = x0 + i * 7 * s + 1.2 * s
        _rect(d, xx, base - wall_h - 6 * s, xx + 4.2 * s, base - wall_h)
    for cx in (x0 + 26 * s, x1 - 26 * s, (x0 + x1) / 2):                              # towers with chhatris
        _rect(d, cx - 11 * s, base - wall_h - 22 * s, cx + 11 * s, base - wall_h)
        _rect(d, cx - 13 * s, base - wall_h - 26 * s, cx + 13 * s, base - wall_h - 22 * s)
        for k in (-8, 0, 8):
            _rect(d, cx + k * s - 1.4 * s, base - wall_h - 38 * s, cx + k * s + 1.4 * s, base - wall_h - 26 * s)
        _dome(d, cx, base - wall_h - 38 * s, 12 * s, 11 * s)
        _rect(d, cx - 0.8, base - wall_h - 58 * s, cx + 0.8, base - wall_h - 46 * s)
    # central gate arch
    cx = (x0 + x1) / 2
    aw = 9 * s
    d.pieslice([(cx - aw) * SS, (base - 30 * s) * SS, (cx + aw) * SS, (base - 30 * s + 2 * aw) * SS], 180, 360, fill=0)
    d.rectangle([(cx - aw) * SS, (base - 30 * s + aw) * SS, (cx + aw) * SS, base * SS], fill=0)


def jama_masjid(d, cx, base, s, canvas=None):
    _rect(d, cx - 70 * s, base - 22 * s, cx + 70 * s, base)
    _rect(d, cx - 24 * s, base - 46 * s, cx + 24 * s, base - 22 * s)               # iwan
    d.pieslice([(cx - 11 * s) * SS, (base - 40 * s) * SS, (cx + 11 * s) * SS, (base - 18 * s) * SS], 180, 360, fill=0)
    d.rectangle([(cx - 11 * s) * SS, (base - 29 * s) * SS, (cx + 11 * s) * SS, (base - 18 * s) * SS], fill=0)
    _onion(d, cx, base - 46 * s, 20 * s)
    for dx in (-44 * s, 44 * s):
        _onion(d, cx + dx, base - 22 * s, 12 * s)
    for dx in (-84 * s, 84 * s):                                                      # minarets
        _poly(d, [(cx + dx - 6 * s, base), (cx + dx - 4.5 * s, base - 110 * s), (cx + dx + 4.5 * s, base - 110 * s), (cx + dx + 6 * s, base)])
        _rect(d, cx + dx - 8 * s, base - 114 * s, cx + dx + 8 * s, base - 108 * s)
        _dome(d, cx + dx, base - 114 * s, 7 * s, 8 * s)
        _rect(d, cx + dx - 0.7, base - 134 * s, cx + dx + 0.7, base - 122 * s)


def parliament(d, cx, base, s, canvas=None):
    r = 58 * s
    _rect(d, cx - r, base - 26 * s, cx + r, base)
    _rect(d, cx - r - 3 * s, base - 30 * s, cx + r + 3 * s, base - 26 * s)
    for i in range(-14, 15):                                                          # colonnade slits
        xx = cx + i * (r / 14.5)
        _rect(d, xx - 0.7 * s, base - 24 * s, xx + 0.7 * s, base - 5 * s, 0)
    _rect(d, cx - 15 * s, base - 42 * s, cx + 15 * s, base - 30 * s)
    _dome(d, cx, base - 42 * s, 16 * s, 12 * s)
    _rect(d, cx - 0.8, base - 66 * s, cx + 0.8, base - 52 * s)


def jantar_mantar(d, cx, base, s, canvas=None):
    """Samrat Yantra stair-gnomon with chhatri + low Ram Yantra drums (re-using the earlier portrait build's art)."""
    rgba = art.jantar_mantar(1500, 520, (0, 0, 0))
    a = Image.fromarray(rgba[..., 3], "L")
    sc = s * 0.42
    a = a.resize((int(1500 * sc * SS), int(520 * sc * SS)), Image.LANCZOS)
    canvas.paste(a, (int((cx - 800 * sc) * SS), int((base - 514 * sc) * SS)), a)


def shikhara(d, cx, base, s, canvas=None):
    """North-Indian temple tower (curvilinear spire)."""
    pts = []
    for y in np.linspace(0, 1, 40):
        w = 20 * s * (1 - y) ** 0.62 * (1 + 0.06 * math.sin(y * 40))
        pts.append((cx - w, base - 110 * s * y))
    for y in np.linspace(1, 0, 40):
        w = 20 * s * (1 - y) ** 0.62 * (1 + 0.06 * math.sin(y * 40))
        pts.append((cx + w, base - 110 * s * y))
    _poly(d, pts)
    _rect(d, cx - 24 * s, base - 8 * s, cx + 24 * s, base)
    d.ellipse([(cx - 5 * s) * SS, (base - 120 * s) * SS, (cx + 5 * s) * SS, (base - 108 * s) * SS], fill=255)


MONUMENTS = {"india_gate": india_gate, "jama": jama_masjid, "parliament": parliament, "jantar": jantar_mantar, "shikhara": shikhara}


def city_layer(Wm, Hm, ground, seed, density=1.0, hmin=30, hmax=150, monuments=(), lit=0.35, fort=None, scale=1.0):
    """Returns (mask, emission) uint8 arrays (Hm,Wm).  monuments: list of (name, x, scale)."""
    rs = np.random.RandomState(seed)
    m = _canvas(Wm, Hm)
    e = _canvas(Wm, Hm)
    dm, de = ImageDraw.Draw(m), ImageDraw.Draw(e)
    x = -20.0
    smooth_h = noise1d(int(Wm) + 200, 140, seed + 3)
    while x < Wm + 20:
        w = rs.uniform(18, 60) * scale
        hh = (hmin + (hmax - hmin) * (0.15 + 0.85 * smooth_h[int(max(0, min(len(smooth_h) - 1, x)))]) * rs.uniform(0.35, 1.0)) * scale
        top = ground - hh
        style = rs.rand()
        _rect(dm, x, top, x + w, ground)
        if style < 0.25:                                                              # stepped crown
            _rect(dm, x + w * 0.15, top - 8 * scale, x + w * 0.85, top)
            _rect(dm, x + w * 0.32, top - 14 * scale, x + w * 0.68, top - 8 * scale)
        elif style < 0.42:                                                            # antenna
            _rect(dm, x + w * 0.48, top - 26 * scale, x + w * 0.52 + 1, top)
        elif style < 0.55:                                                            # dome roof
            _dome(dm, x + w / 2, top, w * 0.4, w * 0.3)
        elif style < 0.65:                                                            # slanted roof
            _poly(dm, [(x, top), (x + w, top), (x + w, top - 10 * scale)])
        # lit windows
        if lit > 0:
            cw, ch = 7 * scale, 9 * scale
            for yy in np.arange(top + 6 * scale, ground - 8 * scale, ch):
                for xx in np.arange(x + 4 * scale, x + w - 5 * scale, cw):
                    if rs.rand() < lit * 0.55:
                        v = int(255 * rs.uniform(0.55, 1.0))
                        _rect(de, xx, yy, xx + 2.6 * scale, yy + 3.6 * scale, v)
        x += w * rs.uniform(0.85, 1.12) / max(density, 0.2) + rs.uniform(0, 5)
    _rect(dm, -50, ground, Wm + 50, Hm + 10)            # solid ground below the skyline
    for name, mx, ms in monuments:
        MONUMENTS[name](dm, mx, ground + 2, ms, canvas=m)
        # monuments are dark silhouettes: carve their windows out of the emission map
    if fort:
        red_fort(dm, fort[0], fort[1], ground + 2, fort[2], canvas=m)
    m = np.asarray(_down(m, Wm, Hm))
    e = np.asarray(_down(e, Wm, Hm).filter(ImageFilter.GaussianBlur(0.6)))
    return m, e


# ----------------------------------------------------------------------------------------------------------------------
# crowds & flags (re-using tools/art.py from the portrait build, read-only)
# ----------------------------------------------------------------------------------------------------------------------
def crowd_rows(Wm, Hm, rows, seed):
    """rows: list of dict(scale, base, density, raised_prob, pole_prob). Returns list of (mask uint8 (Hm,Wm), flag anchors)."""
    spec = [dict(scale=r["scale"], base=r["base"], density=r.get("density", 1.0), color=(255, 255, 255),
                 raised_prob=r.get("raised_prob", 0.18), pole_prob=r.get("pole_prob", 0.5)) for r in rows]
    strips, flags = art.crowd_strip(int(Wm), int(Hm), spec, seed=seed)
    return [(s[..., 3].copy(), f) for s, f in zip(strips, flags)]


def flag_frames(w, h, n=16, amp=4.0, tint=1.0):
    """Pre-rendered ripple cycle of a tricolor flag, PIL RGBA images."""
    return [Image.fromarray(art.flag_sprite(w, h, ph, amp, tint=tint)) for ph in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def chakra_ring(size, spokes=24, width_px=3):
    return Image.fromarray(art.chakra_ring(size, (255, 255, 255), spokes, width_px))


def waving_flag(w, h, n=24, amp=34.0, wl_frac=0.62, tint=1.0):
    """Large tricolor flag with low-frequency cloth waves + slope shading. Returns list of PIL RGBA frames."""
    base = art.flag_sprite(w, h, 0.0, 0.0, tint=1.0)            # flat flag incl. chakra (h+2 rows)
    bh = base.shape[0]
    pad = int(amp * 1.5) + 4
    H2 = bh + 2 * pad
    bp = np.zeros((bh + 2 * pad + 2, w, 4), np.float32)
    bp[pad:pad + bh] = base
    xs = np.arange(w)
    frames = []
    for k in range(n):
        ph = 2 * math.pi * k / n
        env = (xs / float(w)) ** 0.85
        wl = w * wl_frac
        dy = amp * env * np.sin(2 * math.pi * xs / wl - ph) + 0.35 * amp * env * np.sin(2 * math.pi * xs / (wl * 0.43) - 1.7 * ph + 1.1)
        slope = np.gradient(dy)
        src = (np.arange(H2)[:, None] - dy[None, :])             # source row for each output pixel
        y0 = np.floor(src).astype(int)
        fr = (src - y0)[..., None]
        y0c = np.clip(y0 + 0, 0, bp.shape[0] - 2)
        a = bp[y0c, xs[None, :]]
        b = bp[y0c + 1, xs[None, :]]
        out = a * (1 - fr) + b * fr
        shade = np.clip(1.0 - 1.35 * slope * 3.0 + 0.04, 0.55, 1.35)[None, :, None]
        out[..., :3] = np.clip(out[..., :3] * shade * tint, 0, 255)
        frames.append(Image.fromarray(out.astype(np.uint8), "RGBA"))
    return frames
