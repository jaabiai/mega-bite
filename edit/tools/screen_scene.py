"""Screen-recording scene compositor.

Renders a 1920x1080 clip in which the iPhone screen recording is shown inside a phone window with a virtual camera
(smooth zoom/pan), narration-synced highlights (spotlight dim + glowing ring), tap ripples and swipe-finger hints,
next to a graded speaker picture-in-picture, over the branded dark background.

The recording's own audio is never used. The time-map (`segs`) cuts idle moments so every on-screen action lands on
the spoken word that describes it; cuts only happen between frames that look identical (checked by --check).

usage:
  screen_scene.py render <scene> <out.mp4>            full render
  screen_scene.py dump   <scene> <outdir> t1 t2 ...   debug PNGs at the given main-timeline seconds
  screen_scene.py check  <scene>                      print frame difference at every jump cut
"""
import importlib
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FPS = 30
CW, CH = 1920, 1080
SRC_W, SRC_H = 1320, 2868
WIN_W, WIN_H = 394, 856
WIN_X, WIN_Y = 763, 30
PIP_W, PIP_H = 480, 270
PIP_X, PIP_Y = 1300, 70
UI = 1.0  # size multiplier for tap ripples / swipe finger (the 9:16 reel uses a larger viewport)

SCRATCH = os.environ.get("SCRATCH", "/tmp/claude-0/-home-user-mega-bite/f59bda35-f4bb-5fe4-b000-af77d2d4ed63/scratchpad")
SCREEN = f"{SCRATCH}/screen/screen_sdr30.mp4"
BASE = f"{SCRATCH}/base/base.mp4"

AMBER = np.array([255, 184, 28], np.float32)
WHITE = np.array([255, 255, 255], np.float32)


# ----------------------------------------------------------------------------- helpers
def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def view_for(tx, ty, z, ay=0.38):
    """camera centre so that source point (tx,ty) sits at `ay` of the window height."""
    vh = SRC_H / z
    return tx, ty + (0.5 - ay) * vh, z


