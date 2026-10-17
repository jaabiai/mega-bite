"""9:16 (1080x1920) scenes for the Reels / Shorts cut.  Time inside a reel scene is *reel time*; every scene maps it to the
original narration time (`src0 + t - r0`) so the demo highlights / captions defined for the long video are reused as-is."""
import functools
import math
import os

import cv2
import numpy as np

from . import gfx, grade
from .common import (W, H, FPS, FONT_BLACK, FONT_XBOLD, clamp, ramp, lerp, ease_out, ease_in_out, ease_out_back, smooth)
from .scenes import DemoScene, chip_sprite, _broll_lut, SR_W, SR_H
from .sources import PipeReader

RW, RH = 1080, 1920
VIEW_ASPECT = RH / RW


@functools.lru_cache(maxsize=1)
def _shade_gain():
    """dark gradients top (logo / title) and bottom (captions) so white text stays readable on any footage"""
    yy = np.arange(RH, dtype=np.float32)
    s = lambda a, b: np.clip((yy - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((yy - a) / (b - a), 0, 1))
    g = 1 - 0.58 * s(1000, 1700) - 0.32 * (1 - s(0, 360))
    col = (np.clip(g, 0, 1) * 255).astype(np.uint8)
    return cv2.merge([np.tile(col[:, None], (1, RW))] * 3)


def shade(img):
    return cv2.multiply(img, _shade_gain(), scale=1 / 255.0)


def pop_factor(t, r0, amount=0.07, dur=0.32):
    return 1 + amount * (1 - ease_out(ramp(t, r0, r0 + dur)))


# ====================================================================== talking head
class ReelTH:
    kind = "th"

    def __init__(self, r0, r1, src0, zoom=(1.0, 1.06), cx=0.5, cy=0.5):
        self.t0, self.t1, self.src0, self.zoom, self.cx, self.cy = r0, r1, src0, zoom, cx, cy

    def render(self, ctx, t):
        ts = self.src0 + (t - self.t0)
        f = ctx.main.graded(int(round(ts * FPS)))
        z = lerp(self.zoom[0], self.zoom[1], ramp(t, self.t0, self.t1)) * pop_factor(t, self.t0)
        ch = H / z
        cw = ch * RW / RH
        x0 = clamp(self.cx * W - cw / 2, 0, W - cw)
        y0 = clamp(self.cy * H - ch / 2, 0, H - ch)
        img = gfx.crop_zoom(f, (x0, y0, cw, ch), RW, RH)
        img = grade.sharpen(img, 0.22, 1.6)
        return shade(img)


# ====================================================================== b-roll
class ReelBroll:
    kind = "broll"

    def __init__(self, r0, r1, clip, start=0.4, zoom=(1.0, 1.1), cx=0.5):
        self.t0, self.t1, self.clip, self.start, self.zoom, self.cx = r0, r1, clip, start, zoom, cx

    def render(self, ctx, t):
        from .common import WORK
        path = os.path.join(WORK, f"broll/hd/{self.clip}.mp4")
        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        r = ctx.reader(id(self), path, self.start, vf)
        f = r.get(int(round((t - self.t0) * FPS)))
        if f is None:
            f = np.zeros((H, W, 3), np.uint8)
        z = lerp(self.zoom[0], self.zoom[1], ramp(t, self.t0, self.t1)) * pop_factor(t, self.t0)
        ch = H / z
        cw = ch * RW / RH
        x0 = clamp(self.cx * W - cw / 2, 0, W - cw)
        img = gfx.crop_zoom(f, (x0, (H - ch) / 2, cw, ch), RW, RH)
        img = grade.apply_lut(img, _broll_lut())
        return shade(gfx.darken(img, 0.85))


# ====================================================================== screen demo (full-bleed, camera follows the highlight)
@functools.lru_cache(maxsize=64)
def reel_title(text):
    size = 96
    while size > 44 and gfx.text_width(text, FONT_BLACK, size) > 940:
        size -= 4
    return gfx.text_sprite(text, FONT_BLACK, size, fill=(255, 255, 255), stroke=max(5, size // 16), stroke_fill=(5, 16, 44),
                           shadow=(0, 7), shadow_blur=7, shadow_alpha=0.6, glow=(20, 110, 255), glow_blur=size // 4, pad=size // 4), size


class ReelDemo:
    kind = "demo"

    def __init__(self, r0, r1, src0, tl, hls_all, cam=(), titles=None):
        self.t0, self.t1, self.src0, self.tl = r0, r1, src0, tl
        self.hls_all = hls_all
        self.cam = cam                    # [(src_t0, src_t1, rect)] - frame this rect instead of the current highlight
        self.titles = titles or {}
        self.helper = DemoScene(0, 0, tl)
        self._cache = {}

    @staticmethod
    def cam_rect(rect):
        x, y, w, h = rect
        cw = clamp(max(w * 1.45, 900.0), 900.0, float(SR_W))
        ch = cw * VIEW_ASPECT
        while h * 1.5 > ch * 0.45 and cw < SR_W:
            cw = min(cw * 1.1, SR_W)
            ch = cw * VIEW_ASPECT
        cx, cy = x + w / 2, y + h / 2
        return (clamp(cx - cw / 2, 0, SR_W - cw), clamp(cy - 0.40 * ch, -0.22 * ch, SR_H - ch), cw, ch)

    def camera(self, T):
        hls = self.hls_all
        k = 0
        for i, h in enumerate(hls):
            if h.t0 <= T + 0.02:
                k = i
        cur = hls[k]
        for a, b, rect in self.cam:
            if a <= T <= b:
                return self.cam_rect(rect)
        crop = self.cam_rect(cur.rect_at(T))
        if k > 0 and cur.t0 >= self.src0 - 0.01:                  # ease from the previous highlight (only inside this clip)
            p = ease_in_out(ramp(T, cur.t0, cur.t0 + 0.45))
            if p < 1:
                prev = self.cam_rect(hls[k - 1].rect_at(T))
                crop = tuple(lerp(a, b, p) for a, b in zip(prev, crop))
        return crop

    def _ring(self, w, h):
        k = (w // 4, h // 4)
        if k not in self._cache:
            self._cache[k] = gfx.ring_sprite(w, h, 26, 6, (46, 214, 255), glow=16, glow_strength=1.0)
        return self._cache[k]

    def render(self, ctx, t):
        T = self.src0 + (t - self.t0)
        sr = self.helper._screen(ctx, T)
        x0, y0, cw, ch = self.camera(T)
        pf = pop_factor(t, self.t0, 0.06, 0.3)                      # punch-in at the start of every clip
        cxm, cym = x0 + cw / 2, y0 + ch / 2
        cw2, ch2 = cw / pf, ch / pf
        x0, y0 = clamp(cxm - cw2 / 2, 0, SR_W - cw2), clamp(cym - ch2 / 2, -0.22 * ch2, SR_H - ch2)
        cw, ch = cw2, ch2
        view = gfx.crop_zoom(sr, (x0, y0, cw, ch), RW, RH)
        sc = RW / cw
        hls = [h for h in self.hls_all if h.t0 - 0.05 <= T <= h.t1 + 0.25]
        spot = [h for h in hls if h.spot]
        if spot:
            vis = max(ramp(T, h.t0 - 0.05, h.t0 + 0.25) * (1 - ramp(T, h.t1 + 0.05, h.t1 + 0.3)) for h in spot)
            if vis > 0.01:
                m = np.zeros((RH // 4, RW // 4), np.float32)
                for h in spot:
                    x, y, w, hh = h.rect_at(T)
                    a, b = int(((x - x0) * sc - 18) / 4), int(((y - y0) * sc - 18) / 4)
                    c, d = int(((x + w - x0) * sc + 18) / 4), int(((y + hh - y0) * sc + 18) / 4)
                    cv2.rectangle(m, (a, b), (c, d), 1.0, -1)
                m = cv2.GaussianBlur(m, (0, 0), 5)
                m = cv2.resize(m, (RW, RH), interpolation=cv2.INTER_LINEAR)
                gain = (1 - 0.55 * vis * (1 - m))[..., None]
                view = np.clip(view.astype(np.float32) * gain, 0, 255).astype(np.uint8)
        view = np.ascontiguousarray(view)
        newest = max(hls, key=lambda h: h.t0) if hls else None
        for h in hls:
            if not h.ring:
                continue
            vis = ramp(T, h.t0 - 0.05, h.t0 + 0.2) * (1 - ramp(T, h.t1 + 0.05, h.t1 + 0.25))
            if vis <= 0.01:
                continue
            x, y, w, hh = h.rect_at(T)
            pulse = 1 + 0.025 * math.sin(T * 9)
            rw, rh = int(w * sc * pulse) + 26, int(hh * sc * pulse) + 26
            cx, cy = (x + w / 2 - x0) * sc, (y + hh / 2 - y0) * sc
            spr, pad = self._ring(rw, rh)
            gfx.blit(view, spr, cx - rw / 2 - pad, cy - rh / 2 - pad, vis)
            if h.tap is not None:
                self.helper._tap(view, cx, cy, T - h.tap, 0.5)
            if h.label and h is newest:
                chip = chip_sprite(h.label, size=40, bg=((20, 30, 60), (8, 16, 40)), fg=(120, 235, 255))
                cw_chip = gfx.sprite_size(chip)[0]
                ccx = clamp(cx, cw_chip / 2 + 30, RW - cw_chip / 2 - 30)
                ccy = clamp(cy + rh / 2 + 52, 200, 1330)
                gfx.draw_sprite(view, chip, ccx, ccy, opacity=vis * ramp(T, h.t0, h.t0 + 0.25))
        view = shade(view)
        # title block (top)
        step = self.tl.step_at(T)
        if step:
            a = T - step.t0
            e = ease_out_back(ramp(a, 0, 0.4), 1.5)
            op = clamp(a / 0.18)
            chip_txt, title_txt = self.titles.get(step.title, (step.chip, step.title))
            gfx.draw_sprite(view, chip_sprite(chip_txt), 70 + (1 - e) * -50, 262, opacity=op, anchor="l")
            spr, size = reel_title(title_txt)
            gfx.blit(view, spr, 70 - size // 4 + (1 - e) * -70, 290, op)
        return view


# ====================================================================== end card
class EndCard:
    """'Full video on YouTube - MEGA BYTE' card (Manglish/Malayalam text) that builds up over the last seconds"""

    def __init__(self, t0, t1):
        from .overlays import asset
        self.t0, self.t1 = t0, t1
        self._asset = asset
        self._name = gfx.text_sprite("MEGA BYTE", FONT_BLACK, 150, stroke=10, stroke_fill=(5, 16, 44), gradient=((170, 248, 255), (30, 140, 255)),
                                     shadow=(0, 9), shadow_blur=9, shadow_alpha=0.7, glow=(20, 110, 255), glow_blur=34)

    def active(self, t):
        return self.t0 - 0.01 <= t <= self.t1 + 0.5

    def draw(self, frame, t):
        a = t - self.t0
        asset = self._asset

        def pop(delay, dur=0.45):
            return ease_out_back(ramp(a, delay, delay + dur), 1.8)

        e = pop(0.25)
        gfx.draw_sprite(frame, self._name, RW / 2, 640 + (1 - e) * 50, scale=lerp(0.7, 1, e), opacity=ramp(a, 0.25, 0.4))
        e = pop(0.4)
        gfx.draw_sprite(frame, asset("reel_ml_name"), RW / 2, 770 + (1 - e) * 30, scale=0.72 * lerp(0.7, 1, e), opacity=ramp(a, 0.4, 0.6))
        e = pop(0.6)
        gfx.draw_sprite(frame, asset("reel_ml"), RW / 2, 985 + (1 - e) * 30, scale=1.0, opacity=ramp(a, 0.6, 0.85))
        e = pop(0.85)
        gfx.draw_sprite(frame, asset("reel_fullvideo"), RW / 2, 1165 + (1 - e) * 40, scale=0.8 * lerp(0.6, 1, e), opacity=ramp(a, 0.85, 1.0))
        return frame
