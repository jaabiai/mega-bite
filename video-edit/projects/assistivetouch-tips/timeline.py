"""Timeline for the V Create video "two AssistiveTouch tips: screenshot and restart without buttons" - Signal style
(render_signal.py).  All times are narration seconds T (= output time of the 16:9 edit).  Screen times S are seconds
of the cleaned 30 fps copy of the 1320x2868 iPhone recording (screen_rules.py)."""
import numpy as np

STYLE = "signal"
FPS = 30
NARR_END = 183.45
TOTAL = NARR_END + 0.35                        # no end card
END_SWELL = 0.0
SCREEN_SIZE = (1320, 2868)
SCREEN_FPS = 30
SCREEN_T0, SCREEN_END = 0.0, 390.80
FACE_ANCHOR = dict(fx=0.586, fy=0.46)
LOGO = "vcreate.png"
CHANNEL = "V CREATE"
GRADE = dict(exposure=-0.10, temp=0.006, tint=-0.004, dehaze=0.34, contrast=0.50, toe=0.020, shoulder=0.70,
             skin_sat=0.95, skin_warm=0.012, red_sat=0.82, red_val=0.94, green_sat=0.52, green_val=0.80, green_hue=-14.0,
             sky_teal=0.06, split=1.70, vibrance=0.05, sat=0.90, face_lift=0.18, face_contrast=0.12, clarity=0.10,
             halation=0.08, bloom=0.05, vignette=0.36, grain=0.018)
BROLL_GRADE = dict(exposure=-0.04, dehaze=0.15, green_sat=0.7, vignette=0.30)

# ---- opening title --------------------------------------------------------------------------------------------
TITLE_BEATS = [(-0.20, 3.04, [("2 BRILLIANT", "silver", 0.58), ("iPHONE TRICKS", "lime", 1.0)],
                {"kicker": "V CREATE  ·  iPHONE TIPS", "sub": "that most people still don't know", "cy": 0.44})]
TITLE_BEATS_REEL = [(-0.20, 3.04, [("2 BRILLIANT", "silver", 0.62), ("iPHONE", "lime", 1.0), ("TRICKS", "lime", 1.0)],
                     {"kicker": "V CREATE  ·  iPHONE TIPS", "sub": "most people don't know", "cy": 0.40, "box": (0.84, 0.26)})]

# ---- the two tips: (T0, T1, n, title, path) - the ring fills from T0 to T1 ------------------------------------------
TIPS = [
    (23.82, 101.10, 1, "Screenshot without buttons", "AssistiveTouch  →  Device  →  Screenshot"),
    (101.50, 171.40, 2, "Restart without buttons", "AssistiveTouch  →  System  →  Restart"),
]
TIP_CARD = 2.3

# ---- scenes -----------------------------------------------------------------------------------------------------
F = lambda t0, t1, z=(1.0, 1.04), tx=0.60, name=None: dict(kind="face", t0=t0, t1=t1, zoom=z, tx=tx, name=name or f"f{t0}")
C = lambda t0, t1, name=None: F(t0, t1, (1.16, 1.20), 0.68, name)              # close framing
B = lambda t0, t1, clip, ct=0.0, cx=0.5, rcx=0.5, name=None: dict(kind="broll", t0=t0, t1=t1, clip=clip, clip_t=ct, cx=cx,
                                                                  reel_cx=rcx, name=name or f"b{clip}_{t0}")
P = lambda t0, t1, name: dict(kind="phone", t0=t0, t1=t1, name=name)
SCENES = [
    dict(kind="title", t0=0.0, t1=3.04, name="title"),
    F(3.04, 7.00),
    B(7.00, 10.68, "21262", 2.0, 0.55, 0.55),
    C(10.68, 18.79),
    F(18.79, 23.82),
    F(23.82, 28.89, (1.0, 1.03)),
    B(28.89, 33.60, "1711", 1.0, 0.5, 0.62),
    F(33.60, 41.00),
    C(41.00, 48.31),
    P(48.31, 101.50, "tip1"),
    F(101.50, 105.55),
    B(105.55, 109.86, "21605", 1.5, 0.5, 0.5),
    C(109.86, 118.56),
    F(118.56, 123.07),
    B(123.07, 129.86, "8757", 0.5, 0.5, 0.45),
    C(129.86, 132.56),
    P(132.56, 141.32, "restart-demo"),
    F(141.32, 145.43),
    P(145.43, 171.70, "tip2"),
    B(171.70, 175.40, "9067", 1.0, 0.5, 0.5),
    C(175.40, NARR_END + 1.0),
]
MIXES = [sc["t0"] for sc in SCENES[2:]]                 # lens-blur crossfade on every cut after the title
TRANSITIONS = [(t, "mix") for t in MIXES]
TRANSITION_SFX = {"mix": ("1492", -0.25, -17)}

