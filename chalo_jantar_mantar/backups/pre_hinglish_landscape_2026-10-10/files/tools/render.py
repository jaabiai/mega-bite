"""Cinematic Hindi lyric-video compositor.

Reads lyric_timing.json (editable) and renders frames of a 1080x1920 portrait video on top of the
ORIGINAL footage (its animated colour field + cover art are kept and graded).
Frames are produced by a pure function of time -> render_frame(t), so any time range can be
rendered independently (and in parallel).
"""
import os, sys, json, math, functools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

T = os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")
A = T + "assets/"
W, H, FPS = 1080, 1920, 30
SAFFRON = (255, 153, 51)
GREEN = (19, 136, 8)
WHITE = (255, 255, 255)
NAVY = (0, 0, 128)

# --------------------------------------------------------------------------------------
# small math helpers
# --------------------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def smooth(x):
    x = clamp(x); return x * x * (3 - 2 * x)

def ease_out(x):
    x = clamp(x); return 1 - (1 - x) ** 3

def ease_out_back(x, s=1.9):
    x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2

def lerp(a, b, t):
    return a + (b - a) * t

# --------------------------------------------------------------------------------------
# fonts & text sprites
# --------------------------------------------------------------------------------------
FONT_FILES = {
    "body": "Hind-Bold.ttf",
    "display": "RozhaOne-Regular.ttf",
    "punch": "Khand-Bold.ttf",
    "light": "Hind-SemiBold.ttf",
}

@functools.lru_cache(maxsize=64)
def font(kind, size):
    return ImageFont.truetype(A + FONT_FILES[kind], size, layout_engine=ImageFont.Layout.RAQM)

def text_w(txt, f):
    return f.getlength(txt)

def wrap_balanced(text, f, max_w):
    words = text.split(" ")
    if text_w(text, f) <= max_w or len(words) < 2:
        return [text]
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        wa, wb = text_w(a, f), text_w(b, f)
        if max(wa, wb) <= max_w:
            sc = abs(wa - wb)
            if best is None or sc < best[0]:
                best = (sc, [a, b])
    if best:
        return best[1]
    # three lines fallback
    n = len(words); i, j = n // 3, 2 * n // 3
    return [" ".join(words[:i]), " ".join(words[i:j]), " ".join(words[j:])]

def render_text(txt, f, fill=WHITE, pad=36, gradient=None, stroke=0, stroke_fill=(0, 0, 0)):
    """Returns RGBA PIL image with `pad` px of transparent margin. gradient: list[(pos, rgb)] vertical."""
    asc, desc = f.getmetrics()
    w = int(text_w(txt, f)) + pad * 2 + 4
    h = asc + desc + pad * 2
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((pad, pad), txt, font=f, fill=255, stroke_width=stroke)
    return _fill_from_mask(mask, fill, gradient, stroke=stroke)

def render_text_outlined(txt, f, fill=WHITE, pad=48, gradient=None, stroke=5, stroke_rgba=(5, 7, 22, 230)):
    """Fill text with a dark outline underneath (keeps bright gradients legible over bloom)."""
    asc, desc = f.getmetrics()
    w = int(text_w(txt, f)) + pad * 2 + 4
    h = asc + desc + pad * 2
    m_out = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m_out).text((pad, pad), txt, font=f, fill=255, stroke_width=stroke)
    m_in = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m_in).text((pad, pad), txt, font=f, fill=255)
    out = Image.new("RGBA", (w, h), tuple(stroke_rgba[:3]) + (255,))
    out.putalpha(m_out.point(lambda v: int(v * stroke_rgba[3] / 255)))
    out.alpha_composite(_fill_from_mask(m_in, fill, gradient))
    return out

def _fill_from_mask(mask, fill, gradient=None, stroke=0):
    w, h = mask.size
    if gradient is None:
        col = Image.new("RGBA", (w, h), tuple(fill) + (255,))
    else:
        g = np.zeros((h, 3), np.float32)
        ys = np.linspace(0, 1, h)
        pos = [p for p, _ in gradient]
        for c in range(3):
            g[:, c] = np.interp(ys, pos, [rgb[c] for _, rgb in gradient])
        col = Image.fromarray(np.repeat(g[:, None, :], w, 1).astype(np.uint8)).convert("RGBA")
    col.putalpha(mask)
    return col

def glow_of(img, radius, color, gain=1.0):
    """Blurred coloured halo of an RGBA sprite's alpha (RGBA)."""
    a = img.split()[3].filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: min(255, int(v * gain)))
    out = Image.new("RGBA", img.size, tuple(color) + (255,))
    out.putalpha(a)
    return out

def shadow_of(img, radius=10, alpha=0.7, dy=6):
    a = img.split()[3].filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(v * alpha))
    out = Image.new("RGBA", img.size, (0, 0, 0, 255)); out.putalpha(a)
    if dy:
        out = out.transform(out.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy))
    return out

# --------------------------------------------------------------------------------------
# frame compositing helpers (uint8 frame, float math on the touched region only)
# --------------------------------------------------------------------------------------
_XFORM_CACHE = {}

def blit(frame, spr, cx, cy, opacity=1.0, mode="over", scale=1.0, rot=0.0, cache=False):
    """Blit PIL RGBA sprite centred at (cx,cy). cache=True memoises the scaled/rotated sprite on
    quantised scale (0.003) / angle (0.5 deg) - only for long-lived sprites."""
    if opacity <= 0.003:
        return
    if scale != 1.0 or rot:
        if cache:
            scale = round(scale / 0.003) * 0.003
            rot = round(rot / 0.5) * 0.5
            key = (id(spr), round(scale, 4), rot)
            hit = _XFORM_CACHE.get(key)
            if hit is not None:
                spr = hit
            else:
                spr = _xform(spr, scale, rot)
                if len(_XFORM_CACHE) > 90:
                    _XFORM_CACHE.clear()
                _XFORM_CACHE[key] = spr
        else:
            spr = _xform(spr, scale, rot)
    sw, sh = spr.size
    x0, y0 = int(round(cx - sw / 2)), int(round(cy - sh / 2))
    _blit_xy(frame, spr, x0, y0, opacity, mode)

