""""Aurora" look for V Create: ink-plum backdrops with an orchid / rose / amber gradient, Anton + Outfit type, a full-screen
extruded 3D title, calm karaoke captions that live in their own dock (never over the presenter), prism and light-sweep
transitions.  Buttons, callouts, taps and the logo sting come from the cine kit, re-skinned through cine.set_theme().

Everything draws into float32 RGB frames (0..1) in output pixels.
"""
import math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cine as C
import text3d as T3
from gfx import blend, ease_io, ease_out, ease_back, clamp01, lerp, rrect, aa_shape, with_mask

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
ANTON = os.path.join(FONT_DIR, "Anton-Regular.ttf")

INK = (11, 8, 18)
PANEL = (26, 19, 38)
TEXT = (248, 245, 252)
MUTE = (168, 158, 188)
ORCHID, ROSE, AMBER = (184, 96, 255), (255, 84, 140), (255, 176, 74)
AURORA = [(0.0, AMBER), (0.5, ROSE), (1.0, ORCHID)]                 # left -> right
AURORA_R = [(0.0, ORCHID), (0.5, ROSE), (1.0, AMBER)]
FACE_WHITE = ("v", [(0.0, (255, 255, 255)), (1.0, (226, 214, 244))])
FACE_AURORA = ("h", AURORA)
SIDE = [(0.0, (120, 52, 210)), (0.5, (214, 44, 112)), (1.0, (232, 120, 34))]

C.set_theme(
    pal=dict(gold=ROSE, gold_hi=(255, 150, 176), gold_lo=(170, 48, 100), silver=(232, 226, 242), steel=(150, 140, 170),
             ink=INK, panel=PANEL, text=TEXT),
    roles={"display": ("Anton-Regular.ttf", None), "display_m": ("Anton-Regular.ttf", None),
           "cap": ("Outfit-700.ttf", None), "bold": ("Outfit-700.ttf", None),
           "semi": ("Outfit-600.ttf", None), "med": ("Outfit-500.ttf", None)},
    accent=[(0.0, (255, 196, 120)), (0.5, ROSE), (1.0, (196, 110, 255))],
    chrome=[(0.0, (255, 255, 255)), (1.0, (228, 218, 244))],
    hot_fill=AURORA, leak=[1.0, 0.45, 0.72])

_F = {}


def font(weight, size):
    key = (weight, int(round(size)))
    if key not in _F:
        _F[key] = ImageFont.truetype(os.path.join(FONT_DIR, f"Outfit-{weight}.ttf"), key[1])
    return _F[key]


def ramp(n, stops):
    xs = np.linspace(0, 1, max(int(n), 1), dtype=np.float32)
    pos = [p for p, _ in stops]
    return np.stack([np.interp(xs, pos, [c[k] for _, c in stops]) for k in range(3)], -1)


def grad_fill(mask, stops, alpha=1.0):
    """RGBA layer: an L mask filled with a left -> right gradient."""
    w, h = mask.size
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = ramp(w, stops)[None, :, :].astype(np.uint8)
    out[..., 3] = (np.asarray(mask, np.float32) * alpha).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------------------------------------- backdrops
