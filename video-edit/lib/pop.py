""""Pop" style kit: a light, neo-brutalist explainer look.

Warm paper with a drifting dot grid, everything outlined in ink with hard offset shadows (no blur), marker-yellow
karaoke captions on white speech cards, sticker labels, a pink hand-drawn marker ring for the thing being talked about,
a magnifier loupe joined to the phone by an ink line, chunky extruded 3D titles, sticker CTAs and a diagonal
yellow paper wipe between scenes.  No blue anywhere (MEGABYTE rule).  Fonts: Bricolage Grotesque (display),
Figtree (text), Space Mono (labels) - all OFL, in assets/fonts.
"""
import math, os, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from gfx import ease_io, ease_out, ease_back, clamp01, lerp, blend, aa_shape
import text3d as T3

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")

PAPER = (246, 241, 231)
DOTC = (216, 207, 190)
INK = (22, 21, 24)
YELLOW = (255, 208, 48)
PINK = (255, 90, 136)
MINT = (44, 206, 146)
ORANGE = (255, 136, 52)
LILAC = (192, 160, 255)
WHITE = (255, 255, 255)
MUTE = (128, 122, 112)
INKF = np.array(INK, np.float32) / 255.0

_F = {}


def font(kind, size):
    """kind: display | display7 | text | text7 | text6 | mono"""
    files = {"display": "BricolageGrotesque-800.ttf", "display7": "BricolageGrotesque-700.ttf", "text": "Figtree-800.ttf",
             "text7": "Figtree-700.ttf", "text6": "Figtree-600.ttf", "mono": "SpaceMono-700.ttf"}
    key = (kind, int(size))
    if key not in _F:
        _F[key] = ImageFont.truetype(os.path.join(FONT_DIR, files[kind]), int(size))
    return _F[key]


# ---------------------------------------------------------------------------------------------- readers
class SeekReader:
    """Sequential ffmpeg reader with cheap forward seeks (restarts the decoder only for back / far jumps)."""

    def __init__(self, path, w, h, fps, vf, t_off=0.0, jump=90):
        self.path, self.w, self.h, self.fps, self.vf, self.t_off, self.jump = path, w, h, fps, vf, t_off, jump
        self.proc, self.pos, self.cur = None, -10 ** 9, None
        self.size = w * h * 3

    def _start(self, idx):
        self.close()
        t = self.t_off + idx / self.fps
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", self.path, "-vf", self.vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.size * 2)
        self.pos = idx - 1

    def get(self, idx):
        idx = max(int(idx), 0)
        if idx == self.pos and self.cur is not None:
            return self.cur
        if self.proc is None or idx < self.pos or idx > self.pos + self.jump:
            self._start(idx)
        while self.pos < idx:
            buf = self.proc.stdout.read(self.size)
            if len(buf) < self.size:
                self.pos = idx
                break
            self.cur = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
            self.pos += 1
        return self.cur

    def close(self):
        if self.proc is not None:
            try:
                self.proc.stdout.close(); self.proc.kill(); self.proc.wait()
            except Exception:
                pass
            self.proc = None


