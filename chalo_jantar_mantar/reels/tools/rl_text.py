"""Vertical (1080x1920) typography for the Reel.  Roman letters only (hl_text.make_sprite refuses anything else).

Built on the landscape engine's primitives (hl_text, imported read-only) but every layout is new for a 9:16 frame:
  * regular lines are stacked in 1-3 centred rows inside the 900 px safe width, in the lower-middle of the frame (clear of the Reels UI zones:
    top ~220 px, bottom ~420 px)
  * hooks are re-staged as tall stacks: stamp (2 two-line banners), defiant (3 rows, the last word enlarged), march (slab + giant word,
    split at the hyphen when it is too wide)
  * no letterbox bars (they would read as black bars in a vertical frame) - the "defiant" pinch is a red vignette pulse instead.
"""
import rl_common  # noqa: F401  (must be first)
import itertools
import math
import re

import numpy as np
from PIL import Image

from hl_common import W, H, clamp, smooth, ease_out, ease_out_quint, ease_out_back, ease_in_out, lerp, beat_pulse
import hl_text as HT
from hl_text import (font, make_sprite, blit, trail, dark_pad, glow_blob, hsh, syllables, accent_word, blur_of,
                     WHITE, GOLD, SAFFRON, GREEN, RED, CREAM)

SAFE_W = 900                      # text width inside the 1080 frame (90 px side margins)
LYR_Y = 1195                      # vertical centre of the regular lyric block
HOOK_Y = 900                      # vertical centre of the hook stacks
FUNC = {"ka", "ke", "ki", "ko", "se", "mein", "par", "ye", "na", "hai", "aur", "to", "jo", "ek", "har", "apne", "apni", "apna", "kal"}


# ----------------------------------------------------------------------------------------------------------------------------------
# row fitting
# ----------------------------------------------------------------------------------------------------------------------------------
def fit_rows(widths, space, maxw, max_rows):
    """Split words (given widths) into <= max_rows consecutive rows that fit maxw. Fewest rows first; balanced; avoids ending a row on a
    function word. Returns list of index lists or None."""
    n = len(widths)
    for nr in range(1, min(max_rows, n) + 1):
        best = None
        for cuts in itertools.combinations(range(1, n), nr - 1):
            bounds = (0,) + cuts + (n,)
            rows = [list(range(bounds[i], bounds[i + 1])) for i in range(nr)]
            rw = [sum(widths[i] for i in r) + space * (len(r) - 1) for r in rows]
            if max(rw) > maxw:
                continue
            score = max(rw) + 0.35 * float(np.std(rw))
            best = (score, rows) if best is None or score < best[0] else best
        if best:
            return best[1]
    return None


def fit_rows_penalised(words, widths, space, maxw, max_rows):
    n = len(widths)
    for nr in range(1, min(max_rows, n) + 1):
        best = None
        for cuts in itertools.combinations(range(1, n), nr - 1):
            bounds = (0,) + cuts + (n,)
            rows = [list(range(bounds[i], bounds[i + 1])) for i in range(nr)]
            rw = [sum(widths[i] for i in r) + space * (len(r) - 1) for r in rows]
            if max(rw) > maxw:
                continue
            pen = sum(70 for r in rows[:-1] if re.sub(r"[^a-z]", "", words[r[-1]].lower()) in FUNC)
            score = max(rw) + 0.35 * float(np.std(rw)) + pen
            best = (score, rows) if best is None or score < best[0] else best
        if best:
            return best[1]
    return None