def backdrop(w, h, seed=3, blobs=None, grid=True):
    """Ink-plum field with soft orchid / rose / amber glows, a faint dot grid and a vignette (float RGB)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    asp = w / h
    img = np.zeros((h, w, 3), np.float32) + np.array(INK, np.float32) / 255
    blobs = blobs or [(0.16, 0.20, 0.42, ORCHID, 0.30), (0.84, 0.78, 0.46, ROSE, 0.24), (0.92, 0.10, 0.30, AMBER, 0.16)]
    for bx, by, br, col, a in blobs:
        d = np.hypot((u - bx) * asp, v - by) / br
        img += (np.exp(-d * d * 2.2) * a)[..., None] * np.array(col, np.float32) / 255
    if grid:
        step = max(int(min(w, h) * 0.042), 24)
        dots = np.zeros((h, w), np.float32)
        dots[step // 2::step, step // 2::step] = 1.0
        dots = cv2.GaussianBlur(dots, (0, 0), 1.1) * 9.0
        img += dots[..., None] * 0.035
    streak = np.exp(-((u - v * 0.5 - 0.22) / 0.18) ** 2) * 0.035
    img += streak[..., None]
    vig = 1 - 0.42 * np.clip(np.hypot((u - 0.5) * 1.15, v - 0.5) / 0.75 - 0.35, 0, 1) ** 1.4
    return np.clip(img * vig[..., None], 0, 1).astype(np.float32)


def dock_panel(w, h, line="top"):
    """Caption dock: solid ink with a soft gradient hairline along one edge (float RGB, w x h)."""
    img = backdrop(w, h * 3, seed=5, grid=False, blobs=[(0.5, 0.5, 0.9, ORCHID, 0.07)])[h:2 * h].copy()
    img = img * 0.55 + np.array(INK, np.float32) / 255 * 0.45
    if line in ("top", "bottom"):
        hair = ramp(w, AURORA)[None, :, :] / 255.0
        glow = np.exp(-(np.arange(h, dtype=np.float32) / 14.0) ** 2)[:, None, None] * 0.20
        if line == "bottom":
            glow = glow[::-1]
        img = 1 - (1 - img) * (1 - hair * glow)
        img[slice(0, 3) if line == "top" else slice(h - 3, h)] = hair * 0.95
    return img.astype(np.float32)


def window_edge(w, h, radius):
    """RGBA overlay for a picture window with rounded top corners: (mask L of the window, gradient rim along its top)."""
    m = aa_shape((w, h), lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, (h + radius * 2) * s], radius=radius * s, fill=255))
    ring = aa_shape((w, h), lambda d, s: d.rounded_rectangle([1.5 * s, 1.5 * s, w * s - 1.5 * s, (h + radius * 2) * s],
                                                               radius=radius * s, outline=255, width=int(3 * s)))
    fade = np.clip(1 - np.arange(h, dtype=np.float32) / (radius * 2.2), 0, 1)[:, None]
    rim = grad_fill(Image.fromarray((np.asarray(ring, np.float32) * fade).astype(np.uint8)), AURORA, 0.95)
    return np.asarray(m, np.float32)[..., None] / 255.0, rim


# ---------------------------------------------------------------------------------------------- bug
def draw_bug(fr, x, y, alpha=1.0, size=60):
    if alpha <= 0:
        return
    lg = C.logo(size)
    blend(fr, lg, x, y, alpha)
    f = font(700, size * 0.36)
    txt = "V CREATE"
    tr = size * 0.10
    wd = sum(f.getlength(c) for c in txt) + tr * (len(txt) - 1)
    lay = Image.new("RGBA", (int(wd) + 8, int(size * 0.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    xx = 2
    for c in txt:
        d.text((xx, lay.height / 2), c, font=f, fill=TEXT + (255,), anchor="lm")
        xx += f.getlength(c) + tr
    blend(fr, lay, x + size + 14, y + size / 2 - lay.height / 2, alpha * 0.95)


# ---------------------------------------------------------------------------------------------- captions
def caption_layer(words, act, age, size, max_w, lines_max=2, prev_frac=None):
    """Calm karaoke line: spoken words white, upcoming words dim, the current word in the gradient with a bar that
    glides under it.  No scaling, no bounce."""
    ft = font(700, size)
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
    lh = int((asc + desc) * 1.06)
    pad = int(size * 0.5)
    W_ = int(max(sum(widths[i] for i in L) + sp * (len(L) - 1) for L in lines)) + 2 * pad
    H_ = lh * len(lines) + 2 * pad
    base = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    pos = {}
    for li, L in enumerate(lines):
        lw = sum(widths[i] for i in L) + sp * (len(L) - 1)
        x = (W_ - lw) / 2
        y = pad + li * lh + asc
        for i in L:
            pos[i] = (x, y, li)
            if i != act:
                d.text((x, y), words[i], font=ft, fill=TEXT + ((255,) if i < act else (112,)), anchor="ls")
            x += widths[i] + sp
    if act in pos:
        x, y, li = pos[act]
        m = Image.new("L", (W_, H_), 0)
        ImageDraw.Draw(m).text((x, y), words[act], font=ft, fill=255, anchor="ls")
        k = ease_out(age / 0.14)
        # the word warms from white into the gradient as it is spoken
        base.alpha_composite(with_mask((W_, H_), TEXT, m, 1 - k))
        g = np.asarray(grad_fill(m, AURORA), np.uint8).copy()
        x0, x1 = int(x), int(x + widths[act]) + 1
        g[..., :3] = 0
        g[:, max(x0, 0):min(x1, W_), :3] = ramp(min(x1, W_) - max(x0, 0), [(0, AMBER), (1, ROSE)])[None].astype(np.uint8)
        gl = Image.fromarray(g, "RGBA")
        gl.putalpha(Image.fromarray((np.asarray(m, np.float32) * k).astype(np.uint8)))
        base.alpha_composite(gl)
        # underline bar glides from the previous word
        bx0, bx1 = x, x + widths[act]
        if act - 1 in pos and pos[act - 1][2] == li:
            px0 = pos[act - 1][0]
            bx0 = lerp(px0, x, k)
            bx1 = lerp(px0 + widths[act - 1], x + widths[act], k)
        by = y + size * 0.20
        bar = Image.new("L", (W_, H_), 0)
        ImageDraw.Draw(bar).rounded_rectangle([bx0, by, bx1, by + max(size * 0.085, 3)], radius=size * 0.05, fill=235)
        base.alpha_composite(grad_fill(bar, [(0, AMBER), (1, ROSE)]))
    return base


def draw_caption(fr, words, act, age, cx, cy, size, max_w, alpha=1.0, rise=0.0, lines_max=2, shadow=False):
    if alpha <= 0:
        return
    img = caption_layer(words, act, age, size, max_w, lines_max)
    if shadow:
        sh = img.getchannel("A").filter(ImageFilter.GaussianBlur(size * 0.12))
        blend(fr, with_mask(img.size, (0, 0, 0), sh, 0.8), cx - img.width / 2, cy - img.height / 2 + rise + 3, alpha)
    blend(fr, img, cx - img.width / 2, cy - img.height / 2 + rise, alpha)


# ---------------------------------------------------------------------------------------------- step chip / labels
def draw_step(fr, n, total, label, alpha, x_right, y, size=26, anchor="r"):
    """Chip with a gradient number disc, the step name and segmented progress underneath; anchor "r": x is the right
    edge, "l": x is the left edge."""
    if alpha <= 0:
        return
    f = font(700, size)
    fk = font(600, size * 0.62)
    tw = f.getlength(label)
    kick = f"STEP {n} OF {total}"
    h = int(size * 2.5)
    w = int(max(tw, fk.getlength(kick) + size * 0.2) + h + size * 1.5)
    chip = rrect((w, h), (0, 0, w - 1, h - 1), h / 2, PANEL, 0.90, outline=(255, 255, 255, 46), width=1.5)
    disc = aa_shape((h, h), lambda d, s: d.ellipse([6 * s, 6 * s, (h - 6) * s, (h - 6) * s], fill=255))
    chip.alpha_composite(grad_fill(disc, [(0, AMBER), (1, ROSE)]))
    d = ImageDraw.Draw(chip)
    d.text((h / 2, h / 2), str(n), font=font(800, size * 1.05), fill=INK + (255,), anchor="mm")
    d.text((h + size * 0.35, h * 0.30), kick, font=fk, fill=MUTE + (255,), anchor="lm")
    d.text((h + size * 0.35, h * 0.66), label, font=f, fill=TEXT + (255,), anchor="lm")
    xl = x_right - w if anchor == "r" else x_right
    blend(fr, chip, xl + (1 - alpha) * (24 if anchor == "r" else -24), y, alpha)
    seg, gap = 26, 6
    tot_w = total * seg + (total - 1) * gap
    x0 = x_right - tot_w - 4 if anchor == "r" else x_right + 4
    for i in range(total):
        bar = Image.new("RGBA", (seg, 4), (ROSE if i < n else MUTE) + (255,))
        blend(fr, bar, x0 + i * (seg + gap), y + h + 10, alpha * (1.0 if i < n else 0.4))


def draw_tag(fr, text, x, y, alpha=1.0, size=22, anchor="l"):
    """Small glass tag (used for the presenter's name and section labels)."""
    if alpha <= 0:
        return
    f = font(600, size)
    tw = f.getlength(text)
    w, h = int(tw + size * 2.2), int(size * 2.0)
    pill = rrect((w, h), (0, 0, w - 1, h - 1), h / 2, PANEL, 0.86, outline=(255, 255, 255, 50), width=1.5)
    dot = aa_shape((h, h), lambda d, s: d.ellipse([(h / 2 - 5) * s, (h / 2 - 5) * s, (h / 2 + 5) * s, (h / 2 + 5) * s], fill=255))
    pill.alpha_composite(grad_fill(dot, [(0, AMBER), (1, ROSE)]), (int(size * 0.2), 0))
    ImageDraw.Draw(pill).text((size * 1.5, h / 2), text, font=f, fill=TEXT + (255,), anchor="lm")
    xx = x if anchor == "l" else (x - w if anchor == "r" else x - w / 2)
    blend(fr, pill, xx, y + (1 - alpha) * 10, alpha)


# ---------------------------------------------------------------------------------------------- transitions
def prism(fr, p):
    """Zoom-blur with a red / blue channel split around a cut (p in [-1, 1], 0 = the cut)."""
    if p <= -1 or p >= 1:
        return fr
    k = math.exp(-(p / 0.40) ** 2)
    if k < 0.02:
        return fr
    H, W = fr.shape[:2]
    acc = np.zeros_like(fr)
    n = 6
    for i in range(n):
        z = 1 + 0.16 * k * i / (n - 1)
        M = np.array([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H / 2]], np.float32)
        acc += cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = acc / n
    sh = int(round(14 * k))
    if sh > 0:
        out[..., 0] = np.roll(out[..., 0], sh, axis=1)
        out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    return np.clip(out * (1 + 0.30 * k), 0, 1)


