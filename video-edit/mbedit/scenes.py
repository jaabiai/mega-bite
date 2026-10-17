"""Scene renderers (talking head, B-roll, screen-recording demo) and transitions."""
import functools
import math
import os

import cv2
import numpy as np

from . import gfx, grade
from .common import (WORK, W, H, FPS, NF, FONT_BLACK, FONT_XBOLD, FONT_BOLD, CYAN, BLUE, NAVY, clamp, ramp, lerp,
                     ease_out, ease_in_out, ease_out_back, smooth)
from .sources import PipeReader

SR_W, SR_H = 1320, 2868
SDR = os.path.join(WORK, "work/screen_sdr.mp4")


# ====================================================================== context
class Ctx:
    def __init__(self):
        from .sources import MainSource
        self.main = MainSource()
        self.screen = PipeReader(SDR, SR_W, SR_H)
        self.screen2 = PipeReader(SDR, SR_W, SR_H)
        self.readers = {}
        self.extra = {}

    def reader(self, key, path, offset, vf):
        if key not in self.readers:
            self.readers[key] = PipeReader(path, W, H, vf=vf, offset=offset)
        return self.readers[key]

    def gc(self, t, scenes):
        for sc in scenes:
            r = self.readers.get(id(sc))
            if r is not None and t > sc.t1 + 2.5:
                r.close()
                del self.readers[id(sc)]

    def close(self):
        self.main.close()
        self.screen.close()
        self.screen2.close()
        for r in self.readers.values():
            r.close()


# ====================================================================== talking head
class THScene:
    kind = "th"

    def __init__(self, t0, t1, zoom=(1.0, 1.0), center=(0.5, 0.42), shake=0.0):
        self.t0, self.t1, self.zoom, self.center = t0, t1, zoom, center

    def render(self, ctx, t):
        idx = int(round(t * FPS))
        f = ctx.main.graded(idx)
        z = lerp(self.zoom[0], self.zoom[1], ease_in_out(ramp(t, self.t0, self.t1)))
        if z > 1.001:
            f = gfx.cover_resize(f, W, H, zoom=z, cx=self.center[0], cy=self.center[1])
        return f


# ====================================================================== b-roll
@functools.lru_cache(maxsize=1)
def _broll_lut():
    x = np.arange(256, dtype=np.float32) / 255
    s = np.clip(x + 0.16 * (x - 0.5) * (1 - np.abs(2 * x - 1) ** 1.6), 0, 1) * 0.97 + 0.015
    return grade._lut_rgb(s * 0.98, s, np.clip(s * 1.05, 0, 1))


class BrollScene:
    kind = "broll"

    def __init__(self, t0, t1, clip, start=0.6, zoom=(1.0, 1.08), center=(0.5, 0.5), dim=0.82, side_shade=None):
        self.t0, self.t1, self.clip, self.start, self.zoom, self.center, self.dim = t0, t1, clip, start, zoom, center, dim
        self.side_shade = side_shade
        self.path = os.path.join(WORK, f"broll/hd/{clip}.mp4")

    def render(self, ctx, t):
        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        r = ctx.reader(id(self), self.path, self.start, vf)
        f = r.get(int(round((t - self.t0) * FPS)))
        if f is None:
            f = np.zeros((H, W, 3), np.uint8)
        z = lerp(self.zoom[0], self.zoom[1], ease_in_out(ramp(t, self.t0 - 0.3, self.t1 + 0.3)))
        if z > 1.001:
            f = gfx.cover_resize(f, W, H, zoom=z, cx=self.center[0], cy=self.center[1])
        f = grade.apply_lut(f, _broll_lut())
        f = gfx.apply_gain_map(f, gfx.VIG)
        f = gfx.darken(f, self.dim)
        if self.side_shade:
            f = gfx.shade_side(f, self.side_shade, 1000, 0.5)
        return f


# ====================================================================== demo (screen recording)
PH = dict(x=1196, y=104, w=405, h=880)          # phone screen rectangle (SR is 1320x2868 -> 405x880)
PHK = PH["w"] / SR_W
CARD = dict(x=90, y=326, w=1000, h=500)
PIP = dict(cx=1768, cy=650, r=118)
CARD_ASPECT = CARD["w"] / CARD["h"]


def _fit_title(text, max_w=1000, max_size=104):
    size = max_size
    while size > 40 and gfx.text_width(text, FONT_BLACK, size) > max_w:
        size -= 4
    return size


