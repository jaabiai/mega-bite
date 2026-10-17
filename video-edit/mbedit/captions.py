"""Word-by-word Manglish captions: the word being spoken is big + brand-cyan, the rest of the phrase is small/dim.

Text comes verbatim from the user's script; timing from the forced alignment (mbedit.common.Align).
"""
import bisect

import numpy as np

from . import gfx
from .common import FONT_XBOLD, CYAN, W, H, ease_out_back, ease_out, clamp, ramp

INACTIVE_SCALE = 0.74
ACTIVE_COLOR = (62, 220, 255)
GAP = 0.26                          # word gap in em (of the base font size)

ZONES = {
    # name: (font px, centre x, baseline y, max line width px)
    "full": dict(size=92, cx=W / 2, base=1000, max_w=1560),
    "left": dict(size=70, cx=590, base=1018, max_w=1000),
    "reel": dict(size=84, cx=540, base=1500, max_w=940),      # 9:16 reels / shorts (kept clear of the platform UI)
}


class Chunk:
    __slots__ = ("t0", "t1", "words", "zone", "t0_disp", "t1_disp")

    def __init__(self, words, zone):
        self.words = words          # list of dict(text, s, e)
        self.zone = zone
        self.t0 = words[0]["s"]
        self.t1 = words[-1]["e"]


def _wlen(text, size):
    return gfx.text_width(text, FONT_XBOLD, size)


def build_chunks(align, zone_at, max_words=3):
    """Group the aligned words into short on-screen phrases (never crossing a script line)."""
    chunks = []
    for cue in sorted(align.by_cue):
        ws = [dict(text=w["text"], s=w["start"], e=w["end"]) for w in align.by_cue[cue]]
        i = 0
        while i < len(ws):
            zone = zone_at(ws[i]["s"])
            z = ZONES[zone]
            cur = []
            while i < len(ws) and len(cur) < max_words:
                trial = cur + [ws[i]]
                lens = [_wlen(w["text"], z["size"]) for w in trial]
                width = sum(lens) * INACTIVE_SCALE + max(lens) * (1 - INACTIVE_SCALE) + (len(trial) - 1) * GAP * z["size"] + 0.3 * z["size"]
                if cur and width > z["max_w"]:
                    break
                cur.append(ws[i])
                i += 1
                if cur[-1]["text"].rstrip().endswith((",", ".", "...", "?", "!", "'")) and len(cur) >= 2:
                    break
            # avoid a lonely one-word tail when the next line chunk would be single
            if i < len(ws) and len(ws) - i == 1 and len(cur) >= 2:
                cur2 = cur[:-1]
                i -= 1
                cur = cur2
            chunks.append(Chunk(cur, zone))
    # continuous display window per chunk
    for k, c in enumerate(chunks):
        nxt = chunks[k + 1] if k + 1 < len(chunks) else None
        start = c.t0 - 0.05
        if k > 0:
            start = max(start, chunks[k - 1].t1 - 0.02)
        c.t0_disp = start
        if nxt is not None and nxt.t0 - c.t1 < 0.55:
            c.t1_disp = nxt.t0 - 0.05
        else:
            c.t1_disp = c.t1 + 0.28
    return chunks


class CaptionRenderer:
    def __init__(self, chunks):
        self.chunks = chunks
        self.starts = [c.t0_disp for c in chunks]
        self._cache = {}

    def _sprite(self, text, size, state):
        key = (text, size, state)
        if key in self._cache:
            return self._cache[key]
        if state == "active":
            s = gfx.text_sprite(text, FONT_XBOLD, size, fill=ACTIVE_COLOR, stroke=max(6, size // 13), stroke_fill=(6, 14, 38), shadow=(0, 7), shadow_blur=7, shadow_alpha=0.7, pad=size // 3)
        else:
            s = gfx.text_sprite(text, FONT_XBOLD, size, fill=(255, 255, 255), stroke=max(6, size // 13), stroke_fill=(6, 14, 38), shadow=(0, 7), shadow_blur=7, shadow_alpha=0.7, pad=size // 3)
            if state == "dim":
                s = gfx.scale_sprite(s, 1.0, blur=0.8)
        self._cache[key] = s
        return s

    def draw(self, frame, t, zone_override=None):
        k = bisect.bisect_right(self.starts, t) - 1
        if k < 0:
            return frame
        c = self.chunks[k]
        if t > c.t1_disp:
            return frame
        z = ZONES[zone_override or c.zone]
        size = z["size"]
        # entrance / exit
        age = t - c.t0_disp
        enter = ease_out(ramp(age, 0, 0.12))
        leave = 1 - ramp(t, c.t1_disp - 0.07, c.t1_disp)
        op = enter * leave
        dy = (1 - enter) * 16
        # per-word activation
        words = c.words
        items = []
        for i, w in enumerate(words):
            nxt = words[i + 1]["s"] if i + 1 < len(words) else w["e"] + 0.12
            a_in = ease_out_back(ramp(t, w["s"] - 0.01, w["s"] + 0.11), 2.2)
            a_out = ramp(t, nxt - 0.02, nxt + 0.07)
            act = clamp(a_in) * (1 - a_out) if t >= w["s"] - 0.01 else 0.0
            act = max(act, 0.0)
            state = "active" if act > 0.5 else ("normal" if t >= w["s"] else "dim")
            sc = INACTIVE_SCALE + (1.0 - INACTIVE_SCALE) * a_in * (1 - a_out) if t >= w["s"] - 0.01 else INACTIVE_SCALE
            spr = self._sprite(w["text"], size, state)
            items.append((spr, sc, state))
        gap = GAP * size
        pad = size // 3
        widths = [gfx.sprite_size(sp)[0] * sc - 2 * pad * sc for sp, sc, _ in items]     # visible text width (sprite padding stripped)
        total = sum(widths) + gap * (len(items) - 1)
        fit = min(1.0, z["max_w"] / max(total, 1.0))          # never let a long word run out of its zone
        if fit < 1.0:
            items = [(sp, sc * fit, st) for sp, sc, st in items]
            widths = [wv * fit for wv in widths]
            gap *= fit
            total *= fit
        x = z["cx"] - total / 2
        for (spr, sc, state), wv in zip(items, widths):
            alpha = op * (1.0 if state != "dim" else 0.88)
            _blit_scaled(frame, spr, sc, x - pad * sc, z["base"] + dy, alpha)
            x += wv + gap
        return frame


def _blit_scaled(frame, spr, sc, x, bottom_y, alpha):
    """draw sprite scaled by sc, left edge at x and bottom edge on bottom_y (so every word shares one baseline)"""
    s = gfx.scale_sprite(spr, sc) if abs(sc - 1) > 0.004 else spr
    h = gfx.sprite_size(s)[1]
    gfx.blit(frame, s, x, bottom_y - h, alpha)