def _xform(spr, scale, rot):
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
    return spr

def _blit_xy(frame, spr, x0, y0, opacity=1.0, mode="over"):
    sw, sh = spr.size
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(W, x0 + sw), min(H, y0 + sh)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    s = np.asarray(spr)[fy0 - y0: fy1 - y0, fx0 - x0: fx1 - x0].astype(np.float32)
    a = (s[..., 3:4] / 255.0) * opacity
    sub = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    rgb = s[..., :3]
    if mode == "over":
        out = sub * (1 - a) + rgb * a
    elif mode == "add":
        out = sub + rgb * a
    elif mode == "screen":
        out = 255 - (255 - sub) * (255 - rgb * a) / 255.0
    else:
        raise ValueError(mode)
    frame[fy0:fy1, fx0:fx1] = np.clip(out, 0, 255).astype(np.uint8)

def add_color(frame, box, color, amount):
    """Additive flat colour over a box (x0,y0,x1,y1)."""
    if amount <= 0.003: return
    x0, y0, x1, y1 = box
    sub = frame[y0:y1, x0:x1].astype(np.float32)
    sub += np.array(color, np.float32) * amount
    frame[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)

def radial_sprite(size_w, size_h, color, power=2.0):
    yy, xx = np.mgrid[0:size_h, 0:size_w].astype(np.float32)
    d = np.sqrt(((xx - size_w / 2) / (size_w / 2)) ** 2 + ((yy - size_h / 2) / (size_h / 2)) ** 2)
    a = np.clip(1 - d, 0, 1) ** power
    rgba = np.zeros((size_h, size_w, 4), np.uint8)
    rgba[..., :3] = color
    rgba[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgba)

# --------------------------------------------------------------------------------------
# Timeline data
# --------------------------------------------------------------------------------------
SPECIAL_RULES = [
    ("wake", lambda t: "देशवासियो" in t),
    ("stamp", lambda t: "Vote Chori" in t),
    ("defiant", lambda t: "ये मुल्क तेरा बाप का नहीं" in t),
    ("people", lambda t: "ये जनता का हिंदुस्तान है" in t),
    ("march", lambda t: ("चलो" in t and "जंतर-मंतर" in t) or t.startswith("जंतर-मंतर चलो")),
]

def classify(text):
    for name, rule in SPECIAL_RULES:
        if rule(text):
            return name
    return "regular"

# per-section "light level" (0..1) keyed on the lyric-file section labels (prefix match)
SECTION_LEVEL = [
    ("INTRO", 0.30), ("BEAT BEGINS", 0.45), ("VERSE 1", 0.55), ("PRE-CHORUS", 0.70), ("CHORUS", 0.95),
    ("VERSE 2", 0.65), ("HOOK", 0.85), ("VERSE 3", 0.70), ("BRIDGE", 0.38), ("FINAL CHORUS", 1.0),
    ("FINAL RAP", 0.90), ("OUTRO", 0.55), ("FINAL VOICE", 0.80),
]

def section_level(sec):
    for k, v in SECTION_LEVEL:
        if sec.upper().startswith(k):
            return v
    return 0.5


