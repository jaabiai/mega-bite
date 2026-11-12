"""Cinematic grade v2 ("film" look) for daylight face-cam footage shot on a phone.

Float32 RGB in 0..1 (Rec.709 display referred) -> graded float32 RGB, at output resolution.  Order of operations
mirrors a colourist's node tree:

  1. balance      exposure trim, white balance (temperature / tint)
  2. dehaze       pulls the milky haze out of bright, low-saturation background (window, sky, fields)
  3. tone         filmic curve with a soft toe and a long highlight shoulder (no clipped sky)
  4. colour       hue-selective work in HSV: skin kept natural (and protected from the split tone),
                  loud reds calmed, foliage pushed to olive, sky to cyan; teal shadows / warm highlights
  5. face         soft power window that follows the face track: a little exposure and local contrast
  6. clarity      large-radius local contrast on luminance
  7. film         halation (warm glow around hot edges), bloom, vignette, fine luminance grain

All strengths live in a params dict so a project can trim them (timeline.GRADE).
"""
import cv2
import numpy as np

DEFAULT = dict(
    exposure=-0.14,       # stops
    temp=0.000,           # + warmer (R up, B down)
    tint=-0.004,          # + magenta / - green
    dehaze=0.30,
    contrast=0.44,        # S-curve strength
    toe=0.022,            # black lift
    shoulder=0.70,        # highlight knee
    skin_sat=0.94, skin_warm=0.010,
    red_sat=0.80, red_val=0.93,
    green_sat=0.56, green_val=0.84, green_hue=-11.0,   # degrees; negative = toward yellow / olive
    sky_teal=0.040,
    split=1.55,           # teal shadows / warm highlights
    vibrance=0.06, sat=0.92,
    face_lift=0.16, face_contrast=0.10,
    clarity=0.10,
    halation=0.07, bloom=0.05,
    vignette=0.32,
    grain=0.016,
)