# ---- highlights ----------------------------------------------------------------------------------------------------
KEY_WORDS = ["screenshot", "screenshots", "assistivetouch", "restart", "settings", "customise", "device", "system",
             "plus", "power", "check", "hangs", "button", "buttons", "shortcut"]
KEY_POINTS = [                                          # (T0, T1, phrase) - 16:9 left column
    (37.29, 40.90, "Something simpler is built in"),
    (51.36, 54.00, "Add Screenshot to AssistiveTouch"),
    (113.11, 118.24, "Add Restart to AssistiveTouch"),
    (125.79, 129.34, "Phone hanging? Restart it"),
    (132.56, 135.40, "No buttons needed"),
]

# ---- prompts ----------------------------------------------------------------------------------------------------
CTAS = [(15.40, "share"), (19.60, "like"), (21.10, "comment"), (177.20, "share"), (180.40, "subscribe")]
REEL_CTAS = [(15.40, "share"), (177.20, "share"), (180.40, "follow")]

# ---- phone: narration T -> recording S (rows <= 0.02 s apart are cuts) ------------------------------------------------
SCREEN_MAP = [
    # tip 1 - the finished AssistiveTouch menu, then Settings -> search -> AssistiveTouch
    (48.31, 1.60), (54.00, 7.30), (55.36, 10.60), (56.75, 12.62), (57.60, 13.85), (58.10, 16.00), (58.60, 16.60),
    (58.61, 26.60), (59.80, 29.10), (59.81, 34.00), (63.35, 35.70), (64.50, 36.85), (67.64, 40.00),
    (67.65, 57.60), (69.53, 59.50), (72.05, 59.85), (72.25, 60.05),
    (72.26, 77.00), (79.17, 84.39), (80.30, 85.50), (81.55, 89.00), (82.20, 89.65), (83.00, 90.45),     # 4 icons, +, new slot
    (83.01, 230.00), (83.72, 230.71), (84.40, 231.40), (89.87, 236.33), (91.10, 237.56), (94.38, 242.10),  # Device, Done
    (95.00, 242.70), (98.55, 245.15), (100.20, 246.80), (101.60, 248.20),                                  # open, Screenshot
    # restart: the finished menu
    (132.56, 374.55), (136.30, 376.00), (136.90, 376.55), (141.40, 378.15),
    # tip 2 - Settings -> AssistiveTouch -> Customise -> + -> slot -> System -> Restart -> Done -> open
    (145.43, 330.90), (146.40, 331.75), (146.90, 332.30), (146.91, 335.90), (148.33, 337.38), (149.40, 338.60),
    (152.00, 341.08), (152.60, 341.65), (154.38, 343.43), (155.20, 344.25), (156.90, 346.10), (157.50, 346.70),
    (159.00, 348.20), (159.01, 357.00), (159.82, 357.81), (160.50, 358.50), (162.18, 361.68), (162.90, 362.30),
    (162.91, 372.20), (165.28, 374.05), (166.00, 374.77), (168.15, 375.98), (168.60, 376.45), (171.80, 378.15),
]


def screen_time(T):
    """Linear between rows; two rows at most 0.02 s apart are a cut (the earlier S holds until the later T)."""
    for (t0, s0), (t1, s1) in zip(SCREEN_MAP[:-1], SCREEN_MAP[1:]):
        if t1 - t0 <= 0.02 and t0 <= T < t1:
            return s0
    return float(np.interp(T, [p[0] for p in SCREEN_MAP], [p[1] for p in SCREEN_MAP]))


