"""Timeline for the V Create video "build your own free AI assistant (Tab)" - Aurora style (render_aurora.py).

All times are narration seconds (= 16:9 output time).  Screen-recording times (S) are seconds of the cleaned 30 fps copy.
"""
import numpy as np

STYLE = "aurora"
FPS = 30
NARR_END = 177.48
TOTAL = NARR_END + 0.30                       # no end card: a short fade after the last word
END_SWELL = 0.0                               # mix_audio: no music swell at the end
FACE_ANCHOR = dict(fx=0.57, fy=0.46)
GRADE = dict(clarity=0.08, face_lift=0.16, tint=0.6)
STING_T0 = 8.70                               # "Welcome to V Create"

# ---- full-screen 3D title (the topic), spoken over the first 7 s ---------------------------------------
TITLE_BEATS = [
    (-0.35, 2.86, [("YOUR OWN", "white", 0.58), ("AI ASSISTANT", "aurora", 1.0)]),
    (2.88, 5.78, [("DOES ANYTHING", "white", 0.80), ("YOU SAY", "aurora", 1.0)]),
    (5.80, 6.95, [("AND IT'S", "white", 0.40), ("FREE", "aurora", 1.0)]),
]
TITLE_BEATS_REEL = [
    (-0.35, 2.86, [("YOUR OWN", "white", 0.50), ("AI", "aurora", 1.25), ("ASSISTANT", "aurora", 0.62)]),
    (2.88, 5.78, [("DOES", "white", 0.55), ("ANYTHING", "aurora", 1.0), ("YOU SAY", "white", 0.86)]),
    (5.80, 6.95, [("AND IT'S", "white", 0.40), ("FREE", "aurora", 1.0)]),
]
# section header in 3D: (T0, T1, wide lines, reel lines)
HEADERS_3D = [
    (95.40, 96.95, [("HOW TO", "white", 0.55), ("SET IT UP", "aurora", 1.0)],
     [("HOW TO", "white", 0.55), ("SET IT UP", "aurora", 1.0)]),
]

# ---- scenes -------------------------------------------------------------------------------------------
F = lambda t0, t1, z=(1.0, 1.05), name="face", **k: dict(kind="face", t0=t0, t1=t1, zoom=z, name=name, **k)
B = lambda t0, t1, clip, ct=0.0, name=None, cx=0.5: dict(kind="broll", t0=t0, t1=t1, clip=clip, clip_t=ct, reel_cx=cx,
                                                         name=name or f"b{clip}_{t0}")
SCENES = [
    dict(kind="title", t0=0.0, t1=6.95, name="title"),
    F(6.95, 21.20, (1.0, 1.06), "intro"),
    B(21.20, 23.75, "49042", 3.0, "robot"),
    B(23.75, 26.50, "29050", 1.5, "restaurant"),
    B(26.50, 29.80, "32457", 1.0, "food"),
    B(29.80, 34.05, "4196", 2.0, "hotel"),
    B(34.05, 38.25, "23073", 4.0, "call", cx=0.55),
    B(38.25, 41.70, "3298", 2.0, "takeoff"),
    B(41.70, 45.10, "17999", 2.0, "clouds"),
    B(45.10, 48.00, "42123", 2.0, "shop-phone", cx=0.62),
    B(48.00, 51.60, "49381", 2.0, "clothes", cx=0.45),
    B(51.60, 54.40, "51123", 1.0, "screenshot"),
    F(54.40, 58.00, (1.10, 1.13), "order"),
    B(58.00, 61.00, "42130", 2.5, "delivery"),
    F(61.00, 67.28, (1.0, 1.04), "flight"),
    B(67.28, 71.00, "1787", 1.5, "email", cx=0.42),
    F(71.00, 76.10, (1.0, 1.04), "auto"),
    F(76.10, 82.40, (1.12, 1.16), "simple"),
    F(82.40, 95.40, (1.0, 1.06), "cta"),
    F(95.40, 99.10, (1.08, 1.12), "link"),
    dict(kind="phone", t0=99.10, t1=167.20, name="steps"),
    F(167.20, NARR_END + 1.0, (1.0, 1.07), "outro"),
]

