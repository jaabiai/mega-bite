"""Typography engine for the Hinglish landscape lyric video.

Only Roman (Latin) text is ever drawn: `assert_roman()` rejects anything else (so no Devanagari can reach a frame).

Regular lyric families
  rap       Barlow Condensed ExtraBold, upper-case, word-by-word punch-ins with motion trails, accent colours
  melodic   Playfair Display Italic, white->gold gradient, rising words + light sweep
  emotional Cormorant Garamond Italic, slow blur-in per word, gentle upward drift
Hooks (each unique: typeface, palette, motion, effects)
  wake      "Deshwasiyo Jaago!"            Cinzel Black    - rising-sun bloom, letter-spaced reveal, slam + shock-ring + dust
  march     "Chalo Jantar-Mantar!"         Anton           - words slam in from both sides, speed lines, tricolor bar
  stamp     "Vote Chori! Gaddi Chor!"      Black Ops One   - protest stamp banners, ink splatter, glitch, siren pulse
  defiant   "Ye Mulk Tera Baap Ka Nahin!"  Alfa Slab One   - word-by-word hammer, cracks, letterbox pinch
  people    "Ye Janta Ka Hindustan Hai!"   Playfair Black  - tricolor gradient, rotating chakra, sun rays, petals
"""
import math, os, re
import numpy as np
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from hl_common import W, H, FPS, BEAT, PHASE, clamp, smooth, ease_out, ease_out_quint, ease_out_back, ease_in_out, lerp, beat_pulse

HERE = os.path.dirname(os.path.abspath(__file__))
FONTDIR = os.path.abspath(os.path.join(HERE, "..", "assets", "fonts"))
ROMAN_OK = re.compile(r"^[A-Za-z0-9 …,!?'\-.]+$")
RECORD = set()            # every string that was ever drawn (used by the verification report)

GOLD = (255, 200, 80)
SAFFRON = (255, 145, 40)
GREEN = (34, 160, 70)
RED = (226, 48, 44)
WHITE = (255, 255, 255)
CREAM = (255, 244, 226)


def assert_roman(s):
    if not ROMAN_OK.match(s):
        raise ValueError(f"non-Roman text refused: {s!r}")
    RECORD.add(s)
    return s


FONTS = {
    "rap": ("BarlowCondensed-ExtraBold.ttf", None), "rap_black": ("BarlowCondensed-Black.ttf", None),
    "melodic": ("PlayfairDisplay-Italic-VF.ttf", 700), "emotional": ("CormorantGaramond-Italic-VF.ttf", 600),
    "wake": ("Cinzel-VF.ttf", 900), "march": ("Anton-Regular.ttf", None), "stamp": ("BlackOpsOne-Regular.ttf", None),
    "defiant": ("AlfaSlabOne-Regular.ttf", None), "people": ("PlayfairDisplay-VF.ttf", 900), "people_small": ("PlayfairDisplay-Italic-VF.ttf", 700),
    "title": ("Cinzel-VF.ttf", 700), "small": ("Marcellus-Regular.ttf", None),
}


@lru_cache(maxsize=128)
def font(kind, size):
    fn, wght = FONTS[kind]
    f = ImageFont.truetype(os.path.join(FONTDIR, fn), int(size), layout_engine=ImageFont.Layout.BASIC)
    if wght is not None:
        f.set_variation_by_axes([wght])
    return f


# ----------------------------------------------------------------------------------------------------------------------
# sprites
# ----------------------------------------------------------------------------------------------------------------------
def _gradient_img(w, h, stops):
    ys = np.linspace(0, 1, h)
    pos = [p for p, _ in stops]
    g = np.stack([np.interp(ys, pos, [c[i] for _, c in stops]) for i in range(3)], axis=-1).astype(np.uint8)
    return Image.fromarray(np.repeat(g[:, None, :], w, 1), "RGB")


def make_sprite(text, f, fill=WHITE, gradient=None, stroke=0, stroke_col=(8, 10, 24), pad=40, glow=None, shadow=True, cap_gradient=False):
    """Returns dict(main=RGBA, glow=RGBA|None). Text is drawn with an outline underneath.
    cap_gradient: map the gradient stops over the cap-height band (so a tricolor ramp spans the visible letters)."""
    assert_roman(text)
    asc, desc = f.getmetrics()
    tw = int(f.getlength(text)) + 4
    w, h = tw + 2 * pad, asc + desc + 2 * pad
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((pad, pad), text, font=f, fill=255)
    if gradient and cap_gradient:
        bb = f.getbbox("HIL")
        top, bot = pad + bb[1], pad + bb[3]
        ys = np.arange(h)
        u = np.clip((ys - top) / max(1.0, bot - top), 0, 1)
        pos = [p_ for p_, _ in gradient]
        g = np.stack([np.interp(u, pos, [c[i] for _, c in gradient]) for i in range(3)], axis=-1).astype(np.uint8)
        fillimg = Image.fromarray(np.repeat(g[:, None, :], w, 1), "RGB")
    else:
        fillimg = _gradient_img(w, h, gradient) if gradient else Image.new("RGB", (w, h), fill)
    main = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = mask.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.7))
        shim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        shim.putalpha(sh)
        shim = shim.transform((w, h), Image.AFFINE, (1, 0, 0, 0, 1, -7))
        main.alpha_composite(shim)
    if stroke > 0:
        om = Image.new("L", (w, h), 0)
        ImageDraw.Draw(om).text((pad, pad), text, font=f, fill=255, stroke_width=stroke)
        ol = Image.new("RGBA", (w, h), stroke_col + (255,))
        ol.putalpha(om)
        main.alpha_composite(ol)
    fl = fillimg.convert("RGBA")
    fl.putalpha(mask)
    main.alpha_composite(fl)
    out = dict(main=main, w=tw, h=asc + desc, pad=pad, asc=asc, mask=mask)
    if glow:
        gm = mask.filter(ImageFilter.GaussianBlur(glow[1]))
        g = Image.new("RGBA", (w, h), tuple(glow[0]) + (255,))
        g.putalpha(gm.point(lambda v: min(255, int(v * glow[2]))))
        out["glow"] = g
    return out


def blur_of(spr, r):
    return spr.filter(ImageFilter.GaussianBlur(r))