class VRow:
    """A lyric line laid out as 1-3 centred rows of word sprites (vertical frame)."""

    def __init__(self, text, kind, size0, maxw=SAFE_W, upper=False, fill=WHITE, gradient=None, stroke=4, glow=True, accent=True, max_rows=3,
                 min_size=64, step=4, line_k=0.90, max_h=620):
        words = text.upper().split() if upper else text.split()
        size = size0
        while True:
            f = font(kind, size)
            space = f.getlength(" ")
            rows = fit_rows_penalised(words, [f.getlength(w) for w in words], space, maxw, max_rows)
            asc_, desc_ = f.getmetrics()
            if (rows is not None and len(rows) * (asc_ + desc_) * line_k <= max_h) or size <= min_size:
                break
            size -= step
        if rows is None:
            rows = [list(range(len(words)))]
        self.size, self.f, self.words = size, f, words
        ai, acol = accent_word(words) if accent else (None, None)
        self.sprites = []
        for i, w in enumerate(words):
            col = acol if i == ai else fill
            grad = None if (i == ai and acol) else gradient
            self.sprites.append(make_sprite(w, f, col, grad, stroke, glow=((acol or SAFFRON), 14, 1.1) if (glow and i == ai) else None))
        self.rows = rows
        asc, desc = f.getmetrics()
        self.line_h = int((asc + desc) * line_k)
        self.pos = {}
        for r, idxs in enumerate(rows):
            wl = [f.getlength(words[i]) for i in idxs]
            rw = sum(wl) + space * (len(idxs) - 1)
            x = -rw / 2
            for k, i in enumerate(idxs):
                self.pos[i] = (x + wl[k] / 2, r)
                x += wl[k] + space
        self.nrows = len(rows)
        self.weights = [syllables(w) for w in words]
        self.block_h = self.line_h * self.nrows