TRANSITIONS = [
    (6.95, "prism"), (21.20, "sweep"), (54.40, "sweep"), (58.00, "sweep"), (61.00, "sweep"), (67.28, "sweep"),
    (71.00, "sweep"), (99.10, "prism"), (139.10, "sweep"), (155.00, "sweep"), (167.20, "prism"),
]
TRANSITION_SFX = {"prism": ("1491", -0.35, -12), "sweep": ("1492", -0.30, -15), "dip": None}

TAGS = [(7.25, 10.30, "Jabir Varikkodan"), (97.20, 99.05, "Link in the description")]

# ---- calls to action ----------------------------------------------------------------------------------------
CTAS = [(14.60, "like"), (84.30, "subscribe"), (87.00, "share"), (93.60, "save"), (169.20, "share"), (172.50, "subscribe")]


def _cta_sfx(ctas):
    out = []
    for c in ctas:
        t0, what = c[0], c[1]
        if what == "subscribe":
            out += [(t0 + 1.2, "2354", -11), (t0 + 1.35, "933", -15)]
        elif what in ("like", "share", "comment", "save"):
            out += [(t0 + {"like": 0.8, "share": 1.0, "comment": 0.9, "save": 0.85}[what], "2350", -15)]
    return out


BASE_SFX = [(0.02, "1485", -12), (2.84, "1492", -15), (5.76, "1492", -15), (STING_T0 - 0.08, "2596", -11),
            (95.35, "1485", -13)]
EXTRA_SFX = BASE_SFX + _cta_sfx(CTAS)

# ---- reel: whole sentences in narration order (few joins, all at scene changes or covered by the 3D header) ---
REEL_CUTS = [(0.00, 6.85), (10.64, 29.66), (38.40, 60.84), (67.30, 76.06), (95.70, 114.20), (116.76, 135.84),
             (139.36, 167.08), (174.67, 177.30)]
REEL_CTAS = [(11.5, "like"), (52.0, "share"), (121.4, "subscribe")]
REEL_EXTRA_SFX = _cta_sfx(REEL_CTAS)
REEL_JOIN_SFX = False
TAP_SFX = "1109"

# ---- phone screen: narration T -> recording S --------------------------------------------------------------
SCREEN_FPS = 30
SCREEN_T0, SCREEN_END = 0.0, 137.5
SCREEN_MAP = [                       # jumps at 110.2 and 155.0 skip frames where the number is not yet / no longer blurred
    (99.10, 0.30), (101.40, 1.40), (103.90, 2.60), (107.60, 4.40), (108.10, 4.75), (108.70, 5.60), (109.90, 8.70),
    (110.20, 8.95), (110.2001, 9.33), (112.50, 10.00), (113.20, 10.75), (117.00, 14.60), (119.60, 16.80), (120.40, 17.60),
    (121.90, 19.40), (122.50, 20.00), (123.60, 23.70), (124.30, 24.30), (139.05, 40.80),
    (139.10, 46.00), (142.90, 49.80), (142.95, 77.00), (143.60, 78.10), (145.00, 80.60), (145.40, 81.20),
    (146.30, 83.00), (147.30, 85.20), (147.70, 86.80), (148.20, 91.90), (148.60, 92.40), (148.65, 93.35),
    (150.30, 94.90), (150.35, 97.60), (151.30, 98.80), (151.70, 99.30), (154.9999, 104.50),
    (155.00, 116.20), (156.65, 116.85), (156.66, 118.00), (157.20, 118.80), (157.85, 119.45),
    (157.86, 121.10), (158.50, 122.05), (159.15, 122.70), (159.16, 124.30), (159.80, 125.10), (160.45, 125.75),
    (160.46, 132.80), (161.10, 133.60), (167.20, 135.60),
]


def screen_time(T):
    return float(np.interp(T, [p[0] for p in SCREEN_MAP], [p[1] for p in SCREEN_MAP]))