class Scene:
    LEAD = 0.05     # text appears this long before the sung onset
    HOLD = 0.30     # text lingers this long after the line ends (if the next line hasn't started)

    def __init__(self, timing_path, global_offset=None):
        data = json.load(open(timing_path, encoding="utf-8"))
        self.meta = data["meta"]
        self.offset = self.meta.get("global_offset_s", 0.0) if global_offset is None else global_offset
        self.lines = data["lines"]
        for l in self.lines:
            l["style"] = l.get("style") or classify(l["text"])
        self.duration = self.meta.get("duration_s", 267.2)
        self._prepare_levels()
        self._load_assets()
        self._prepare_audio_features()
        self._prepare_text()

    # ---------------- assets ----------------
    def _load_assets(self):
        self.field = np.memmap(A + "field_clean.u8", dtype=np.uint8, mode="r").reshape(-1, 192, 108, 3)
        tile = Image.open(A + "tile.png")
        self.tile = tile.resize((560, 760), Image.LANCZOS)
        self.credit_by = Image.open(A + "credit_by.png")
        self.credit_suno = Image.open(A + "credit_suno.png")
        self.credit_by = self.credit_by.resize((int(self.credit_by.width * 1.3), int(self.credit_by.height * 1.3)), Image.LANCZOS)
        self.credit_suno = self.credit_suno.resize((int(self.credit_suno.width * 1.3), int(self.credit_suno.height * 1.3)), Image.LANCZOS)
        self.crowd = [Image.open(A + f"crowd{i}.png") for i in range(3)]
        self.flags = json.load(open(A + "flags.json"))
        self.jantar = Image.open(A + "jantar.png")
        self.jantar = self.jantar.resize((int(self.jantar.width * 0.72), int(self.jantar.height * 0.72)), Image.LANCZOS)
        self.chakra = Image.open(A + "chakra.png")
        self.icons = {k: Image.open(A + f"icon_{k}.png").resize((200, 200), Image.LANCZOS) for k in ("vote", "book", "scales", "diya")}
        self.icon_glow = {k: glow_of(v, 14, (255, 190, 110) if k != "vote" else (190, 140, 255), 0.9) for k, v in self.icons.items()}
        # tile halo
        halo = Image.new("RGBA", (self.tile.width + 260, self.tile.height + 260), (0, 0, 0, 0))
        m = Image.new("L", halo.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([130, 130, 130 + self.tile.width, 130 + self.tile.height], 22, fill=255)
        m = m.filter(ImageFilter.GaussianBlur(70))
        halo = Image.new("RGBA", halo.size, SAFFRON + (255,)); halo.putalpha(m)
        self.tile_halo = halo
        sh = Image.new("RGBA", halo.size, (0, 0, 0, 255)); sh.putalpha(m.point(lambda v: int(v * 0.9)))
        self.tile_shadow = sh
        # tile edge
        edge = Image.new("RGBA", (self.tile.width + 8, self.tile.height + 8), (0, 0, 0, 0))
        ImageDraw.Draw(edge).rounded_rectangle([0, 0, edge.width - 1, edge.height - 1], 20, outline=(255, 244, 220, 255), width=3)
        self.tile_edge = edge
        # ember sprite
        self.ember = radial_sprite(26, 26, (255, 200, 120), 1.6)
        self.ember_w = radial_sprite(26, 26, (255, 255, 255), 2.4)
        # flag sprites (pre-rendered frames of a ripple cycle)
        import art
        self.flag_frames = [Image.fromarray(art.flag_sprite(112, 72, ph, 4.2, tint=0.78)) for ph in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
        # vignette + coordinate grids at low res for background maths
        self.bw, self.bh = 360, 640
        yy, xx = np.mgrid[0:self.bh, 0:self.bw].astype(np.float32)
        xn, yn = (xx / self.bw - 0.5) * 2, (yy / self.bh - 0.5) * 2
        self.vig = (1 - 0.5 * np.clip((xn ** 2 * 0.9 + yn ** 2 * 0.55), 0, 1.6) ** 1.1).astype(np.float32)
        # rays centred on the tile
        cx, cy = 0.5 * self.bw, (590 / H) * self.bh
        self.ray_ang = np.arctan2(yy - cy, xx - cx).astype(np.float32)
        self.ray_dist = (np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / self.bh).astype(np.float32)
        # horizon glow
        gx, gy = 0.5 * self.bw, (1500 / H) * self.bh
        self.sun = np.exp(-(((xx - gx) / (self.bw * 0.62)) ** 2 + ((yy - gy) / (self.bh * 0.16)) ** 2)).astype(np.float32)
        self.base_grad = np.zeros((self.bh, self.bw, 3), np.float32)
        top, mid, bot = np.array([4, 6, 20]), np.array([13, 15, 42]), np.array([22, 14, 34])
        for i in range(self.bh):
            t = i / self.bh
            self.base_grad[i, :] = (top + (mid - top) * (t / 0.55) if t < 0.55 else mid + (bot - mid) * ((t - 0.55) / 0.45))
        rng = np.random.RandomState(7)
        self.em = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(18, 60), rng.uniform(0, 6.28), rng.uniform(0.4, 1.0)) for _ in range(70)]
        self.scrim = self._make_scrim()

    def _make_scrim(self):
        h = 420
        a = np.zeros((h, W), np.float32)
        y = np.linspace(0, 1, h)
        prof = np.sin(np.pi * y) ** 1.2
        a[:] = prof[:, None]
        rgba = np.zeros((h, W, 4), np.uint8)
        rgba[..., :3] = (3, 4, 14)
        rgba[..., 3] = (a * 160).astype(np.uint8)
        return Image.fromarray(rgba)

    # ---------------- audio-derived features ----------------
    def _prepare_audio_features(self):
        env = np.load(T + "work/low_env.npy")  # 200 Hz low-band envelope
        d = np.maximum(0, np.diff(env, prepend=env[0]))
        d = d / (np.percentile(d, 97) + 1e-9)
        n = int(self.duration * FPS) + 2
        k = np.zeros(n, np.float32)
        for i in range(n):
            a, b = int(i / FPS * 200), int((i + 1) / FPS * 200)
            k[i] = d[a:max(b, a + 1)].max() if a < len(d) else 0
        k = np.clip(k, 0, 1)
        out = np.zeros_like(k)
        acc = 0.0
        for i in range(n):
            acc = max(k[i], acc * 0.80)
            out[i] = acc
        self.kick = out
        # slow loudness for glow breathing
        self.loud = np.convolve(out, np.ones(15) / 15, mode="same")

    def _kick(self, t):
        i = int(clamp(t * FPS, 0, len(self.kick) - 1))
        return float(self.kick[i])

    # ---------------- sections / levels ----------------
    def _prepare_levels(self):
        pts = [(0.0, 0.18)]
        for l in self.lines:
            lv = section_level(l.get("section", ""))
            pts.append((l["start"] + self.offset, lv))
        pts.append((self.duration - 6, pts[-1][1]))
        pts.append((self.duration, 0.1))
        self.level_pts = pts

    def level(self, t):
        xs = [p[0] for p in self.level_pts]; ys = [p[1] for p in self.level_pts]
        # smooth over ~2 s so section changes bloom instead of jump
        samples = [np.interp(t + dt, xs, ys, left=ys[0]) for dt in np.linspace(-1.5, 1.5, 7)]
        return float(np.mean(samples))

    # ---------------- text prep ----------------
    def _prepare_text(self):
        self.cards = {}
        for i, l in enumerate(self.lines):
            if l["style"] != "regular":
                continue
            f = font("body", 80)
            rows = wrap_balanced(l["text"], f, 950)
            if len(rows) > 2:
                f = font("body", 68); rows = wrap_balanced(l["text"], f, 960)
            asc, desc = f.getmetrics()
            line_h = int((asc + desc) * 0.98)
            sprites = [render_text(r, f, WHITE) for r in rows]
            w = max(s.width for s in sprites)
            h = line_h * len(rows) + 72
            card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            for j, s in enumerate(sprites):
                card.alpha_composite(s, ((w - s.width) // 2, j * line_h))
            shadow = shadow_of(card, 14, 0.85, 8)
            glow = glow_of(card, 22, (255, 170, 80), 0.55)
            self.cards[l["id"]] = (card, shadow, glow, len(rows))
        self.special_cache = {}
        self.motif = {}
        for l in self.lines:
            if l["style"] != "regular":
                continue
            tx = l["text"]
            m = None
            if "दीप" in tx: m = "diya"
            elif "इंसाफ़" in tx: m = "scales"
            elif "संविधान" in tx or "अधिकार" in tx: m = "book"
            elif any(w in tx for w in ("वोट", "स्याही", "पर्ची", "गिनती")): m = "vote"
            if m: self.motif[l["id"]] = m
        self.title_sprites = self._make_title()

    def _make_title(self):
        t1 = render_text("चलो जंतर-मंतर", font("display", 150), WHITE, gradient=[(0, (255, 255, 255)), (0.55, (255, 236, 205)), (1, (255, 190, 110))])
        t2 = render_text("आवाज़ जनता की", font("body", 62), (255, 225, 190))
        return t1, t2

    # ---------------- visibility windows ----------------
    def display_window(self, i):
        """(show_from, show_until) in seconds for line i."""
        l = self.lines[i]
        st = l["start"] + self.offset
        en = l["end"] + self.offset
        nxt = self.lines[i + 1]["start"] + self.offset if i + 1 < len(self.lines) else self.duration
        show_from = st - self.LEAD
        until = min(en + self.HOLD, nxt + (0.0 if l["style"] == "regular" else 0.10))
        return show_from, max(until, st + 0.6)

    # ----------------------------------------------------------------------------------
    # background
    # ----------------------------------------------------------------------------------
    def background(self, t):
        lvl = self.level(t)
        kick = self._kick(t)
        fi = clamp(t * 10, 0, self.field.shape[0] - 2)
        i0 = int(fi); fr = fi - i0
        F = (self.field[i0].astype(np.float32) * (1 - fr) + self.field[i0 + 1].astype(np.float32) * fr) / 255.0
        Fb = np.asarray(Image.fromarray((F * 255).astype(np.uint8)).resize((self.bw, self.bh), Image.BICUBIC)).astype(np.float32) / 255.0
        lum = Fb @ np.array([0.299, 0.587, 0.114], np.float32)
        light = np.clip((lum - 0.40) / 0.45, 0, 1) ** 1.3
        chroma = Fb - lum[..., None]
        tint = np.array([1.0, 0.70, 0.36], np.float32)[None, None, :] + chroma * 1.6
        tint = np.clip(tint, 0, 1.3)
        amt = (0.20 + 0.55 * lvl)
        img = self.base_grad + (light[..., None] * tint * 255.0 * 0.62 * amt)
        # horizon sunrise
        sun_col = np.array([255, 150, 55], np.float32)
        img += self.sun[..., None] * sun_col * (0.22 + 0.62 * lvl + 0.10 * kick)
        # god-rays from the tile centre
        ang = self.ray_ang
        rot = t * 0.05
        r1 = (0.5 + 0.5 * np.sin(14 * ang + rot * 6 + 1.3)) ** 4
        r2 = (0.5 + 0.5 * np.sin(23 * ang - rot * 4)) ** 5
        ray = (0.65 * r1 + 0.45 * r2) * np.exp(-self.ray_dist * 2.1)
        ray *= (0.07 + 0.22 * lvl + 0.16 * kick)
        img += ray[..., None] * np.array([255, 205, 140], np.float32)
        img *= self.vig[..., None]
        img = np.clip(img, 0, 255).astype(np.uint8)
        return np.asarray(Image.fromarray(img).resize((W, H), Image.BILINEAR)).copy()

    # ----------------------------------------------------------------------------------
    # focus envelope: how "takeover" the current moment is (0 calm .. 1 special line on screen)
    # ----------------------------------------------------------------------------------
    def focus(self, t):
        f = 0.0
        for i, l in enumerate(self.lines):
            if l["style"] == "regular":
                continue
            a, b = self.display_window(i)
            if t < a - 0.2 or t > b + 1.0:
                continue
            v = smooth((t - (a - 0.2)) / 0.25) * (1 - smooth((t - b) / 0.9))
            f = max(f, v)
        return f

    def active_special(self, t):
        for i, l in enumerate(self.lines):
            if l["style"] == "regular":
                continue
            a, b = self.display_window(i)
            if a <= t <= b + 0.35:
                return i
        return None

    # ----------------------------------------------------------------------------------
    # main frame
    # ----------------------------------------------------------------------------------
    def render_frame(self, t):
        frame = self.background(t)
        lvl = self.level(t)
        kick = self._kick(t)
        foc = self.focus(t)
        sp_idx = self.active_special(t)
        sp_style = self.lines[sp_idx]["style"] if sp_idx is not None else None
        end_fade = clamp((self.duration - t) / 2.2)
        # --- chakra ring behind the tile -------------------------------------------------
        ring_a = (0.10 + 0.20 * lvl) * (1 - 0.3 * foc) * (1 + 0.5 * kick)
        blit(frame, self.chakra, 540, 590, ring_a, "add", scale=0.98 + 0.06 * foc + 0.01 * kick, rot=-(t * 4.0) % 360, cache=True)
        # --- Jantar Mantar silhouette ---------------------------------------------------
        jm_on = 0.55 + 0.45 * (1.0 if sp_style in ("march", "people") else 0.0)
        bridge = self._in_section(t, "BRIDGE")
        jm_alpha = (0.0 if bridge else jm_on) * clamp(t / 6.0)
        if jm_alpha > 0.01:
            self._draw_jantar(frame, t, jm_alpha, lvl, sp_style)
        # --- hero tile -----------------------------------------------------------------
        self._draw_tile(frame, t, lvl, kick, foc)
        # --- crowd ---------------------------------------------------------------------
        self._draw_crowd(frame, t, lvl, kick, bridge)
        # --- embers --------------------------------------------------------------------
        self._draw_embers(frame, t, lvl, kick)
        # --- title ---------------------------------------------------------------------
        self._draw_title(frame, t)
        # --- lyrics --------------------------------------------------------------------
        self._draw_lyrics(frame, t, lvl, kick)
        # --- credits (source marks kept) ----------------------------------------------------
        cr = clamp(t / 2.0) * end_fade
        blit(frame, self.credit_by, 540, 150, 0.78 * cr)
        blit(frame, self.credit_suno, 540, 1868, 0.62 * cr)
        # --- global fades -------------------------------------------------------------------
        fade = clamp(t / 1.6) * clamp((self.duration - t) / 2.0)
        if fade < 0.999:
            frame = (frame.astype(np.float32) * fade).astype(np.uint8)
        return frame

    def _in_section(self, t, name):
        for i, l in enumerate(self.lines):
            if l.get("section", "").upper().startswith(name):
                a = l["start"] + self.offset
                # section spans until the first later line with a different section
                j = i
                while j + 1 < len(self.lines) and self.lines[j + 1].get("section", "").upper().startswith(name):
                    j += 1
                b = self.lines[j]["end"] + self.offset
                if a - 0.5 <= t <= b + 0.5:
                    return True
        return False

    # ---------------- scene pieces ----------------
    def _draw_tile(self, frame, t, lvl, kick, foc):
        zoom = 1.0 + 0.035 * (t / self.duration) + 0.012 * kick
        s = zoom * (1 - 0.16 * foc)
        a = 1 - 0.58 * foc
        cx, cy = 540, 590 - 40 * foc
        blit(frame, self.tile_shadow, cx, cy + 30, 0.9 * a, "over", scale=s, cache=True)
        blit(frame, self.tile_halo, cx, cy, (0.22 + 0.38 * lvl + 0.25 * kick) * a, "add", scale=s, cache=True)
        blit(frame, self.tile, cx, cy, a, "over", scale=s, cache=True)
        blit(frame, self.tile_edge, cx, cy, 0.55 * a, "over", scale=s, cache=True)

    def _draw_jantar(self, frame, t, alpha, lvl, sp_style):
        jm = self.jantar
        x = 540 + 10 - 10 * math.sin(t * 0.05)  # slow drift
        y = 1690 - jm.height / 2 + 6
        # bright halo behind
        if sp_style in ("march", "people"):
            glow = radial_sprite(900, 520, (255, 160, 70), 1.4)
            blit(frame, glow, x + 60, y + 90, 0.55 * alpha, "add")
        spr = jm.copy()
        blit(frame, spr, x, y, alpha, "over")

    def _draw_crowd(self, frame, t, lvl, kick, bridge):
        beat = 0.5 + 0.5 * math.cos(2 * math.pi * (t - 0.31) / 0.6475)
        bob = (1.8 * kick) + (0.6 if lvl > 0.5 else 0.2) * beat
        offs = [(-160 + 14 * math.sin(t * 0.07), 1428, 0.45), (-160 - 10 * math.sin(t * 0.06 + 1), 1428, 0.7), (-160 + 8 * math.sin(t * 0.05 + 2), 1428, 1.0)]
        dim = 0.8 if bridge else 1.0
        for r, (ox, oy, shade) in enumerate(offs):
            blit(frame, self.crowd[r], ox + self.crowd[r].width / 2, oy + self.crowd[r].height / 2 - bob * (r + 1) * 0.8, 1.0 * dim, "over")
            if r < 2:
                # flags on rows 0 and 1
                for (px, py, s) in self.flags[r]:
                    fx = ox + px
                    fy = oy - bob * (r + 1) * 0.8 + py
                    if -80 < fx < W + 80:
                        fi = int((t * 1.7 + px * 0.01) * 24) % 24
                        fl = self.flag_frames[fi]
                        k = 0.5 + 0.5 * s
                        blit(frame, fl, fx + 56 * k, fy + 26 * k, (0.9 if r else 0.7) * dim, "over", scale=k * 0.95)

    def _draw_embers(self, frame, t, lvl, kick):
        n = int(18 + 52 * lvl)
        for (x, y, sp, ph, a) in self.em[:n]:
            yy = (y - sp * t * (0.8 + 0.6 * lvl)) % (H + 60) - 30
            xx = x + 22 * math.sin(t * 0.6 + ph)
            tw = 0.55 + 0.45 * math.sin(t * 2.3 + ph * 3)
            blit(frame, self.ember if a < 0.75 else self.ember_w, xx, yy, 0.55 * a * tw * (0.4 + 0.6 * lvl) * (1 + 0.4 * kick), "add", scale=0.5 + a * 0.5)

    def _draw_title(self, frame, t):
        a = smooth((t - 0.4) / 0.9) * (1 - smooth((t - 3.0) / 0.55))
        if a <= 0.01:
            return
        t1, t2 = self.title_sprites
        dy = (1 - ease_out((t - 0.4) / 1.4)) * 18
        blit(frame, glow_of(t1, 26, (255, 150, 60), 0.5), 540, 1180 + dy, a * 0.7, "add")
        blit(frame, t1, 540, 1180 + dy, a)
        blit(frame, t2, 540, 1318 + dy, a * 0.9)
        # tricolor hairline
        self._tricolor_bar(frame, 540, 1272 + dy, 300 * ease_out((t - 0.8) / 0.9), 6, a)

    def _tricolor_bar(self, frame, cx, cy, width, height, alpha):
        if width < 2 or alpha <= 0.01:
            return
        w = int(width); h = int(height)
        x0 = int(cx - w / 2); seg = w / 3.0
        for k, col in enumerate((SAFFRON, (250, 250, 245), GREEN)):
            xa, xb = int(x0 + k * seg), int(x0 + (k + 1) * seg)
            xa, xb = max(0, xa), min(W, xb)
            ya, yb = int(cy - h / 2), int(cy + h / 2)
            if xb > xa:
                sub = frame[ya:yb, xa:xb].astype(np.float32)
                sub = sub * (1 - alpha) + np.array(col, np.float32) * alpha
                frame[ya:yb, xa:xb] = sub.astype(np.uint8)

    # ---------------- regular lyric cards ----------------
    def _draw_lyrics(self, frame, t, lvl, kick):
        # scrim behind lyric zone while any regular line is on screen
        active = []
        for i, l in enumerate(self.lines):
            a, b = self.display_window(i)
            if a - 0.1 <= t <= b + 0.25:
                active.append((i, a, b))
        any_regular = any(self.lines[i]["style"] == "regular" for i, _, _ in active)
        if any_regular:
            blit(frame, self.scrim, 540, 1295, 0.9)
        for i, a, b in active:
            l = self.lines[i]
            if l["style"] == "regular":
                self._draw_regular(frame, l, t, a, b, kick)
            else:
                self._draw_special(frame, i, l, t, a, b, kick)

    def _draw_regular(self, frame, l, t, a, b, kick):
        card, shadow, glow, nrows = self.cards[l["id"]]
        tin = (t - a) / 0.20
        tout = (t - (b - 0.14)) / 0.14
        alpha = ease_out(tin) * (1 - smooth(tout))
        if alpha <= 0.01:
            return
        dy = (1 - ease_out(tin)) * 26 + smooth(tout) * -10
        sc = 0.96 + 0.04 * ease_out(tin)
        cy = 1285 + dy
        # slow breathing (readable, subtle)
        sc *= 1 + 0.012 * clamp((t - a) / 4.0)
        blit(frame, glow, 540, cy, alpha * (0.35 + 0.25 * kick), "add", scale=sc)
        blit(frame, shadow, 540, cy, alpha, "over", scale=sc)
        blit(frame, card, 540, cy, alpha, "over", scale=sc)
        # tricolor tick under the text, grows with the line
        prog = ease_out((t - a) / 0.5)
        self._tricolor_bar(frame, 540, int(cy + card.height / 2 - 14), 150 * prog, 5, alpha * 0.9)
        m = self.motif.get(l["id"])
        if m:
            u = (t - a - 0.08) / 0.30
            ia = ease_out(u) * (1 - smooth(tout))
            iy = 1075 + (1 - ease_out(u)) * 24 + 4 * math.sin(t * 1.6)
            blit(frame, self.icon_glow[m], 540, iy, ia * (0.45 + 0.3 * kick), "add")
            blit(frame, self.icons[m], 540, iy, ia * 0.95, "over")

    # ---------------- special lines ----------------
    def _special_rows(self, text, style):
        words = text.split(" ")
        if style == "defiant":
            half = (len(words) + 1) // 2
            return [" ".join(words[:half]), " ".join(words[half:])]
        if style == "stamp":
            return [" ".join(words[:2]), " ".join(words[2:])]
        if style == "people":
            return [" ".join(words[:3]), " ".join(words[3:])] if len(words) >= 5 else [text]
        return [words[0], " ".join(words[1:])] if len(words) > 1 else [text]

    def _special_assets(self, l):
        key = l["id"]
        if key in self.special_cache:
            return self.special_cache[key]
        style = l["style"]
        rows = self._special_rows(l["text"], style)
        specs = {"wake": ("display", 215, None), "march": ("punch", 250, None), "stamp": ("punch", 290, None),
                 "defiant": ("punch", 222, None), "people": ("display", 160, [(0, (255, 168, 76)), (0.5, (255, 255, 255)), (1, (60, 190, 90))])}
        kind, size, grad = specs[style]
        # shrink to fit width
        f = font(kind, size)
        while max(text_w(r, f) for r in rows) > 900 and size > 80:
            size -= 6; f = font(kind, size)
        sprites = []
        for r in rows:
            spr = render_text_outlined(r, f, WHITE, 48, grad, 5 if style != "stamp" else 6)
            sprites.append((r, spr, glow_of(spr, 26, SAFFRON if style != "people" else (255, 200, 120), 0.9), shadow_of(spr, 16, 0.9, 10)))
        words = None
        if style == "defiant":
            words = []
            for r in rows:
                ws = r.split(" ")
                row_words = []
                for w_ in ws:
                    ws_spr = render_text_outlined(w_, f, WHITE, 44, None, 5)
                    row_words.append((w_, ws_spr, glow_of(ws_spr, 22, SAFFRON, 0.9), shadow_of(ws_spr, 14, 0.9, 8)))
                words.append(row_words)
        self.special_cache[key] = (rows, sprites, f, words)
        return self.special_cache[key]

    def _draw_special(self, frame, i, l, t, a, b, kick):
        rows, sprites, f, words = self._special_assets(l)
        style = l["style"]
        tr = t - a
        dur = b - a
        out = 1 - smooth((t - (b - 0.22)) / 0.30)
        shake = 0.0
        cy0 = 800
        asc, desc = f.getmetrics()
        row_h = int((asc + desc) * 0.80)
        n = len(sprites)
        if style == "stamp":
            ink = max((sp[1].getbbox()[3] - sp[1].getbbox()[1]) for sp in sprites)
            row_h = int(ink * 1.10)
        ys = [cy0 + (j - (n - 1) / 2) * row_h for j in range(n)]
        base_scale = 1.0 + 0.03 * clamp(tr / max(dur, 0.5))
        # soft dark backing so bright blooms never wash the type out
        pad_a = {"people": 0.62, "wake": 0.50, "march": 0.42, "stamp": 0.30, "defiant": 0.45}[style]
        blit(frame, self._dark_pad(), 540, cy0, pad_a * smooth(tr / 0.25) * out, "over")

        def hit(t0, amp):  # decaying shake
            dt = tr - t0
            return amp * math.exp(-dt / 0.11) * math.sin(dt * 70) if dt >= 0 else 0.0

        if style == "wake":
            self._bloom(frame, 540, cy0, tr, dur, out, 0.9, (255, 175, 90), big=True)
            t_row = [0.0, 0.32]
            for j, (txt, spr, glw, shd) in enumerate(sprites):
                u = tr - t_row[min(j, 1)]
                if u < -0.02: continue
                e = ease_out(u / 0.45)
                eb = ease_out_back(u / 0.38, 1.2)
                sc = base_scale * (lerp(1.32 if j else 1.12, 1.0, eb))
                al = clamp(u / 0.20) * out
                # soft left->right reveal
                spr_v = self._wipe(spr, e)
                dx = hit(t_row[min(j, 1)], 7) if j else 0
                blit(frame, glw, 540 + dx, ys[j], al * (0.65 + 0.35 * kick), "add", scale=sc)
                blit(frame, shd, 540 + dx, ys[j], al, "over", scale=sc)
                blit(frame, spr_v, 540 + dx, ys[j], al, "over", scale=sc)
            u = tr - 0.32
            if 0 <= u < 0.6:
                self._ring(frame, 540, ys[min(1, n - 1)], u / 0.6, (255, 200, 120), out)
                add_color(frame, (0, 0, W, H), (255, 220, 170), 0.20 * math.exp(-u / 0.10) * out)
        elif style == "march":
            self._bloom(frame, 540, cy0 + 120, tr, dur, out, 0.55, (255, 150, 60))
            t_row = [0.0, 0.30]
            widest = 0
            for j, (txt, spr, glw, shd) in enumerate(sprites):
                u = tr - t_row[min(j, 1)]
                if u < -0.02: continue
                eb = ease_out_back(u / 0.20, 1.6)
                sc = base_scale * lerp(1.7, 1.0, eb)
                al = clamp(u / 0.10) * out
                dx = hit(t_row[min(j, 1)], 10)
                dy = hit(t_row[min(j, 1)] + 0.02, 6)
                blit(frame, glw, 540 + dx, ys[j] + dy, al * (0.6 + 0.4 * kick), "add", scale=sc)
                blit(frame, shd, 540 + dx, ys[j] + dy, al, "over", scale=sc)
                blit(frame, spr, 540 + dx, ys[j] + dy, al, "over", scale=sc)
                widest = max(widest, text_w(txt, f))
            u = tr - 0.55
            if u > 0:
                self._tricolor_bar(frame, 540, ys[-1] + row_h * 0.52, widest * 0.86 * ease_out(u / 0.45), 12, out)
            u = tr - t_row[1]
            if 0 <= u < 0.45:
                self._ring(frame, 540, ys[min(1, n - 1)], u / 0.45, (255, 190, 110), out * 0.8)
        elif style == "stamp":
            self._bloom(frame, 540, cy0, tr, dur, out, 0.5, (255, 90, 60))
            t_row = [0.0, 0.50]
            # plate behind both rows
            plate_a = smooth(tr / 0.2) * out
            self._stamp_plate(frame, 540, cy0, plate_a, n, row_h)
            for j, (txt, spr, glw, shd) in enumerate(sprites):
                u = tr - t_row[min(j, 1)]
                if u < -0.02: continue
                eb = ease_out(u / 0.14)
                sc = base_scale * lerp(2.3, 1.0, eb)
                al = clamp(u / 0.06) * out
                rot = lerp(-9, -3.2, eb)
                dx = hit(t_row[min(j, 1)], 15)
                dy = hit(t_row[min(j, 1)] + 0.015, 12)
                blit(frame, glw, 540 + dx, ys[j] + dy, al * 0.8, "add", scale=sc, rot=rot)
                blit(frame, shd, 540 + dx, ys[j] + dy, al, "over", scale=sc, rot=rot)
                blit(frame, spr, 540 + dx, ys[j] + dy, al, "over", scale=sc, rot=rot)
                if 0 <= u < 0.40:
                    self._ring(frame, 540, ys[j], u / 0.40, (255, 120, 70), out * 0.9)
                    add_color(frame, (0, 0, W, H), (255, 235, 220), 0.30 * math.exp(-u / 0.07) * out)
        elif style == "defiant":
            self._bloom(frame, 540, cy0, tr, dur, out, 0.5, (255, 170, 80))
            # word-by-word punch-in spread over the first ~60% of the line (proportional to characters)
            flat = [len(w_[0]) for rw in words for w_ in rw]
            nch = max(1, sum(flat))
            span = min(dur * 0.62, 1.7)
            seen = 0
            for r, rw in enumerate(words):
                widths = [text_w(w_[0], f) for w_ in rw]
                gap = int(f.size * 0.30)
                tot = sum(widths) + gap * (len(rw) - 1)
                x = 540 - tot / 2
                for k, (wtxt, spr, glw, shd) in enumerate(rw):
                    ws = widths[k]
                    wt0 = span * seen / nch
                    seen += len(wtxt)
                    u = tr - wt0
                    cxw = x + ws / 2
                    x += ws + gap
                    if u < -0.01: continue
                    eb = ease_out_back(u / 0.18, 1.5)
                    sc = base_scale * lerp(1.45, 1.0, eb)
                    al = clamp(u / 0.08) * out
                    dy = hit(wt0, 4)
                    blit(frame, glw, cxw, ys[r] + dy, al * (0.5 + 0.4 * kick), "add", scale=sc)
                    blit(frame, shd, cxw, ys[r] + dy, al, "over", scale=sc)
                    blit(frame, spr, cxw, ys[r] + dy, al, "over", scale=sc)
            u = tr - span
            if u > -0.05:
                self._tricolor_bar(frame, 540, ys[-1] + row_h * 0.5, 640 * ease_out((u + 0.05) / 0.5), 12, out)
                if 0 <= u < 0.45:
                    add_color(frame, (0, 0, W, H), (255, 225, 190), 0.22 * math.exp(-u / 0.09) * out)
        elif style == "people":
            self._bloom(frame, 540, cy0 + 60, tr, dur, out, 1.0, (255, 185, 100), big=True)
            # big chakra behind
            ca = (0.07 + 0.11 * ease_out(tr / 1.2)) * out
            blit(frame, self.chakra, 540, cy0, ca, "add", scale=1.35 + 0.03 * tr, rot=-(t * 6.0) % 360)
            for j, (txt, spr, glw, shd) in enumerate(sprites):
                u = tr - 0.18 * j
                if u < -0.02: continue
                e = ease_out(u / 0.7)
                sc = base_scale * lerp(0.90, 1.0, e)
                al = clamp(u / 0.35) * out
                dy = (1 - e) * 60
                spr_v = self._wipe(spr, e, vertical=True)
                blit(frame, glw, 540, ys[j] + dy, al * (0.7 + 0.5 * kick), "add", scale=sc)
                blit(frame, shd, 540, ys[j] + dy, al, "over", scale=sc)
                blit(frame, spr_v, 540, ys[j] + dy, al, "over", scale=sc)
            u = tr - 0.4
            if 0 <= u < 0.9:
                self._ring(frame, 540, cy0, u / 0.9, (255, 210, 140), out * 0.8)

    # ---------------- special-effect helpers ----------------
    def _dark_pad(self):
        if "dark_pad" not in self.special_cache:
            self.special_cache["dark_pad"] = radial_sprite(1500, 1100, (3, 4, 14), 0.9)
        return self.special_cache["dark_pad"]

    def _wipe(self, spr, e, vertical=False):
        """Soft-edged wipe reveal of an RGBA sprite, e in 0..1."""
        if e >= 0.999:
            return spr
        w, h = spr.size
        a = np.asarray(spr.split()[3]).astype(np.float32)
        edge = 0.18
        if vertical:
            pos = np.linspace(1, 0, h)[:, None]
            m = np.clip((e * (1 + edge) - pos) / edge, 0, 1)
        else:
            pos = np.linspace(0, 1, w)[None, :]
            m = np.clip((e * (1 + edge) - pos) / edge, 0, 1)
        out = spr.copy()
        out.putalpha(Image.fromarray((a * m).astype(np.uint8)))
        return out

    def _ring(self, frame, cx, cy, u, color, alpha):
        if u <= 0 or u >= 1 or alpha <= 0.01:
            return
        r = 80 + 520 * ease_out(u)
        size = int(r * 2 + 40)
        spr = self._ring_sprite(size, color)
        blit(frame, spr, cx, cy, 0.55 * (1 - u) ** 1.5 * alpha, "add")

    @functools.lru_cache(maxsize=256)
    def _ring_sprite(self, size, color):
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([20, 20, size - 20, size - 20], outline=tuple(color) + (255,), width=6)
        return im.filter(ImageFilter.GaussianBlur(2.0))

    def _bloom(self, frame, cx, cy, tr, dur, out, strength, color, big=False):
        e = ease_out(tr / 0.8)
        spr = self._bloom_sprite(color, big)
        blit(frame, spr, cx, cy, strength * e * out * 0.55, "add", scale=1.0 + 0.05 * tr)

    @functools.lru_cache(maxsize=16)
    def _bloom_sprite(self, color, big):
        return radial_sprite(1500 if big else 1200, 900 if big else 640, color, 1.5)

    def _stamp_plate(self, frame, cx, cy, alpha, n, row_h):
        if alpha <= 0.01:
            return
        key = ("plate", n, row_h)
        if key not in self.special_cache:
            w, h = 980, int(row_h * n + 120)
            im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([40, 40, 40 + w, 40 + h], 22, fill=(4, 5, 16, 150))
            d.rounded_rectangle([40, 40, 40 + w, 40 + h], 22, outline=SAFFRON + (255,), width=9)
            d.rounded_rectangle([62, 62, 18 + w, 18 + h], 14, outline=(255, 255, 255, 190), width=3)
            self.special_cache[key] = im.rotate(-3.2, resample=Image.BICUBIC, expand=True)
        blit(frame, self.special_cache[key], cx, cy, alpha * 0.95, "over")


def load_scene(timing_path=None):
    return Scene(timing_path or (T + "work/lyric_timing.json"))


if __name__ == "__main__":
    # usage: render.py preview OUTDIR t1 t2 ...
    if sys.argv[1] == "preview":
        sc = load_scene(os.environ.get("CJM_TIMING"))
        out = sys.argv[2]
        os.makedirs(out, exist_ok=True)
        for tt in sys.argv[3:]:
            tt = float(tt)
            Image.fromarray(sc.render_frame(tt)).save(f"{out}/f_{tt:08.3f}.png")
            print("wrote", tt)