# ---- camera on the phone: (T, zoom, u, v) ---------------------------------------------------------------------------
O = lambda t: (t, 1.0, 0.5, 0.5)
CAMERA = [
    O(48.31), (49.30, 1.35, 0.52, 0.40), (54.00, 1.35, 0.52, 0.40), O(55.00), (55.90, 1.30, 0.60, 0.64), (56.90, 1.30, 0.60, 0.64),
    O(57.60), O(58.60), (59.10, 1.45, 0.50, 0.45), (59.80, 1.45, 0.50, 0.45), (60.40, 1.75, 0.62, 0.22), (63.70, 1.75, 0.62, 0.22),
    (64.40, 1.55, 0.70, 0.30), (67.64, 1.55, 0.70, 0.30), (68.60, 1.65, 0.50, 0.38), (72.05, 1.65, 0.50, 0.38),
    (72.60, 1.05, 0.50, 0.45), (77.20, 1.05, 0.50, 0.45), (78.00, 1.75, 0.74, 0.60), (79.60, 1.75, 0.74, 0.60),
    (80.40, 1.35, 0.50, 0.33), (81.60, 1.35, 0.50, 0.33), (82.30, 1.55, 0.50, 0.40), (84.30, 1.55, 0.50, 0.40),
    (85.00, 1.55, 0.50, 0.55), (87.60, 1.55, 0.50, 0.55), (88.30, 1.80, 0.76, 0.16), (89.90, 1.80, 0.76, 0.16),
    (90.80, 1.40, 0.50, 0.34), (92.80, 1.40, 0.50, 0.34), (93.40, 1.45, 0.74, 0.62), (94.50, 1.45, 0.74, 0.62),
    (95.30, 1.40, 0.50, 0.52), (100.0, 1.40, 0.50, 0.52), O(101.5),
    O(132.56), (133.40, 1.45, 0.70, 0.48), (136.30, 1.45, 0.70, 0.48), (137.00, 1.45, 0.50, 0.53), (141.40, 1.45, 0.50, 0.53),
    O(145.43), O(146.90), (147.50, 1.45, 0.50, 0.45), (148.40, 1.45, 0.50, 0.45), (149.20, 1.65, 0.50, 0.38),
    (152.00, 1.65, 0.50, 0.38), (152.70, 1.05, 0.50, 0.45), (153.50, 1.75, 0.74, 0.60), (154.50, 1.75, 0.74, 0.60),
    (155.30, 1.40, 0.50, 0.47), (157.00, 1.40, 0.50, 0.47), (157.70, 1.55, 0.50, 0.50), (159.90, 1.55, 0.50, 0.50),
    (160.60, 1.45, 0.50, 0.56), (162.90, 1.45, 0.50, 0.56), (163.60, 1.80, 0.76, 0.16), (165.40, 1.80, 0.76, 0.16),
    (166.10, 1.40, 0.60, 0.48), (168.30, 1.40, 0.60, 0.48), (169.00, 1.40, 0.50, 0.53), (171.80, 1.40, 0.50, 0.53),
]

# ---- taps (T, u, v) and highlights (T0, T1, (u0, v0, u1, v1), label) ---------------------------------------------------
TAPS = [(56.75, 0.61, 0.70), (58.12, 0.50, 0.945), (59.80, 0.50, 0.47), (63.40, 0.86, 0.186), (72.05, 0.50, 0.378),
        (79.17, 0.82, 0.642), (81.55, 0.50, 0.235), (83.72, 0.30, 0.402), (86.60, 0.30, 0.572), (89.87, 0.875, 0.11),
        (94.38, 0.91, 0.735), (98.60, 0.50, 0.40),
        (136.33, 0.91, 0.53),
        (146.38, 0.50, 0.945), (148.35, 0.50, 0.47), (152.00, 0.50, 0.378), (154.38, 0.853, 0.64), (156.90, 0.50, 0.49),
        (159.84, 0.30, 0.585), (162.20, 0.30, 0.59), (165.28, 0.875, 0.11), (168.17, 0.91, 0.53)]
