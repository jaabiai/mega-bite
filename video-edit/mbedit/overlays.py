"""Time-based overlay layers drawn on top of the composited scene: headlines, CTAs, logo, dimmers."""
import math
import os

import numpy as np
import cv2

from . import gfx
from .common import (WORK, W, H, FONT_BLACK, FONT_XBOLD, CYAN, BLUE, clamp, ramp, lerp, ease_out, ease_in, ease_in_out,
                     ease_out_back, smooth)

ASSETS = os.path.join(WORK, "assets")
_sprite_cache = {}


def asset(name):
    if name not in _sprite_cache:
        _sprite_cache[name] = gfx.sprite_from_png(os.path.join(ASSETS, name + ".png"))
    return _sprite_cache[name]


class Layer:
    t0 = t1 = 0.0

    def active(self, t):
        return self.t0 - 0.01 <= t <= self.t1 + 0.01

    def draw(self, frame, t):
        raise NotImplementedError


# ------------------------------------------------------------------ dim / shade
class Dim(Layer):
    """darken the whole frame (e.g. behind the logo reveal)"""

    def __init__(self, t0, t1, k=0.55, fade=0.3):
        self.t0, self.t1, self.k, self.fade = t0, t1, k, fade

    def draw(self, frame, t):
        v = ramp(t, self.t0, self.t0 + self.fade) * (1 - ramp(t, self.t1 - self.fade, self.t1))
        return gfx.darken(frame, 1 - (1 - self.k) * v)