# ----------------------------------------------------------------------------------------------------------------------
# frame blending (uint8 frame H,W,3)
# ----------------------------------------------------------------------------------------------------------------------
def blit(frame, spr, cx, cy, op=1.0, mode="over", scale=1.0, rot=0.0, tint=None):
    if op <= 0.004:
        return
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
    sw, sh = spr.size
    x0, y0 = int(round(cx - sw / 2)), int(round(cy - sh / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + sw), min(H, y0 + sh)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    s = np.asarray(spr)[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0].astype(np.float32)
    a = (s[..., 3:4] / 255.0) * op
    sub = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    rgb = s[..., :3]
    if tint is not None:
        rgb = rgb * np.asarray(tint, np.float32)
    if mode == "over":
        out = sub * (1 - a) + rgb * a
    elif mode == "add":
        out = sub + rgb * a
    else:
        raise ValueError(mode)
    frame[fy0:fy1, fx0:fx1] = np.clip(out, 0, 255).astype(np.uint8)


def trail(frame, spr, cx, cy, dx, dy, op=1.0, n=6, scale=1.0, mode="over"):
    """Motion-blur stand-in: n ghost copies behind (cx,cy) moving from (cx-dx, cy-dy)."""
    for k in range(n, 0, -1):
        f = k / n
        blit(frame, spr, cx - dx * f, cy - dy * f, op * 0.22 * (1 - f * 0.7), "over", scale)
    blit(frame, spr, cx, cy, op, mode, scale)


_RAD = {}


def radial(w, h, power=1.6):
    key = (w, h, power)
    if key not in _RAD:
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
        a = np.clip(1 - d, 0, 1) ** power
        im = np.zeros((h, w, 4), np.uint8)
        im[..., :3] = 255
        im[..., 3] = (a * 255).astype(np.uint8)
        _RAD[key] = Image.fromarray(im)
    return _RAD[key]


def dark_pad(frame, cx, cy, w, h, amt, power=1.1):
    """Soft dark ellipse behind a hook so bright blooms never wash the letters out."""
    blit(frame, radial(w, h, power), cx, cy, amt, "over", tint=np.array([0.0, 0.0, 0.0], np.float32))


def glow_blob(frame, cx, cy, w, h, color, amt, power=1.6):
    blit(frame, radial(w, h, power), cx, cy, amt, "add", tint=np.array(color, np.float32) / 255.0)


_RAYS = {}


def rays_sprite(size=1500, n=22, seed=3):
    key = (size, n, seed)
    if key not in _RAYS:
        rs = np.random.RandomState(seed)
        y, x = np.mgrid[0:size, 0:size].astype(np.float32)
        cx = size / 2
        th = np.arctan2(y - cx, x - cx)
        r = np.sqrt((x - cx) ** 2 + (y - cx) ** 2) / cx
        ph = rs.uniform(0, 6.28, 4)
        v = 0.5 + 0.5 * np.sin(n * th + ph[0]) * 0.6 + 0.5 * np.sin(n * 2.3 * th + ph[1]) * 0.4
        v = np.clip(v, 0, 1) ** 2.2
        a = v * np.clip(1 - r, 0, 1) ** 1.3
        im = np.zeros((size, size, 4), np.uint8)
        im[..., :3] = 255
        im[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        _RAYS[key] = Image.fromarray(im)
    return _RAYS[key]


def hsh(n):
    """Deterministic pseudo-random in [0,1) from an integer."""
    x = math.sin(n * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


# ----------------------------------------------------------------------------------------------------------------------
# helpers for words
# ----------------------------------------------------------------------------------------------------------------------
def syllables(w):
    return max(1, len(re.findall(r"[aeiouAEIOU]+", w)))


ACCENT = [(RED, {"chori", "chor", "darr", "nafrat", "hinsa", "zanjeer", "gaddi"}),
          (GOLD, {"vote", "janta", "haq", "sach", "awaaz", "insaaf", "samvidhaan", "adhikaar", "loktantra", "vishwaas", "hindustan", "zameer"}),
          (SAFFRON, {"sawaal", "sawaalon", "jawaab", "hisaab", "ummeed", "subah", "dil", "dam", "deep", "mazbooti"})]


def accent_word(words):
    for col, st in ACCENT:
        for i, w in enumerate(words):
            if re.sub(r"[^a-z]", "", w.lower()) in st:
                return i, col
    return None, None


def split_rows(words, f, maxw):
    """Balanced split of words into 1-2 rows fitting maxw."""
    space = f.getlength(" ")
    wl = [f.getlength(w) for w in words]
    total = sum(wl) + space * (len(words) - 1)
    if total <= maxw or len(words) < 2:
        return [list(range(len(words)))], total
    best = None
    for i in range(1, len(words)):
        a = sum(wl[:i]) + space * (i - 1)
        b = sum(wl[i:]) + space * (len(words) - i - 1)
        if max(a, b) <= maxw:
            sc = abs(a - b)
            if best is None or sc < best[0]:
                best = (sc, i, max(a, b))
    if best:
        return [list(range(best[1])), list(range(best[1], len(words)))], best[2]
    return None, total


class WordRow:
    """Pre-laid-out line made of word sprites (shared by the three regular families)."""

    def __init__(self, text, kind, size0, maxw=1560, upper=False, fill=WHITE, gradient=None, stroke=4, glow=True, accent=True, min_size=60, step=4):
        words = text.upper().split() if upper else text.split()
        size = size0
        while True:
            f = font(kind, size)
            rows, wid = split_rows(words, f, maxw)
            if rows is not None or size <= min_size:
                break
            size -= step
        if rows is None:
            rows = [list(range(len(words)))]
        self.size, self.f = size, f
        self.words = words
        ai, acol = accent_word(words) if accent else (None, None)
        self.sprites = []
        for i, w in enumerate(words):
            col = acol if i == ai else fill
            grad = None if (i == ai and acol) else gradient
            sp = make_sprite(w, f, col, grad, stroke, glow=((acol or SAFFRON), 14, 1.1) if (glow and i == ai) else None)
            self.sprites.append(sp)
        self.rows = rows
        space = f.getlength(" ")
        asc, desc = f.getmetrics()
        self.line_h = int((asc + desc) * 0.88)
        self.pos = []                                       # (row, x offset from row centre, row width)
        for r, idxs in enumerate(rows):
            wl = [f.getlength(words[i]) for i in idxs]
            rw = sum(wl) + space * (len(idxs) - 1)
            x = -rw / 2
            for k, i in enumerate(idxs):
                self.pos.append((i, r, x + wl[k] / 2, rw))
                x += wl[k] + space
        self.pos.sort()
        self.nrows = len(rows)
        # syllable-proportional timing weights
        self.weights = [syllables(w) for w in words]


# ----------------------------------------------------------------------------------------------------------------------
# the engine
# ----------------------------------------------------------------------------------------------------------------------
SECTION_FAMILY = [("INTRO", "emotional"), ("BEAT", "rap"), ("VERSE", "rap"), ("PRE-CHORUS", "melodic"), ("CHORUS", "melodic"), ("HOOK", "melodic"),
                  ("BRIDGE", "emotional"), ("FINAL CHORUS", "melodic"), ("FINAL RAP", "rap"), ("OUTRO", "emotional"), ("FINAL VOICE", "emotional")]


def family_of(section):
    s = section.upper()
    for key, fam in sorted(SECTION_FAMILY, key=lambda kv: -len(kv[0])):
        if s.startswith(key):
            return fam
    return "rap"


class TextEngine:
    LEAD = 0.05
    HOLD = 0.28

    def __init__(self, lines, title=("Chalo Jantar-Mantar", "Awaaz Janta Ki")):
        self.lines = lines
        for l in self.lines:
            assert_roman(l["roman"])
        self.cache = {}
        self.title = title
        self._scrim = None
        self._title_sprites = None

    # ---------------- timing windows ----------------
    def window(self, i):
        l = self.lines[i]
        s, e = l["start"], l["end"]
        nxt = self.lines[i + 1]["start"] if i + 1 < len(self.lines) else 1e9
        hook = l["hook"] != "regular"
        show_from = s - self.LEAD
        until = min(e + self.HOLD * (1.4 if hook else 1.0), nxt + (0.12 if hook else 0.0))
        return show_from, max(until, s + 0.7)

    def active(self, t):
        out = []
        for i, l in enumerate(self.lines):
            a, b = self.window(i)
            if a - 0.05 <= t <= b + 0.45:
                out.append((i, a, b))
        return out

    # ---------------- effects consumed by the background stage ----------------
    def effects(self, t):
        fx = dict(shake=(0.0, 0.0), flash=None, chroma=0, bars=0.0, vig_red=0.0, zoom=0.0, bloom=0.0)
        for i, a, b in self.active(t):
            l = self.lines[i]
            if l["hook"] == "regular":
                continue
            h = getattr(self, "fx_" + l["hook"])(l, t - (l["start"]), a, b, t)
            for k, v in h.items():
                if k == "shake":
                    fx["shake"] = (fx["shake"][0] + v[0], fx["shake"][1] + v[1])
                elif k == "flash":
                    if v and (fx["flash"] is None or v[3] > fx["flash"][3]):
                        fx["flash"] = v
                else:
                    fx[k] = max(fx[k], v) if isinstance(v, (int, float)) else v
        return fx

    # ---------------- drawing ----------------
    def scrim(self):
        if self._scrim is None:
            y = np.linspace(0, 1, H)[:, None]
            a = np.clip((y - 0.55) / 0.45, 0, 1) ** 1.5 * 0.62
            self._scrim = (1 - a)[..., None].astype(np.float32)
        return self._scrim

    def draw(self, frame, t, fx_shake=(0, 0)):
        """Draw title + all active lyric lines onto frame (uint8, in place)."""
        self._draw_title(frame, t)
        act = self.active(t)
        any_regular = any(self.lines[i]["hook"] == "regular" for i, _, _ in act)
        if any_regular:
            frame[:] = np.clip(frame.astype(np.float32) * self.scrim(), 0, 255).astype(np.uint8)
        for i, a, b in act:
            l = self.lines[i]
            if l["hook"] == "regular":
                getattr(self, "draw_" + family_of(l["section"]))(frame, l, t, a, b)
            else:
                getattr(self, "draw_" + l["hook"])(frame, l, t - l["start"], a, b, t, fx_shake)

    # ---------------- title ----------------
    def _draw_title(self, frame, t):
        a = smooth((t - 0.5) / 0.9) * (1 - smooth((t - 3.0) / 0.55))
        if a <= 0.01:
            return
        if self._title_sprites is None:
            s1 = make_sprite(self.title[0].upper(), font("title", 120), gradient=[(0, (255, 255, 255)), (0.6, (255, 232, 190)), (1, (255, 190, 110))], stroke=3,
                             glow=(SAFFRON, 22, 0.8))
            s2 = make_sprite(self.title[1], font("small", 56), fill=CREAM, stroke=2)
            self._title_sprites = (s1, s2)
        s1, s2 = self._title_sprites
        dy = (1 - ease_out((t - 0.5) / 1.4)) * 18
        blit(frame, s1["glow"], W / 2, 500 + dy, a * 0.6, "add")
        blit(frame, s1["main"], W / 2, 500 + dy, a)
        blit(frame, s2["main"], W / 2, 622 + dy, a * 0.95)
        self._tri_bar(frame, W / 2, 575 + dy, 360 * ease_out((t - 0.8) / 0.9), 6, a)

    @staticmethod
    def _tri_bar(frame, cx, cy, width, height, alpha):
        if width < 3 or alpha < 0.01:
            return
        w, h = int(width), int(height)
        x0 = int(cx - w / 2)
        seg = w / 3.0
        for k, col in enumerate(((255, 145, 40), (250, 250, 245), (34, 160, 70))):
            xa, xb = max(0, int(x0 + k * seg)), min(W, int(x0 + (k + 1) * seg))
            ya, yb = int(cy - h / 2), int(cy + h / 2)
            if xb > xa:
                sub = frame[ya:yb, xa:xb].astype(np.float32)
                frame[ya:yb, xa:xb] = (sub * (1 - alpha) + np.array(col, np.float32) * alpha).astype(np.uint8)

    # ================= regular families =================
    def _row(self, l, kind):
        key = (l["id"], kind)
        if key in self.cache:
            return self.cache[key]
        txt = l["roman"]
        if kind == "rap":
            wr = WordRow(txt, "rap", 112, upper=True, stroke=4)
        elif kind == "melodic":
            wr = WordRow(txt, "melodic", 98, stroke=3, gradient=[(0, (255, 255, 255)), (0.55, (255, 236, 190)), (1, (255, 196, 96))])
        else:
            wr = WordRow(txt, "emotional", 108, fill=CREAM, stroke=3, maxw=1500, accent=True)
        wr.blur = [blur_of(sp["main"], 9) for sp in wr.sprites] if kind != "rap" else None
        self.cache[key] = wr
        return wr

    def _word_times(self, wr, l, kind):
        s, e = l["start"], l["end"]
        n = len(wr.words)
        tot = float(sum(wr.weights))
        if kind == "emotional":
            step = min(0.30, 0.72 * (e - s) / max(1, n))
            return [s + 0.08 + k * step for k in range(n)]
        cum = np.concatenate([[0], np.cumsum(wr.weights)])
        span = (e - s) * (0.90 if kind == "rap" else 0.75)
        return [s - 0.02 + span * cum[k] / tot for k in range(n)]

    def _place(self, wr, k):
        """Return (cx, cy) of word k for the lower-third layout."""
        i, r, x, rw = wr.pos[k]
        base = 880 if wr.nrows == 1 else 830
        cy = base + r * wr.line_h * 1.02 if wr.nrows > 1 else base
        return W / 2 + x, cy

    def draw_rap(self, frame, l, t, a, b):
        wr = self._row(l, "rap")
        times = self._word_times(wr, l, "rap")
        out = 1 - smooth((t - (b - 0.14)) / 0.14)
        pul = 1 + 0.018 * beat_pulse(t, 8.0)
        for k, sp in enumerate(wr.sprites):
            u = (t - times[k]) / 0.17
            if u < 0:
                continue
            e = ease_out_back(u, 1.9)
            sc = lerp(1.55, 1.0, e) * pul
            dx = (1 - ease_out(u)) * 90
            al = clamp(u * 2.2) * out
            cx, cy = self._place(wr, k)
            if "glow" in sp:
                blit(frame, sp["glow"], cx, cy, al * 0.7 * (0.8 + 0.4 * beat_pulse(t, 6.0)), "add", sc)
            if u < 1.0:
                trail(frame, sp["main"], cx + dx, cy, dx * 1.2, 0, al, 5, sc)
            else:
                blit(frame, sp["main"], cx, cy, al, "over", sc)
        if wr.nrows >= 1:
            self._tri_bar(frame, W / 2, 880 + (wr.line_h * 0.62 if wr.nrows == 1 else wr.line_h * 1.62), 160 * ease_out((t - l["start"]) / 0.5), 5, 0.9 * out)

    def draw_melodic(self, frame, l, t, a, b):
        wr = self._row(l, "melodic")
        times = self._word_times(wr, l, "melodic")
        out = 1 - smooth((t - (b - 0.18)) / 0.18)
        sweep = ((t - l["start"]) / 0.9)
        for k, sp in enumerate(wr.sprites):
            u = (t - times[k]) / 0.34
            if u < 0:
                continue
            e = ease_out(u)
            cx, cy = self._place(wr, k)
            cy += (1 - e) * 30
            al = clamp(u * 1.6) * out
            blit(frame, wr.blur[k], cx, cy, al * (1 - e) * 0.8, "over")
            blit(frame, sp["main"], cx, cy, al * e + al * 0.0, "over", 1.0 + 0.02 * beat_pulse(t, 7.0))
            # warm glow + light sweep across the word
            if 0.0 < sweep < 1.3:
                self._sweep(frame, sp["main"], cx, cy, sweep, al)
        # soft golden underline
        self._tri_bar(frame, W / 2, 880 + (wr.line_h * 0.62 if wr.nrows == 1 else wr.line_h * 1.62), 140 * ease_out((t - l["start"]) / 0.5), 4, 0.8 * out)

    def draw_emotional(self, frame, l, t, a, b):
        wr = self._row(l, "emotional")
        times = self._word_times(wr, l, "emotional")
        out = 1 - smooth((t - (b - 0.35)) / 0.45)
        drift = -16 * clamp((t - l["start"]) / max(1.0, l["end"] - l["start"]))
        for k, sp in enumerate(wr.sprites):
            u = (t - times[k]) / 0.55
            if u < 0:
                continue
            e = ease_out(u)
            cx, cy = self._place(wr, k)
            cy += (1 - e) * 22 + drift
            al = clamp(u * 1.3) * out
            blit(frame, wr.blur[k], cx, cy, al * (1 - e), "over", 1.0 + 0.05 * (1 - e))
            blit(frame, sp["main"], cx, cy, al * (0.25 + 0.75 * e), "over")
        self._tri_bar(frame, W / 2, 880 + (wr.line_h * 0.55 if wr.nrows == 1 else wr.line_h * 1.5), 90 * ease_out((t - l["start"]) / 0.8), 3, 0.65 * out)

    @staticmethod
    def _sweep(frame, spr, cx, cy, pos, al):
        """Diagonal light sweep clipped to the sprite's alpha."""
        w, h = spr.size
        a = np.asarray(spr.split()[3], np.float32) / 255.0
        xs = (np.arange(w)[None, :] + np.arange(h)[:, None] * 0.35) / (w + h * 0.35)
        band = np.exp(-((xs - (pos - 0.15)) / 0.07) ** 2)
        m = (a * band * 0.9)
        im = np.zeros((h, w, 4), np.uint8)
        im[..., :3] = 255
        im[..., 3] = (np.clip(m, 0, 1) * 255).astype(np.uint8)
        blit(frame, Image.fromarray(im), cx, cy, al, "add")

    # ================= hooks =================
    def _plan(self, key, build):
        if key not in self.cache:
            self.cache[key] = build()
        return self.cache[key]

    # ---------- 1. wake : Deshwasiyo Jaago! ----------
    WAKE_INT = {8: 0.55, 27: 0.85, 31: 0.9, 75: 1.0, 76: 1.1, 90: 0.55, 92: 0.6}

    def _wake_plan(self, l):
        def build():
            toks = l["roman"].upper().split()
            w1 = toks[0]                                  # keeps its "…" when the lyric has one ("DESHWASIYO…")
            w2 = " ".join(toks[1:])
            tail = ""
            f1 = font("wake", 190)
            while f1.getlength(w1) > 1500:
                f1 = font("wake", f1.size - 6)
            f2 = font("wake", int(f1.size * 1.35))
            while f2.getlength(w2 + tail) > 1250:
                f2 = font("wake", f2.size - 6)
            grad1 = [(0, (255, 255, 255)), (0.5, (255, 238, 196)), (1, (255, 196, 100))]
            grad2 = [(0, (255, 244, 214)), (0.45, (255, 205, 90)), (1, (255, 140, 40))]
            letters = []
            x = 0.0
            tw = f1.getlength(w1)
            for i, ch in enumerate(w1):
                adv = f1.getlength(w1[:i + 1]) - f1.getlength(w1[:i])
                sp = make_sprite(ch, f1, gradient=grad1, stroke=4, glow=(GOLD, 16, 0.9), shadow=False) if ch != " " else None
                letters.append((sp, f1.getlength(w1[:i]) - tw / 2 + adv / 2))
            s2 = make_sprite(w2 + tail, f2, gradient=grad2, stroke=5, glow=(SAFFRON, 28, 1.0))
            s2["blur"] = blur_of(s2["main"], 12)
            return dict(letters=letters, s2=s2, f1=f1, f2=f2, w1=w1)
        return self._plan(("wake", l["id"]), build)

    def _wake_tl(self, l, tr, a, b):
        I = self.WAKE_INT.get(l["id"], 0.8)
        dur = b - l["start"]
        t2 = min(0.58, 0.32 * dur)           # when "JAAGO!" lands
        return I, dur, t2

    def fx_wake(self, l, tr, a, b, t):
        I, dur, t2 = self._wake_tl(l, tr, a, b)
        u = tr - t2
        fx = {}
        if u >= 0:
            fx["shake"] = (math.sin(u * 95) * 9 * I * math.exp(-u / 0.12), math.cos(u * 83) * 6 * I * math.exp(-u / 0.12))
            fx["flash"] = (255, 225, 160, 0.30 * I * math.exp(-u / 0.10))
        fx["bloom"] = 0.5 * I * ease_out(tr / 1.0)
        return fx

    def draw_wake(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P = self._wake_plan(l)
        I, dur, t2 = self._wake_tl(l, tr, a, b)
        out = 1 - smooth((tr - (dur - 0.3)) / 0.4)
        cy1, cy2 = 430, 640
        zoom = 1.0 + 0.04 * clamp(tr / max(dur, 1)) + (0.012 * beat_pulse(t, 6.0) * I)
        # rising sun bloom + rotating rays
        g = ease_out(tr / 0.9) * out
        rs = rays_sprite(1500, 22, 4)
        blit(frame, rs.rotate(-(t * 7) % 360, resample=Image.BILINEAR), W / 2, 520, 0.55 * g * I, "add", 1.45, tint=np.array([1.0, 0.82, 0.45]))
        glow_blob(frame, W / 2, 520, 1500, 800, (255, 190, 90), 0.45 * g * I, 1.5)
        dark_pad(frame, W / 2, 540, 1750, 760, 0.30 * g)
        # letters of the first word: letter-spaced reveal
        n = len(P["letters"])
        for k, (sp, xo) in enumerate(P["letters"]):
            if sp is None:
                continue
            u = (tr - (0.05 + 0.055 * k)) / 0.55
            if u <= 0:
                continue
            e = ease_out_quint(u)
            spread = 1.0 + 0.32 * (1 - e)
            al = clamp(u * 1.8) * out
            cx = W / 2 + xo * spread * zoom
            cy = cy1 - (1 - e) * 26
            blit(frame, sp["glow"], cx, cy, al * 0.55, "add", zoom * (1 + 0.15 * (1 - e)))
            blit(frame, sp["main"], cx, cy, al * (0.35 + 0.65 * e), "over", zoom * (1 + 0.20 * (1 - e)))
        # second word: slam
        u = tr - t2
        if u >= 0:
            s2 = P["s2"]
            e = ease_out_quint(u / 0.26)
            sc = lerp(1.9, 1.0, e) * zoom
            al = out
            blit(frame, s2["glow"], W / 2, cy2, al * (0.7 + 0.3 * beat_pulse(t, 6)), "add", sc)
            if u < 0.26:
                blit(frame, s2["blur"], W / 2, cy2, al * (1 - e) * 0.9, "over", sc)
            blit(frame, s2["main"], W / 2, cy2, al, "over", sc)
            # shock ring
            if u < 0.7:
                r = 120 + 900 * ease_out(u / 0.7)
                self._ring(frame, W / 2, cy2, r, 8, (255, 214, 120), 0.7 * (1 - u / 0.7) * I * out)
            # light streak
            if u < 0.5:
                blit(frame, radial(1900, 60, 1.2), W / 2, cy2, 0.8 * (1 - u / 0.5) * I, "add", 1.0, tint=np.array([1.0, 0.86, 0.55]))
            # periodic light sweep
            sw = ((tr - t2 - 0.35) * 0.55) % 1.9
            if 0 < sw < 1.35 and u > 0.3:
                self._sweep(frame, s2["main"], W / 2, cy2, sw, out * 0.9 * I)
        # gold dust rising
        self._dust(frame, t, tr, I * out, cy2)

    def _dust(self, frame, t, tr, amt, cy):
        if amt <= 0.02:
            return
        sp = radial(24, 24, 1.8)
        n = int(26 * amt)
        for k in range(n):
            r1, r2, r3 = hsh(k * 3 + 1), hsh(k * 3 + 2), hsh(k * 3 + 3)
            life = (tr * (0.18 + 0.2 * r3) + r1) % 1.0
            x = W / 2 + (r2 - 0.5) * 1300 + math.sin(t * 0.9 + k) * 30
            y = cy + 120 - life * 520
            blit(frame, sp, x, y, 0.8 * math.sin(math.pi * life) * amt, "add", 0.5 + r3 * 0.8, tint=np.array([1.0, 0.8, 0.4]))

    @staticmethod
    def _ring(frame, cx, cy, r, width, col, op):
        if op <= 0.01:
            return
        size = int(r * 2 + 2 * width + 8)
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([4, 4, size - 4, size - 4], outline=col + (255,), width=int(width))
        im = im.filter(ImageFilter.GaussianBlur(2.2))
        blit(frame, im, cx, cy, op, "add")

    # ---------- 2. march : Chalo Jantar-Mantar! ----------
    def _march_plan(self, l):
        def build():
            rom = l["roman"]
            toks = rom.split(" ")
            a_txt = toks[0].upper()                      # punctuation stays attached exactly as written: "CHALO…", "JANTAR-MANTAR,"
            b_txt = " ".join(toks[1:]).upper()
            f2 = font("march", 290)
            f1 = font("march", int(f2.size * 0.78))
            while f2.getlength(b_txt) > 1560 or f1.getlength(a_txt) > 1560:
                f2 = font("march", f2.size - 8)
                f1 = font("march", int(f2.size * 0.78))
            s1 = make_sprite(a_txt, f1, WHITE, stroke=5, glow=(SAFFRON, 18, 0.8))
            s2 = make_sprite(b_txt, f2, WHITE, stroke=6, glow=(GOLD, 20, 0.7))
            slow = rom.endswith("…")                     # chant lines with ellipses are slower, heavier
            return dict(s1=s1, s2=s2, a=a_txt, b=b_txt, slow=slow, f1=f1, f2=f2)
        return self._plan(("march", l["id"]), build)

    def _march_tl(self, l, tr, a, b):
        P = self._march_plan(l)
        dur = b - l["start"]
        d2 = 0.50 if P["slow"] else 0.27
        flip = (l["id"] % 2 == 0)
        return P, dur, d2, flip

    def fx_march(self, l, tr, a, b, t):
        P, dur, d2, flip = self._march_tl(l, tr, a, b)
        fx = {}
        sh = 0.0
        sx = sy = 0.0
        for t0 in (0.16, d2 + 0.16):
            u = tr - t0
            if u >= 0:
                amp = 16 * math.exp(-u / 0.10) * (0.7 if P["slow"] else 1.0)
                sx += math.sin(u * 110) * amp
                sy += math.cos(u * 97) * amp * 0.6
        fx["shake"] = (sx, sy)
        for t0 in (0.16, d2 + 0.16):
            u = tr - t0
            if 0 <= u < 0.16:
                fx["flash"] = (255, 240, 220, 0.22 * (1 - u / 0.16))
                fx["chroma"] = 3
        return fx

    def draw_march(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P, dur, d2, flip = self._march_tl(l, tr, a, b)
        out_t = clamp((tr - (dur - 0.22)) / 0.22)
        y1, y2 = 400, 640
        dark_pad(frame, W / 2, 520, 1800, 700, 0.30 * (1 - out_t) * clamp(tr / 0.2))
        pul = 1.0 + (0.03 if not P["slow"] else 0.015) * beat_pulse(t, 7.0)
        # tricolor flag stripes sliding behind the text
        k0 = ease_out_quint(tr / 0.5)
        for j, col in enumerate(((255, 145, 40), (245, 245, 240), (34, 160, 70))):
            yy = 520 + (j - 1) * 30
            im = Image.new("RGBA", (W, 16), col + (255,))
            blit(frame, im, W / 2 + (1 - k0) * (-W if not flip else W), yy, 0.28 * (1 - out_t))
        rows = ((P["s1"], y1, 0.16, -1 if not flip else 1), (P["s2"], y2, d2 + 0.16, 1 if not flip else -1))
        for sp, y, t0, direction in rows:
            u = (tr - (t0 - 0.16)) / 0.16
            if u < 0:
                continue
            e = ease_out_quint(u)
            x = W / 2 - direction * (1 - e) * (W * 0.9) - direction * out_t * W
            al = (1 - out_t)
            if sp is P["s1"]:
                # saffron slab behind the first word
                w = int(sp["w"] + 120)
                slab = Image.new("RGBA", (w, int(sp["h"] * 0.82)), (255, 140, 30, 255))
                blit(frame, slab, x, y - 6, 0.92 * al * min(1, u * 3), "over", pul)
            blit(frame, sp["glow"], x, y, al * 0.7, "add", pul)
            if u < 1:
                trail(frame, sp["main"], x, y, -direction * 150 * (1 - e), 0, al, 7, pul)
            else:
                blit(frame, sp["main"], x, y, al, "over", pul)
        # underline bar + speed lines after the second hit
        u2 = tr - d2
        if u2 > 0.1:
            self._tri_bar(frame, W / 2, y2 + P["s2"]["h"] * 0.52, P["s2"]["w"] * 0.92 * ease_out((u2 - 0.1) / 0.45), 14, 1 - out_t)
        for t0 in (0.0, d2):
            u = tr - t0 - 0.16
            if 0 <= u < 0.35:
                for k in range(12):
                    yy = 150 + hsh(k * 7 + int(t0 * 10)) * 780
                    ln = 400 + hsh(k * 5 + 2) * 900
                    xx = W / 2 + (hsh(k * 3) - 0.5) * 1200 + (u * 900) * (1 if k % 2 else -1)
                    im = Image.new("RGBA", (int(ln), 3), (255, 255, 255, 255))
                    blit(frame, im, xx, yy, 0.55 * (1 - u / 0.35), "add")

    # ---------- 3. stamp : Vote Chori! Gaddi Chor! ----------
    def _stamp_plan(self, l):
        def build():
            f = font("stamp", 230)
            ta, tb = "VOTE CHORI!", "GADDI CHOR!"
            while f.getlength(ta) > 1400:
                f = font("stamp", f.size - 8)
            sa = make_sprite(ta, f, WHITE, stroke=0, shadow=False)
            sb = make_sprite(tb, f, RED, stroke=0, shadow=False)
            pad_x, pad_y = 110, 40
            ba = self._banner(int(sa["w"] + 2 * pad_x), int(sa["h"] + 2 * pad_y), (190, 22, 28), 11)
            bb = self._banner(int(sb["w"] + 2 * pad_x), int(sb["h"] + 2 * pad_y), (246, 240, 228), 12)
            return dict(sa=sa, sb=sb, ba=ba, bb=bb)
        return self._plan(("stamp", l["id"]), build)

    @staticmethod
    def _banner(w, h, col, seed):
        rs = np.random.RandomState(seed)
        pad = 24
        im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([pad, pad, pad + w, pad + h], fill=col + (255,))
        # rough edges: bite small notches out of the border
        for _ in range(70):
            side = rs.randint(4)
            if side == 0:
                x, y = pad + rs.randint(w), pad
            elif side == 1:
                x, y = pad + rs.randint(w), pad + h
            elif side == 2:
                x, y = pad, pad + rs.randint(h)
            else:
                x, y = pad + w, pad + rs.randint(h)
            r = rs.randint(2, 7)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0, 0))
        # speckled ink wear
        arr = np.asarray(im).copy()
        noise = rs.rand(*arr.shape[:2])
        wear = (noise > 0.965)
        arr[..., 3] = np.where(wear, (arr[..., 3] * 0.45).astype(np.uint8), arr[..., 3])
        # border line
        out = Image.fromarray(arr)
        ImageDraw.Draw(out).rectangle([pad + 10, pad + 10, pad + w - 10, pad + h - 10], outline=(0, 0, 0, 90), width=3)
        return out

    def _stamp_tl(self, l, tr, a, b):
        dur = b - l["start"]
        d2 = 0.42 if dur > 2.3 else 0.36
        return dur, d2

    def fx_stamp(self, l, tr, a, b, t):
        dur, d2 = self._stamp_tl(l, tr, a, b)
        fx = {}
        sx = sy = 0.0
        for t0 in (0.10, d2 + 0.10):
            u = tr - t0
            if u >= 0:
                amp = 26 * math.exp(-u / 0.09)
                sx += math.sin(u * 130) * amp
                sy += math.cos(u * 101) * amp
                if u < 0.12:
                    fx["flash"] = (255, 255, 255, 0.42 * (1 - u / 0.12))
        fx["shake"] = (sx, sy)
        fx["vig_red"] = 0.55 * beat_pulse(t, 5.5) * (1 if tr > 0.15 else 0.0)
        gl = hsh(int(t * 9))
        fx["chroma"] = 5 if (tr > 0.2 and gl > 0.86) or (0 <= tr - 0.10 < 0.2) or (0 <= tr - d2 - 0.10 < 0.2) else 0
        return fx

    def draw_stamp(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P = self._stamp_plan(l)
        dur, d2 = self._stamp_tl(l, tr, a, b)
        out_vis = 1.0 if tr < dur - 0.05 else 0.0
        gap = (P["ba"].height + P["bb"].height) / 2 * 0.74 + 18
        ya = 540 - gap / 2
        items = ((P["ba"], P["sa"], ya, -3.2, 0.10), (P["bb"], P["sb"], ya + gap, 2.4, d2 + 0.10))
        for ban, sp, y, rot, t0 in items:
            u = (tr - (t0 - 0.10)) / 0.10
            if u < 0 or not out_vis:
                continue
            e = clamp(u) ** 2.2
            sc = lerp(3.4, 1.0, e)
            al = clamp(u * 3)
            jx = (hsh(int(t * 12)) - 0.5) * 3
            blit(frame, ban, W / 2 + jx, y, al, "over", sc, rot)
            blit(frame, sp["main"], W / 2 + jx, y - 4, al, "over", sc, rot)
            if u >= 1.0:
                v = tr - t0
                if v < 0.5:
                    self._ring(frame, W / 2, y, 140 + 1000 * ease_out(v / 0.5), 10, (255, 90, 70), 0.75 * (1 - v / 0.5))
                    self._splatter(frame, W / 2, y, v, int(t0 * 100))
        # glitch slices
        if tr > 0.2 and hsh(int(t * 9)) > 0.86:
            for k in range(3):
                yy = 300 + hsh(k + int(t * 9)) * 500
                dx = (hsh(k * 3 + int(t * 9)) - 0.5) * 60
                self._slice(frame, int(yy), 26, int(dx))

    @staticmethod
    def _slice(frame, y, h, dx):
        y0, y1 = max(0, y), min(H, y + h)
        if y1 > y0 and dx != 0:
            frame[y0:y1] = np.roll(frame[y0:y1], dx, axis=1)

    def _splatter(self, frame, cx, cy, v, seed):
        sp = radial(30, 30, 1.2)
        for k in range(26):
            ang = hsh(seed + k) * 6.283
            sp_ = 380 + hsh(seed + k + 50) * 900
            r = sp_ * ease_out(v / 0.45)
            x, y = cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.62
            sz = (0.4 + hsh(seed + k + 100) * 1.1) * (1 - clamp(v / 0.5) * 0.6)
            blit(frame, sp, x, y, 0.95 * (1 - clamp(v / 0.5)), "over", sz, tint=np.array([0.95, 0.12, 0.10]))

    # ---------- 4. defiant : Ye Mulk Tera Baap Ka Nahin! ----------
    def _defiant_plan(self, l):
        def build():
            rom = l["roman"]
            tail = rom[-1] if rom[-1] in ",!…" else ""
            words = rom.rstrip(",!…").split()
            words = [w.upper() for w in words]
            words[-1] += tail
            f = font("defiant", 185)
            half = (len(words) + 1) // 2
            rows = [list(range(half)), list(range(half, len(words)))]
            while True:
                sp = f.getlength(" ")
                big = font("defiant", int(f.size * 1.22))
                rw = [sum((big if i == len(words) - 1 else f).getlength(words[i]) for i in r) + sp * (len(r) - 1) for r in rows]
                if max(rw) <= 1560 or f.size < 100:
                    break
                f = font("defiant", f.size - 6)
            sprites = {}
            for i, w in enumerate(words):
                last = (i == len(words) - 1)
                fi = font("defiant", int(f.size * (1.22 if last else 1.0)))
                if last:
                    sprites[i] = make_sprite(w, fi, gradient=[(0, (255, 232, 130)), (0.55, (255, 170, 50)), (1, (220, 50, 40))], stroke=6, glow=((255, 70, 40), 26, 1.2))
                elif w.rstrip(",!…") == "BAAP":
                    sprites[i] = make_sprite(w, fi, SAFFRON, stroke=5, glow=(SAFFRON, 14, 0.8))
                else:
                    sprites[i] = make_sprite(w, fi, WHITE, stroke=5, glow=None)
            # layout
            sp = f.getlength(" ")
            pos = {}
            for r, idxs in enumerate(rows):
                ws = [sprites[i]["w"] for i in idxs]
                rwid = sum(ws) + sp * (len(idxs) - 1)
                x = -rwid / 2
                for k, i in enumerate(idxs):
                    pos[i] = (x + ws[k] / 2, r)
                    x += ws[k] + sp
            return dict(words=words, sprites=sprites, pos=pos, f=f, rows=rows)
        return self._plan(("defiant", l["id"]), build)

    def _defiant_times(self, P, l):
        n = len(P["words"])
        dur = l["end"] - l["start"]
        echo = l["roman"].endswith("…")
        span = min(dur * (0.80 if echo else 0.66), 2.0 if not echo else 2.4)
        w = np.array([max(1, syllables(x)) for x in P["words"]], float)
        w[-1] *= 1.6
        cum = np.concatenate([[0], np.cumsum(w)])
        t0 = [span * (cum[i] / cum[-1]) * 0.9 for i in range(n)]
        # keep minimum spacing so each hit is readable
        for i in range(1, n):
            t0[i] = max(t0[i], t0[i - 1] + 0.16)
        return t0, echo

    def fx_defiant(self, l, tr, a, b, t):
        P = self._defiant_plan(l)
        times, echo = self._defiant_times(P, l)
        sx = sy = 0.0
        fx = {}
        for i, t0 in enumerate(times):
            u = tr - t0
            if u >= 0:
                last = (i == len(times) - 1)
                amp = (34 if last else 11) * math.exp(-u / (0.14 if last else 0.09)) * (0.5 if echo else 1.0)
                sx += math.sin(u * 120) * amp
                sy += math.cos(u * 93) * amp * 0.7
                if last and u < 0.14:
                    fx["flash"] = (255, 70, 50, 0.5 * (1 - u / 0.14) * (0.5 if echo else 1.0))
                    fx["chroma"] = 6
        fx["shake"] = (sx, sy)
        dur = b - l["start"]
        fx["bars"] = clamp((tr - times[-1] + 0.1) / 0.3) * (1 - smooth((tr - (dur - 0.35)) / 0.35)) * (0.5 if echo else 1.0)
        return fx

    def draw_defiant(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P = self._defiant_plan(l)
        times, echo = self._defiant_times(P, l)
        dur = b - l["start"]
        out = 1 - smooth((tr - (dur - 0.3)) / 0.35)
        y_rows = (430, 650)
        for i, w in enumerate(P["words"]):
            u = (tr - times[i]) / 0.14
            if u < 0:
                continue
            last = (i == len(P["words"]) - 1)
            sp = P["sprites"][i]
            x, r = P["pos"][i]
            e = clamp(u) ** 2.0
            sc = lerp(2.4 if last else 1.9, 1.0, e)
            cy = y_rows[r] + (1 - e) * -90
            al = clamp(u * 3) * out
            cx = W / 2 + x
            if "glow" in sp:
                blit(frame, sp["glow"], cx, cy, al * (0.65 + 0.3 * beat_pulse(t, 6)), "add", sc)
            blit(frame, sp["main"], cx, cy, al, "over", sc * (1.0 + 0.012 * beat_pulse(t, 7)))
            v = tr - times[i]
            if v >= 0.14 and v < 0.55 and last:
                self._ring(frame, cx, cy, 120 + 1200 * ease_out((v - 0.14) / 0.41), 12, (255, 120, 60), 0.8 * (1 - (v - 0.14) / 0.41) * (0.5 if echo else 1.0))
            if last and 0.14 <= v < 1.0:
                self._cracks(frame, cx, cy, ease_out((v - 0.14) / 0.3), (1 - clamp((v - 0.14) / 0.85)) * (0.5 if echo else 1.0), int(l["id"]))

    def _cracks(self, frame, cx, cy, grow, op, seed):
        if op <= 0.02:
            return
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for k in range(9):
            ang = hsh(seed * 7 + k) * 6.283
            x, y = cx, cy
            L = (260 + hsh(seed + k * 3) * 700) * grow
            steps = 9
            for s in range(steps):
                ang += (hsh(seed * 3 + k * 11 + s) - 0.5) * 1.1
                nx, ny = x + math.cos(ang) * L / steps, y + math.sin(ang) * L / steps * 0.8
                d.line([(x, y), (nx, ny)], fill=(255, 245, 230, 255), width=max(1, 5 - s // 2))
                x, y = nx, ny
        g = im.filter(ImageFilter.GaussianBlur(5))
        blit(frame, g, W / 2, H / 2, op * 0.8, "add", tint=np.array([1.0, 0.5, 0.3]))
        blit(frame, im, W / 2, H / 2, op, "over")

    def apply_bars(self, frame, amt):
        if amt <= 0.01:
            return
        h = int(H * 0.115 * ease_out(amt))
        frame[:h] = 0
        frame[H - h:] = 0

    # ---------- 5. people : Ye Janta Ka Hindustan Hai! ----------
    def _people_plan(self, l):
        def build():
            rom = l["roman"]
            words = rom.split()
            top = " ".join(words[:3])                # Ye Janta Ka
            bot = " ".join(words[3:]).upper()        # HINDUSTAN HAI!
            f2 = font("people", 210)
            while f2.getlength(bot) > 1560:
                f2 = font("people", f2.size - 8)
            f1 = font("people_small", int(f2.size * 0.60))
            grad_bot = [(0, (255, 140, 30)), (0.28, (255, 168, 70)), (0.40, (255, 244, 230)), (0.60, (255, 255, 255)), (0.72, (120, 215, 140)), (1, (14, 138, 60))]
            s1 = make_sprite(top, f1, gradient=[(0, (255, 244, 220)), (1, (255, 198, 100))], stroke=3, glow=(GOLD, 14, 0.7))
            s2 = make_sprite(bot, f2, gradient=grad_bot, stroke=5, stroke_col=(60, 34, 6), glow=(GOLD, 26, 0.9), cap_gradient=True)
            letters = []
            tw = f2.getlength(bot)
            for i, ch in enumerate(bot):
                if ch == " ":
                    letters.append((None, 0))
                    continue
                sp = make_sprite(ch, f2, gradient=grad_bot, stroke=5, stroke_col=(60, 34, 6), shadow=False, cap_gradient=True)
                adv = f2.getlength(bot[:i + 1]) - f2.getlength(bot[:i])
                letters.append((sp, f2.getlength(bot[:i]) - tw / 2 + adv / 2))
            return dict(s1=s1, s2=s2, letters=letters, f2=f2, chakra=self._chakra())
        return self._plan(("people", l["id"]), build)

    def _chakra(self):
        if "chakra" not in self.cache:
            import art
            arr = art.chakra_ring(1000, (255, 255, 255), 24, 5)
            self.cache["chakra"] = Image.fromarray(arr)
        return self.cache["chakra"]

    def fx_people(self, l, tr, a, b, t):
        fin = (l["id"] == 95)
        return dict(bloom=(0.7 if fin else 0.55) * ease_out(tr / 1.3), zoom=0.02 * clamp(tr / 3.0))

    def draw_people(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P = self._people_plan(l)
        dur = b - l["start"]
        fin = (l["id"] == 95)
        out = 1 - smooth((tr - (dur - (0.6 if fin else 0.35))) / (0.7 if fin else 0.4))
        zoom = 1.0 + 0.05 * clamp(tr / max(dur, 1.0))
        # backdrop: rays + warm bloom + rotating chakra
        g = ease_out(tr / 1.2) * out
        blit(frame, rays_sprite(1500, 26, 9).rotate((t * 4.5) % 360, resample=Image.BILINEAR), W / 2, 540, 0.38 * g, "add", 1.55, tint=np.array([1.0, 0.85, 0.5]))
        glow_blob(frame, W / 2, 560, 1700, 900, (255, 195, 100), 0.35 * g, 1.4)
        dark_pad(frame, W / 2, 500, 1800, 760, 0.42 * g)
        ch = P["chakra"].rotate(-(t * 7) % 360, resample=Image.BILINEAR)
        blit(frame, ch, W / 2, 560, 0.26 * g, "add", 1.0 + 0.5 * ease_out(tr / 1.4), tint=np.array([1.0, 0.95, 0.8]))
        # first line fades up
        u1 = (tr - 0.10) / 0.7
        if u1 > 0:
            e = ease_out(u1)
            blit(frame, P["s1"]["glow"], W / 2, 350 + (1 - e) * 26, 0.5 * clamp(u1) * out, "add", zoom)
            blit(frame, P["s1"]["main"], W / 2, 350 + (1 - e) * 26, clamp(u1 * 1.4) * out, "over", zoom)
        # second line: letter-spacing contracts + light sweep wipe
        u2 = (tr - 0.45) / 1.15
        if u2 > 0:
            e = ease_out_quint(u2)
            spread = 1.0 + 0.55 * (1 - e)
            blit(frame, P["s2"]["glow"], W / 2, 590, 0.65 * clamp(u2 * 2) * out * (0.85 + 0.25 * beat_pulse(t, 6)), "add", zoom)
            for k, (sp, xo) in enumerate(P["letters"]):
                if sp is None:
                    continue
                lu = clamp((u2 * 1.25 - k * 0.03))
                if lu <= 0:
                    continue
                blit(frame, sp["main"], W / 2 + xo * spread * zoom, 590 + (1 - ease_out(lu)) * 24, clamp(lu * 1.6) * out, "over", zoom * (1 + 0.1 * (1 - lu)))
            sw = ((tr - 1.2) * 0.5) % 2.2
            if tr > 1.4 and 0 < sw < 1.4:
                self._sweep(frame, P["s2"]["main"], W / 2, 590, sw, out * 0.85)
        # tricolor petals
        self._petals(frame, t, tr, out * (1.0 if fin else 0.7))

    def _petals(self, frame, t, tr, amt):
        if amt <= 0.02:
            return
        cols = ((255, 150, 50), (255, 252, 245), (40, 170, 80))
        for k in range(int(46 * amt)):
            r1, r2, r3 = hsh(k * 5 + 1), hsh(k * 5 + 2), hsh(k * 5 + 3)
            life = (tr * (0.10 + 0.12 * r3) + r1) % 1.0
            x = (r2 * (W + 200) - 100) + math.sin(t * (0.7 + r3) + k) * 60
            y = -60 + life * (H + 120)
            ang = (t * 70 * (r3 - 0.5) * 2 + k * 40)
            im = Image.new("RGBA", (26, 12), cols[k % 3] + (255,))
            blit(frame, im, x, y, 0.85 * amt * math.sin(math.pi * clamp(life)) ** 0.5, "over", 0.7 + r3, ang)