def sweep(fr, p):
    """A gradient light bar wipes across the cut."""
    if p <= -1 or p >= 1:
        return fr
    H, W = fr.shape[:2]
    k = math.exp(-(p / 0.45) ** 2)
    q = 8
    yy, xx = np.mgrid[0:H // q, 0:W // q].astype(np.float32)
    pos = (0.5 + 0.75 * p) * (W / q + H / q * 0.4)
    band = np.exp(-(((xx + yy * 0.4) - pos) / (0.10 * W / q)) ** 2)
    band = cv2.resize(band, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    col = (np.array(ROSE, np.float32) * 0.6 + np.array(AMBER, np.float32) * 0.4) / 255
    fr[:] = 1 - (1 - fr) * (1 - np.clip(band * k * 1.1, 0, 1) * col)
    return np.clip(fr * (1 + 0.22 * k), 0, 1)


def dip(fr, p):
    return C.dip(fr, p)


# ---------------------------------------------------------------------------------------------- 3D title sequence
class Title3D:
    """Full-screen extruded titles.  beats: [(t0, t1, [(text, style, rel_size), ...], opts)] with style "white" | "aurora";
    opts: dir (+1 / -1 swing direction), box (max_w, max_h as fractions of the frame), cy (centre as a fraction of H)."""

    def __init__(self, W, H, beats, box=(0.86, 0.60)):
        self.W, self.H = W, H
        self.beats = []
        for i, b in enumerate(beats):
            t0, t1, lines = b[:3]
            opts = b[3] if len(b) > 3 else {}
            bw, bh = opts.get("box", box)
            ln = [(txt, FACE_AURORA if st == "aurora" else FACE_WHITE, rel) for txt, st, rel in lines]
            size = T3.fit_size(ln, ANTON, W * bw, H * bh)
            blk = T3.Block(ln, ANTON, size, SIDE, depth=0.26, layers=28)
            self.beats.append((t0, t1, blk, opts.get("dir", 1 if i % 2 == 0 else -1), opts.get("cy", 0.5)))
        yy, xx = np.mgrid[0:H // 8, 0:W // 8].astype(np.float32)
        self._u, self._v = xx / (W / 8), yy / (H / 8)
        rng = np.random.default_rng(21)
        self._dust = rng.uniform(0, 1, (46, 5)).astype(np.float32)

    def span(self):
        return self.beats[0][0], self.beats[-1][1]

    def background(self, fr, t):
        """Turns the live picture into the title's backdrop: blurred, darkened, washed with moving gradient light."""
        W, H = self.W, self.H
        small = cv2.resize(fr, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), 5.0)
        luma = small.mean(-1, keepdims=True)
        small = (small * 0.45 + luma * 0.55) * 0.24 + np.array(INK, np.float32) / 255 * 0.55
        asp = W / H
        for (bx, by, br, col, a, sp, ph) in ((0.22, 0.30, 0.55, ORCHID, 0.25, 0.11, 0.0), (0.80, 0.72, 0.55, ROSE, 0.21, 0.09, 2.1),
                                             (0.60, 0.10, 0.40, AMBER, 0.11, 0.13, 4.0)):
            cx = bx + 0.06 * math.sin(t * sp * 2 * math.pi + ph)
            cy = by + 0.05 * math.cos(t * sp * 2 * math.pi + ph)
            d = np.hypot((self._u - cx) * asp, self._v - cy) / br
            small += (np.exp(-d * d * 2.4) * a)[..., None] * np.array(col, np.float32) / 255
        vig = 1 - 0.5 * np.clip(np.hypot((self._u - 0.5) * 1.1, self._v - 0.5) / 0.72 - 0.30, 0, 1) ** 1.3
        small *= vig[..., None]
        out = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
        # drifting dust
        dust = np.zeros((H // 2, W // 2), np.float32)
        for (x, y, r, a, s) in self._dust:
            px = int(((x + 0.012 * t * (0.4 + s)) % 1.0) * W / 2)
            py = int(((y - 0.020 * t * (0.3 + s)) % 1.0) * H / 2)
            cv2.circle(dust, (px, py), 1 + int(r * 3), float(0.25 + 0.5 * a), -1, lineType=cv2.LINE_AA)
        dust = cv2.resize(cv2.GaussianBlur(dust, (0, 0), 1.0), (W, H), interpolation=cv2.INTER_LINEAR)
        out += dust[..., None] * np.array([0.42, 0.34, 0.46], np.float32)
        return np.clip(out, 0, 1).astype(np.float32)

    def draw(self, fr, t):
        W, H = self.W, self.H
        for bi, (t0, t1, blk, direction, cyf) in enumerate(self.beats):
            last = bi == len(self.beats) - 1
            # one beat on screen at a time: a beat swings out over its last 0.22 s, before the next one swings in;
            # the last beat is closed by the cut that follows it (single headers keep their own exit)
            if not (t0 - 0.05 <= t < t1 + 0.02):
                continue
            tt = t - t0
            dur = t1 - t0
            k_in = ease_out(tt / 0.55)
            k_out = 0.0 if (last and len(self.beats) > 1) else ease_io((tt - (dur - 0.22)) / 0.22)
            hold = clamp01(tt / max(dur, 0.01))
            yaw = direction * (lerp(-62, -11, k_in) + 19 * hold) + direction * 64 * k_out
            pitch = lerp(16, 5, k_in) - 3 * hold
            scale = lerp(0.52, 1.0, ease_back(clamp01(tt / 0.6), 1.2)) * (1 + 0.035 * hold) * (1 + 0.5 * k_out)
            alpha = clamp01((tt + 0.05) / 0.16) * (1 - k_out)
            cy = H * cyf + (1 - k_in) * H * 0.07
            sw = (tt - 0.45) / 0.9
            lay = blk.render(W, H, yaw=yaw, pitch=pitch, roll=direction * (1 - k_in) * -4, scale=scale, cx=W / 2, cy=cy,
                             sweep=sw if 0 < sw < 1 else None, alpha=alpha)
            if lay is None:
                continue
            # anamorphic streak behind the block when it lands
            st = math.exp(-((tt - 0.45) / 0.28) ** 2)
            if st > 0.02:
                ys = np.arange(H, dtype=np.float32)
                line = np.exp(-((ys - cy) / (H * 0.012)) ** 2)[:, None, None] * st * 0.55
                fr[:] = 1 - (1 - fr) * (1 - line * np.array([1.0, 0.72, 0.86], np.float32))
            T3.shadow_and_glow(fr, lay, shadow=0.55 * alpha, glow=0.34 * alpha, offset=(0, int(H * 0.022)), tint=(1.0, 0.50, 0.74))
            T3.composite(fr, lay)


# ---------------------------------------------------------------------------------------------- logo sting
def draw_sting(fr, t, cx, cy, size=260, bug=(48, 34, 60), dur=2.9, name=True):
    """Logo reveal that stays off the presenter: a soft dark halo and rays behind the logo only (no full-frame dimming),
    the logo scales in with a shine, the channel name settles under it, then the logo flies to the corner bug."""
    if t < 0 or t > dur:
        return
    a_in = ease_out(t / 0.35)
    fly = ease_io((t - (dur - 0.75)) / 0.7)
    r = int(size * 1.45)
    key = ("halo", r)
    if key not in _STING:
        yy, xx = np.mgrid[0:2 * r, 0:2 * r].astype(np.float32) - r
        d = np.hypot(xx, yy) / r
        halo = np.zeros((2 * r, 2 * r, 4), np.uint8)
        halo[..., :3] = INK
        halo[..., 3] = (np.clip((1 - d) * 1.5, 0, 1) ** 1.2 * 232).astype(np.uint8)
        _STING[key] = Image.fromarray(halo, "RGBA")
    blend(fr, _STING[key], cx - r, cy - r, a_in * (1 - fly))
    rays = C._rays(r)
    M = cv2.getRotationMatrix2D((r, r), t * 9.0, 1.0)
    blend(fr, Image.fromarray(cv2.warpAffine(rays, M, (2 * r, 2 * r), flags=cv2.INTER_LINEAR), "RGBA"), cx - r, cy - r,
          0.75 * a_in * (1 - fly))
    sc = lerp(0.72, 1.0, ease_back(t / 0.55)) if t < 0.55 else 1.0
    s = lerp(size * sc, bug[2], fly)
    lx = lerp(cx - s / 2, bug[0], fly)
    ly = lerp(cy - s / 2 - (size * 0.10 if name else 0), bug[1], fly)
    lg = C.logo(max(int(s), 8)).copy()
    k = (t - 0.55) / 0.8
    if 0 < k < 1:
        w_, h_ = lg.size
        yy, xx = np.mgrid[0:h_, 0:w_].astype(np.float32)
        band = np.exp(-(((xx + yy * 0.6) / (w_ * 1.6) - (k * 1.4 - 0.2)) / 0.06) ** 2)
        arr = np.asarray(lg, np.float32).copy()
        arr[..., :3] = np.clip(arr[..., :3] + band[..., None] * 140, 0, 255)
        lg = Image.fromarray(arr.astype(np.uint8), "RGBA")
    blend(fr, lg, lx, ly, clamp01(t / 0.25))
    if name:
        ta = ease_out((t - 0.35) / 0.6) * (1 - ease_io((t - (dur - 0.9)) / 0.35))
        if ta > 0:
            f = font(700, size * 0.15)
            txt = "V CREATE"
            tr = lerp(size * 0.14, size * 0.07, ease_out((t - 0.35) / 1.0))
            wd = sum(f.getlength(c) for c in txt) + tr * (len(txt) - 1)
            lay = Image.new("RGBA", (int(wd) + 8, int(size * 0.26)), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            xx = 2
            for c in txt:
                d.text((xx, lay.height / 2), c, font=f, fill=TEXT + (255,), anchor="lm")
                xx += f.getlength(c) + tr
            blend(fr, lay, cx - lay.width / 2, cy + size * 0.44, ta)
            lw = int(wd * 0.7 * ease_out((t - 0.6) / 0.6))
            if lw > 2:
                bar = Image.new("L", (lw, 4), 255)
                blend(fr, grad_fill(bar, AURORA), cx - lw / 2, cy + size * 0.44 + lay.height + 4, ta)


_STING = {}


def bookmark_icon(size, rgb):
    s = int(size)

    def fn(d, ss):
        k = s * ss
        d.polygon([(0.24 * k, 0.08 * k), (0.76 * k, 0.08 * k), (0.76 * k, 0.92 * k), (0.50 * k, 0.70 * k), (0.24 * k, 0.92 * k)], fill=255)
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def cta_save(fr, t, x, y, dur=2.6, scale=1.0):
    return C._icon_pill(fr, t, x, y, bookmark_icon, "SAVE", 0.85, dur, scale, burst=True)