# ------------------------------------------------------------------ kinetic headline
class Headline(Layer):
    """Big pop-in words. lines = [[(word, accent_bool), ...], ...]"""

    def __init__(self, t0, t1, lines, size=150, anchor="left", x=90, y=210, stagger=0.13, line_gap=0.98, shade=0.5,
                 exit_dur=0.25, delays=None, color_accent=((140, 240, 255), (30, 140, 255)), cx=None):
        self.cx = W / 2 if cx is None else cx
        self.t0, self.t1 = t0, t1
        self.lines, self.size, self.anchor, self.x, self.y = lines, size, anchor, x, y
        self.stagger, self.line_gap, self.shade, self.exit_dur = stagger, line_gap, shade, exit_dur
        self.delays = delays            # optional explicit per-word start times (flat list)
        self.color_accent = color_accent
        self._spr = {}

    def _sprite(self, word, accent):
        k = (word, accent)
        if k not in self._spr:
            st = max(6, self.size // 15)
            if accent:
                self._spr[k] = gfx.text_sprite(word, FONT_BLACK, self.size, stroke=st, stroke_fill=(5, 16, 44), gradient=self.color_accent,
                                               shadow=(0, 8), shadow_blur=8, shadow_alpha=0.65, glow=(20, 110, 255), glow_blur=self.size // 4, pad=self.size // 3)
            else:
                self._spr[k] = gfx.text_sprite(word, FONT_BLACK, self.size, fill=(255, 255, 255), stroke=st, stroke_fill=(5, 16, 44),
                                               shadow=(0, 8), shadow_blur=8, shadow_alpha=0.65, glow=(20, 110, 255), glow_blur=self.size // 4, pad=self.size // 3)
        return self._spr[k]

    def draw(self, frame, t):
        vis = ramp(t, self.t0, self.t0 + 0.2) * (1 - ramp(t, self.t1 - self.exit_dur, self.t1))
        if vis <= 0:
            return frame
        if self.shade and self.anchor in ("left", "right"):
            frame = gfx.shade_side(frame, self.anchor, 1000, self.shade * vis)
        pad = self.size // 3
        step = self.size * self.line_gap
        k = 0
        y = self.y
        for line in self.lines:
            sprites = [self._sprite(w, a) for w, a in line]
            gap = self.size * 0.2
            vis_w = [gfx.sprite_size(s)[0] - 2 * pad for s in sprites]
            total = sum(vis_w) + gap * (len(line) - 1)
            x = self.x if self.anchor == "left" else (self.x - total if self.anchor == "right" else self.cx - total / 2)
            for s, vw in zip(sprites, vis_w):
                ts = self.delays[k] if self.delays else self.t0 + k * self.stagger
                k += 1
                p = (t - ts) / 0.34
                if p < 0:
                    x += vw + gap
                    continue
                sc = lerp(0.35, 1.0, ease_out_back(p, 2.0))
                op = ramp(t, ts, ts + 0.12) * (1 - ramp(t, self.t1 - self.exit_dur, self.t1))
                rot = lerp(-5, 0, ease_out(p))
                out_sc = 1 + 0.06 * ramp(t, self.t1 - self.exit_dur, self.t1)
                cx = x - pad + (vw + 2 * pad) / 2
                gfx.draw_sprite(frame, s, cx, y + (self.size * 0.55), scale=sc * out_sc, opacity=op, rot=rot)
                x += vw + gap
            y += step
        return frame


# ------------------------------------------------------------------ count-up number
class CountUp(Layer):
    def __init__(self, t0, t1, target=100, size=330, x=W / 2, y=380, label=None, count_dur=0.9):
        self.t0, self.t1, self.target, self.size, self.x, self.y = t0, t1, target, size, x, y
        self.label, self.count_dur = label, count_dur
        self._spr = {}

    def _num(self, n):
        if n not in self._spr:
            self._spr[n] = gfx.text_sprite(str(n), FONT_BLACK, self.size, stroke=self.size // 14, stroke_fill=(5, 16, 44),
                                           gradient=((150, 245, 255), (30, 140, 255)), shadow=(0, 10), shadow_blur=10, shadow_alpha=0.7,
                                           glow=(20, 110, 255), glow_blur=self.size // 4)
        return self._spr[n]

    def draw(self, frame, t):
        vis = ramp(t, self.t0, self.t0 + 0.18) * (1 - ramp(t, self.t1 - 0.25, self.t1))
        if vis <= 0:
            return frame
        p = ease_out(ramp(t, self.t0 + 0.1, self.t0 + 0.1 + self.count_dur))
        n = int(round(self.target * p))
        n = min(self.target, (n // 4) * 4 if n < self.target else n)
        pop = ease_out_back(ramp(t, self.t0, self.t0 + 0.4), 2.2)
        gfx.draw_sprite(frame, self._num(n), self.x, self.y, scale=lerp(0.5, 1.0, pop) * (1 + 0.03 * math.sin((t - self.t0) * 6)), opacity=vis)
        return frame


# ------------------------------------------------------------------ CTA: subscribe
def _ripple(frame, cx, cy, age, color=(255, 255, 255), max_r=120, dur=0.6, thick=6):
    if age < 0 or age > dur:
        return
    p = age / dur
    r = int(max_r * ease_out(p))
    a = (1 - p) ** 1.5
    ov = frame.copy()
    cv2.circle(ov, (int(cx), int(cy)), max(r, 1), color, thick, cv2.LINE_AA)
    cv2.addWeighted(ov, a, frame, 1 - a, 0, frame)


class SubscribeCTA(Layer):
    """big red SUBSCRIBE pill -> cursor click -> SUBSCRIBED + ringing bell"""

    def __init__(self, t0, t1, cx=420, cy=300, scale=1.0, click=None):
        self.t0, self.t1, self.cx, self.cy, self.sc = t0, t1, cx, cy, scale
        self.click = click

    def draw(self, frame, t):
        a = t - self.t0
        dur = self.t1 - self.t0
        enter = ease_out_back(ramp(a, 0, 0.42), 1.9)
        leave = 1 - ramp(t, self.t1 - 0.3, self.t1)
        op = clamp(a / 0.2) * leave
        if op <= 0:
            return frame
        click_t = self.click if self.click is not None else min(1.25, dur - 1.6)
        clicked = a >= click_t
        sc = self.sc * lerp(0.55, 1.0, enter) * (1 + (0.035 * math.sin(a * 7) if not clicked else 0))
        if click_t <= a < click_t + 0.14:
            sc *= 1 - 0.07 * math.sin((a - click_t) / 0.14 * math.pi)
        sc *= 1 - 0.1 * (1 - leave)
        cy = self.cy + (1 - enter) * 50
        spr = asset("cta_subscribed" if clicked else "cta_subscribe")
        # soft glow behind
        gfx.draw_sprite(frame, spr, self.cx, cy, scale=sc, opacity=op)
        w, h = gfx.sprite_size(spr)
        # bell on the right once subscribed
        if clicked:
            ba = a - click_t
            bell = asset("bell_gold")
            ang = 24 * math.exp(-ba * 2.2) * math.sin(ba * 24)
            bs = self.sc * (0.2 + 0.8 * ease_out_back(ramp(ba, 0, 0.3), 2.5))
            gfx.draw_sprite(frame, bell, self.cx + w * sc / 2 + 30 * self.sc, cy - 24 * self.sc, scale=bs, opacity=op, rot=ang)
            _ripple(frame, self.cx + 140 * self.sc, cy, ba, (255, 255, 255), max_r=int(150 * self.sc))
        # cursor travelling to the button
        if a < click_t + 0.5:
            cur = asset("cursor")
            p = ease_in_out(ramp(a, click_t - 0.55, click_t))
            sx, sy = self.cx + 380 * self.sc, cy + 230 * self.sc
            tx, ty = self.cx + 150 * self.sc, cy + 10 * self.sc
            px, py = lerp(sx, tx, p), lerp(sy, ty, p)
            cop = ramp(a, click_t - 0.7, click_t - 0.45) * (1 - ramp(a, click_t + 0.3, click_t + 0.5)) * op
            gfx.draw_sprite(frame, cur, px + 30, py + 36, scale=self.sc * (1 - 0.1 * (click_t <= a < click_t + 0.12)), opacity=cop, anchor="c")
        return frame


# ------------------------------------------------------------------ CTA: engage pills
class EngagePill(Layer):
    """LIKE / COMMENT / SHARE pill that pops when the word is spoken"""

    def __init__(self, kind, t0, t1, cx, cy, scale=1.0):
        self.kind, self.t0, self.t1, self.cx, self.cy, self.sc = kind, t0, t1, cx, cy, scale

    def draw(self, frame, t):
        a = t - self.t0
        leave = 1 - ramp(t, self.t1 - 0.28, self.t1)
        op = clamp(a / 0.12) * leave
        if op <= 0:
            return frame
        pop = ease_out_back(ramp(a, 0, 0.38), 2.4)
        sc = self.sc * lerp(0.4, 1.0, pop) * (1 + 0.04 * math.sin(a * 6.5) * ramp(a, 0.4, 0.6))
        sc *= 1 - 0.12 * (1 - leave)
        rot = 6 * math.exp(-a * 5) * math.sin(a * 22)
        spr = asset("cta_" + self.kind)
        w, h = gfx.sprite_size(spr)
        # flash ring at the moment of the spoken word
        if a < 0.55:
            p = a / 0.55
            ring = int(w * sc * (0.55 + 0.25 * ease_out(p)))
            ov = frame.copy()
            cv2.ellipse(ov, (int(self.cx), int(self.cy)), (int(w * sc / 2 * (1.04 + 0.10 * ease_out(p))), int(h * sc / 2 * (1.1 + 0.28 * ease_out(p)))), 0, 0, 360, (255, 255, 255), 5, cv2.LINE_AA)
            al = (1 - p) * 0.8
            cv2.addWeighted(ov, al, frame, 1 - al, 0, frame)
        gfx.draw_sprite(frame, spr, self.cx, self.cy + (1 - pop) * 30, scale=sc, opacity=op, rot=rot)
        return frame


class LinkBelow(Layer):
    """'LINK BELOW' badge with a bouncing arrow feel"""

    def __init__(self, t0, t1, cx=W / 2, cy=860, scale=1.0):
        self.t0, self.t1, self.cx, self.cy, self.sc = t0, t1, cx, cy, scale

    def draw(self, frame, t):
        a = t - self.t0
        leave = 1 - ramp(t, self.t1 - 0.25, self.t1)
        op = clamp(a / 0.15) * leave
        if op <= 0:
            return frame
        pop = ease_out_back(ramp(a, 0, 0.4), 2.0)
        bounce = 10 * abs(math.sin(a * 5))
        gfx.draw_sprite(frame, asset("badge_link"), self.cx, self.cy - bounce + (1 - pop) * 30, scale=self.sc * lerp(0.5, 1.0, pop), opacity=op)
        return frame


# ------------------------------------------------------------------ logo (always on) + reveal
class Logo:
    """Channel logo: top-right watermark from the first to the last frame; flies to the centre for the
    'Welcome to Mega Byte' moment and back."""

    def __init__(self, reveal=None, corner=(1822, 98), corner_size=128, center=(W / 2, 395, 470)):
        self.center = center
        raw = gfx.sprite_from_png(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png"))
        base = 560
        self.base = gfx.scale_sprite(raw, base / gfx.sprite_size(raw)[0])
        self.corner, self.corner_size = corner, corner_size
        self.reveal = reveal            # (t_start, t_hold_end) or None
        self._shadow = None

    def state(self, t):
        cx, cy = self.corner
        size = self.corner_size
        if self.reveal:
            r0, r1 = self.reveal
            fly_in = ease_out_back(ramp(t, r0, r0 + 0.6), 1.5)
            fly_out = ease_in_out(ramp(t, r1, r1 + 0.7))
            tx, ty, ts = self.center
            if t < r0 + 0.6 or t < r1:
                p = fly_in
                cx, cy, size = lerp(cx, tx, p), lerp(cy, ty, p), lerp(size, ts, p)
                if t >= r0 + 0.6:
                    cy += 7 * math.sin((t - r0) * 3.2)
            else:
                cx, cy, size = lerp(tx, cx, fly_out), lerp(ty, cy, fly_out), lerp(ts, size, fly_out)
        return cx, cy, size

    def draw(self, frame, t):
        cx, cy, size = self.state(t)
        sc = size / gfx.sprite_size(self.base)[0]
        # drop shadow (cheap: darker, blurred, offset copy)
        if self._shadow is None:
            a = self.base["a"]
            sh = cv2.GaussianBlur(a, (0, 0), 14)
            self._shadow = {"pm": np.zeros_like(self.base["pm"]), "a": (sh * 0.55).astype(np.uint8)}
        big = size > 200
        if big and self.reveal:
            r0 = self.reveal[0]
            # rings radiating from the logo during the reveal
            for k in range(3):
                age = t - (r0 + 0.55 + k * 0.28)
                if 0 <= age < 1.0:
                    p = age / 1.0
                    ov = frame.copy()
                    cv2.circle(ov, (int(cx), int(cy)), int(size * 0.5 + 330 * ease_out(p)), (60, 200, 255), 4, cv2.LINE_AA)
                    al = (1 - p) * 0.75
                    cv2.addWeighted(ov, al, frame, 1 - al, 0, frame)
        gfx.draw_sprite(frame, self._shadow, cx + 3, cy + 6, scale=sc)
        gfx.draw_sprite(frame, self.base, cx, cy, scale=sc)
        return frame


class TitleCard(Layer):
    """small kicker + large gradient title under the logo (used for 'Welcome to Mega Byte')"""

    def __init__(self, t0, t1, kicker, title, y=745):
        self.t0, self.t1, self.kicker, self.title, self.y = t0, t1, kicker, title, y
        self._k = gfx.text_sprite(kicker, FONT_XBOLD, 54, fill=(230, 240, 255), stroke=5, stroke_fill=(5, 16, 44), shadow=(0, 5), shadow_blur=5)
        self._t = gfx.text_sprite(title, FONT_BLACK, 150, stroke=10, stroke_fill=(5, 16, 44), gradient=((170, 248, 255), (30, 140, 255)),
                                  shadow=(0, 9), shadow_blur=9, shadow_alpha=0.7, glow=(20, 110, 255), glow_blur=34)

    def draw(self, frame, t):
        a = t - self.t0
        op = clamp(a / 0.25) * (1 - ramp(t, self.t1 - 0.3, self.t1))
        if op <= 0:
            return frame
        e = ease_out_back(ramp(a, 0, 0.5), 1.6)
        gfx.draw_sprite(frame, self._k, W / 2, self.y - 90 + (1 - e) * 40, scale=1.0, opacity=op)
        gfx.draw_sprite(frame, self._t, W / 2, self.y + (1 - e) * 60, scale=lerp(0.7, 1.0, e), opacity=op)
        return frame
