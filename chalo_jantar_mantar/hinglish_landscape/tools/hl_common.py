"""Shared helpers for the landscape (1920x1080) Hinglish lyric video: constants, easing, noise textures, sprite blending."""
import math
import numpy as np
from PIL import Image

W, H, FPS = 1920, 1080, 30          # output
WW, WH = 1280, 720                   # working resolution of the procedural background (upscaled 1.5x at the end)
BEAT, PHASE = 0.6475, 0.31           # 92.66 BPM grid measured from the audio
BAR = 4 * BEAT                       # 2.59 s

SAFFRON = (1.0, 0.60, 0.20)
WHITE = (1.0, 1.0, 1.0)
GREEN = (0.10, 0.55, 0.20)
GOLD = (1.0, 0.78, 0.30)
RED = (0.86, 0.12, 0.12)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_out_quint(x):
    x = clamp(x)
    return 1 - (1 - x) ** 5


def ease_in_out(x):
    x = clamp(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_out_back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_c(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def bar_pos(t):
    """Position inside the current bar in [0,1) and the bar index."""
    x = (t - PHASE) / BAR
    return x - math.floor(x), int(math.floor(x))


def beat_pulse(t, decay=7.0):
    """Sharp-attack / exponential-decay pulse that peaks on every beat of the 92.66 BPM grid."""
    x = ((t - PHASE) / BEAT) % 1.0
    return math.exp(-decay * x)


# ----------------------------------------------------------------------------------------------------------------------
# tileable noise (FFT-filtered) and a wrap-around sampler
# ----------------------------------------------------------------------------------------------------------------------
def fbm_tex(w, h, beta=2.2, seed=0, stretch=1.0):
    """Tileable fractal noise via FFT filtering. stretch > 1 elongates features horizontally (stratus-like)."""
    rng = np.random.RandomState(seed)
    fx = np.fft.fftfreq(w)[None, :] * stretch
    fy = np.fft.fftfreq(h)[:, None]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    amp = 1.0 / (f ** beta)
    amp[0, 0] = 0
    ph = rng.uniform(0, 2 * np.pi, (h, w))
    img = np.fft.ifft2(amp * np.exp(1j * ph)).real
    lo, hi = np.percentile(img, [1, 99])
    return np.clip((img - lo) / (hi - lo), 0, 1).astype(np.float32)


class Tile:
    """Tileable float texture sampled with wrap-around, scale and sub-pixel offsets (PIL affine on a 2x2 tiled copy).
    The sampled window is clamped so it can never leave the tiled image (no black fill)."""

    def __init__(self, arr):
        self.h, self.w = arr.shape
        big = np.tile(arr, (2, 2))
        self.im = Image.fromarray(big.astype(np.float32), mode="F")

    def sample(self, ox, oy, out_w, out_h, sx=1.0, sy=None, resample=Image.BILINEAR):
        sy = sx if sy is None else sy
        sx = min(sx, (self.w - 2.0) / out_w)
        sy = min(sy, (self.h - 2.0) / out_h)
        ox = ox % self.w
        oy = oy % self.h
        return np.asarray(self.im.transform((out_w, out_h), Image.AFFINE, (sx, 0, ox, 0, sy, oy), resample=resample), dtype=np.float32)


# ----------------------------------------------------------------------------------------------------------------------
# blending helpers on float32 RGB images (H,W,3) in 0..1
# ----------------------------------------------------------------------------------------------------------------------
def over(dst, rgb, a):
    """dst = dst*(1-a) + rgb*a ; rgb either (3,) colour or (h,w,3); a (h,w) or (h,w,1)."""
    if a.ndim == 2:
        a = a[..., None]
    dst *= (1 - a)
    dst += (np.asarray(rgb, np.float32) * a)
    return dst


def screen(dst, add):
    """Screen blend: 1-(1-dst)(1-add)."""
    np.subtract(1.0, dst, out=dst)
    dst *= (1.0 - np.clip(add, 0, 1))
    np.subtract(1.0, dst, out=dst)
    return dst


def gauss_blur(arr2d_or_3d, radius):
    """Fast gaussian blur through PIL (works on uint8-converted data); input float 0..1 (h,w) or (h,w,3)."""
    from PIL import ImageFilter
    a = np.clip(arr2d_or_3d, 0, 1)
    if a.ndim == 2:
        im = Image.fromarray((a * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius))
        return np.asarray(im, np.float32) / 255.0
    im = Image.fromarray((a * 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(im, np.float32) / 255.0


def resize_f(arr, w, h, resample=Image.BICUBIC):
    """Resize a float (h,w) or (h,w,3) array through PIL 'F' planes."""
    if arr.ndim == 2:
        return np.asarray(Image.fromarray(arr.astype(np.float32), "F").resize((w, h), resample), np.float32)
    return np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(arr[..., c]).astype(np.float32), "F").resize((w, h), resample), np.float32)
                     for c in range(3)], axis=-1)
