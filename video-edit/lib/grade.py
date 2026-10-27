"""Cinematic colour grade for the main (face-cam) footage.

Operates on float32 RGB frames in 0..1 (display referred, Rec.709 / sRGB-ish).
All numbers are tuned for this clip: backlit van interior, blown-out sky on the
left, face a little under-exposed, vivid green foliage.
"""
import cv2
import numpy as np

# Face "power window" (normalised coords of the 16:9 frame).
FACE_CX, FACE_CY = 0.54, 0.36
FACE_RX, FACE_RY = 0.26, 0.42


def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def build_curve_lut():
    """Filmic S-curve + highlight roll-off, as a 1D LUT over 0..1."""
    x = np.linspace(0, 1, 1024, dtype=np.float32)
    # gentle S contrast around mid grey
    s = x + 0.22 * (_smoothstep(x) - x)
    # lift blacks a touch (film-like), roll highlights off above the knee
    s = 0.015 + s * 0.985
    knee = 0.78
    hi = s > knee
    s[hi] = knee + (s[hi] - knee) * 0.62
    return np.clip(s, 0, 1)


_LUT = build_curve_lut()
_masks = {}


def _window_masks(h, w, face=None):
    fx, fy, rx, ry = face or (FACE_CX, FACE_CY, FACE_RX, FACE_RY)
    key = (h, w, round(fx, 3), round(fy, 3), round(rx, 3), round(ry, 3))
    if key in _masks:
        return _masks[key]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xx /= w
    yy /= h
    d = np.sqrt(((xx - fx) / rx) ** 2 + ((yy - fy) / ry) ** 2)
    face = 1.0 - _smoothstep((d - 0.35) / 0.9)           # 1 at face, 0 outside
    # vignette: darker towards the corners, extra weight on the left (sky)
    dv = np.sqrt(((xx - 0.52) / 0.75) ** 2 + ((yy - 0.45) / 0.80) ** 2)
    vig = 1.0 - 0.38 * _smoothstep((dv - 0.60) / 0.80)
    left = 1.0 - 0.07 * _smoothstep((0.38 - xx) / 0.38)   # tiny pull on the white sky
    m = (face[..., None], (vig * left)[..., None])
    _masks[key] = m
    return m


def grade(rgb, grain=0.0, rng=None, face=None, clarity=0.12, face_lift=0.20, tint=1.0):
    """rgb: float32 HxWx3 in 0..1 -> graded float32.  clarity / face_lift / tint (strength of the teal-orange split tone) are per-project."""
    h, w, _ = rgb.shape
    face, vig = _window_masks(h, w, face)

    # 1. face exposure lift (~ +0.35 stop) with a soft window
    img = rgb * (1.0 + face_lift * face)

    # 2. highlight / sky handling before the curve
    img = np.clip(img, 0, 1.4)

    # 3. filmic curve through the 1D LUT
    idx = np.clip(img, 0, 1) * 1023.0
    img = np.interp(idx, np.arange(1024), _LUT).astype(np.float32)

    # 4. colour: split-tone (teal shadows, warm highlights, neutral-warm mids)
    luma = (img * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    sh = (1.0 - _smoothstep(luma / 0.45)) * 1.0
    hl = _smoothstep((luma - 0.55) / 0.40)
    teal = np.array([-0.020, 0.006, 0.030], np.float32)
    warm = np.array([0.012, 0.006, -0.014], np.float32)
    img = img + tint * (sh * teal + hl * warm)

    # 5. selective saturation in HSV: calm the loud greens, add vibrance
    hsv = cv2.cvtColor(np.clip(img, 0, 1), cv2.COLOR_RGB2HSV)  # H 0..360
    hue = hsv[..., 0]
    green = np.exp(-((hue - 100.0) / 38.0) ** 2)               # foliage
    hsv[..., 1] *= (1.00 - 0.38 * green)
    # nudge foliage hue slightly toward teal for the cinematic palette
    hsv[..., 0] = np.where(green > 0.05, hue + 10.0 * green, hue)
    hsv[..., 1] = np.clip(hsv[..., 1], 0, 1)
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    # 5b. clarity: gentle large-radius local contrast on luminance
    blur = cv2.GaussianBlur(img, (0, 0), max(h, w) / 90.0)
    img = np.clip(img + clarity * (img - blur), 0, 1)

    # 6. vignette
    img = img * vig

    # 7. subtle grain
    if grain > 0:
        rng = rng or np.random.default_rng(7)
        g = rng.standard_normal((h, w, 1)).astype(np.float32) * grain
        img = img + g * (0.4 + 0.6 * (1 - np.abs(luma - 0.5) * 2))

    return np.clip(img, 0, 1)
