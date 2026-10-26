"""Phone-in-frame scene: branded background, procedurally drawn phone, camera zoom, screen re-timing."""
import math
import numpy as np
import cv2
from PIL import Image
import phone, scene as scene_mod
from gfx import ease_io, ease_out, clamp01, blend

SRC_W, SRC_H = 1320, 2868


def cam_at(T, keys):
    """keys: [(T, z, u, v)] -> (z, u, v), eased between keyframes (log-zoom)."""
    if T <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys[:-1], keys[1:]):
        if a[0] <= T <= b[0]:
            k = ease_io((T - a[0]) / max(b[0] - a[0], 1e-6))
            z = math.exp(math.log(a[1]) * (1 - k) + math.log(b[1]) * k)
            return z, a[2] * (1 - k) + b[2] * k, a[3] * (1 - k) + b[3] * k
    return keys[-1][1:]


class PhoneScene:
    def __init__(self, S, pal, out_w, out_h, layout="wide"):
        self.S, self.W, self.H, self.layout = S, out_w, out_h, layout
        if layout == "reel":
            self.hb = 0.52 * out_h                     # phone screen height at zoom 1 (leaves room for captions on top)
            self.anchor = (0.50 * out_w, 0.565 * out_h)
            glow_center = (0.5, 0.58)
        else:
            self.hb = 0.88 * out_h                     # phone screen height (output px) at zoom 1
            self.anchor = (0.675 * out_w, 0.50 * out_h)
            glow_center = (0.70, 0.5)
        self.HI = int(round(2300 * S))                 # hi-res frame build size (screen height)
        frame, smask, (sx, sy, sw, sh) = phone.build(self.HI)
        self.frame_hi = np.asarray(frame, np.uint8)                       # RGBA
        self.smask_hi = np.asarray(smask, np.uint8)                       # L (screen shape)
        self.sx, self.sy, self.sw, self.sh = sx, sy, sw, sh
        gloss = np.asarray(phone.glass_gloss(sw, sh, 0.06), np.uint8)
        self.gloss_hi = gloss
        mg = int(0.08 * out_w)
        self.bg = np.asarray(scene_mod.background(out_w + 2 * mg, out_h + 2 * mg, pal, glow_center=glow_center), np.float32) / 255.0
        self.mg = mg

    # -- geometry -------------------------------------------------------------------------------
    def geometry(self, cam, extra=(0.0, 0.0), scale_mul=1.0):
        z, u, v = cam
        s = z * self.hb / SRC_H * scale_mul
        ax, ay = self.anchor
        X0 = ax - u * SRC_W * s
        width = SRC_W * s
        if self.layout == "reel":
            lo, hi = 24 * self.S, self.W - 24 * self.S - width      # phone narrower than the frame: keep it inside
            if lo > hi:                                              # zoomed past the frame width: keep it filling the frame
                lo, hi = hi, lo
            X0 = min(max(X0, lo), hi)
        else:
            # keep the phone clear of the caption column on the left and inside the frame on the right
            x_min = 830 * self.S
            x_max = self.W - 24 * self.S - width
            X0 = min(max(X0, x_min), max(x_max, x_min))
        X0 += extra[0]
        Y0 = ay - v * SRC_H * s + extra[1]
        return dict(s=s, X0=X0, Y0=Y0)

    def to_out(self, g, u, v):
        return g["X0"] + u * SRC_W * g["s"], g["Y0"] + v * SRC_H * g["s"]

    # -- rendering ------------------------------------------------------------------------------
    def render(self, screen_rgb, g, opacity=1.0, sway=0.0):
        W, H = self.W, self.H
        s = g["s"]
        f = s * SRC_H / self.HI                          # hi-res px -> output px
        fh, fw = self.frame_hi.shape[:2]
        gw, gh = max(int(round(fw * f)), 8), max(int(round(fh * f)), 8)
        frame_rs = cv2.resize(self.frame_hi, (gw, gh), interpolation=cv2.INTER_AREA)
        sx_o, sy_o = int(round(self.sx * f)), int(round(self.sy * f))
        sw_o, sh_o = int(round(self.sw * f)), int(round(self.sh * f))
        sw_o, sh_o = min(sw_o, gw - sx_o), min(sh_o, gh - sy_o)
        interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_CUBIC
        scr = cv2.resize(screen_rgb, (sw_o, sh_o), interpolation=interp)
        mask = cv2.resize(self.smask_hi, (gw, gh), interpolation=cv2.INTER_AREA)[sy_o:sy_o + sh_o, sx_o:sx_o + sw_o]
        gl = cv2.resize(self.gloss_hi, (sw_o, sh_o), interpolation=cv2.INTER_AREA)

        grp = np.zeros((gh, gw, 4), np.float32)           # premultiplied RGB + A
        m = mask.astype(np.float32)[..., None] / 255.0
        sc = scr.astype(np.float32) / 255.0
        g_a = gl[..., 3:4].astype(np.float32) / 255.0
        sc = sc * (1 - g_a) + (gl[..., :3].astype(np.float32) / 255.0) * g_a   # gloss over the screen
        grp[sy_o:sy_o + sh_o, sx_o:sx_o + sw_o, :3] = sc * m
        grp[sy_o:sy_o + sh_o, sx_o:sx_o + sw_o, 3:4] = m
        fr = frame_rs.astype(np.float32) / 255.0
        fa = fr[..., 3:4]
        grp[..., :3] = grp[..., :3] * (1 - fa) + fr[..., :3] * fa
        grp[..., 3:4] = grp[..., 3:4] * (1 - fa) + fa

        # placement with sub-pixel translation
        tx = g["X0"] - self.sx * f
        ty = g["Y0"] - self.sy * f + sway
        M = np.array([[1, 0, tx], [0, 1, ty]], np.float32)
        placed = cv2.warpAffine(grp, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        # soft drop shadow from the alpha channel
        a_small = grp[..., 3]
        sig = max(26 * f * self.S ** 0 * (self.HI / 2300.0) ** 0, 3.0) * 0.9
        pad = int(sig * 3)
        a_pad = cv2.copyMakeBorder(a_small, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        a_blur = cv2.GaussianBlur(a_pad, (0, 0), sig)
        M2 = np.array([[1, 0, tx - pad], [0, 1, ty - pad + 30 * f]], np.float32)
        shadow = cv2.warpAffine(a_blur, M2, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0) * 0.62

        # background with gentle parallax against the phone's position
        cx = g["X0"] + 0.5 * SRC_W * s
        cy = g["Y0"] + 0.5 * SRC_H * s
        dx = float(np.clip(-(cx - self.anchor[0]) * 0.06, -self.mg * 0.9, self.mg * 0.9))
        dy = float(np.clip(-(cy - self.anchor[1]) * 0.04, -self.mg * 0.9, self.mg * 0.9))
        x0, y0 = int(self.mg + dx), int(self.mg + dy)
        out = self.bg[y0:y0 + H, x0:x0 + W].copy()
        out = out * (1 - shadow[..., None] * opacity)
        a = placed[..., 3:4] * opacity
        out = out * (1 - a) + placed[..., :3] * opacity
        return out