HIGHLIGHTS = [
    (48.90, 51.30, (0.14, 0.23, 0.91, 0.55), "AssistiveTouch menu"),
    (51.40, 54.00, (0.60, 0.27, 0.80, 0.40), "Screenshot"),
    (55.90, 56.75, (0.53, 0.66, 0.69, 0.75), "Settings"),
    (59.20, 59.80, (0.03, 0.445, 0.97, 0.50), "AssistiveTouch"),
    (60.50, 63.40, (0.03, 0.165, 0.97, 0.21), "Turn it on"),
    (64.60, 67.60, (0.83, 0.355, 0.92, 0.405), "AssistiveTouch button"),
    (69.70, 72.05, (0.03, 0.355, 0.97, 0.40), "Customise Top Level Menu"),
    (77.60, 79.17, (0.77, 0.62, 0.88, 0.665), "Add"),
    (80.50, 81.55, (0.41, 0.20, 0.59, 0.275), "New slot"),
    (82.40, 83.72, (0.03, 0.380, 0.97, 0.425), "Device"),
    (85.60, 87.60, (0.03, 0.552, 0.97, 0.592), "Screenshot"),
    (88.40, 89.87, (0.82, 0.085, 0.93, 0.135), "Done"),
    (91.20, 93.00, (0.42, 0.19, 0.58, 0.27), "Screenshot added"),
    (93.30, 94.38, (0.86, 0.71, 0.96, 0.76), ""),
    (95.60, 98.60, (0.40, 0.365, 0.60, 0.455), "Screenshot"),
    (133.20, 136.30, (0.86, 0.505, 0.96, 0.555), "AssistiveTouch"),
    (138.40, 141.20, (0.40, 0.575, 0.60, 0.66), "Restart"),
    (147.60, 148.35, (0.03, 0.445, 0.97, 0.50), "AssistiveTouch"),
    (150.00, 152.00, (0.03, 0.355, 0.97, 0.40), "Customise Top Level Menu"),
    (153.30, 154.38, (0.80, 0.62, 0.90, 0.665), "Add"),
    (155.60, 156.90, (0.41, 0.45, 0.59, 0.53), "New slot"),
    (158.20, 159.84, (0.03, 0.56, 0.97, 0.61), "System"),
    (161.40, 162.20, (0.03, 0.57, 0.97, 0.61), "Restart"),
    (163.60, 165.28, (0.82, 0.085, 0.93, 0.135), "Done"),
    (166.10, 167.60, (0.42, 0.455, 0.58, 0.535), "Restart added"),
    (167.60, 168.17, (0.86, 0.505, 0.96, 0.555), ""),
    (169.30, 171.50, (0.40, 0.575, 0.60, 0.66), "Restart"),
]
STEPS = [                                         # step line in the free column: (T0, T1, n, label)
    (55.36, 59.90, 1, "Settings  ›  search AssistiveTouch"),
    (59.90, 69.50, 2, "Turn AssistiveTouch on"),
    (69.50, 77.30, 3, "Customise Top Level Menu"),
    (77.30, 84.60, 4, "Tap +  ›  new slot  ›  Device"),
    (84.60, 90.30, 5, "Screenshot  ›  Done"),
    (90.30, 101.00, 6, "Open AssistiveTouch  ›  Screenshot"),
    (145.43, 149.30, 1, "Settings  ›  AssistiveTouch"),
    (149.30, 152.50, 2, "Customise Top Level Menu"),
    (152.50, 157.70, 3, "Tap +  ›  new slot"),
    (157.70, 163.50, 4, "System  ›  Restart"),
    (163.50, 166.50, 5, "Tap Done"),
    (166.50, 171.40, 6, "Open AssistiveTouch  ›  Restart"),
]


def _cta_sfx(ctas):
    out = []
    for t0, what in ctas:
        out += [(t0, "1491", -20), (t0 + 1.2, "2354", -13)]
        if what == "subscribe":
            out += [(t0 + 1.3, "933", -17)]
    return out


BASE_SFX = ([(0.0, "1485", -12)] + [(t0, "2596", -13) for t0, *_ in TIPS] + [(t1, "3005", -15) for _, t1, *_ in TIPS]
            + [(t0 + 0.1, "3005", -20) for t0, *_ in KEY_POINTS])
EXTRA_SFX = BASE_SFX + _cta_sfx(CTAS)

# ---- 9:16 reel: the talk without the repeats ("many know, more don't", like / comment, "old option, not new") -------
REEL_CUTS = [(0.00, 3.04), (12.84, 18.79), (22.48, 40.92), (46.10, 118.42), (123.16, 141.76), (143.90, NARR_END)]
REEL_PAD = (0.06, 0.10)


def reel_time(T):
    u = 0.0
    for a, b in REEL_CUTS:
        a, b = max(a - REEL_PAD[0], 0.0), min(b + REEL_PAD[1], NARR_END)
        if a <= T < b:
            return u + T - a
        u += b - a
    return None


REEL_EXTRA_SFX = [(reel_time(t), n, g) for t, n, g in _cta_sfx(REEL_CTAS) if reel_time(t) is not None]
REEL_JOIN_SFX = False