# ----------------------------------------------------------------------------------------------------------------------------------
# the engine
# ----------------------------------------------------------------------------------------------------------------------------------
class ReelText(HT.TextEngine):
    """Same line windows / word timing rules as the landscape engine, vertical layouts."""

    def __init__(self, lines, clip_start, clip_end):
        super().__init__(lines)
        self.t0, self.t1 = clip_start, clip_end
        # lines that take part: sung span overlaps the clip, and does not merely start in the last 0.3 s
        self.include = {i for i, l in enumerate(lines) if l["end"] > clip_start and l["start"] < clip_end - 0.3}

    def active(self, t):
        out = []
        for i, l in enumerate(self.lines):
            if i not in self.include:
                continue
            a, b = self.window(i)
            if a - 0.05 <= t <= b + 0.45:
                out.append((i, a, b))
        return out

    # ---- scrim: soft dark band behind the lyric block, eased in/out so that nothing pops --------------------------------------
    def scrim_amount(self, t):
        e = 0.0
        for i, a, b in self.active(t):
            if self.lines[i]["hook"] == "regular":
                e = max(e, smooth((t - (a - 0.12)) / 0.22) * (1 - smooth((t - b) / 0.30)))
        return e

    def scrim_img(self):
        if getattr(self, "_vscrim", None) is None:
            y = np.arange(H, dtype=np.float32)[:, None]
            a = np.exp(-((y - (LYR_Y + 40)) / 430.0) ** 2) * 0.58 + np.clip((y - 1500) / 420.0, 0, 1) * 0.30
            self._vscrim = a.astype(np.float32)
        return self._vscrim

    def draw(self, frame, t, fx_shake=(0, 0)):
        s = self.scrim_amount(t)
        if s > 0.01:
            m = 1.0 - self.scrim_img() * s
            frame[:] = np.clip(frame.astype(np.float32) * m[..., None], 0, 255).astype(np.uint8)
        for i, a, b in self.active(t):
            l = self.lines[i]
            if l["hook"] == "regular":
                kind = HT.family_of(l["section"])
                (self.draw_vrap if kind == "rap" else self.draw_vmelodic)(frame, l, t, a, b)
            else:
                getattr(self, "draw_" + l["hook"])(frame, l, t - l["start"], a, b, t, fx_shake)

    # ================= regular lines =================
    def _vrow(self, l, kind):
        key = ("vrow", l["id"], kind)
        if key in self.cache:
            return self.cache[key]
        txt = l["roman"]
        if kind == "rap":
            wr = VRow(txt, "rap", 240, upper=True, stroke=6, max_rows=4, max_h=530)
        else:
            wr = VRow(txt, "melodic", 170, stroke=5, max_rows=4, max_h=530, gradient=[(0, (255, 255, 255)), (0.55, (255, 236, 190)), (1, (255, 196, 96))], line_k=0.96)
            wr.blur = [blur_of(sp["main"], 9) for sp in wr.sprites]
        self.cache[key] = wr
        return wr

    def _vtimes(self, wr, l, kind):
        s, e = l["start"], l["end"]
        n = len(wr.words)
        tot = float(sum(wr.weights))
        cum = np.concatenate([[0], np.cumsum(wr.weights)])
        span = (e - s) * (0.90 if kind == "rap" else 0.75)
        return [s - 0.02 + span * cum[k] / tot for k in range(n)]

    def _vplace(self, wr, k):
        x, r = wr.pos[k]
        return W / 2 + x, LYR_Y + (r - (wr.nrows - 1) / 2.0) * wr.line_h

    def draw_vrap(self, frame, l, t, a, b):
        wr = self._vrow(l, "rap")
        times = self._vtimes(wr, l, "rap")
        out = 1 - smooth((t - (b - 0.14)) / 0.14)
        pul = 1 + 0.018 * beat_pulse(t, 8.0)
        for k, sp in enumerate(wr.sprites):
            u = (t - times[k]) / 0.17
            if u < 0:
                continue
            e = ease_out_back(u, 1.9)
            sc = lerp(1.55, 1.0, e) * pul
            side = 1 if (l["id"] + k) % 2 == 0 else -1
            dx = (1 - ease_out(u)) * 110 * side
            al = clamp(u * 2.2) * out
            cx, cy = self._vplace(wr, k)
            if "glow" in sp:
                blit(frame, sp["glow"], cx, cy, al * 0.7 * (0.8 + 0.4 * beat_pulse(t, 6.0)), "add", sc)
            if u < 1.0:
                trail(frame, sp["main"], cx + dx, cy, dx * 1.2, 0, al, 5, sc)
            else:
                blit(frame, sp["main"], cx, cy, al, "over", sc)
        self._tri_bar(frame, W / 2, LYR_Y + wr.block_h / 2 + 14, 240 * ease_out((t - l["start"]) / 0.5), 6, 0.9 * out)

    def draw_vmelodic(self, frame, l, t, a, b):
        wr = self._vrow(l, "melodic")
        times = self._vtimes(wr, l, "melodic")
        out = 1 - smooth((t - (b - 0.18)) / 0.18)
        sweep = ((t - l["start"]) / 0.9)
        for k, sp in enumerate(wr.sprites):
            u = (t - times[k]) / 0.34
            if u < 0:
                continue
            e = ease_out(u)
            cx, cy = self._vplace(wr, k)
            cy += (1 - e) * 34
            al = clamp(u * 1.6) * out
            blit(frame, wr.blur[k], cx, cy, al * (1 - e) * 0.8, "over")
            blit(frame, sp["main"], cx, cy, al * e, "over", 1.0 + 0.02 * beat_pulse(t, 7.0))
            if 0.0 < sweep < 1.3:
                self._sweep(frame, sp["main"], cx, cy, sweep, al)
        self._tri_bar(frame, W / 2, LYR_Y + wr.block_h / 2 + 14, 220 * ease_out((t - l["start"]) / 0.5), 5, 0.8 * out)

    # ================= hook: march  (Chalo Jantar-Mantar!) =================
    def _march_plan(self, l):
        def build():
            toks = l["roman"].split(" ")
            a_txt = toks[0].upper()
            b_txt = " ".join(toks[1:]).upper()
            slow = l["roman"].endswith("…")
            # giant word(s): split at the hyphen when one row would be too wide
            def fit(txt, start):
                f = font("march", start)
                while f.getlength(txt) > SAFE_W:
                    f = font("march", f.size - 8)
                return f
            f_one = fit(b_txt, 560)
            parts = [b_txt]
            if "-" in b_txt and f_one.size < 330:
                h = b_txt.index("-") + 1
                parts = [b_txt[:h], b_txt[h:]]
                f_big = min(fit(parts[0], 460), fit(parts[1], 460), key=lambda f: f.size)
            else:
                f_big = f_one
            f_a = font("march", int(min(f_big.size * 0.55, 150)))
            while f_a.getlength(a_txt) > SAFE_W - 40:
                f_a = font("march", f_a.size - 6)
            s_a = make_sprite(a_txt, f_a, WHITE, stroke=5, glow=(SAFFRON, 18, 0.8))
            sb = [make_sprite(p, f_big, WHITE, stroke=7, glow=(GOLD, 22, 0.7)) for p in parts]
            return dict(sa=s_a, sb=sb, a=a_txt, parts=parts, slow=slow, f_a=f_a, f_big=f_big)
        return self._plan(("vmarch", l["id"]), build)

    def _march_tl(self, l, tr, a, b):
        P = self._march_plan(l)
        dur = b - l["start"]
        d2 = 0.50 if P["slow"] else 0.27
        flip = (l["id"] % 2 == 0)
        return P, dur, d2, flip

    def fx_march(self, l, tr, a, b, t):
        P, dur, d2, flip = self._march_tl(l, tr, a, b)
        fx = {}
        hits = [0.16, d2 + 0.16] + ([d2 + 0.34] if len(P["sb"]) > 1 else [])
        sx = sy = 0.0
        for t0 in hits:
            u = tr - t0
            if u >= 0:
                amp = 12 * math.exp(-u / 0.10) * (0.7 if P["slow"] else 1.0)
                sx += math.sin(u * 110) * amp
                sy += math.cos(u * 97) * amp * 0.9
        fx["shake"] = (sx, sy)
        for t0 in hits:
            u = tr - t0
            if 0 <= u < 0.16:
                fx["flash"] = (255, 240, 220, 0.22 * (1 - u / 0.16))
                fx["chroma"] = 3
        return fx

    def draw_march(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P, dur, d2, flip = self._march_tl(l, tr, a, b)
        out_t = clamp((tr - (dur - 0.22)) / 0.22)
        hb = [sp["h"] * 0.80 for sp in P["sb"]]
        ha = P["sa"]["h"] * 0.82
        gap = 6
        total = ha + gap + sum(hb) + gap * (len(hb) - 1)
        y = HOOK_Y - total / 2
        y_a = y + ha / 2
        ys_b = []
        yy = y + ha + gap
        for h_ in hb:
            ys_b.append(yy + h_ / 2)
            yy += h_ + gap
        dark_pad(frame, W / 2, HOOK_Y, 1500, 1250, 0.34 * (1 - out_t) * clamp(tr / 0.2))
        pul = 1.0 + (0.03 if not P["slow"] else 0.015) * beat_pulse(t, 7.0)
        k0 = ease_out_quint(tr / 0.5)
        mid = HOOK_Y
        for j, col in enumerate(((255, 145, 40), (245, 245, 240), (34, 160, 70))):
            im = Image.new("RGBA", (W, 18), col + (255,))
            blit(frame, im, W / 2 + (1 - k0) * (-W if not flip else W), mid + (j - 1) * 40 - total / 2 - 70, 0.30 * (1 - out_t))
        rows = [(P["sa"], y_a, 0.16, -1 if not flip else 1, True)]
        for k, (sp, yb) in enumerate(zip(P["sb"], ys_b)):
            rows.append((sp, yb, d2 + 0.16 + 0.18 * k, 1 if (not flip) ^ (k % 2 == 1) else -1, False))
        for sp, yv, t0, direction, is_a in rows:
            u = (tr - (t0 - 0.16)) / 0.16
            if u < 0:
                continue
            e = ease_out_quint(u)
            x = W / 2 - direction * (1 - e) * (W * 0.9) - direction * out_t * W
            al = (1 - out_t)
            if is_a:
                w = int(sp["w"] + 110)
                slab = Image.new("RGBA", (w, int(sp["h"] * 0.82)), (255, 140, 30, 255))
                blit(frame, slab, x, yv - 5, 0.92 * al * min(1, u * 3), "over", pul)
            blit(frame, sp["glow"], x, yv, al * 0.7, "add", pul)
            if u < 1:
                trail(frame, sp["main"], x, yv, -direction * 150 * (1 - e), 0, al, 7, pul)
            else:
                blit(frame, sp["main"], x, yv, al, "over", pul)
        u2 = tr - (d2 + 0.16 + 0.18 * (len(P["sb"]) - 1))
        if u2 > 0.1:
            self._tri_bar(frame, W / 2, ys_b[-1] + hb[-1] / 2 + 26, P["sb"][-1]["w"] * 0.90 * ease_out((u2 - 0.1) / 0.45), 16, 1 - out_t)
        for t0 in (0.0, d2):
            u = tr - t0 - 0.16
            if 0 <= u < 0.35:
                for k in range(12):
                    ypos = 330 + hsh(k * 7 + int(t0 * 10)) * 1100
                    ln = 400 + hsh(k * 5 + 2) * 700
                    xx = W / 2 + (hsh(k * 3) - 0.5) * 900 + (u * 900) * (1 if k % 2 else -1)
                    im = Image.new("RGBA", (int(ln), 3), (255, 255, 255, 255))
                    blit(frame, im, xx, ypos, 0.55 * (1 - u / 0.35), "add")

    # ================= hook: stamp  (Vote Chori! Gaddi Chor!) =================
    def _stamp_plan(self, l):
        def build():
            words_a, words_b = ["VOTE", "CHORI!"], ["GADDI", "CHOR!"]
            f = font("stamp", 230)
            while max(f.getlength(w) for w in words_a + words_b) > 720:
                f = font("stamp", f.size - 8)

            def banner(ws, col_txt, col_bg, seed):
                sps = [make_sprite(w, f, col_txt, stroke=0, shadow=False) for w in ws]
                lh = int(sps[0]["h"] * 0.84)
                bw = int(max(sp["w"] for sp in sps) + 2 * 78)
                bh = int(lh * len(ws) + 2 * 46)
                ban = HT.TextEngine._banner(bw, bh, col_bg, seed)
                comp = ban.copy()
                for i, sp in enumerate(sps):
                    cy = ban.height / 2 + (i - (len(ws) - 1) / 2) * lh - 4
                    comp.alpha_composite(sp["main"], (int(ban.width / 2 - sp["main"].width / 2), int(cy - sp["main"].height / 2)))
                return comp
            ba = banner(words_a, WHITE, (190, 22, 28), 11)
            bb = banner(words_b, RED, (246, 240, 228), 12)
            return dict(ba=ba, bb=bb)
        return self._plan(("vstamp", l["id"]), build)

    def draw_stamp(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P = self._stamp_plan(l)
        dur, d2 = self._stamp_tl(l, tr, a, b)
        out_vis = 1.0 if tr < dur - 0.05 else 0.0
        gap = (P["ba"].height + P["bb"].height) / 2 * 0.80 + 10
        ya = HOOK_Y - gap / 2
        items = ((P["ba"], ya, -3.2, 0.10), (P["bb"], ya + gap, 2.4, d2 + 0.10))
        for ban, y, rot, t0 in items:
            u = (tr - (t0 - 0.10)) / 0.10
            if u < 0 or not out_vis:
                continue
            e = clamp(u) ** 2.2
            sc = lerp(3.4, 1.0, e)
            al = clamp(u * 3)
            jx = (hsh(int(t * 12)) - 0.5) * 3
            blit(frame, ban, W / 2 + jx, y, al, "over", sc, rot)
            if u >= 1.0:
                v = tr - t0
                if v < 0.5:
                    HT.TextEngine._ring(frame, W / 2, y, 140 + 900 * ease_out(v / 0.5), 10, (255, 90, 70), 0.75 * (1 - v / 0.5))
                    self._splatter(frame, W / 2, y, v, int(t0 * 100))
        if tr > 0.2 and hsh(int(t * 9)) > 0.86:
            for k in range(3):
                yy = 500 + hsh(k + int(t * 9)) * 800
                dx = (hsh(k * 3 + int(t * 9)) - 0.5) * 60
                self._slice(frame, int(yy), 26, int(dx))

    # ================= hook: defiant  (Ye Mulk Tera Baap Ka Nahin!) =================
    def _defiant_plan(self, l):
        def build():
            rom = l["roman"]
            tail = rom[-1] if rom[-1] in ",!…" else ""
            words = [w.upper() for w in rom.rstrip(",!…").split()]
            words[-1] += tail
            f = font("defiant", 190)
            while True:
                big = font("defiant", int(f.size * 1.22))
                sp = f.getlength(" ")
                widths = [(big if i == len(words) - 1 else f).getlength(w) for i, w in enumerate(words)]
                rows = fit_rows(widths, sp, SAFE_W, 3)
                if rows is not None and len(rows) >= 3 or f.size < 110:
                    break
                if rows is not None and len(rows) < 3 and f.size <= 150:
                    break
                f = font("defiant", f.size - 6)
            if rows is None:
                rows = [list(range(len(words)))]
            sprites = {}
            for i, w in enumerate(words):
                last = (i == len(words) - 1)
                fi = font("defiant", int(f.size * (1.22 if last else 1.0)))
                if last:
                    sprites[i] = make_sprite(w, fi, gradient=[(0, (255, 232, 130)), (0.55, (255, 170, 50)), (1, (220, 50, 40))], stroke=7, glow=((255, 70, 40), 26, 1.2))
                elif w.rstrip(",!…") == "BAAP":
                    sprites[i] = make_sprite(w, fi, SAFFRON, stroke=6, glow=(SAFFRON, 14, 0.8))
                else:
                    sprites[i] = make_sprite(w, fi, WHITE, stroke=6, glow=None)
            sp = f.getlength(" ")
            pos = {}
            for r, idxs in enumerate(rows):
                ws = [sprites[i]["w"] for i in idxs]
                rwid = sum(ws) + sp * (len(idxs) - 1)
                x = -rwid / 2
                for k, i in enumerate(idxs):
                    pos[i] = (x + ws[k] / 2, r)
                    x += ws[k] + sp
            return dict(words=words, sprites=sprites, pos=pos, f=f, rows=rows, line_h=int(f.size * 1.12))
        return self._plan(("vdefiant", l["id"]), build)

    def fx_defiant(self, l, tr, a, b, t):
        P = self._defiant_plan(l)
        times, echo = self._defiant_times(P, l)
        sx = sy = 0.0
        fx = {}
        for i, t0 in enumerate(times):
            u = tr - t0
            if u >= 0:
                last = (i == len(times) - 1)
                amp = (28 if last else 9) * math.exp(-u / (0.14 if last else 0.09)) * (0.5 if echo else 1.0)
                sx += math.sin(u * 120) * amp
                sy += math.cos(u * 93) * amp * 0.9
                if last and u < 0.14:
                    fx["flash"] = (255, 70, 50, 0.5 * (1 - u / 0.14) * (0.5 if echo else 1.0))
                    fx["chroma"] = 6
        fx["shake"] = (sx, sy)
        dur = b - l["start"]
        pinch = clamp((tr - times[-1] + 0.1) / 0.3) * (1 - smooth((tr - (dur - 0.35)) / 0.35)) * (0.5 if echo else 1.0)
        fx["vig_red"] = 0.8 * pinch
        return fx

    def draw_defiant(self, frame, l, tr, a, b, t, shake=(0, 0)):
        P = self._defiant_plan(l)
        times, echo = self._defiant_times(P, l)
        dur = b - l["start"]
        out = 1 - smooth((tr - (dur - 0.3)) / 0.35)
        nrows = len(P["rows"])
        dark_pad(frame, W / 2, HOOK_Y, 1500, 1150, 0.30 * out * clamp(tr / 0.2))
        for i, w in enumerate(P["words"]):
            u = (tr - times[i]) / 0.14
            if u < 0:
                continue
            last = (i == len(P["words"]) - 1)
            sp = P["sprites"][i]
            x, r = P["pos"][i]
            e = clamp(u) ** 2.0
            sc = lerp(2.4 if last else 1.9, 1.0, e)
            cy = HOOK_Y + (r - (nrows - 1) / 2.0) * P["line_h"] + (1 - e) * -90
            al = clamp(u * 3) * out
            cx = W / 2 + x
            if "glow" in sp:
                blit(frame, sp["glow"], cx, cy, al * (0.65 + 0.3 * beat_pulse(t, 6)), "add", sc)
            blit(frame, sp["main"], cx, cy, al, "over", sc * (1.0 + 0.012 * beat_pulse(t, 7)))
            v = tr - times[i]
            if 0.14 <= v < 0.55 and last:
                HT.TextEngine._ring(frame, cx, cy, 120 + 1000 * ease_out((v - 0.14) / 0.41), 12, (255, 120, 60), 0.8 * (1 - (v - 0.14) / 0.41) * (0.5 if echo else 1.0))
            if last and 0.14 <= v < 1.0:
                self._cracks(frame, cx, cy, ease_out((v - 0.14) / 0.3), (1 - clamp((v - 0.14) / 0.85)) * (0.5 if echo else 1.0), int(l["id"]))

    def apply_bars(self, frame, amt):          # intentionally a no-op: no letterbox bars in the vertical frame
        return