def camera_at(keys, t):
    """keys: [(t, cx, cy, z)] -> eased interpolation (zoom in log space)."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for (t0, x0, y0, z0), (t1, x1, y1, z1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = ease_io((t - t0) / max(t1 - t0, 1e-6))
            return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * k)
    return keys[-1][1:]


def rrect_sdf(X, Y, x0, y0, x1, y1, r):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    px, py = np.abs(X - cx) - hx, np.abs(Y - cy) - hy
    return np.hypot(np.maximum(px, 0), np.maximum(py, 0)) + np.minimum(np.maximum(px, py), 0) - r


_YY, _XX = np.mgrid[0:WIN_H, 0:WIN_W].astype(np.float32)


# ----------------------------------------------------------------------------- static layers
def make_background():
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    top, bot = np.array([13, 14, 22], np.float32), np.array([6, 7, 11], np.float32)
    g = (yy / CH)[..., None]
    bg = top * (1 - g) + bot * g
    # soft brand glows (amber top-left, magenta bottom-right) + faint dot grid
    def glow(cx, cy, rx, ry, col, a):
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        return np.exp(-d)[..., None] * (np.array(col, np.float32) * a)
    bg += glow(260, 160, 620, 420, (255, 150, 20), 0.16)
    bg += glow(1700, 980, 700, 460, (255, 40, 110), 0.14)
    bg += glow(960, 540, 520, 700, (40, 60, 120), 0.10)
    dots = ((xx % 40 < 2) & (yy % 40 < 2)).astype(np.float32)[..., None] * 9
    bg += dots
    return np.clip(bg, 0, 255).astype(np.uint8)


def rounded_mask(w, h, r, ss=4):
    m = np.zeros((h * ss, w * ss), np.uint8)
    cv2.rectangle(m, (r * ss, 0), (w * ss - r * ss - 1, h * ss - 1), 255, -1)
    cv2.rectangle(m, (0, r * ss), (w * ss - 1, h * ss - r * ss - 1), 255, -1)
    for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
        cv2.circle(m, (cx * ss, cy * ss), r * ss, 255, -1, cv2.LINE_AA)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


class Layers:
    """pre-rendered shadows, bezels and masks"""

    def __init__(self):
        self.bg = make_background()
        self.win_r = 40
        self.win_mask = rounded_mask(WIN_W, WIN_H, self.win_r)[..., None]
        # phone shadow + amber rim glow around the window (RGBA on a local patch)
        pad = 90
        pw, ph = WIN_W + 2 * pad, WIN_H + 2 * pad
        patch = np.zeros((ph, pw), np.float32)
        patch[pad:pad + WIN_H, pad:pad + WIN_W] = rounded_mask(WIN_W, WIN_H, self.win_r)
        self.pad = pad
        self.shadow = cv2.GaussianBlur(patch, (0, 0), 26) * 0.75
        self.glow = cv2.GaussianBlur(patch, (0, 0), 14) * 0.55
        # bezel ring (silver edge + dark body) just outside the window
        outer = np.zeros((ph, pw), np.uint8)
        b = 10
        ring_mask = rounded_mask(WIN_W + 2 * b, WIN_H + 2 * b, self.win_r + b)
        full = np.zeros((ph, pw), np.float32)
        full[pad - b:pad - b + WIN_H + 2 * b, pad - b:pad - b + WIN_W + 2 * b] = ring_mask
        inner = patch
        self.bezel_a = np.clip(full - inner, 0, 1)
        edge = np.zeros((ph, pw), np.float32)
        e = rounded_mask(WIN_W + 2 * b, WIN_H + 2 * b, self.win_r + b)
        e_in = rounded_mask(WIN_W + 2 * b - 4, WIN_H + 2 * b - 4, self.win_r + b - 2)
        edge[pad - b:pad - b + WIN_H + 2 * b, pad - b:pad - b + WIN_W + 2 * b] = e
        e2 = np.zeros_like(edge)
        e2[pad - b + 2:pad - b + 2 + WIN_H + 2 * b - 4, pad - b + 2:pad - b + 2 + WIN_W + 2 * b - 4] = e_in
        self.edge_a = np.clip(edge - e2, 0, 1)
        self.pip_mask = rounded_mask(PIP_W, PIP_H, 26)[..., None]
        ppad = 40
        pp = np.zeros((PIP_H + 2 * ppad, PIP_W + 2 * ppad), np.float32)
        pp[ppad:ppad + PIP_H, ppad:ppad + PIP_W] = rounded_mask(PIP_W, PIP_H, 26)
        self.pip_pad = ppad
        self.pip_shadow = cv2.GaussianBlur(pp, (0, 0), 14) * 0.7
        ring = np.clip(cv2.GaussianBlur(pp, (0, 0), 1.2) - cv2.erode(pp, np.ones((5, 5), np.uint8)), 0, 1)
        self.pip_ring = ring

    def blend_patch(self, canvas, x0, y0, a, color):
        h, w = a.shape
        xa, ya = max(x0, 0), max(y0, 0)
        xb, yb = min(x0 + w, CW), min(y0 + h, CH)
        if xb <= xa or yb <= ya:
            return
        aa = a[ya - y0:yb - y0, xa - x0:xb - x0, None]
        reg = canvas[ya:yb, xa:xb].astype(np.float32)
        col = np.asarray(color, np.float32)
        canvas[ya:yb, xa:xb] = np.clip(reg * (1 - aa) + col * aa, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------- tracking
def track_rows(ref_r, rect, ra, rb, step=1 / 30):
    """vertical offset (src px) of a UI row over recording time, by template matching a text strip."""
    x0, y0, x1, y1 = rect

    def grab(r):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{r:.4f}", "-i", SCREEN, "-frames:v", "1",
                              "-vf", "scale=660:1434:flags=area,format=gray", "-f", "rawvideo", "-"],
                             capture_output=True).stdout
        return np.frombuffer(raw, np.uint8).reshape(1434, 660)

    ref = grab(ref_r)
    tpl = ref[y0 // 2:y1 // 2, x0 // 2:x1 // 2]
    out = {}
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ra:.4f}", "-t", f"{rb - ra:.4f}", "-i", SCREEN,
                          "-vf", "fps=30,scale=660:1434:flags=area,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, 1434, 660)
    for i, fr in enumerate(frames):
        strip = fr[:, max(x0 // 2 - 20, 0):x1 // 2 + 20]
        if strip.shape[1] < tpl.shape[1]:
            continue
        res = cv2.matchTemplate(strip, tpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(res)
        out[round(ra + i / 30, 3)] = ((loc[1] - y0 // 2) * 2, mx)
    return out


# ----------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, name):
        mod = importlib.import_module("scenes")
        self.sp = getattr(mod, name)
        self.name = name
        self.t0, self.t1 = self.sp["t0"], self.sp["t1"]
        self.N = int(round((self.t1 - self.t0) * FPS))
        self.layers = Layers()
        self.tracks = {}
        for key, tr in self.sp.get("tracks", {}).items():
            self.tracks[key] = track_rows(tr["ref_r"], tr["rect"], tr["ra"], tr["rb"])
        self._seg_cache = None

    # time map ---------------------------------------------------------------------------
    def seg_at(self, t):
        for i, (a, b, r0, sp) in enumerate(self.sp["segs"]):
            if a - 1e-6 <= t < b - 1e-6:
                return i, r0 + (t - a) * sp
        a, b, r0, sp = self.sp["segs"][-1]
        return len(self.sp["segs"]) - 1, r0 + (b - a) * sp

    def track_dy(self, key, r):
        tr = self.tracks[key]
        k = round(r * 30) / 30
        keys = sorted(tr)
        best = min(keys, key=lambda x: abs(x - k))
        dy, sc = tr[best]
        return dy if sc > 0.55 else None

    # overlays on the window -------------------------------------------------------------
    def draw_overlays(self, img, t, r, vx0, vy0, s):
        sp = self.sp
        H, W = img.shape[:2]
        dim_f = np.ones((H, W), np.float32)
        add = np.zeros((H, W, 3), np.float32)
        ring_layers = []

        def to_win(x, y):
            return (x - vx0) * s, (y - vy0) * s

        for f in sp.get("focus", []):
            a, b = f["t0"], f["t1"]
            if not (a - 0.3 <= t <= b + 0.3):
                continue
            k = smooth((t - a) / 0.3) * (1 - smooth((t - b) / 0.3))
            if k <= 0.001:
                continue
            x0, y0, x1, y1 = f["rect"]
            if "track" in f:
                dy = self.track_dy(f["track"], r)
                if dy is None:
                    continue
                y0, y1 = y0 + dy, y1 + dy
            pad = f.get("pad", 18)
            pulse = 0.5 + 0.5 * math.sin((t - a) * 2 * math.pi / 1.1)
            wx0, wy0 = to_win(x0 - pad, y0 - pad)
            wx1, wy1 = to_win(x1 + pad, y1 + pad)
            if wy1 < 0 or wy0 > H or wx1 < 0 or wx0 > W:     # highlighted element is scrolled out of the viewport
                continue
            rad = min(f.get("radius", 40) * s * 1.4 + 6, (wx1 - wx0) / 2, (wy1 - wy0) / 2)
            d = rrect_sdf(_XX, _YY, wx0 - pulse * 3, wy0 - pulse * 3, wx1 + pulse * 3, wy1 + pulse * 3, rad + pulse * 3)
            inside = np.clip(0.5 - d / 16, 0, 1)
            dim = f.get("dim", 0.42)
            dim_f = np.minimum(dim_f, 1 - dim * k * (1 - inside))
            th = 3.2
            ring = np.clip(1.0 - np.abs(d) / th, 0, 1) * k * (0.82 + 0.18 * pulse)
            glow = np.exp(-np.maximum(d, 0) / 14) * 0.26 * k * (0.7 + 0.3 * pulse) * (d > -th)
            ring_layers.append((ring, glow))
        img *= dim_f[..., None]
        for ring, glow in ring_layers:
            add += glow[..., None] * AMBER
            img[:] = img * (1 - ring[..., None]) + AMBER * ring[..., None]
            core = np.clip(ring - 0.55, 0, 1) * 1.6
            img[:] = img * (1 - 0.18 * core[..., None]) + WHITE * 0.18 * core[..., None]
        img += add

        for tp in sp.get("taps", []):
            age = t - tp["t"]
            if age < -0.02 or age > 0.75:
                continue
            cx, cy = to_win(tp["x"], tp["y"])
            if not (-120 < cx < W + 120 and -120 < cy < H + 120):
                continue
            x0, x1 = int(max(cx - 130 * UI, 0)), int(min(cx + 130 * UI, W))
            y0, y1 = int(max(cy - 130 * UI, 0)), int(min(cy + 130 * UI, H))
            if x1 <= x0 or y1 <= y0:
                continue
            dist = np.hypot(_XX[y0:y1, x0:x1] - cx, _YY[y0:y1, x0:x1] - cy)
            u = min(max(age, 0) / 0.7, 1.0)
            rr = (16 + 86 * ease_out(u)) * UI
            ring = np.clip(1 - np.abs(dist - rr) / (3.2 * UI), 0, 1) * (1 - u) ** 1.4
            dot_r = 9 * UI * (1 - smooth(max(age, 0) / 0.30))
            dot = np.clip((dot_r - dist) / 1.5 + 0.5, 0, 1) * (1 - smooth(max(age, 0) / 0.40))
            halo = np.exp(-(dist / (rr + 10)) ** 2) * 0.10 * (1 - u)
            reg = img[y0:y1, x0:x1]
            reg[:] = reg * (1 - ring[..., None]) + AMBER * ring[..., None]
            reg[:] = reg * (1 - 0.85 * dot[..., None]) + WHITE * 0.85 * dot[..., None]
            reg[:] = reg * (1 - halo[..., None]) + AMBER * halo[..., None]

        for sw in sp.get("swipes", []):
            if not (sw["t0"] - 0.25 <= t <= sw["t1"] + 0.35):
                continue
            u = ease_io((t - sw["t0"]) / (sw["t1"] - sw["t0"]))
            fade = smooth((t - sw["t0"] + 0.25) / 0.25) * (1 - smooth((t - sw["t1"]) / 0.35))
            for j in range(7):
                uu = ease_io(max((t - sw["t0"]) / (sw["t1"] - sw["t0"]) - j * 0.035, 0))
                fx = sw["x0"] + (sw["x1"] - sw["x0"]) * uu
                cx, cy = to_win(fx, sw["y"])
                rad = 32 * UI * (1 - 0.06 * j)
                x0, x1 = int(max(cx - 60 * UI, 0)), int(min(cx + 60 * UI, W))
                y0, y1 = int(max(cy - 60 * UI, 0)), int(min(cy + 60 * UI, H))
                if x1 <= x0 or y1 <= y0:
                    continue
                dist = np.hypot(_XX[y0:y1, x0:x1] - cx, _YY[y0:y1, x0:x1] - cy)
                disc = np.clip((rad - dist) / 1.5 + 0.5, 0, 1)
                edge = np.clip(1 - np.abs(dist - rad) / 2.0, 0, 1)
                a = fade * (0.55 if j == 0 else 0.16 * (1 - j / 8))
                reg = img[y0:y1, x0:x1]
                reg[:] = reg * (1 - (disc * a)[..., None]) + WHITE * (disc * a)[..., None]
                if j == 0:
                    reg[:] = reg * (1 - (edge * fade)[..., None]) + AMBER * (edge * fade)[..., None]
        return img

    # one frame --------------------------------------------------------------------------
    def window_image(self, src, t, r):
        keys = self.sp["camera"]
        cx, cy, z = camera_at(keys, t)
        s_out = WIN_W * z / SRC_W
        vw = SRC_W / z
        vh = WIN_H / s_out
        vx0 = min(max(cx - vw / 2, 0), SRC_W - vw)
        vy0 = min(max(cy - vh / 2, 0), SRC_H - vh)
        lvl = 0.5 if s_out <= 0.49 else 0.75
        if lvl == 0.5:
            base = cv2.resize(src, (660, 1434), interpolation=cv2.INTER_AREA)
        else:
            base = src
        sc = s_out / lvl
        # window px = (src_px - v0) * s_out ; level px = src_px * lvl
        M = np.array([[sc, 0, -vx0 * s_out], [0, sc, -vy0 * s_out]], np.float32)
        img = cv2.warpAffine(base, M, (WIN_W, WIN_H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        img = img.astype(np.float32)
        img = self.draw_overlays(img, t, r, vx0, vy0, s_out)
        return np.clip(img, 0, 255).astype(np.uint8)

    def compose(self, src, pip, t, r):
        L = self.layers
        canvas = L.bg.copy()
        # background drift
        # phone shadow + glow + bezel
        px, py = WIN_X - L.pad, WIN_Y - L.pad
        L.blend_patch(canvas, px, py + 14, L.shadow, (0, 0, 0))
        L.blend_patch(canvas, px, py, L.glow * 0.5, AMBER * 0.85)
        win = self.window_image(src, t, r)
        reg = canvas[WIN_Y:WIN_Y + WIN_H, WIN_X:WIN_X + WIN_W].astype(np.float32)
        canvas[WIN_Y:WIN_Y + WIN_H, WIN_X:WIN_X + WIN_W] = (reg * (1 - L.win_mask) + win * L.win_mask).astype(np.uint8)
        L.blend_patch(canvas, px, py, L.bezel_a, (12, 12, 16))
        L.blend_patch(canvas, px, py, L.edge_a * 0.9, (190, 196, 210))
        if pip is not None and self.sp.get("pip", True):
            ppx, ppy = PIP_X - L.pip_pad, PIP_Y - L.pip_pad
            L.blend_patch(canvas, ppx, ppy + 8, L.pip_shadow, (0, 0, 0))
            reg = canvas[PIP_Y:PIP_Y + PIP_H, PIP_X:PIP_X + PIP_W].astype(np.float32)
            canvas[PIP_Y:PIP_Y + PIP_H, PIP_X:PIP_X + PIP_W] = (reg * (1 - L.pip_mask) + pip * L.pip_mask).astype(np.uint8)
            L.blend_patch(canvas, ppx, ppy, L.pip_ring * 0.95, AMBER)
        return canvas

    # decoders ---------------------------------------------------------------------------
    def decode_seg(self, i):
        a, b, r0, sp = self.sp["segs"][i]
        n = int(round((b - a) * FPS))
        vf = "scale=990:2151:flags=area"
        if abs(sp - 1) > 1e-6:
            vf = f"setpts=PTS/{sp},fps=30," + vf
        else:
            vf = "fps=30," + vf
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{r0:.4f}", "-i", SCREEN, "-frames:v", str(n + 2),
                              "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        fs = 990 * 2151 * 3
        last = None
        while True:
            buf = p.stdout.read(fs)
            if len(buf) < fs:
                break
            last = np.frombuffer(buf, np.uint8).reshape(2151, 990, 3)
            yield last
        while True:  # hold last frame if the segment is requested longer than the decode
            yield last

    def decode_pip(self):
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{self.t0:.4f}", "-i", BASE, "-frames:v", str(self.N + 2),
                              "-vf", f"crop=960:540:{self.sp.get('pip_crop_x', 560)}:{self.sp.get('pip_crop_y', 90)},"
                                     f"scale={PIP_W}:{PIP_H}:flags=area",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        fs = PIP_W * PIP_H * 3
        while True:
            buf = p.stdout.read(fs)
            if len(buf) < fs:
                yield None
                continue
            yield np.frombuffer(buf, np.uint8).reshape(PIP_H, PIP_W, 3).astype(np.float32)

    def render(self, out):
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW}x{CH}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
                                "-g", "30", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                                "-color_trc", "bt709", out], stdin=subprocess.PIPE)
        pip_gen = self.decode_pip() if os.path.exists(BASE) else iter(lambda: None, 1)
        cur, gen = -1, None
        for n in range(self.N):
            t = self.t0 + n / FPS
            i, r = self.seg_at(t)
            if i != cur:
                gen, cur = self.decode_seg(i), i
            src = next(gen)
            pip = next(pip_gen)
            enc.stdin.write(self.compose(src, pip, t, r).tobytes())
            if n % 150 == 0:
                print(f"{self.name}: {n}/{self.N}", flush=True)
        enc.stdin.close()
        enc.wait()

    def frame_at(self, t):
        i, r = self.seg_at(t)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{r:.4f}", "-i", SCREEN, "-frames:v", "1",
                              "-vf", "scale=990:2151:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        src = np.frombuffer(raw, np.uint8).reshape(2151, 990, 3)
        pip = None
        if os.path.exists(BASE):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", BASE, "-frames:v", "1", "-vf",
                                  f"crop=960:540:{self.sp.get('pip_crop_x', 560)}:{self.sp.get('pip_crop_y', 90)},"
                                  f"scale={PIP_W}:{PIP_H}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                 capture_output=True).stdout
            if len(raw) == PIP_W * PIP_H * 3:
                pip = np.frombuffer(raw, np.uint8).reshape(PIP_H, PIP_W, 3).astype(np.float32)
        return self.compose(src, pip, t, r)

    def check_cuts(self):
        segs = self.sp["segs"]
        for (a0, b0, r0, s0), (a1, b1, r1, s1) in zip(segs, segs[1:]):
            r_end = r0 + (b0 - a0) * s0
            def grab(r):
                raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{r:.4f}", "-i", SCREEN, "-frames:v", "1",
                                      "-vf", "scale=330:717:flags=area,format=gray", "-f", "rawvideo", "-"],
                                     capture_output=True).stdout
                return np.frombuffer(raw, np.uint8).reshape(717, 330).astype(float)
            d = np.abs(grab(r_end - 1 / 30) - grab(r1)).mean()
            print(f"cut @main {b0:7.2f}: r {r_end:7.2f} -> {r1:7.2f}   mean|diff| = {d:5.2f}  {'OK' if d < 1.5 else '<<< CHECK'}")


if __name__ == "__main__":
    cmd, name = sys.argv[1], sys.argv[2]
    sc = Scene(name)
    if cmd == "render":
        sc.render(sys.argv[3])
    elif cmd == "dump":
        os.makedirs(sys.argv[3], exist_ok=True)
        for tt in sys.argv[4:]:
            fr = sc.frame_at(float(tt))
            cv2.imwrite(f"{sys.argv[3]}/{name}_{float(tt):07.2f}.png", cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
    elif cmd == "check":
        sc.check_cuts()
