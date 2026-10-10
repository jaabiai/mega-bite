"""Procedural cinematic scene engine (original footage generated in code - NOT stock footage).

A Scene renders a float32 RGB image (WH, WW, 3) in 0..1 at the 1280x720 working resolution from a spec dict:
  sky gradient + sun + lit clouds + god-rays  (computed at half resolution, upscaled)
  ground layers: mountains / city+monuments / crowd+flags  (masks recoloured per frame: haze, rim light, windows)
  smoke (tricolor / saffron / dark), big waving flags, bokeh lights, diyas, birds, stars, lightning
  camera: slow push/pan with parallax, handheld drift.
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from hl_common import *
import hl_sprites as SP

HW, HH = WW // 2, WH // 2          # half resolution for soft layers
MX, MY = int(WW * 0.30), 90          # frame offset inside the (larger) sprite canvases
CW, CH = WW + 2 * MX, WH + 2 * MY    # sprite canvas size


def C(*v):
    return np.array(v, np.float32)


PAL = {
    "night":   dict(top=C(.008, .012, .04), mid=C(.02, .035, .10), hor=C(.07, .09, .19), sun=C(.80, .85, 1.0), haze=C(.07, .09, .17), ground=C(.004, .006, .014)),
    "predawn": dict(top=C(.03, .05, .13), mid=C(.17, .17, .32), hor=C(.80, .42, .30), sun=C(1.0, .65, .35), haze=C(.42, .30, .38), ground=C(.012, .014, .03)),
    "sunrise": dict(top=C(.10, .17, .38), mid=C(.55, .42, .48), hor=C(1.0, .60, .24), sun=C(1.0, .78, .45), haze=C(.85, .55, .38), ground=C(.03, .02, .035)),
    "golden":  dict(top=C(.17, .28, .52), mid=C(.72, .55, .46), hor=C(1.0, .72, .36), sun=C(1.0, .85, .55), haze=C(.88, .66, .45), ground=C(.045, .03, .03)),
    "dusk":    dict(top=C(.07, .07, .20), mid=C(.42, .18, .38), hor=C(1.0, .42, .18), sun=C(1.0, .55, .28), haze=C(.65, .30, .30), ground=C(.015, .01, .025)),
    "red":     dict(top=C(.035, .015, .04), mid=C(.30, .06, .07), hor=C(.95, .28, .10), sun=C(1.0, .45, .18), haze=C(.55, .14, .10), ground=C(.012, .004, .006)),
    "blue":    dict(top=C(.025, .05, .13), mid=C(.09, .18, .36), hor=C(.38, .50, .70), sun=C(.75, .85, 1.0), haze=C(.30, .42, .60), ground=C(.008, .012, .03)),
    "storm":   dict(top=C(.02, .025, .045), mid=C(.10, .11, .16), hor=C(.55, .38, .30), sun=C(1.0, .70, .45), haze=C(.30, .26, .28), ground=C(.006, .006, .012)),
    "glow":    dict(top=C(.18, .30, .58), mid=C(.90, .66, .50), hor=C(1.0, .82, .50), sun=C(1.0, .92, .65), haze=C(.95, .72, .52), ground=C(.05, .035, .03)),
}

# ----------------------------------------------------------------------------------------------------------------------
# global (shared) noise textures - built once per process
# ----------------------------------------------------------------------------------------------------------------------
_TEX = {}


def tex(name):
    if name not in _TEX:
        cfgs = {"c1": (2048, 1024, 2.5, 11, 1.0),      # big cumulus blobs
                "c2": (2048, 1024, 2.4, 12, 4.5),      # stratus / cirrus (horizontally stretched)
                "c3": (1024, 1024, 2.2, 13, 1.0),      # mid detail
                "cf": (1024, 512, 1.9, 14, 1.0),       # fine detail
                "s1": (1024, 1024, 2.7, 21, 1.0), "s2": (1024, 1024, 2.3, 22, 1.0), "f1": (1024, 256, 2.4, 31, 3.0)}
        w, h, b, s_, st = cfgs[name]
        _TEX[name] = Tile(fbm_tex(w, h, b, s_, st))
    return _TEX[name]


_GRID = {}


def grid(w, h):
    key = (w, h)
    if key not in _GRID:
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        _GRID[key] = ((x + 0.5) / h, (y + 0.5) / h)     # x in units of frame height (aspect-correct), y in 0..1
    return _GRID[key]


def band(yy, y0, y1, fade=0.12):
    """Smooth bump: 0 outside [y0,y1], 1 inside, soft edges of width fade."""
    return smoothstep(y0 - fade, y0 + fade, yy) * (1.0 - smoothstep(y1 - fade, y1 + fade, yy))


def pal_get(name_or_dict):
    return PAL[name_or_dict] if isinstance(name_or_dict, str) else name_or_dict


# ----------------------------------------------------------------------------------------------------------------------
# camera
# ----------------------------------------------------------------------------------------------------------------------
class Cam:
    def __init__(self, spec, seed):
        self.pan = spec.get("pan", (0.0, 0.0))            # working px / second
        self.zoom = spec.get("zoom", (1.0, 1.0))
        self.shake = spec.get("shake", 1.0)
        self.ph = np.random.RandomState(seed).uniform(0, 6.28, 6)

    def at(self, tl, u):
        z = lerp(self.zoom[0], self.zoom[1], ease_in_out(clamp(u)))
        s = self.shake
        hx = s * (1.6 * math.sin(0.61 * tl + self.ph[0]) + 0.8 * math.sin(1.37 * tl + self.ph[1]))
        hy = s * (1.2 * math.sin(0.53 * tl + self.ph[2]) + 0.6 * math.sin(1.71 * tl + self.ph[3]))
        return dict(px=self.pan[0] * tl + hx, py=self.pan[1] * tl + hy, zoom=z)


def window(canvas, par, cam, mxy=(MX, MY), out=(WW, WH), pscale=1.0):
    """Crop a sprite canvas (PIL image) for the camera (pan with parallax, zoom) and resize to `out`."""
    z = 1.0 + (cam["zoom"] - 1.0) * (0.35 + 0.65 * par)
    cw, ch = out[0] / z, out[1] / z
    cx = mxy[0] + out[0] / 2 - par * cam["px"] * pscale
    cy = mxy[1] + out[1] / 2 - par * cam["py"] * 0.5 * pscale
    x0 = min(max(cx - cw / 2, 0), canvas.width - cw)
    y0 = min(max(cy - ch / 2, 0), canvas.height - ch)
    return canvas.resize(out, Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


def blend_rgba(dst, spr_rgb, spr_a, x, y):
    """Blend float sprite (h,w,3) with alpha (h,w,1) into dst at integer (x,y) with clipping."""
    h, w = spr_a.shape[:2]
    fx0, fy0, fx1, fy1 = max(0, x), max(0, y), min(WW, x + w), min(WH, y + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    aa = spr_a[fy0 - y:fy1 - y, fx0 - x:fx1 - x]
    sub = dst[fy0:fy1, fx0:fx1]
    sub *= (1 - aa)
    sub += spr_rgb[fy0 - y:fy1 - y, fx0 - x:fx1 - x] * aa


# ----------------------------------------------------------------------------------------------------------------------
# layers
# ----------------------------------------------------------------------------------------------------------------------
class SkyLayer:
    """Gradient + sun + clouds + god-rays, evaluated at half resolution then upscaled."""

    def __init__(self, spec, pal, seed):
        self.s = spec
        self.pal = pal
        self.seed = seed
        self.rays_n = noise1d_wrap(720, 18, seed + 5)
        self.stars = None
        if spec.get("stars", 0) > 0:
            self.stars = make_stars(spec["stars"], seed)

    def render(self, ctx):
        s, p = self.s, self.pal
        t, cam = ctx["tl"], ctx["cam"]
        X, Y = grid(HW, HH)
        yy = Y
        hor = s.get("horizon", 0.68)
        u = np.clip(yy / hor, 0, 1)
        a = np.clip(u / 0.62, 0, 1)[..., None]
        b = (np.clip((u - 0.62) / 0.38, 0, 1) ** 1.5)[..., None]
        img = p["top"] * (1 - a) + p["mid"] * a
        img = img * (1 - b) + p["hor"] * b
        below = (yy > hor)[..., None]
        img = np.where(below, p["hor"] * 0.85, img).astype(np.float32)
        # sun
        sun = s.get("sun")
        sx = sy = None
        if sun:
            k = ease_in_out(ctx["u"])
            sxf = lerp(sun["x"][0], sun["x"][1], k) if isinstance(sun["x"], tuple) else sun["x"]
            syf = lerp(sun["y"][0], sun["y"][1], k) if isinstance(sun["y"], tuple) else sun["y"]
            sx = (sxf * WW - cam["px"] * 0.08) / WH
            sy = syf - cam["py"] * 0.0004
            r = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
            I = sun.get("i", 1.0) * (1.0 + 0.06 * ctx["kick"])
            glow = (np.exp(-(r / 0.13) ** 1.1) * 0.75 + np.exp(-(r / 0.50) ** 1.0) * 0.40) * I
            img += glow[..., None] * p["sun"] * sun.get("glow", 0.8)
            sun_disc = (smoothstep(sun.get("r", 0.032) * 1.08, sun.get("r", 0.032) * 0.80, r) * sun.get("disc", 1.0))
        ctx["sun_xy"] = (sx, sy)
        # stars
        if self.stars is not None:
            st = window(self.stars, 0.12, cam, out=(HW, HH), mxy=(MX // 2, MY // 2), pscale=0.5)
            twinkle = 0.8 + 0.2 * math.sin(t * 2.1)
            sv = np.asarray(st, np.float32) / 255.0 * twinkle * self.s.get("stars", 1.0)
            img += (sv * np.clip(1.4 - u * 0.0 - (yy / hor) * 1.2, 0, 1))[..., None] * C(.85, .9, 1.0)
        # clouds
        cloud_cover = np.zeros((HH, HW), np.float32)
        for L in s.get("clouds", []):
            d = self._cloud(img, L, ctx, X, Y, p, sx, sy)
            cloud_cover = np.maximum(cloud_cover, d)
        # god rays
        if sun and s.get("rays", 0) > 0:
            th = np.arctan2(Y - sy, X - sx)
            idx = (th / (2 * np.pi) * 720 + t * 0.9 + 720.0) % 720
            ray = np.interp(idx, np.arange(721), np.append(self.rays_n, self.rays_n[0]))
            ray = np.clip(ray * 1.6 - 0.35, 0, 1) ** 1.6
            rr = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
            ray *= np.exp(-rr * 1.7) * (1.0 - 0.55 * cloud_cover)
            img += (ray * s["rays"] * (1 + 0.25 * ctx["kick"]))[..., None] * p["sun"] * 0.50
        # lightning flashes
        fl = ctx.get("flash", 0.0)
        if fl > 0.01:
            img += fl * (0.30 + 0.5 * cloud_cover[..., None]) * C(.55, .65, 1.0)
        if sun:
            hdr = (p["sun"] * 0.5 + 0.5) * 5.0
            img = img * (1 - sun_disc[..., None]) + hdr[None, None, :] * sun_disc[..., None]
        ctx["cloud_cover"] = cloud_cover
        return resize_f(np.clip(img, 0, 8), WW, WH, Image.BICUBIC)

    def _shape(self, L, ox, oy, dx=0.0, dy=0.0):
        sc = L.get("sc", 1.3)
        T1, T2 = tex(L.get("tex", "c1")), tex(L.get("tex2", "c3"))
        return (0.60 * T1.sample(ox + dx, oy + dy, HW, HH, sc, sc)
                + 0.40 * T2.sample(ox * 0.7 + 300 + dx * 0.9, oy * 0.7 + 100 + dy * 0.9, HW, HH, sc * 0.9, sc * 0.9))

    def _vmask(self, Y, L):
        y0, y1 = L.get("y0", 0.1), L.get("y1", 0.5)
        fb, ft = L.get("fade_bottom", 0.025), L.get("fade_top", 0.14)
        return smoothstep(y0 - ft, y0 + ft, Y) * smoothstep(y1 + fb, y1 - fb, Y)

    def _pick_offset(self, L, Y):
        """Choose a texture offset giving the requested cloud cover so every shot gets a proper bank."""
        target = L.get("cover", 0.35)
        c0 = L.get("c0", 0.55)
        vm = self._vmask(Y, L)
        best, bo = 9, 0.0
        for k in range(10):
            o = k * 207.0 + L.get("ox", 0)
            n = self._shape(L, o, L.get("oy", 0) + 60 * k % 400)
            cover = float((smoothstep(c0, c0 + 0.08, n) * vm).sum() / max(1.0, vm.sum()))
            if abs(cover - target) < best:
                best, bo = abs(cover - target), o
        return bo

    def _cloud(self, img, L, ctx, X, Y, p, sx, sy):
        t, cam = ctx["tl"], ctx["cam"]
        sc = L.get("sc", 1.3)
        if "_ox" not in L:
            L["_ox"] = self._pick_offset(L, Y)
        ox = L["_ox"] + t * L.get("speed", 10) + cam["px"] * L.get("par", 0.2) * 0.5
        oy = L.get("oy", 0) + cam["py"] * L.get("par", 0.2) * 0.3 + t * L.get("rise", 0.0)
        T3 = tex("cf")
        n3 = T3.sample(ox * 1.1 + 900, oy * 1.1 + 400, HW, HH, sc * 0.8, sc * 0.8)
        nn = self._shape(L, ox, oy) + (n3 - 0.5) * 0.12
        vm = self._vmask(Y, L)
        c0 = L.get("c0", 0.55)
        edge = max(0.03, L.get("edge", 0.07))
        alpha = smoothstep(c0, c0 + edge, nn) * vm
        thick = smoothstep(c0, c0 + L.get("thick", 0.30), nn)
        if sx is not None:
            dx, dy = (sx - HW / HH / 2), (sy - 0.5)
            ln = math.hypot(dx, dy) + 1e-6
            k = L.get("k", 9)
            ns = self._shape(L, ox, oy, sc * k * dx / ln, sc * k * dy / ln) + (n3 - 0.5) * 0.12
            lit = np.clip(0.5 + (nn - ns) * L.get("gain", 12.0), 0, 1) ** 1.2
        else:
            lit = np.full_like(alpha, 0.25)
        rowu = np.clip(Y / self.s.get("horizon", 0.68), 0, 1)[..., None]
        litcol = lerp_arr(p["sun"] * 0.9 + 0.10, p["hor"] * 1.1, smoothstep(0.15, 0.95, rowu))
        shadow = (p["top"] * 0.55 + p["mid"] * 0.10 + C(0.03, 0.03, 0.075)) * L.get("dark", 1.0)
        shadow = shadow * (1 - L.get("shadow_lift", 0.0)) + p["haze"] * L.get("shadow_lift", 0.0)
        shade = (lit * (1 - 0.50 * thick))[..., None]
        col = shadow * (1 - shade) + litcol * shade
        if sx is not None:
            r = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
            col = col + ((1 - thick) * alpha * np.exp(-r / 0.55))[..., None] * p["sun"] * L.get("silver", 0.9) * 0.9
        op = (alpha * L.get("op", 0.95))[..., None]
        img *= (1 - op)
        img += col * op
        return alpha


def lerp_arr(a, b, t):
    return a + (b - a) * t


def noise1d_wrap(n, spacing, seed):
    """Periodic 1D value noise (period n)."""
    rs = np.random.RandomState(seed)
    k = int(n / spacing)
    nodes = rs.rand(k)
    xs = np.arange(n) / float(spacing)
    i = np.floor(xs).astype(int)
    f = xs - i
    w = f * f * (3 - 2 * f)
    return nodes[i % k] * (1 - w) + nodes[(i + 1) % k] * w


def make_stars(density, seed):
    rs = np.random.RandomState(seed + 99)
    cw, ch = CW // 2, CH // 2
    arr = np.zeros((ch, cw), np.float32)
    n = int(2600 * density)
    xs, ys = rs.randint(0, cw, n), (rs.rand(n) ** 1.3 * ch * 0.8).astype(int)
    br = rs.rand(n) ** 3
    arr[ys, xs] = 0.25 + 0.75 * br
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.7))
    return Image.fromarray(np.clip(np.asarray(im, np.float32) * 2.2, 0, 255).astype(np.uint8), "L")


class GroundBase:
    sun_dir = (0, -3)

    def haze_color(self, p, depth, sunI=0.0):
        hz = p["haze"] * (0.75 + 0.35 * sunI)
        return lerp_arr(p["ground"], hz, depth ** 0.75)

    def blit(self, dst, mask_img, par, ctx, color, rim_img=None, rim_gain=0.0, sun_col=None):
        a = np.asarray(window(mask_img, par, ctx["cam"]), np.float32) / 255.0
        over(dst, color, a)
        if rim_img is not None and rim_gain > 0:
            r = np.asarray(window(rim_img, par, ctx["cam"]), np.float32) / 255.0
            dst += (r * rim_gain)[..., None] * sun_col
        return a


class MountainLayer(GroundBase):
    def __init__(self, spec, pal, seed):
        n = spec.get("n", 5)
        self.p = pal
        self.layers = []
        ys = np.linspace(spec.get("y_far", 0.62), spec.get("y_near", 0.86), n)
        amp = np.linspace(spec.get("amp_far", 0.04), spec.get("amp_near", 0.09), n) * WH
        for i in range(n):
            depth = 1.0 - i / max(1, n - 1)
            base = MY + ys[i] * WH
            m = SP.mountain_mask(CW, CH, base, amp[i], seed * 7 + i * 13, sharp=0.50 + 0.08 * (i / max(1, n - 1)), first=420 - 170 * (i / max(1, n - 1)), ridged=spec.get("ridged", 0.5))
            sdx, sdy = spec.get("rim_dir", (0, -3))
            rim = SP.rim_of(m, sdx, sdy, blur=1.2, gain=1.8)
            tx_arr = (tex("cf").sample(i * 91, i * 37, CW, CH, 0.55, 0.55) * 255).astype(np.uint8)
            self.layers.append(dict(mask=Image.fromarray(m, "L"), rim=Image.fromarray(rim, "L"), tex=Image.fromarray(tx_arr, "L"), depth=depth,
                                    par=0.12 + 0.62 * (1 - depth), y=ys[i]))
        self.mist = spec.get("mist", 0.55)
        self.rim = spec.get("rim", 0.18)
        self.seed = seed

    def render(self, dst, ctx):
        p = self.p
        t = ctx["tl"]
        sunI = ctx.get("sunI", 0.5)
        yy = ((np.arange(WH, dtype=np.float32) + 0.5) / WH)[:, None, None]
        for i, L in enumerate(self.layers):
            col = self.haze_color(p, L["depth"], sunI)
            vg = 1.0 - 0.42 * np.clip((yy - L["y"]) / max(0.08, 1.0 - L["y"]), 0, 1) * (1.0 - 0.5 * L["depth"])
            tx = np.asarray(window(L["tex"], L["par"], ctx["cam"], out=(WW, WH)), np.float32)[..., None] / 255.0
            self.blit(dst, L["mask"], L["par"], ctx, col * vg * (0.86 + 0.28 * tx * (1 - 0.5 * L["depth"])), L["rim"],
                      self.rim * ((1 - L["depth"]) ** 1.5) * ctx.get("sunI", 0.5), p["sun"])
            if i < len(self.layers) - 1 and self.mist > 0:
                add_mist(dst, ctx, p, L["y"] + 0.03, 0.10, self.mist * (0.5 + 0.5 * L["depth"]), i + self.seed, ctx["tl"])


def add_mist(dst, ctx, pal, y_center, height, strength, seed, t):
    """Soft drifting fog band (half resolution noise, upscaled)."""
    X, Y = grid(HW, HH)
    cam = ctx["cam"]
    n = tex("f1").sample(t * 6 + seed * 91 + cam["px"] * 0.1, seed * 17, HW, HH, 1.3, 1.3)
    prof = np.exp(-((Y - y_center) / height) ** 2)
    a = np.clip(prof * (0.35 + 0.9 * n) * strength, 0, 1)
    col = (pal["haze"] * 1.05 + pal["sun"] * 0.08 * ctx.get("sunI", 0.5))
    a_full = resize_f(a, WW, WH, Image.BILINEAR)
    over(dst, col, a_full)


class CityLayer(GroundBase):
    def __init__(self, spec, pal, seed):
        self.p = pal
        self.layers = []
        n = spec.get("n", 2)
        for i in range(n):
            depth = 1.0 - i / max(1, n - 1) if n > 1 else 0.06
            ground = MY + (spec.get("ground", 0.86) - 0.012 * (n - 1 - i) * 0) * WH + (1 - depth) * 0
            hmax = spec.get("hmax", 150) * (0.55 + 0.45 * (1 - depth))
            mons = []
            if i == n - 1:
                for name, xf, sc in spec.get("monuments", []):
                    mons.append((name, MX + xf * WW, sc))
            fort = None
            m, e = SP.city_layer(CW, CH, ground - (n - 1 - i) * 0, seed * 5 + i, density=spec.get("density", 1.0), hmin=spec.get("hmin", 30) * (0.6 + 0.4 * (1 - depth)),
                                 hmax=hmax, monuments=mons, lit=spec.get("lit", 0.35) * (0.6 + 0.4 * (1 - depth)), scale=0.7 + 0.45 * (1 - depth))
            sdx, sdy = spec.get("rim_dir", (0, -3))
            rim = SP.rim_of(m, sdx, sdy, blur=1.0, gain=1.6)
            self.layers.append(dict(mask=Image.fromarray(m, "L"), em=Image.fromarray(e, "L"), rim=Image.fromarray(rim, "L"), depth=depth,
                                    par=0.25 + 0.55 * (1 - depth)))
        self.rim = spec.get("rim", 0.45)
        self.lit = spec.get("lit", 0.35)
        self.mist = spec.get("mist", 0.45)
        self.seed = seed

    def render(self, dst, ctx):
        p = self.p
        sunI = ctx.get("sunI", 0.5)
        for i, L in enumerate(self.layers):
            col = self.haze_color(p, L["depth"] * 0.9, sunI)
            a = self.blit(dst, L["mask"], L["par"], ctx, col, L["rim"], self.rim * (0.4 + 0.6 * L["depth"]) * sunI, p["sun"])
            if self.lit > 0:
                em = np.asarray(window(L["em"], L["par"], ctx["cam"]), np.float32) / 255.0
                fl = 0.85 + 0.15 * math.sin(ctx["tl"] * 3.1 + i)
                dst += (em * (0.55 + 0.45 * (1 - ctx.get("daylight", 0.0))) * fl)[..., None] * C(1.0, .72, .38) * (1.0 - 0.7 * ctx.get("daylight", 0.0)) * 0.9
            if i < len(self.layers) - 1:
                add_mist(dst, ctx, p, 0.80, 0.08, self.mist, 40 + i + self.seed, ctx["tl"])


class CrowdLayer(GroundBase):
    def __init__(self, spec, pal, seed):
        self.p = pal
        self.spec = spec
        rows_spec = spec.get("rows") or [dict(scale=0.78, base=MY + 0.80 * WH, density=0.95, raised_prob=0.30, pole_prob=0.62),
                                          dict(scale=1.15, base=MY + 0.91 * WH, density=1.0, raised_prob=0.28, pole_prob=0.55),
                                          dict(scale=1.65, base=MY + 1.06 * WH, density=1.05, raised_prob=0.20, pole_prob=0.35)]
        rows = SP.crowd_rows(CW, CH, rows_spec, seed)
        sdx, sdy = spec.get("rim_dir", (0, -2))
        self.rows = []
        for i, (m, flags) in enumerate(rows):
            depth = 1.0 - i / max(1, len(rows) - 1)
            rim = SP.rim_of(m, sdx, sdy, blur=1.0, gain=2.4)
            mi = Image.fromarray(m, "L")
            if i == len(rows) - 1 and spec.get("dof", True):
                mi = mi.filter(ImageFilter.GaussianBlur(2.2))
            self.rows.append(dict(mask=mi, rim=Image.fromarray(rim, "L"), flags=flags, depth=depth, par=0.45 + 0.5 * (1 - depth)))
        self.fl = SP.flag_frames(120, 78, n=16, amp=5.0, tint=spec.get("flag_tint", 0.8))
        self.rim = spec.get("rim", 0.9)
        self.seed = seed

    def render(self, dst, ctx):
        p = self.p
        t = ctx["tl"]
        kick = ctx["kick"]
        sunI = ctx.get("sunI", 0.5)
        for i, R in enumerate(self.rows):
            bob = (2.4 * kick + 1.0) * (0.6 + 0.6 * (1 - R["depth"])) * self.spec.get("bob", 1.0)
            cam = dict(ctx["cam"]); cam["py"] = cam["py"] - bob * 2.0
            ctx2 = dict(ctx); ctx2["cam"] = cam
            col = self.haze_color(p, R["depth"] * 0.10, sunI * 0.2) * (0.5 if R["depth"] < 0.3 else 0.8)
            self.blit(dst, R["mask"], R["par"], ctx2, col, R["rim"], self.rim * 0.42 * sunI * (0.65 + 0.35 * (1 - R["depth"])), p["sun"])
            if R["flags"] and self.spec.get("flags", True) and i < len(self.rows) - 1:
                self._flags(dst, R, ctx2)

    def _flags(self, dst, R, ctx):
        cam = ctx["cam"]
        z = 1.0 + (cam["zoom"] - 1.0) * (0.35 + 0.65 * R["par"])
        cx = MX + WW / 2 - R["par"] * cam["px"]
        cy = MY + WH / 2 - R["par"] * cam["py"] * 0.5
        cw, ch = WW / z, WH / z
        x0 = min(max(cx - cw / 2, 0), CW - cw)
        y0 = min(max(cy - ch / 2, 0), CH - ch)
        sc = WW / cw
        t = ctx["tl"]
        base_k = 0.62 + 0.55 * (1 - R["depth"])
        amb = (0.40 + 0.65 * ctx.get("sunI", 0.5)) * (self.p["sun"] * 0.6 + 0.5)
        for (px, py, s_) in R["flags"]:
            fx, fy = (px - x0) * sc, (py - y0) * sc
            if -70 < fx < WW + 20 and -50 < fy < WH + 20:
                f = self.fl[int((t * 1.5 + px * 0.012) * 16) % 16]
                k = base_k * s_ * sc * 1.15
                spr = f.resize((max(2, int(f.width * k)), max(2, int(f.height * k))), Image.BILINEAR)
                arr = np.asarray(spr, np.float32) / 255.0
                blend_rgba(dst, arr[..., :3] * amb, arr[..., 3:4], int(fx), int(fy))


class BigFlagLayer:
    """A large, softly out-of-focus waving flag in the foreground (tricolor detail)."""

    def __init__(self, spec, pal, seed):
        self.s = spec
        w, h = spec.get("size", (900, 560))
        n = 24
        self.frames = SP.waving_flag(w, h, n=n, amp=spec.get("amp", 34), wl_frac=spec.get("wl", 0.62))
        blur = spec.get("blur", 3.0)
        if blur > 0:
            self.frames = [f.filter(ImageFilter.GaussianBlur(blur)) for f in self.frames]
        self.p = pal

    def render(self, dst, ctx):
        s = self.s
        t = ctx["tl"]
        f = self.frames[int(t * s.get("speed", 1.2) * 24) % 24]
        k = s.get("scale", 1.0) * (1.0 + 0.04 * ctx["u"])
        x, y = s.get("pos", (0.1, 0.1))
        spr = f.resize((int(f.width * k), int(f.height * k)), Image.BILINEAR)
        if s.get("flip"):
            spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
        amb = s.get("bright", 0.8) * (0.5 + 0.6 * ctx.get("sunI", 0.5))
        arr = np.asarray(spr, np.float32)
        a = arr[..., 3:4] / 255.0 * s.get("op", 1.0)
        rgb = arr[..., :3] / 255.0 * amb * (self.p["sun"] * 0.5 + 0.55)
        ox, oy = int(x * WW - ctx["cam"]["px"] * 0.9), int(y * WH - ctx["cam"]["py"] * 0.4)
        blend_rgba(dst, rgb, a, ox, oy)


class SmokeLayer:
    """Volumetric-looking smoke from scrolling fbm textures. kinds: tricolor | saffron | white | red | dark"""

    def __init__(self, spec, pal, seed):
        self.s = spec
        self.p = pal
        self.seed = seed

    def render(self, dst, ctx):
        s = self.s
        t, cam = ctx["tl"], ctx["cam"]
        amt = s.get("amount", 0.6) * ctx.get("smoke_gain", 1.0)
        if amt <= 0.01:
            return
        X, Y = grid(HW, HH)
        sp = s.get("speed", 14)
        ox = t * sp + cam["px"] * 0.3 + self.seed * 113
        oy = -t * s.get("rise", 9) + self.seed * 71
        a = tex("s1").sample(ox, oy, HW, HH, s.get("sc", 1.5))
        b = tex("s2").sample(ox * 0.6 + 200, oy * 0.8 + 90, HW, HH, s.get("sc", 1.5) * 2.2)
        # domain-warp-ish second pass for curly detail
        w = tex("s2").sample(ox * 0.4, oy * 0.4 + t * 3, HW, HH, s.get("sc", 1.5) * 1.2)
        c = tex("s1").sample(ox * 0.8 + 170, oy * 0.8 + 60, HW, HH, s.get("sc", 1.5) * 1.6)
        n = np.clip(0.36 * a + 0.22 * b + 0.42 * c * (0.65 + 0.7 * w), 0, 1)
        vm = band(Y, s.get("y0", 0.45), s.get("y1", 1.0), s.get("fade", 0.22))
        d = smoothstep(s.get("c0", 0.42), s.get("c1", 0.80), n) * vm * amt
        kind = s.get("kind", "white")
        xs = (X / (HW / HH)) if False else (np.arange(HW)[None, :] / HW)
        if kind == "tricolor":
            sh = (t * 0.02) % 1.0
            u = np.clip(xs + 0.0 * sh, 0, 1)
            colx = np.where(u[..., None] < 0.38, C(1.0, .52, .12), np.where(u[..., None] < 0.62, C(1.0, .97, .93), C(.20, .78, .32)))
            # soften transitions between the three colours
            wl = smoothstep(0.28, 0.46, u)[..., None]
            wr = smoothstep(0.54, 0.72, u)[..., None]
            colx = (C(1.0, .52, .12) * (1 - wl) + C(1.0, .97, .93) * wl) * (1 - wr) + C(.18, .74, .30) * wr
            col = colx * np.ones((HH, 1, 1), np.float32)
        elif kind == "saffron":
            col = np.ones((HH, HW, 3), np.float32) * C(1.0, .56, .16)
        elif kind == "red":
            col = np.ones((HH, HW, 3), np.float32) * C(.95, .16, .10)
        elif kind == "dark":
            col = np.ones((HH, HW, 3), np.float32) * (self.p["haze"] * 0.5 + 0.03)
        else:
            col = np.ones((HH, HW, 3), np.float32) * (self.p["haze"] * 0.9 + 0.12)
        # light the smoke: brighter on the edges toward the sun
        lit = np.clip(0.55 + (n - a) * 3.0, 0.2, 1.2)[..., None]
        col = col * lit * s.get("bright", 1.0)
        d3 = d[..., None]
        if s.get("blend", "over") == "screen":
            add = col * d3
            full = resize_f(np.clip(add, 0, 2), WW, WH, Image.BILINEAR)
            dst += full * 0.9
        else:
            af = resize_f(np.clip(d, 0, 1), WW, WH, Image.BILINEAR)
            cf = resize_f(col, WW, WH, Image.BILINEAR)
            over(dst, cf, af)


_BOKEH = {}


def bokeh_sprite(r):
    if r not in _BOKEH:
        n = r * 2 + 3
        y, x = np.mgrid[0:n, 0:n].astype(np.float32)
        d = np.sqrt((x - n / 2) ** 2 + (y - n / 2) ** 2) / r
        a = smoothstep(1.0, 0.82, d) * (0.65 + 0.35 * smoothstep(0.55, 1.0, d))   # brighter rim like real bokeh
        _BOKEH[r] = a.astype(np.float32)
    return _BOKEH[r]


class BokehLayer:
    def __init__(self, spec, pal, seed):
        rs = np.random.RandomState(seed + 7)
        n = spec.get("n", 40)
        self.pts = []
        for i in range(n):
            self.pts.append(dict(x=rs.uniform(-0.05, 1.05), y=spec.get("y0", 0.45) + rs.rand() * (spec.get("y1", 0.95) - spec.get("y0", 0.45)),
                                 r=int(rs.choice([5, 8, 12, 16, 22, 30], p=[.2, .25, .22, .17, .1, .06])), ph=rs.uniform(0, 6.28),
                                 col=np.array(spec.get("colors", [(1.0, .75, .4)])[rs.randint(len(spec.get("colors", [(1,.75,.4)])))], np.float32),
                                 par=rs.uniform(0.1, 0.8), v=rs.uniform(0.3, 1.0)))
        self.s = spec

    def render(self, dst, ctx):
        t = ctx["tl"]
        for q in self.pts:
            x = int(q["x"] * WW - ctx["cam"]["px"] * q["par"]) % (WW + 120) - 60
            y = int(q["y"] * WH - ctx["cam"]["py"] * q["par"] * 0.5 + 6 * math.sin(t * 0.5 + q["ph"]))
            r = q["r"]
            spr = bokeh_sprite(r)
            h, w = spr.shape
            x0, y0 = x - w // 2, y - h // 2
            fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(WW, x0 + w), min(WH, y0 + h)
            if fx1 <= fx0 or fy1 <= fy0:
                continue
            flick = 0.75 + 0.25 * math.sin(t * 4.0 + q["ph"] * 3) + 0.2 * ctx["kick"]
            a = spr[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * q["v"] * flick * self.s.get("gain", 0.55)
            dst[fy0:fy1, fx0:fx1] += a[..., None] * q["col"]


class DiyaLayer:
    """Row of small clay lamps with flickering flames (bridge: vigil)."""

    def __init__(self, spec, pal, seed):
        rs = np.random.RandomState(seed + 3)
        self.items = []
        n = spec.get("n", 16)
        for i in range(n):
            depth = rs.rand()
            self.items.append(dict(x=(i + rs.uniform(-0.3, 0.3)) / (n - 1), y=spec.get("y", 0.86) + 0.07 * (1 - depth) * rs.rand() - 0.02 * depth,
                                   s=0.45 + 0.9 * (1 - depth), ph=rs.uniform(0, 6.28), depth=depth))
        self.s = spec

    def render(self, dst, ctx):
        t = ctx["tl"]
        for q in sorted(self.items, key=lambda z: -z["depth"]):
            sc = q["s"]
            cx = q["x"] * WW * 1.04 - 20 - ctx["cam"]["px"] * (0.3 + 0.5 * (1 - q["depth"]))
            cy = q["y"] * WH - ctx["cam"]["py"] * 0.2
            # bowl (dark ellipse with warm rim)
            bw, bh = 34 * sc, 12 * sc
            self._ellipse(dst, cx, cy, bw, bh, C(.02, .012, .01), 1.0)
            self._ellipse(dst, cx, cy - bh * 0.35, bw * 0.92, bh * 0.35, C(1.0, .55, .18), 0.55)
            # flame
            fl = 1.0 + 0.18 * math.sin(t * 9 + q["ph"]) + 0.1 * math.sin(t * 17 + q["ph"] * 2) + 0.15 * ctx["kick"]
            fh, fw = 40 * sc * fl, 9 * sc
            self._flame(dst, cx + 2 * math.sin(t * 5 + q["ph"]) * sc, cy - bh * 0.6, fw, fh, q["depth"])
            # glow
            self._glow(dst, cx, cy - fh * 0.5 - bh * 0.4, 110 * sc * (0.9 + 0.1 * fl), 0.30 * (1 - 0.4 * q["depth"]))

    @staticmethod
    def _ellipse(dst, cx, cy, rx, ry, col, a):
        x0, x1 = int(max(0, cx - rx - 2)), int(min(WW, cx + rx + 2))
        y0, y1 = int(max(0, cy - ry - 2)), int(min(WH, cy + ry + 2))
        if x1 <= x0 or y1 <= y0:
            return
        y, x = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        al = np.clip((1.0 - d) * 3.0, 0, 1) * a
        sub = dst[y0:y1, x0:x1]
        sub *= (1 - al[..., None])
        sub += col * al[..., None]

    @staticmethod
    def _flame(dst, cx, base, w, h, depth):
        x0, x1 = int(max(0, cx - w * 2)), int(min(WW, cx + w * 2))
        y0, y1 = int(max(0, base - h * 1.1)), int(min(WH, base + 4))
        if x1 <= x0 or y1 <= y0:
            return
        y, x = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        v = np.clip((base - y) / h, 0, 1)
        half = w * np.sqrt(np.clip(np.sin(np.pi * v ** 0.75), 0, 1)) * (1 - 0.15 * v)
        d = np.abs(x - cx) / (half + 1e-3)
        al = np.clip((1 - d) * 2.2, 0, 1) * (v > 0) * (v < 1)
        core = np.clip(1 - d * 1.5, 0, 1) * np.clip(1 - v * 1.2, 0, 1)
        col = C(1.0, .52, .12)[None, None, :] * (1 - core[..., None]) + C(1.0, .95, .75)[None, None, :] * core[..., None]
        sub = dst[y0:y1, x0:x1]
        sub *= (1 - 0.9 * al[..., None])
        sub += col * al[..., None] * 1.2

    @staticmethod
    def _glow(dst, cx, cy, r, g):
        x0, x1 = int(max(0, cx - r)), int(min(WW, cx + r))
        y0, y1 = int(max(0, cy - r)), int(min(WH, cy + r))
        if x1 <= x0 or y1 <= y0:
            return
        y, x = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
        dst[y0:y1, x0:x1] += (np.exp(-d * d * 3.2) * g)[..., None] * C(1.0, .6, .25)


class BirdLayer:
    def __init__(self, spec, pal, seed):
        rs = np.random.RandomState(seed + 21)
        self.flocks = []
        for f in range(spec.get("flocks", 2)):
            n = rs.randint(7, 15)
            self.flocks.append(dict(x0=rs.uniform(-0.2, 1.0), y0=rs.uniform(0.15, 0.4), vx=rs.uniform(14, 26) * rs.choice([-1, 1]),
                                    off=[(rs.uniform(-60, 60), rs.uniform(-30, 30), rs.uniform(0, 6.28), rs.uniform(0.6, 1.2)) for _ in range(n)]))
        self.p = pal

    def render(self, dst, ctx):
        t = ctx["tl"]
        im = Image.new("L", (WW, WH), 0)
        d = ImageDraw.Draw(im)
        for F in self.flocks:
            fx = (F["x0"] * WW + F["vx"] * t) % (WW + 300) - 150
            fy = F["y0"] * WH + 12 * math.sin(t * 0.3 + F["x0"] * 5)
            for (ox, oy, ph, s) in F["off"]:
                x, y = fx + ox, fy + oy
                flap = math.sin(t * 6.0 + ph)
                w = 15 * s
                d.line([(x - w, y - 8 * s * flap), (x - w * 0.5, y - 3 * s * flap - 2), (x, y)], fill=255, width=3)
                d.line([(x + w, y - 8 * s * flap), (x + w * 0.5, y - 3 * s * flap - 2), (x, y)], fill=255, width=3)
        a = np.asarray(im, np.float32) / 255.0
        over(dst, self.p["ground"] * 1.5 + 0.01, a * 0.85)


# ----------------------------------------------------------------------------------------------------------------------
# the Scene
# ----------------------------------------------------------------------------------------------------------------------
LAYERS = {"mountains": MountainLayer, "city": CityLayer, "crowd": CrowdLayer, "bigflag": BigFlagLayer, "smoke": SmokeLayer,
          "bokeh": BokehLayer, "diyas": DiyaLayer, "birds": BirdLayer}


class Scene:
    def __init__(self, spec, seed=1):
        self.spec = spec
        self.seed = seed
        self.pal = dict(pal_get(spec.get("pal", "sunrise")))
        for k, v in spec.get("pal_over", {}).items():
            self.pal[k] = C(*v)
        self.cam = Cam(spec.get("cam", {}), seed)
        self.sky = SkyLayer(spec, self.pal, seed)
        self.layers = []
        sun = spec.get("sun")
        if sun:
            sxm = sun["x"][0] if isinstance(sun["x"], tuple) else sun["x"]
            sym = sun["y"][1] if isinstance(sun["y"], tuple) else sun["y"]
            vx, vy = sxm - 0.5, sym - 0.45
            ln = math.hypot(vx, vy) + 1e-6
            rim_dir = (int(round(3 * vx / ln)), int(round(3 * vy / ln)) or -1)
        else:
            rim_dir = (0, -3)
        for item in spec.get("layers", []):
            kind, ls = item
            ls = dict(ls)
            ls.setdefault("rim_dir", rim_dir)
            self.layers.append((kind, LAYERS[kind](ls, self.pal, seed * 3 + len(self.layers)), ls))
        self.flashes = spec.get("flashes", [])

    def render(self, tl, u, kick):
        cam = self.cam.at(tl, u)
        cam["zoom"] += 0.007 * kick
        flash = 0.0
        for (t0, amp) in self.flashes:
            dt = tl - t0
            if 0 <= dt < 0.6:
                flash += amp * math.exp(-dt * 9) * (0.6 + 0.4 * math.sin(dt * 90))
        ctx = dict(tl=tl, u=u, kick=kick, cam=cam, flash=flash, sunI=self.spec.get("sun", {}).get("i", 0.5) if self.spec.get("sun") else 0.15,
                   daylight=self.spec.get("daylight", 0.0), smoke_gain=1.0)
        dst = self.sky.render(ctx)
        for kind, layer, ls in self.layers:
            layer.render(dst, ctx)
        return dst
