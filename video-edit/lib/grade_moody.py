"""Moody green thriller grade (reference: the misty high-range look of Malayalam thrillers such as "Varathan").

Built on top of grade_cine.Grader (balance, dehaze, filmic curve, hue-selective work, skin protection, face window,
halation, bloom, vignette, grain) with three extra stages:

1. highlight roll-off before the grade: the blown sky in the window is pulled down into a soft, grey-green mist;
2. a printer-light style colour decision (lift / gamma / gain per channel): green-teal shadows, olive-green mids,
   slightly cool cream highlights;
3. a final low-saturation pass that keeps skin warmer than the rest (skin is never allowed to go green).

    g = MoodyGrader(w, h, TL.GRADE_MOODY)
    out = g(rgb_float, face=(fx, fy, rx, ry), center=(cx, cy))
"""
import numpy as np
import cv2
from grade_cine import Grader, _ss, _blur

DEFAULT = dict(
    # pre: highlight roll-off (the bright window / sky)
    knee=0.52, roll=2.4, mist=0.30, mist_rgb=(0.86, 0.93, 0.89),
    # base grade (grade_cine.Grader parameters)
    base=dict(exposure=-0.24, temp=-0.012, tint=-0.018, dehaze=0.26, contrast=0.50, toe=0.030, shoulder=0.64,
              skin_sat=0.86, skin_warm=0.008, red_sat=0.66, red_val=0.88, green_sat=0.62, green_val=0.74, green_hue=7.0,
              sky_teal=0.05, split=1.10, vibrance=0.0, sat=0.80, face_lift=0.16, face_contrast=0.12, clarity=0.12,
              halation=0.10, bloom=0.09, vignette=0.46, grain=0.020),
    # post: lift / gamma / gain (R, G, B)
    lift=(-0.010, 0.020, 0.012), gamma=(0.965, 1.035, 0.985), gain=(0.975, 1.000, 0.950),
    sat=0.86, skin_keep=0.55, shadow_green=0.018,
)


class MoodyGrader:
    def __init__(self, w, h, params=None, seed=17):
        p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT.items()}
        if params:
            for k, v in params.items():
                if k == "base":
                    p["base"].update(v)
                else:
                    p[k] = v
        self.p = p
        self.base = Grader(w, h, p["base"], seed=seed)
        self.lift = np.array(p["lift"], np.float32)
        self.gamma = 1.0 / np.array(p["gamma"], np.float32)
        self.gain = np.array(p["gain"], np.float32)
        self.mist_rgb = np.array(p["mist_rgb"], np.float32)

    def _rolloff(self, img):
        p = self.p
        L = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        k, r = p["knee"], p["roll"]
        over = np.maximum(L - k, 0.0)
        Lc = np.where(L > k, k + (1 - k) * 0.86 * (1 - np.exp(-over / (1 - k) * r)) / (1 - np.exp(-r)), L)
        scale = (Lc / np.maximum(L, 1e-4))[..., None]
        img = img * scale
        hi = _ss((L - 0.62) / 0.38)[..., None] * p["mist"]
        return (img * (1 - hi) + Lc[..., None] * self.mist_rgb * hi).astype(np.float32)

    def _skin(self, img):
        hsv = cv2.cvtColor(np.clip(img, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        d = np.abs(((H - 22.0) + 180.0) % 360.0 - 180.0)
        return (np.exp(-(d / 16.0) ** 2) * _ss((S - 0.12) / 0.12) * (1 - _ss((S - 0.65) / 0.2)) * _ss((V - 0.10) / 0.15))[..., None]

    def __call__(self, rgb, face=None, center=(0.5, 0.48), grain_on=True):
        p = self.p
        img = self._rolloff(np.asarray(rgb, np.float32))
        skin0 = self._skin(img)
        img = self.base(img, face=face, center=center, grain_on=grain_on)
        # printer-light colour decision
        x = np.clip(img, 0, 1)
        x = x * self.gain + self.lift * (1 - x)
        x = np.clip(x, 0, 1) ** self.gamma
        # green-black shadows
        L = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        sh = (1 - _ss(L / 0.35))[..., None]
        x = x + sh * np.array([-0.4, 1.0, 0.45], np.float32) * p["shadow_green"]
        # low saturation, skin kept warmer
        L = (x @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
        s = p["sat"] + (1 - p["sat"]) * p["skin_keep"] * skin0
        x = L + (x - L) * s
        # skin must not turn green: pull its green channel back toward its original balance
        x = x + skin0 * np.array([0.010, -0.012, -0.004], np.float32)
        return np.clip(x, 0, 1).astype(np.float32)