def _ss(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _blur(x, sigma):
    """Large-radius Gaussian blur computed at reduced resolution (same look, a fraction of the cost)."""
    h, w = x.shape[:2]
    f = 1 if sigma < 4 else (2 if sigma < 10 else 4)
    if f == 1:
        return cv2.GaussianBlur(x, (0, 0), sigma)
    small = cv2.resize(x, (w // f, h // f), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / f)
    out = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return out if out.ndim == x.ndim else out[..., None]


def _curve_lut(contrast, toe, shoulder):
    x = np.linspace(0, 1, 2048, dtype=np.float32)
    s = x + contrast * (_ss(x) - x)                    # S around mid grey
    s = toe + s * (1.0 - toe)                          # lifted, milky-free blacks
    hi = s > shoulder                                  # long shoulder: highlights roll off instead of clipping
    k = 1.0 - shoulder
    s[hi] = shoulder + k * (1.0 - np.exp(-(s[hi] - shoulder) / k * 1.15)) / (1.0 - np.exp(-1.15))
    return np.clip(s, 0, 1).astype(np.float32)


class Grader:
    def __init__(self, w, h, params=None, seed=11):
        self.w, self.h = w, h
        self.p = dict(DEFAULT)
        if params:
            self.p.update(params)
        p = self.p
        self.lut = _curve_lut(p["contrast"], p["toe"], p["shoulder"])
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.xx, self.yy = xx / w, yy / h
        self.rng = np.random.default_rng(seed)
        self._vig = {}

    # -- helpers -------------------------------------------------------------------------------------------
    def _vignette(self, cx, cy):
        key = (round(cx, 2), round(cy, 2))
        if key not in self._vig:
            d = np.sqrt(((self.xx - cx) / 0.78) ** 2 + ((self.yy - cy) / 0.86) ** 2)
            self._vig[key] = (1.0 - self.p["vignette"] * _ss((d - 0.42) / 0.78))[..., None].astype(np.float32)
        return self._vig[key]

    def _face_mask(self, face):
        fx, fy, rx, ry = face
        d = np.sqrt(((self.xx - fx) / rx) ** 2 + ((self.yy - fy) / ry) ** 2)
        return (1.0 - _ss((d - 0.45) / 0.85))[..., None].astype(np.float32)

    # -- the grade -----------------------------------------------------------------------------------------
    def __call__(self, rgb, face=None, center=(0.5, 0.48), grain_on=True):
        p = self.p
        h, w = rgb.shape[:2]
        img = rgb.astype(np.float32, copy=False)

        # 1. balance
        img = img * (2.0 ** p["exposure"])
        img = img * np.array([1.0 + p["temp"], 1.0 - p["tint"], 1.0 - p["temp"]], np.float32)

        # 2. dehaze: bright, low-saturation areas (haze) get the airlight subtracted
        mx, mn = img.max(-1, keepdims=True), img.min(-1, keepdims=True)
        sat = (mx - mn) / (mx + 1e-4)
        luma = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        haze = _ss((luma - 0.45) / 0.40) * np.clip(1.0 - sat[..., 0] * 2.2, 0, 1)
        haze = _blur(haze, 6)[..., None]
        k = p["dehaze"] * haze
        A = 0.92
        img = (img - A * k) / np.maximum(1.0 - k, 0.35)

        # 3. tone
        img = np.interp(np.clip(img, 0, 1) * 2047.0, np.arange(2048, dtype=np.float32), self.lut).astype(np.float32)

        # 4. colour (HSV, H in degrees)
        hsv = cv2.cvtColor(np.clip(img, 0, 1), cv2.COLOR_RGB2HSV)
        H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        hd = lambda c, wdt: np.exp(-((((H - c) + 180.0) % 360.0 - 180.0) / wdt) ** 2)
        skin = hd(24.0, 16.0) * _ss((S - 0.10) / 0.12) * (1 - _ss((S - 0.62) / 0.2)) * _ss((V - 0.12) / 0.15)
        red = hd(356.0, 11.0) * _ss((S - 0.40) / 0.25)
        green = hd(95.0, 34.0) * _ss((S - 0.12) / 0.15)
        sky = np.maximum(hd(200.0, 30.0) * _ss((V - 0.55) / 0.3), _ss((V - 0.72) / 0.2) * (1 - _ss(S / 0.16)) * (1 - skin))
        S = S * (1 - skin * (1 - p["skin_sat"]))
        S = S * (1 - red * (1 - p["red_sat"]))
        V = V * (1 - red * (1 - p["red_val"]))
        S = S * (1 - green * (1 - p["green_sat"]))
        V = V * (1 - green * (1 - p["green_val"]))
        H = (H + green * p["green_hue"]) % 360.0
        S = S * (p["sat"] + (1 - p["sat"]) * np.maximum(skin, hd(22.0, 14.0) * _ss((S - 0.45) / 0.2)))   # global film desat, skin / orange kept
        S = np.clip(S + p["vibrance"] * (1 - S) * S * (1 - skin), 0, 1)
        hsv = np.stack([H, S, np.clip(V, 0, 1)], -1)
        img = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        skin3 = skin[..., None]
        img = img + skin3 * np.array([p["skin_warm"], p["skin_warm"] * 0.3, -p["skin_warm"]], np.float32)
        img = img + sky[..., None] * np.array([-p["sky_teal"], p["sky_teal"] * 0.25, p["sky_teal"] * 0.6], np.float32)
        luma = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        l3 = luma[..., None]
        sh = 1.0 - _ss(l3 / 0.58)
        hl = _ss((l3 - 0.58) / 0.38)
        teal = np.array([-0.024, 0.006, 0.026], np.float32)
        warm = np.array([0.014, 0.006, -0.012], np.float32)
        img = img + p["split"] * (sh * teal * (1 - 0.8 * skin3) + hl * warm)

        # 5. face window
        if face is not None and p["face_lift"] > 0:
            fm = self._face_mask(face)
            blur_f = _blur(img, max(h, w) / 160.0)
            img = img * (1.0 + p["face_lift"] * fm) + p["face_contrast"] * fm * (img - blur_f)

        # 6. clarity (luminance local contrast)
        L = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        Lb = _blur(L, max(h, w) / 70.0)
        img = img + p["clarity"] * (L - Lb)[..., None]

        # 7. film: halation + bloom from the hot parts, vignette, grain
        hot = np.clip((img.max(-1) - 0.78) / 0.22, 0, 1)
        if p["halation"] > 0:
            hal = _blur(hot, max(h, w) / 260.0)
            img = img + p["halation"] * hal[..., None] * np.array([1.0, 0.42, 0.22], np.float32)
        if p["bloom"] > 0:
            blo = _blur(hot, max(h, w) / 45.0)
            img = img + p["bloom"] * blo[..., None] * np.array([1.0, 0.92, 0.80], np.float32)
        img = img * self._vignette(*center)
        if grain_on and p["grain"] > 0:
            g = self.rng.standard_normal((h // 2, w // 2)).astype(np.float32)
            g = cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
            L = np.clip(img @ np.array([0.2126, 0.7152, 0.0722], np.float32), 0, 1)
            img = img + (p["grain"] * g * (0.35 + 0.65 * (1 - np.abs(L - 0.5) * 2)))[..., None]
        return np.clip(img, 0, 1)