@functools.lru_cache(maxsize=128)
def title_sprite(text):
    size = _fit_title(text)
    return gfx.text_sprite(text, FONT_BLACK, size, fill=(255, 255, 255), stroke=max(5, size // 16), stroke_fill=(5, 16, 44),
                           shadow=(0, 7), shadow_blur=7, shadow_alpha=0.6, glow=(20, 110, 255), glow_blur=size // 4, pad=size // 4), size


@functools.lru_cache(maxsize=128)
def chip_sprite(text, size=34, bg=((52, 170, 255), (24, 108, 240)), fg=(255, 255, 255), padx=26, pady=12):
    f = gfx.font(FONT_XBOLD, size)
    tw = int(f.getlength(text))
    asc, desc = f.getmetrics()
    w, h = tw + 2 * padx, asc + desc + 2 * pady
    base = np.zeros((h, w, 3), np.float32)
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    base[:] = np.array(bg[0], np.float32) * (1 - t) + np.array(bg[1], np.float32) * t
    m = gfx.rr_mask(w, h, h // 2)
    from PIL import Image, ImageDraw
    txt = Image.new("L", (w, h), 0)
    ImageDraw.Draw(txt).text((padx, pady), text, font=f, fill=255)
    tm = np.asarray(txt, np.float32)[..., None] / 255
    rgb = base * (1 - tm) + np.array(fg, np.float32) * tm
    a = (m * 255).astype(np.uint8)
    pm = (rgb * m[..., None]).astype(np.uint8)
    # soft shadow
    return {"pm": pm, "a": a}


def _crop_rect_for(rect):
    """zoom-card crop (x,y,w,h in SR px) that frames `rect` with comfortable padding at the card aspect ratio"""
    x, y, w, h = rect
    cw = max(w * 1.30, 680.0)
    ch = cw / CARD_ASPECT
    if ch < h * 1.45:
        ch = h * 1.45
        cw = ch * CARD_ASPECT
    if cw > SR_W:
        cw = float(SR_W)
        ch = cw / CARD_ASPECT
    cx, cy = x + w / 2, y + h / 2
    x0 = clamp(cx - cw / 2, 0, SR_W - cw)
    y0 = clamp(cy - ch / 2, 0, SR_H - ch)
    return (x0, y0, cw, ch)


class Hl:
    """a highlighted UI element in SR pixel coordinates"""

    def __init__(self, t0, t1, rect, label=None, tap=None, ring=True, spot=True, rect_keys=None):
        self.t0, self.t1, self.rect, self.label, self.tap = t0, t1, rect, label, tap
        self.ring, self.spot, self.rect_keys = ring, spot, rect_keys

    def rect_at(self, t):
        if not self.rect_keys:
            return self.rect
        ts = [k[0] for k in self.rect_keys]
        return tuple(float(np.interp(t, ts, [k[1][i] for k in self.rect_keys])) for i in range(4))


class Step:
    def __init__(self, t0, t1, chip, title, hls):
        self.t0, self.t1, self.chip, self.title, self.hls = t0, t1, chip, title, hls


class DemoTimeline:
    """Shared screen-recording time-warp (narration time T -> screen-recording time S), privacy blurs and steps."""

    def __init__(self, segs, steps, privacy):
        self.segs = segs          # list of (T0, T1, S0, S1) linear segments, sorted by T0 (gaps are fine)
        self.steps = steps
        self.privacy = privacy    # list of (S0, S1, [rects])

    def S(self, T):
        """returns (S_a, S_b, mix) - normally S_a == S_b; around a jump the two frames are cross-faded"""
        segs = self.segs
        i = 0
        for k, (T0, T1, S0, S1) in enumerate(segs):
            if T0 <= T + 1e-9:
                i = k
        T0, T1, S0, S1 = segs[i]
        Tc = min(T, T1)
        s = S0 + (S1 - S0) * (Tc - T0) / max(T1 - T0, 1e-9)
        if i > 0:                                  # first 0.1 s after a jump: fade from the previous screen
            pS1 = segs[i - 1][3]
            if abs(S0 - pS1) > 0.4 and T - T0 < 0.1:
                return pS1, s, 0.5 + (T - T0) / 0.2
        if i + 1 < len(segs):                      # last 0.1 s before a jump: start fading to the next screen
            nT0, nS0 = segs[i + 1][0], segs[i + 1][2]
            if abs(nS0 - S1) > 0.4 and 0 < nT0 - T < 0.1:
                return s, nS0, 0.5 - (nT0 - T) / 0.2
        return s, s, 0.0

    def step_at(self, T):
        cur = None
        for st in self.steps:
            if st.t0 - 0.02 <= T:
                cur = st
        return cur


class DemoScene:
    kind = "demo"

    def __init__(self, t0, t1, tl):
        self.t0, self.t1, self.tl = t0, t1, tl
        self._static = None
        self._ph_cache = {}

    # ---------------------------------------------------------- static layers
    def _statics(self):
        if self._static is not None:
            return self._static
        # background gradient
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.clip((xx / W) * 0.55 + (yy / H) * 0.45, 0, 1)
        c0, c1 = np.array((8, 18, 46), np.float32), np.array((6, 40, 98), np.float32)
        grad = c0[None, None, :] * (1 - d[..., None]) + c1[None, None, :] * d[..., None]
        # glow behind the phone
        g = np.exp(-(((xx - (PH["x"] + PH["w"] / 2)) / 420) ** 2 + ((yy - (PH["y"] + PH["h"] / 2)) / 560) ** 2))
        grad = grad + g[..., None] * np.array((10, 70, 150), np.float32)[None, None, :] * 0.9
        g2 = np.exp(-(((xx - 560) / 700) ** 2 + ((yy - 560) / 520) ** 2))
        grad = grad + g2[..., None] * np.array((4, 24, 60), np.float32)[None, None, :]
        bg = np.clip(grad, 0, 255).astype(np.uint8)
        # phone body
        bez = 15
        body = gfx.solid_sprite(PH["w"] + 2 * bez, PH["h"] + 2 * bez, (12, 16, 28), r=64)
        ring, rp = gfx.ring_sprite(PH["w"] + 2 * bez, PH["h"] + 2 * bez, 64, 3, (110, 170, 255), glow=22, glow_strength=0.55)
        shadow, sp = gfx.glow_sprite(PH["w"] + 2 * bez, PH["h"] + 2 * bez, 64, (0, 0, 0), 26, 0.8)
        # zoom card chrome
        cring, cp = gfx.ring_sprite(CARD["w"], CARD["h"], 34, 4, (46, 214, 255), glow=22, glow_strength=0.9)
        cshadow, csp = gfx.glow_sprite(CARD["w"], CARD["h"], 34, (0, 0, 0), 24, 0.85)
        # PiP chrome
        d2 = PIP["r"] * 2
        pm = np.zeros((d2, d2), np.float32)
        cv2.circle(pm, (PIP["r"], PIP["r"]), PIP["r"] - 4, 1.0, -1, cv2.LINE_AA)
        pipring, pp = gfx.ring_sprite(d2 - 6, d2 - 6, PIP["r"] - 3, 5, (46, 214, 255), glow=14, glow_strength=0.8)
        self._static = dict(bg=bg, body=body, bez=bez, ring=ring, rp=rp, shadow=shadow, sp=sp, cring=cring, cp=cp,
                            cshadow=cshadow, csp=csp, pipmask=pm, pipring=pipring, pp=pp)
        return self._static

    # ---------------------------------------------------------- screen frames
    def _sr(self, ctx, S, reader):
        fr = reader.get(int(round(S * FPS)))
        if fr is None:
            fr = np.zeros((SR_H, SR_W, 3), np.uint8)
        for (s0, s1, rects) in self.tl.privacy:
            if s0 <= S <= s1:
                fr = np.array(fr)          # writable copy
                for r in rects:
                    gfx.box_blur_region(fr, r, 22, feather=20)
        return fr

    def _screen(self, ctx, T):
        Sa, Sb, mix = self.tl.S(T)
        fa = self._sr(ctx, Sa, ctx.screen)
        if mix > 0.01 and abs(Sa - Sb) > 0.01:
            fb = self._sr(ctx, Sb, ctx.screen2)
            return gfx.blend(fa, fb, mix)
        return fa

    # ---------------------------------------------------------- render
    def render(self, ctx, T):
        st = self._statics()
        idx = int(round(T * FPS))
        raw = ctx.main.raw(idx)
        # animated soft background from the presenter footage
        small = cv2.GaussianBlur(cv2.resize(raw, (192, 108), interpolation=cv2.INTER_AREA), (0, 0), 3)
        amb = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
        frame = cv2.addWeighted(st["bg"], 0.82, gfx.darken(amb, 0.38), 0.55, 0)
        sr = self._screen(ctx, T)
        step = self.tl.step_at(T)

        # ---- highlights active now
        hls = step.hls if step else []
        active = [h for h in hls if h.t0 - 0.05 <= T <= h.t1 + 0.25]
        cur = None
        for h in hls:
            if h.t0 <= T + 0.02:
                cur = h
        if cur is None and hls:
            cur = hls[0]

        # ---- phone
        bez = st["bez"]
        gfx.blit(frame, st["shadow"], PH["x"] - bez - st["sp"] + 8, PH["y"] - bez - st["sp"] + 18, 0.9)
        gfx.blit(frame, st["body"], PH["x"] - bez, PH["y"] - bez)
        scr = cv2.resize(sr, (PH["w"], PH["h"]), interpolation=cv2.INTER_AREA)
        spot = 0.0
        if active:
            spot = max(ramp(T, h.t0 - 0.05, h.t0 + 0.25) * (1 - ramp(T, h.t1 + 0.05, h.t1 + 0.3)) for h in active if h.spot) if any(h.spot for h in active) else 0.0
        if spot > 0.01:
            m = np.zeros((PH["h"], PH["w"]), np.float32)
            for h in active:
                if not h.spot:
                    continue
                x, y, w, hh = h.rect_at(T)
                pad = 10
                x0, y0 = int(x * PHK) - pad, int(y * PHK) - pad
                x1, y1 = int((x + w) * PHK) + pad, int((y + hh) * PHK) + pad
                cv2.rectangle(m, (max(x0, 0), max(y0, 0)), (min(x1, PH["w"] - 1), min(y1, PH["h"] - 1)), 1.0, -1)
            m = cv2.GaussianBlur(m, (0, 0), 7)
            gain = 1 - 0.5 * spot * (1 - m)
            scr = np.clip(scr.astype(np.float32) * gain[..., None], 0, 255).astype(np.uint8)
        gfx.paste_rounded(frame, scr, PH["x"], PH["y"], 48)
        gfx.blit(frame, st["ring"], PH["x"] - bez - st["rp"], PH["y"] - bez - st["rp"], 0.9)
        # rings on the phone
        for h in active:
            if not h.ring:
                continue
            vis = ramp(T, h.t0 - 0.05, h.t0 + 0.2) * (1 - ramp(T, h.t1 + 0.05, h.t1 + 0.25))
            if vis <= 0.01:
                continue
            x, y, w, hh = h.rect_at(T)
            pulse = 1 + 0.025 * math.sin(T * 9)
            rw, rh = int(w * PHK * pulse) + 14, int(hh * PHK * pulse) + 14
            cx, cy = PH["x"] + (x + w / 2) * PHK, PH["y"] + (y + hh / 2) * PHK
            spr, pad = self._ring(rw, rh, 12, 3)
            gfx.blit(frame, spr, cx - rw / 2 - pad, cy - rh / 2 - pad, vis)
            if h.tap is not None:
                self._tap(frame, cx, cy, T - h.tap, 0.5)

        # ---- zoom card
        if cur is not None:
            self._card(frame, sr, T, cur, hls)

        # ---- title block
        if step:
            a = T - step.t0
            e = ease_out_back(ramp(a, 0, 0.45), 1.5)
            op = clamp(a / 0.2)
            chip = chip_sprite(step.chip)
            gfx.draw_sprite(frame, chip, CARD["x"] + (1 - e) * -40, 128, opacity=op, anchor="l")
            spr, size = title_sprite(step.title)
            pad = size // 4
            gfx.blit(frame, spr, CARD["x"] - pad + (1 - e) * -60, 168, op)

        # ---- presenter face-cam
        self._pip(frame, raw, T)
        return frame

    # ---------------------------------------------------------- pieces
    def _ring(self, w, h, r, thick):
        k = (w // 4, h // 4, r, thick)
        if k not in self._ph_cache:
            self._ph_cache[k] = gfx.ring_sprite(w, h, r, thick, (46, 214, 255), glow=10, glow_strength=1.0)
        return self._ph_cache[k]

    def _tap(self, frame, cx, cy, age, dur):
        if age < -0.05 or age > dur + 0.3:
            return
        a = max(age, 0.0)
        ov = frame.copy()
        r1 = int(14 + 34 * ease_out(a / dur))
        al = clamp(1 - a / (dur + 0.3))
        cv2.circle(ov, (int(cx), int(cy)), r1, (255, 255, 255), 3, cv2.LINE_AA)
        # touch dot
        dot = int(16 * (1 - 0.35 * ramp(a, 0, 0.12)))
        cv2.circle(ov, (int(cx), int(cy)), dot, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.addWeighted(ov, 0.8 * al, frame, 1 - 0.8 * al, 0, frame)

    def _card(self, frame, sr, T, cur, hls):
        st = self._static
        # crop rect interpolates from the previous highlight to the current one
        idx = hls.index(cur)
        target = _crop_rect_for(cur.rect_at(T))
        p = ease_in_out(ramp(T, cur.t0, cur.t0 + 0.45))
        if idx > 0 and p < 1:
            prev = _crop_rect_for(hls[idx - 1].rect_at(T))
            crop = tuple(lerp(a, b, p) for a, b in zip(prev, target))
        else:
            crop = target
        vis = clamp((T - (self.t0 - 0.2)) / 0.3) if T < self.t0 + 0.3 else 1.0
        img = gfx.crop_zoom(sr, crop, CARD["w"], CARD["h"])
        gfx.blit(frame, st["cshadow"], CARD["x"] - st["csp"] + 6, CARD["y"] - st["csp"] + 14, 0.85)
        # slight lift/scale-in at the start of every new highlight
        gfx.paste_rounded(frame, img, CARD["x"], CARD["y"], 34)
        # ring around the element inside the card
        vis_ring = ramp(T, cur.t0 - 0.02, cur.t0 + 0.3) * (1 - ramp(T, cur.t1 + 0.1, cur.t1 + 0.35)) if cur.ring else 0.0
        if vis_ring > 0.01:
            x, y, w, hh = cur.rect_at(T)
            sc = CARD["w"] / crop[2]
            pulse = 1 + 0.02 * math.sin(T * 9)
            rw, rh = int(w * sc * pulse) + 18, int(hh * sc * pulse) + 18
            cx = CARD["x"] + ((x + w / 2) - crop[0]) * sc
            cy = CARD["y"] + ((y + hh / 2) - crop[1]) * sc
            # keep ring inside the card
            if rw < CARD["w"] and rh < CARD["h"]:
                spr, pad = self._ring_big(rw, rh)
                sub = frame[CARD["y"]:CARD["y"] + CARD["h"], CARD["x"]:CARD["x"] + CARD["w"]]
                gfx.blit(sub, spr, cx - CARD["x"] - rw / 2 - pad, cy - CARD["y"] - rh / 2 - pad, vis_ring)
                if cur.tap is not None:
                    sub2 = sub
                    self._tap(sub2, cx - CARD["x"], cy - CARD["y"], T - cur.tap, 0.5)
        gfx.blit(frame, st["cring"], CARD["x"] - st["cp"], CARD["y"] - st["cp"], 0.95)
        # label chip
        if cur.label:
            chip = chip_sprite(cur.label, size=36, bg=((20, 30, 60), (8, 16, 40)), fg=(120, 235, 255))
            op = ramp(T, cur.t0, cur.t0 + 0.25)
            gfx.draw_sprite(frame, chip, CARD["x"] + 26, CARD["y"] + CARD["h"] - 52, opacity=op, anchor="l")

    def _ring_big(self, w, h):
        k = ("big", w // 6, h // 6)
        if k not in self._ph_cache:
            self._ph_cache[k] = gfx.ring_sprite(w, h, 22, 6, (46, 214, 255), glow=14, glow_strength=1.0)
        return self._ph_cache[k]

    def _pip(self, frame, raw, T):
        st = self._static
        r = PIP["r"]
        cx0, cy0, half = 930, 380, 380
        crop = raw[cy0 - half:cy0 + half, cx0 - half:cx0 + half]
        img = cv2.resize(crop, (2 * r, 2 * r), interpolation=cv2.INTER_AREA)
        img = grade.apply_lut(img, grade.FG_LUT)
        a = (st["pipmask"] * 255).astype(np.uint8)
        spr = {"pm": (img.astype(np.uint16) * a[..., None] // 255).astype(np.uint8), "a": a}
        gfx.blit(frame, spr, PIP["cx"] - r, PIP["cy"] - r)
        gfx.blit(frame, st["pipring"], PIP["cx"] - (2 * r - 6) // 2 - st["pp"], PIP["cy"] - (2 * r - 6) // 2 - st["pp"])


# ====================================================================== result video (optional: user-supplied clip)
class ResultScene:
    """Large player showing the AI-generated clip (assets/result.mp4 in $MB_WORK) while the narration says 'see, the demo video'."""
    kind = "result"

    def __init__(self, t0, t1, path, start_at=None):
        self.t0, self.t1, self.path = t0, t1, path
        self.start_at = t0 if start_at is None else start_at
        self.demo = DemoScene(t0, t1, None)
        self._ph = {}

    def render(self, ctx, T):
        st = self.demo._statics()
        idx = int(round(T * FPS))
        raw = ctx.main.raw(idx)
        small = cv2.GaussianBlur(cv2.resize(raw, (192, 108), interpolation=cv2.INTER_AREA), (0, 0), 3)
        amb = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
        frame = cv2.addWeighted(st["bg"], 0.82, gfx.darken(amb, 0.38), 0.55, 0)
        pw, ph = 1180, 664
        x, y = 90, 236
        vf = "scale=1180:664:force_original_aspect_ratio=increase,crop=1180:664,loop=loop=-1:size=2000:start=0"
        key = ("res", id(self))
        if key not in ctx.readers:
            ctx.readers[key] = PipeReader(self.path, pw, ph, vf=vf.replace(",loop=loop=-1:size=2000:start=0", ""))
        r = ctx.readers[key]
        f = r.get(max(int(round((T - self.start_at) * FPS)), 0))
        if f is None:
            f = np.zeros((ph, pw, 3), np.uint8)
        card, cp = gfx.glow_sprite(pw, ph, 30, (46, 214, 255), 26, 0.9)
        gfx.blit(frame, card, x - cp, y - cp, ramp(T, self.t0, self.t0 + 0.3))
        gfx.paste_rounded(frame, np.array(f), x, y, 30)
        ring, rp = gfx.ring_sprite(pw, ph, 30, 4, (46, 214, 255), glow=18, glow_strength=0.9)
        gfx.blit(frame, ring, x - rp, y - rp, 0.95)
        a = T - self.t0
        e = ease_out_back(ramp(a, 0, 0.45), 1.5)
        chip = chip_sprite("THE RESULT")
        gfx.draw_sprite(frame, chip, x + (1 - e) * -40, 128, opacity=clamp(a / 0.2), anchor="l")
        spr, size = title_sprite("TORTOISE vs HARE RACE")
        gfx.blit(frame, spr, x - size // 4 + (1 - e) * -60, 150 - 0, clamp(a / 0.2))
        chip2 = chip_sprite("AI-GENERATED VIDEO", size=36, bg=((20, 30, 60), (8, 16, 40)), fg=(120, 235, 255))
        gfx.draw_sprite(frame, chip2, x + 26, y + ph - 52, anchor="l")
        self.demo._pip(frame, raw, T)
        return frame


# ====================================================================== transitions
def transition(kind, A, B, p):
    p = clamp(p)
    if kind == "cut" or p >= 1:
        return B
    if kind == "fade":
        return gfx.blend(A, B, smooth(p))
    if kind == "push":
        e = ease_in_out(p)
        sh = int(W * e)
        out = np.empty_like(A)
        out[:, :W - sh] = A[:, sh:]
        out[:, W - sh:] = B[:, :sh]
        k = int(1 + 70 * math.sin(math.pi * p))
        if k > 2:
            out = cv2.blur(out, (k, 1))
        return out
    if kind == "zoom":
        e = ease_in_out(p)
        if e < 0.5:
            f = gfx.cover_resize(A, W, H, zoom=1 + 0.45 * ease_in_out(e * 2))
            f = cv2.GaussianBlur(f, (0, 0), 1 + 14 * (e * 2) ** 2)
            return gfx.blend(f, np.full_like(f, 240), 0.45 * (e * 2) ** 4)
        q = (e - 0.5) * 2
        f = gfx.cover_resize(B, W, H, zoom=1.35 - 0.35 * ease_out(q))
        f = cv2.GaussianBlur(f, (0, 0), max(0.1, 14 * (1 - q) ** 2))
        return gfx.blend(f, np.full_like(f, 240), 0.45 * (1 - q) ** 4)
    if kind == "swipe":
        e = ease_in_out(p)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        proj = xx + 0.28 * yy
        thr = -200 + (W + 0.28 * H + 400) * e
        d = proj - thr
        mB = (d < 0).astype(np.float32)
        out = np.where((d < 0)[..., None], B, A)
        # glowing brand edge
        edge = np.exp(-(d / 18.0) ** 2)
        glow = np.exp(-(d / 90.0) ** 2) * 0.35
        col = np.array((70, 215, 255), np.float32)
        out = out.astype(np.float32) + (edge[..., None] * 0.95 + glow[..., None]) * col[None, None, :]
        return np.clip(out, 0, 255).astype(np.uint8)
    raise ValueError(kind)