# ---------------------------------------------------------------------------------------------- paper
class Paper:
    """Paper with a 36 px dot grid that drifts slowly; a static fibre noise keeps it from looking digital."""

    def __init__(self, w, h, step=36, seed=5):
        self.w, self.h, self.step = w, h, step
        W2, H2 = w + step, h + step
        img = np.zeros((H2, W2, 3), np.float32) + np.array(PAPER, np.float32) / 255
        rng = np.random.default_rng(seed)
        noise = cv2.GaussianBlur(rng.normal(0, 1, (H2 // 2, W2 // 2)).astype(np.float32), (0, 0), 1.2)
        noise = cv2.resize(noise, (W2, H2), interpolation=cv2.INTER_LINEAR)
        img += noise[..., None] * 0.012
        dots = Image.new("L", (W2 * 3, H2 * 3), 0)
        d = ImageDraw.Draw(dots)
        r = 2.3 * 3
        for yy in range(step // 2, H2, step):
            for xx in range(step // 2, W2, step):
                d.ellipse([xx * 3 - r, yy * 3 - r, xx * 3 + r, yy * 3 + r], fill=255)
        m = np.asarray(dots.resize((W2, H2), Image.LANCZOS), np.float32)[..., None] / 255
        img = img * (1 - m) + np.array(DOTC, np.float32) / 255 * m
        yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
        vig = 1 - 0.07 * np.clip(np.hypot(xx / W2 - 0.5, yy / H2 - 0.5) / 0.7, 0, 1) ** 2
        self.img = np.clip(img * vig[..., None], 0, 1).astype(np.float32)

    def at(self, t):
        o = int(t * 7) % self.step
        return self.img[o:o + self.h, o:o + self.w].copy()


# ---------------------------------------------------------------------------------------------- masks / stickers
def rr_mask(w, h, r, ss=3):
    m = aa_shape((w, h), lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=r * s, fill=255), ss)
    return np.asarray(m, np.float32) / 255.0


def paste_mask(fr, mask, x, y, rgb, alpha=1.0):
    """Paint a solid colour through `mask` (float HxW) at integer (x, y)."""
    H, W = fr.shape[:2]
    h, w = mask.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0 or alpha <= 0:
        return
    m = mask[y0 - y:y1 - y, x0 - x:x1 - x, None] * alpha
    reg = fr[y0:y1, x0:x1]
    reg[:] = reg * (1 - m) + np.array(rgb, np.float32) / 255 * m


class HardCard:
    """Picture card: ink border, hard ink shadow offset down-right, rounded corners."""

    def __init__(self, x, y, w, h, r=30, border=6, shadow=14):
        self.x, self.y, self.w, self.h, self.b, self.sh = x, y, w, h, border, shadow
        self.inner = rr_mask(w, h, r)
        self.outer = rr_mask(w + 2 * border, h + 2 * border, r + border)

    def compose(self, fr, pic, dx=0, dy=0, alpha=1.0):
        x, y, b, s = self.x + dx, self.y + dy, self.b, self.sh
        paste_mask(fr, self.outer, x - b + s, y - b + s, INK, alpha)
        paste_mask(fr, self.outer, x - b, y - b, INK, alpha)
        H, W = fr.shape[:2]
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + self.w, W), min(y + self.h, H)
        if x1 <= x0 or y1 <= y0:
            return
        m = self.inner[y0 - y:y1 - y, x0 - x:x1 - x, None] * alpha
        reg = fr[y0:y1, x0:x1]
        reg[:] = reg * (1 - m) + pic[y0 - y:y1 - y, x0 - x:x1 - x] * m


_STK = {}


def sticker(text, size=34, fill=WHITE, fg=INK, kind="text", pad=(20, 10), radius=14, border=4, shadow=6, icon=None,
            min_w=0, tracking=0.0):
    """Label sticker (PIL RGBA, shadow included).  icon: callable(draw, x, y, s, fg) drawn left of the text, s = size."""
    key = (text, size, fill, fg, kind, pad, radius, border, shadow, icon.__name__ if icon else None, min_w, tracking)
    if key in _STK:
        return _STK[key]
    ft = font(kind, size)
    tw = sum(ft.getlength(c) for c in text) + tracking * size * max(len(text) - 1, 0)
    asc, desc = ft.getmetrics()
    th = asc + desc * 0.25
    iw = int(size * 1.15) if icon else 0
    w = int(max(tw + iw + 2 * pad[0], min_w))
    h = int(th + 2 * pad[1])
    W_, H_ = w + 2 * border + shadow, h + 2 * border + shadow
    k = 3
    img = Image.new("RGBA", (W_ * k, H_ * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        d.rounded_rectangle([shadow * k, shadow * k, (W_ - 1) * k, (H_ - 1) * k], radius=(radius + border) * k, fill=INK + (255,))
    d.rounded_rectangle([0, 0, (w + 2 * border) * k - 1, (h + 2 * border) * k - 1], radius=(radius + border) * k, fill=INK + (255,))
    d.rounded_rectangle([border * k, border * k, (w + border) * k - 1, (h + border) * k - 1], radius=radius * k, fill=tuple(fill) + (255,))
    big = font(kind, size * k)
    x = (border + (w - tw - iw) / 2 + iw) * k
    y = (border + pad[1]) * k
    if icon:
        icon(d, (border + (w - tw - iw) / 2) * k, (border + h / 2) * k, size * k, fg)
    for c in text:
        d.text((x, y), c, font=big, fill=tuple(fg) + (255,))
        x += big.getlength(c) + tracking * size * k
    out = img.resize((W_, H_), Image.LANCZOS)
    _STK[key] = out
    return out


def place(fr, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0, anchor="c"):
    """Blend a PIL RGBA sticker centred (anchor c) / left-centred (l) / right-centred (r) at (cx, cy) with scale and rotation."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    im = img
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(int(im.width * scale), 1), max(int(im.height * scale), 1)), Image.BICUBIC)
    if abs(rot) > 0.05:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    x = cx - im.width / 2 if anchor == "c" else (cx if anchor == "l" else cx - im.width)
    blend(fr, im, x, cy - im.height / 2, alpha)


def pop_in(t, dur=0.32):
    """0 -> 1 with overshoot (sticker slap)."""
    if t <= 0:
        return 0.0
    return ease_back(clamp01(t / dur), 2.2)


def life(t, t0, t1, fin=0.32, fout=0.22):
    """(scale, alpha) of a sticker that slaps on at t0 and pops off at t1."""
    if t < t0 or t > t1 + fout:
        return 0.0, 0.0
    s = pop_in(t - t0, fin)
    a = clamp01((t - t0) / 0.08)
    if t > t1:
        k = ease_io((t - t1) / fout)
        s *= 1 - 0.6 * k
        a *= 1 - k
    return s, a


# ---------------------------------------------------------------------------------------------- icons
def ic_bell(d, x, y, s, fg):
    r = s * 0.34
    d.pieslice([x, y - r * 1.2, x + 2 * r, y + r * 0.9], 180, 360, fill=tuple(fg) + (255,))
    d.rectangle([x, y - r * 0.2, x + 2 * r, y + r * 0.55], fill=tuple(fg) + (255,))
    d.polygon([(x - r * 0.25, y + r * 0.75), (x + 2.25 * r, y + r * 0.75), (x + 2 * r, y + r * 0.3), (x, y + r * 0.3)], fill=tuple(fg) + (255,))
    d.ellipse([x + r * 0.7, y + r * 0.8, x + r * 1.3, y + r * 1.35], fill=tuple(fg) + (255,))


def ic_thumb(d, x, y, s, fg):
    r = s * 0.36
    c = tuple(fg) + (255,)
    d.rounded_rectangle([x, y - r * 0.2, x + r * 0.55, y + r * 1.05], radius=r * 0.1, fill=c)
    d.rounded_rectangle([x + r * 0.7, y - r * 0.25, x + r * 2.0, y + r * 1.05], radius=r * 0.3, fill=c)
    d.polygon([(x + r * 0.75, y - r * 0.15), (x + r * 1.05, y - r * 1.25), (x + r * 1.45, y - r * 1.1), (x + r * 1.35, y - r * 0.15)], fill=c)


def ic_share(d, x, y, s, fg):
    r = s * 0.36
    c = tuple(fg) + (255,)
    w = max(int(r * 0.32), 2)
    d.line([(x + r * 0.35, y), (x + r * 1.7, y - r * 0.8)], fill=c, width=w)
    d.line([(x + r * 0.35, y), (x + r * 1.7, y + r * 0.8)], fill=c, width=w)
    for (px, py) in ((x + r * 0.35, y), (x + r * 1.7, y - r * 0.8), (x + r * 1.7, y + r * 0.8)):
        d.ellipse([px - r * 0.38, py - r * 0.38, px + r * 0.38, py + r * 0.38], fill=c)


def ic_chat(d, x, y, s, fg):
    r = s * 0.38
    c = tuple(fg) + (255,)
    d.rounded_rectangle([x, y - r * 0.9, x + r * 2.0, y + r * 0.55], radius=r * 0.45, fill=c)
    d.polygon([(x + r * 0.35, y + r * 0.4), (x + r * 0.2, y + r * 1.05), (x + r * 0.95, y + r * 0.45)], fill=c)


def ic_play(d, x, y, s, fg):
    r = s * 0.38
    c = tuple(fg) + (255,)
    d.rounded_rectangle([x, y - r * 0.85, x + r * 2.0, y + r * 0.85], radius=r * 0.35, outline=c, width=max(int(r * 0.22), 2))
    d.polygon([(x + r * 0.78, y - r * 0.42), (x + r * 0.78, y + r * 0.42), (x + r * 1.4, y)], fill=c)


def ic_star(d, x, y, s, fg):
    r = s * 0.42
    c = tuple(fg) + (255,)
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + r + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=c)


def ic_check(d, x, y, s, fg):
    r = s * 0.40
    c = tuple(fg) + (255,)
    d.line([(x + r * 0.1, y), (x + r * 0.75, y + r * 0.6), (x + r * 1.9, y - r * 0.7)], fill=c, width=max(int(r * 0.42), 2), joint="curve")


def ic_menu(d, x, y, s, fg):
    r = s * 0.36
    c = tuple(fg) + (255,)
    for k in (-0.6, 0.0, 0.6):
        d.rounded_rectangle([x, y + k * r - r * 0.13, x + r * 1.9, y + k * r + r * 0.13], radius=r * 0.13, fill=c)


# ---------------------------------------------------------------------------------------------- captions
def caption_card(words, act, age, size, max_w, lines_max=2, pad=(30, 16), dim_future=True):
    """White speech card, ink border + hard shadow; spoken words ink, the current word on a yellow marker that wipes in,
    the words still to come in a lighter ink.  Returns PIL RGBA (shadow included)."""
    ft = font("text", size)
    space = ft.getlength(" ")
    lines, cur, cw = [], [], 0.0
    for i, w in enumerate(words):
        wl = ft.getlength(w)
        if cur and cw + space + wl > max_w:
            lines.append(cur); cur, cw = [], 0.0
        cur.append((i, w, wl)); cw += (space if len(cur) > 1 else 0) + wl
    if cur:
        lines.append(cur)
    if len(lines) > lines_max:                        # keep the lines around the active word
        li = next((k for k, ln in enumerate(lines) if any(i == act for i, _, _ in ln)), 0)
        s0 = min(max(li - lines_max + 1, 0), len(lines) - lines_max)
        lines = lines[s0:s0 + lines_max]
    asc, desc = ft.getmetrics()
    lh = int(size * 1.22)
    tw = max(sum(wl for _, _, wl in ln) + space * (len(ln) - 1) for ln in lines)
    b, sh = 5, 9
    w, h = int(tw + 2 * pad[0]), int(lh * len(lines) + 2 * pad[1] - size * 0.1)
    k = 2
    img = Image.new("RGBA", ((w + 2 * b + sh) * k, (h + 2 * b + sh) * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = 22
    d.rounded_rectangle([sh * k, sh * k, (w + 2 * b + sh) * k - 1, (h + 2 * b + sh) * k - 1], radius=(r + b) * k, fill=INK + (255,))
    d.rounded_rectangle([0, 0, (w + 2 * b) * k - 1, (h + 2 * b) * k - 1], radius=(r + b) * k, fill=INK + (255,))
    d.rounded_rectangle([b * k, b * k, (w + b) * k - 1, (h + b) * k - 1], radius=r * k, fill=WHITE + (255,))
    big = font("text", size * k)
    fut = tuple(int(c * 0.42 + 255 * 0.58) for c in INK) + (255,)
    for li, ln in enumerate(lines):
        lw = sum(wl for _, _, wl in ln) + space * (len(ln) - 1)
        x = b + pad[0] + (tw - lw) / 2
        y = b + pad[1] + li * lh
        for i, wtxt, wl in ln:
            if i == act:
                grow = ease_out(age / 0.12)
                mx0, my0 = x - size * 0.16, y + size * 0.08
                mx1 = mx0 + (wl + size * 0.32) * grow
                d.rounded_rectangle([mx0 * k, my0 * k, mx1 * k, (y + size * 1.10) * k], radius=size * 0.16 * k, fill=YELLOW + (255,))
            col = INK + (255,) if (i <= act or not dim_future) else fut
            d.text((x * k, (y - size * 0.02) * k), wtxt, font=big, fill=col)
            x += wl + space
    return img.resize((w + 2 * b + sh, h + 2 * b + sh), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------- marker ring / tap / loupe
def _ring_pts(cx, cy, rx, ry, seed=3, turns=1.12):
    rng = np.random.default_rng(seed)
    n = 120
    a = np.linspace(-0.6, -0.6 + 2 * math.pi * turns, n)
    wob = 1 + 0.035 * np.sin(a * 3 + rng.uniform(0, 6)) + 0.02 * np.sin(a * 5 + rng.uniform(0, 6))
    grow = 1 + 0.06 * (a - a[0]) / (a[-1] - a[0])
    return np.stack([cx + rx * wob * grow * np.cos(a), cy + ry * wob * grow * np.sin(a)], 1)


def marker_ring(fr, rect, t, a=1.0, color=PINK, width=7, seed=3):
    """Hand-drawn ellipse that draws itself around rect (x0, y0, x1, y1) over 0.45 s."""
    if a <= 0.01 or t < 0:
        return
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 * 1.16 + 10, (y1 - y0) / 2 * 1.30 + 10
    pts = _ring_pts(cx, cy, rx, ry, seed)
    n = max(int(len(pts) * ease_out(t / 0.45)), 2)
    H, W = fr.shape[:2]
    bx0, by0 = int(max(pts[:, 0].min() - 20, 0)), int(max(pts[:, 1].min() - 20, 0))
    bx1, by1 = int(min(pts[:, 0].max() + 20, W)), int(min(pts[:, 1].max() + 20, H))
    if bx1 <= bx0 or by1 <= by0:
        return
    m = np.zeros((by1 - by0, bx1 - bx0), np.uint8)
    p = ((pts[:n] - [bx0, by0]) * 4).astype(np.int32)
    m4 = np.zeros(((by1 - by0) * 4, (bx1 - bx0) * 4), np.uint8)
    cv2.polylines(m4, [p], False, 255, int(width * 4), cv2.LINE_AA)
    m = cv2.resize(m4, (bx1 - bx0, by1 - by0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * a
    reg = fr[by0:by1, bx0:bx1]
    reg[:] = reg * (1 - m[..., None]) + np.array(color, np.float32) / 255 * m[..., None]


def tap(fr, x, y, t):
    """Yellow press dot with an ink rim and an expanding ink ring."""
    if t < -0.15 or t > 0.85:
        return
    H, W = fr.shape[:2]
    R = 70
    x0, y0 = int(x - R), int(y - R)
    if x0 < 0 or y0 < 0 or x0 + 2 * R > W or y0 + 2 * R > H:
        return
    k = 4
    m_fill = np.zeros((2 * R * k, 2 * R * k), np.uint8)
    m_rim = np.zeros_like(m_fill)
    m_wave = np.zeros_like(m_fill)
    press = ease_out((t + 0.15) / 0.15) * (1 - ease_io((t - 0.35) / 0.3))
    if press > 0.01:
        r = int((20 - 4 * ease_out(t / 0.12)) * k)
        cv2.circle(m_fill, (R * k, R * k), r, 255, -1, cv2.LINE_AA)
        cv2.circle(m_rim, (R * k, R * k), r, 255, int(4 * k), cv2.LINE_AA)
    if t > 0:
        rw = int((22 + 44 * ease_out(t / 0.6)) * k)
        cv2.circle(m_wave, (R * k, R * k), rw, 255, int(5 * k * (1 - t / 0.85) + 1), cv2.LINE_AA)
    sz = (2 * R, 2 * R)
    reg = fr[y0:y0 + 2 * R, x0:x0 + 2 * R]
    for m, col, al in ((m_fill, YELLOW, press), (m_rim, INK, press), (m_wave, INK, 0.9 * (1 - clamp01(t / 0.85)))):
        mm = cv2.resize(m, sz, interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * al
        reg[:] = reg * (1 - mm) + np.array(col, np.float32) / 255 * mm


class Loupe:
    """Circular magnifier with an ink rim and hard shadow."""

    def __init__(self, r):
        self.r = r
        k = 3
        d = 2 * r
        m = Image.new("L", (d * k, d * k), 0)
        ImageDraw.Draw(m).ellipse([0, 0, d * k - 1, d * k - 1], fill=255)
        self.disc = np.asarray(m.resize((d, d), Image.LANCZOS), np.float32) / 255
        b = 8
        m2 = Image.new("L", ((d + 2 * b) * k, (d + 2 * b) * k), 0)
        ImageDraw.Draw(m2).ellipse([0, 0, (d + 2 * b) * k - 1, (d + 2 * b) * k - 1], fill=255)
        self.rim = np.asarray(m2.resize((d + 2 * b, d + 2 * b), Image.LANCZOS), np.float32) / 255
        self.b = b

    def draw(self, fr, cx, cy, content, scale=1.0, alpha=1.0, shadow=14):
        """content: float RGB 2r x 2r."""
        if scale <= 0.02 or alpha <= 0.01:
            return
        r, b = self.r, self.b
        if abs(scale - 1) > 1e-3:
            s = max(int(2 * r * scale), 4)
            disc = cv2.resize(self.disc, (s, s), interpolation=cv2.INTER_AREA)
            rim = cv2.resize(self.rim, (s + 2 * b, s + 2 * b), interpolation=cv2.INTER_AREA)
            content = cv2.resize(content, (s, s), interpolation=cv2.INTER_AREA)
        else:
            s, disc, rim = 2 * r, self.disc, self.rim
        x, y = int(cx - s / 2), int(cy - s / 2)
        paste_mask(fr, rim, x - b + shadow, y - b + shadow, INK, alpha)
        paste_mask(fr, rim, x - b, y - b, INK, alpha)
        H, W = fr.shape[:2]
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + s, W), min(y + s, H)
        if x1 <= x0 or y1 <= y0:
            return
        m = disc[y0 - y:y1 - y, x0 - x:x1 - x, None] * alpha
        reg = fr[y0:y1, x0:x1]
        reg[:] = reg * (1 - m) + content[y0 - y:y1 - y, x0 - x:x1 - x] * m


def ink_line(fr, p0, p1, width=5, alpha=1.0, color=INK):
    if alpha <= 0.01:
        return
    H, W = fr.shape[:2]
    x0, y0 = int(max(min(p0[0], p1[0]) - width - 2, 0)), int(max(min(p0[1], p1[1]) - width - 2, 0))
    x1, y1 = int(min(max(p0[0], p1[0]) + width + 2, W)), int(min(max(p0[1], p1[1]) + width + 2, H))
    if x1 <= x0 or y1 <= y0:
        return
    k = 4
    m = np.zeros(((y1 - y0) * k, (x1 - x0) * k), np.uint8)
    cv2.line(m, (int((p0[0] - x0) * k), int((p0[1] - y0) * k)), (int((p1[0] - x0) * k), int((p1[1] - y0) * k)), 255, int(width * k), cv2.LINE_AA)
    mm = cv2.resize(m, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * alpha
    reg = fr[y0:y1, x0:x1]
    reg[:] = reg * (1 - mm) + np.array(color, np.float32) / 255 * mm


def ring(fr, cx, cy, r, width=5, alpha=1.0, color=INK):
    if alpha <= 0.01:
        return
    H, W = fr.shape[:2]
    R = int(r + width + 2)
    x0, y0 = int(cx - R), int(cy - R)
    if x0 < 0 or y0 < 0 or x0 + 2 * R > W or y0 + 2 * R > H:
        return
    k = 4
    m = np.zeros((2 * R * k, 2 * R * k), np.uint8)
    cv2.circle(m, (int((cx - x0) * k), int((cy - y0) * k)), int(r * k), 255, int(width * k), cv2.LINE_AA)
    mm = cv2.resize(m, (2 * R, 2 * R), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255 * alpha
    reg = fr[y0:y0 + 2 * R, x0:x0 + 2 * R]
    reg[:] = reg * (1 - mm) + np.array(color, np.float32) / 255 * mm


# ---------------------------------------------------------------------------------------------- circular face PiP
class Bubble:
    def __init__(self, r, border=6):
        self.r, self.b = r, border
        self.disc = Loupe(r)

    def draw(self, fr, cx, cy, pic, scale=1.0, alpha=1.0):
        self.disc.draw(fr, cx, cy, pic, scale, alpha, shadow=10)


# ---------------------------------------------------------------------------------------------- 3D block title
class PopBlock(T3.Block):
    """Extruded title block whose face carries an ink outline (sticker-cut letters)."""

    def __init__(self, lines, font_path, size, outline=0.035, **kw):
        super().__init__(lines, font_path, size, [(0.0, (40, 38, 44)), (1.0, (12, 12, 14))], **kw)
        m = self.mask
        r = max(int(size * outline), 2)
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        big = cv2.dilate((m * 255).astype(np.uint8), ker).astype(np.float32) / 255
        big = cv2.GaussianBlur(big, (0, 0), 0.8)
        face = self.face[..., :3] / np.maximum(self.face[..., 3:4], 1e-4)
        face = face * m[..., None] + INKF * (1 - m[..., None])
        self.face = np.dstack([face * big[..., None], big]).astype(np.float32)
        side = np.asarray(self.side[..., :3], np.float32) / 255 / np.maximum(np.asarray(self.side[..., 3:4], np.float32) / 255, 1e-4)
        side = np.clip(side, 0, 1)
        self.side = (np.dstack([side * big[..., None], big]) * 255).astype(np.uint8)
        self.mask = big


def face_stops(rgb):
    hi = tuple(min(255, int(c + (255 - c) * 0.35)) for c in rgb)
    return ("v", [(0.0, hi), (0.55, rgb), (1.0, tuple(int(c * 0.86) for c in rgb))])


class PopTitle:
    """Full-frame title on paper: a slowly turning sunburst, a kicker sticker and extruded outlined blocks that slap in
    (one beat at a time).  beats: [(t0, t1, [(text, rgb, rel_size), ...], opts{box, cy, kicker})]."""

    def __init__(self, W, H, beats, box=(0.80, 0.52)):
        self.W, self.H = W, H
        self.beats = []
        fp = os.path.join(FONT_DIR, "BricolageGrotesque-800.ttf")
        for i, b in enumerate(beats):
            t0, t1, lines = b[:3]
            o = b[3] if len(b) > 3 else {}
            bw, bh = o.get("box", box)
            ln = [(txt, face_stops(rgb), rel) for txt, rgb, rel in lines]
            size = T3.fit_size(ln, fp, W * bw, H * bh, line_gap=0.92)
            blk = PopBlock(ln, fp, size, depth=0.20, layers=22, line_gap=0.92)
            self.beats.append((t0, t1, blk, o.get("cy", 0.53), o.get("kicker"), -1 if i % 2 else 1))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.ang = np.arctan2(yy - H * 0.5, xx - W * 0.5)
        self.rad = np.hypot(xx - W * 0.5, yy - H * 0.5) / max(W, H)

    def span(self):
        return self.beats[0][0], self.beats[-1][1]

    def background(self, paper, t):
        rays = (np.sin(self.ang * 12 + t * 0.35) > 0.35).astype(np.float32)
        rays = cv2.GaussianBlur(rays, (0, 0), 0.7)
        k = (rays * 0.55 * np.clip(1.25 - self.rad * 1.4, 0, 1))[..., None]
        return paper * (1 - k) + np.array((255, 228, 140), np.float32) / 255 * k

    def draw(self, fr, t):
        W, H = self.W, self.H
        for bi, (t0, t1, blk, cyf, kicker, direction) in enumerate(self.beats):
            last = bi == len(self.beats) - 1
            if not (t0 - 0.05 <= t < t1 + (0.25 if last else 0.02)):
                continue
            tt = t - t0
            dur = t1 - t0
            k_in = ease_out(tt / 0.42)
            k_out = ease_io((tt - dur) / 0.25) if last else ease_io((tt - (dur - 0.18)) / 0.18)
            yaw = direction * (lerp(-48, -9, k_in) + 10 * clamp01(tt / max(dur, 0.01))) + direction * 50 * k_out
            pitch = lerp(22, 7, k_in)
            roll = direction * lerp(-9, -3, k_in)
            scale = lerp(0.35, 1.0, ease_back(clamp01(tt / 0.48), 1.8)) * (1 + 0.03 * clamp01(tt / max(dur, 0.01))) * (1 + 0.4 * k_out)
            alpha = clamp01((tt + 0.05) / 0.12) * (1 - k_out)
            cy = H * cyf
            lay = blk.render(W, H, yaw=yaw, pitch=pitch, roll=roll, scale=scale, cx=W / 2, cy=cy, alpha=alpha)
            if lay is not None:
                rgb, a, (x0, y0) = lay
                # hard offset shadow of the whole block
                off = int(H * 0.016)
                hh, ww = a.shape
                xs, ys = x0 + off, y0 + off
                xe, ye = min(xs + ww, W), min(ys + hh, H)
                if xe > xs and ye > ys:
                    sa = a[:ye - ys, :xe - xs, None] * 0.9
                    reg = fr[ys:ye, xs:xe]
                    reg[:] = reg * (1 - sa) + INKF * sa
                T3.composite(fr, lay)
            if kicker:
                s, al = life(t, t0 + 0.12, t1 - 0.05 if not last else t1, 0.3, 0.18)
                img = sticker(kicker, size=int(H * (0.030 if W > H else 0.024)), fill=INK, fg=YELLOW, kind="mono",
                              pad=(22, 10), radius=10, border=0, shadow=0, tracking=0.04)
                ky = cy - (blk.h * scale) * 0.5 - H * 0.055
                place(fr, img, W / 2, ky, scale=s, rot=2.0 * direction, alpha=al * (1 - k_out))


# ---------------------------------------------------------------------------------------------- CTA stickers
def _hand(d, x, y, s):
    """Tiny pointing-hand cursor (white with ink outline), tip at (x, y)."""
    c = INK + (255,)
    w = (255, 255, 255, 255)
    pts = [(x, y), (x + s * 0.18, y), (x + s * 0.18, y + s * 0.42), (x + s * 0.55, y + s * 0.42), (x + s * 0.62, y + s * 1.0),
           (x - s * 0.18, y + s * 1.0), (x - s * 0.3, y + s * 0.55), (x, y + s * 0.6)]
    d.polygon(pts, fill=w, outline=c, width=max(int(s * 0.07), 2))


def cta(fr, kind, t, x, y, scale=1.0, dur=3.2):
    """Sticker CTA at left-centre (x, y): slaps on, a cursor clicks it, it flips to the done state, pops off."""
    if t < 0 or t > dur + 0.3:
        return
    sz = int(40 * scale)
    spec = {"subscribe": ("SUBSCRIBE", PINK, WHITE, ic_bell, "SUBSCRIBED", INK, YELLOW),
            "like": ("LIKE", YELLOW, INK, ic_thumb, "LIKED", INK, YELLOW),
            "share": ("SHARE", LILAC, INK, ic_share, "SHARED", INK, LILAC),
            "comment": ("COMMENT", MINT, INK, ic_chat, "COMMENT", INK, MINT),
            "follow": ("FOLLOW", ORANGE, INK, ic_star, "FOLLOWING", INK, ORANGE)}[kind]
    label, fill, fg, icon, label2, fill2, fg2 = spec
    t_click = 1.15
    done = t >= t_click + 0.05
    img = sticker(label2 if done else label, size=sz, fill=fill2 if done else fill, fg=fg2 if done else fg, kind="text",
                  pad=(int(24 * scale), int(12 * scale)), radius=int(18 * scale), border=5, shadow=8, icon=icon, min_w=int(330 * scale))
    s, a = life(t, 0.0, dur, 0.34, 0.24)
    bump = 1 + 0.10 * math.exp(-((t - t_click - 0.05) / 0.09) ** 2)
    wig = 4.0 * math.sin((t - t_click) * 30) * math.exp(-(t - t_click) * 5) if t > t_click else 0.0
    place(fr, img, x, y, scale=s * bump, rot=-3 + wig, alpha=a, anchor="l")
    # cursor
    if 0.45 < t < t_click + 0.55:
        k = ease_io((t - 0.45) / (t_click - 0.45))
        tx, ty = x + img.width * 0.62, y + 4
        cx, cy = lerp(tx + 160 * scale, tx, k), lerp(ty + 120 * scale, ty, k)
        press = 0.85 if abs(t - t_click) < 0.08 else 1.0
        hs = int(64 * scale * press)
        h = Image.new("RGBA", (hs + 20, hs + 20), (0, 0, 0, 0))
        _hand(ImageDraw.Draw(h), 10 + hs * 0.3, 6, hs)
        ca = a * (1 - clamp01((t - t_click - 0.3) / 0.25))
        blend(fr, h, cx - 10 - hs * 0.3, cy - 6, ca)
        if abs(t - t_click) < 0.5 and t > t_click:
            ring(fr, tx, ty, 14 + 40 * ease_out((t - t_click) / 0.4), 4, (1 - (t - t_click) / 0.5) * a)


# ---------------------------------------------------------------------------------------------- transitions
def paper_wipe(fr, p, angle=0.28):
    """Diagonal yellow band with ink edges crossing the frame; p in (-1, 1), 0 = the cut (band covering the centre)."""
    if not (-1 < p < 1):
        return fr
    H, W = fr.shape[:2]
    u = (p + 1) / 2
    band = W * 0.42
    cx = lerp(-band - H * angle, W + band + H * angle, ease_io(u))
    def poly(x0, x1):
        return np.array([[x0 - H * angle, H], [x0 + H * angle, 0], [x1 + H * angle, 0], [x1 - H * angle, H]], np.int32)
    k = 2
    m = np.zeros((H // k, W // k), np.uint8)
    cv2.fillPoly(m, [poly(cx - band / 2, cx + band / 2) // k], 255, cv2.LINE_AA)
    e = np.zeros_like(m)
    cv2.fillPoly(e, [poly(cx - band / 2 - 14, cx - band / 2 + 2) // k, poly(cx + band / 2 - 2, cx + band / 2 + 14) // k], 255, cv2.LINE_AA)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32)[..., None] / 255
    e = cv2.resize(e, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32)[..., None] / 255
    fr = fr * (1 - m) + np.array(YELLOW, np.float32) / 255 * m
    return fr * (1 - e) + INKF * e


def pop_zoom(fr, p):
    """Quick punch: the new shot lands 4 % large and settles (p in 0..1 after the cut)."""
    if not (0 <= p < 1):
        return fr
    H, W = fr.shape[:2]
    s = 1 + 0.045 * (1 - ease_out(p))
    M = np.array([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]], np.float32)
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------------------------------------- logo bug
_LOGO = {}


def logo_bug(size, path):
    """Round sticker with the channel logo: white disc, ink rim, hard shadow (PIL RGBA)."""
    key = (size, path)
    if key in _LOGO:
        return _LOGO[key]
    k = 3
    b, sh = 4, 6
    S = size + 2 * b + sh
    img = Image.new("RGBA", (S * k, S * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([sh * k, sh * k, (S - 1) * k, (S - 1) * k], fill=INK + (255,))
    d.ellipse([0, 0, (size + 2 * b) * k - 1, (size + 2 * b) * k - 1], fill=INK + (255,))
    d.ellipse([b * k, b * k, (size + b) * k - 1, (size + b) * k - 1], fill=(255, 255, 255, 255))
    lg = Image.open(path).convert("RGBA")
    ls = int(size * 0.86 * k)
    lg = lg.resize((ls, ls), Image.LANCZOS)
    mask = Image.new("L", (ls, ls), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, ls - 1, ls - 1], fill=255)
    a = Image.fromarray((np.asarray(lg.split()[3], np.float32) * np.asarray(mask, np.float32) / 255).astype(np.uint8))
    lg.putalpha(a)
    off = int((b + size * 0.07) * k)
    img.alpha_composite(lg, (off, off))
    out = img.resize((S, S), Image.LANCZOS)
    _LOGO[key] = out
    return out