# ---- camera on the whole phone: (T, zoom, u, v) ---------------------------------------------------------
OV = lambda t, z=1.0: (t, z, 0.5, 0.5)
CAMERA = [
    (99.10, 0.92, 0.5, 0.5), OV(99.7), (100.3, 1.35, 0.5, 0.80), (101.3, 1.35, 0.5, 0.80), OV(102.2), OV(104.0),
    (104.7, 1.45, 0.5, 0.25), (107.4, 1.45, 0.5, 0.25), (108.3, 1.60, 0.5, 0.33), (109.9, 1.60, 0.5, 0.31),
    (110.7, 1.30, 0.5, 0.42), (112.6, 1.30, 0.5, 0.40), (113.3, 1.70, 0.5, 0.313), (116.8, 1.70, 0.5, 0.313),
    (117.6, 1.55, 0.5, 0.43), (120.4, 1.55, 0.5, 0.43), (121.3, 1.55, 0.5, 0.50), (122.8, 1.55, 0.5, 0.50),
    OV(123.7), (124.4, 1.40, 0.5, 0.20), (127.0, 1.40, 0.5, 0.20), OV(128.0), OV(129.6),
    (130.4, 1.45, 0.5, 0.21), (135.6, 1.45, 0.5, 0.21), OV(136.6), OV(142.8),
    (143.3, 1.60, 0.63, 0.15), (144.4, 1.60, 0.63, 0.15), OV(145.2), (146.0, 1.60, 0.5, 0.27), (148.7, 1.60, 0.5, 0.31),
    (149.6, 1.15, 0.5, 0.45), (150.3, 1.15, 0.5, 0.45), (151.6, 1.50, 0.5, 0.60), (154.8, 1.50, 0.5, 0.60),
    (155.2, 1.15, 0.5, 0.50), (160.9, 1.15, 0.5, 0.50), (161.6, 1.35, 0.5, 0.62), (166.6, 1.35, 0.5, 0.62),
    (167.2, 1.20, 0.5, 0.50),
]

# ---- taps (T, u, v) and spotlight highlights (T0, T1, (u0, v0, u1, v1), label) -----------------------------
TAPS = [(108.05, 0.5, 0.435), (120.10, 0.12, 0.392), (122.25, 0.5, 0.525), (143.65, 0.635, 0.108),
        (145.35, 0.5, 0.565), (148.55, 0.5, 0.326)]
HIGHLIGHTS = [
    (99.70, 101.30, (0.38, 0.922, 0.70, 0.958), "tab.bot"),
    (104.30, 107.40, (0.12, 0.172, 0.88, 0.285), "This page"),
    (108.30, 109.90, (0.07, 0.272, 0.93, 0.328), "First name"),
    (113.30, 116.80, (0.07, 0.288, 0.93, 0.338), "Mobile number"),
    (117.60, 120.30, (0.08, 0.378, 0.92, 0.478), "Tick the agreement"),
    (121.50, 122.60, (0.075, 0.503, 0.925, 0.549), "Sign up"),
    (124.40, 127.00, (0.04, 0.100, 0.96, 0.250), "You're on the waitlist"),
    (130.20, 135.60, (0.04, 0.168, 0.96, 0.248), "Then text \"Hey Tab\""),
    (143.30, 144.40, (0.57, 0.088, 0.70, 0.128), "Sign in"),
    (146.10, 147.90, (0.08, 0.228, 0.92, 0.278), "Mobile number"),
    (148.00, 148.62, (0.08, 0.305, 0.92, 0.350), "Send code"),
    (151.70, 154.80, (0.08, 0.627, 0.92, 0.695), "Text Tab once to finish setup"),
    (161.30, 166.90, (0.18, 0.712, 0.82, 0.800), "Photo edits"),
]

STEPS = [
    (99.10, 107.60, 1, "Open tab.bot"),
    (107.60, 117.00, 2, "Name & mobile number"),
    (117.00, 123.60, 3, "Tick & Sign up"),
    (123.60, 139.10, 4, "Wait for your Tab line"),
    (139.10, 152.60, 5, "Sign in with your number"),
    (152.60, 167.20, 6, "Text Tab anything"),
]
N_STEPS = 6
