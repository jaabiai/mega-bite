"""Timeline for the V Create video "record calls without the announcement" (Google Phone app on Android) - Studio style
(render_studio.py).  All times are narration seconds (= output time in both formats; the reel is the whole talk).
Screen-recording times (S) are seconds of the cleaned 30 fps copy of the 720x1608 Android recording."""
import numpy as np

STYLE = "studio"
FPS = 30
NARR_END = 95.30
TOTAL = NARR_END + 0.30                      # no end card
END_SWELL = 0.0
DEVICE = "android"                            # punch-hole camera top-left
SCREEN_SIZE = (720, 1608)
SCREEN_FPS = 30
SCREEN_T0, SCREEN_END = 0.0, 93.5
FACE_ANCHOR = dict(fx=0.55, fy=0.40)
GRADE = dict(clarity=0.08, face_lift=0.14, tint=0.4)
STING_T0 = 22.45                              # "Welcome to V Create"
TOPIC_KICKER = "Google Phone app · Android"
TOPIC = "Record calls without the announcement"
TOPIC_SHORT = "Record calls without the announcement"

# ---- full-screen 3D title (the topic), spoken over the first 11 s ----------------------------------------
TITLE_BEATS = [
    (-0.35, 4.80, [("“THIS CALL IS", "white", 0.66), ("BEING RECORDED”", "rec", 1.0)]),
    (4.82, 8.70, [("THE OTHER PERSON", "white", 0.56), ("HEARS IT", "accent", 1.0)]),
    (8.78, 11.20, [("HERE'S THE", "white", 0.42), ("FIX", "accent", 1.0)]),
]
TITLE_BEATS_REEL = [
    (-0.35, 4.80, [("“THIS CALL", "white", 0.62), ("IS BEING", "white", 0.62), ("RECORDED”", "rec", 1.0)]),
    (4.82, 8.70, [("THE OTHER", "white", 0.6), ("PERSON", "white", 0.6), ("HEARS IT", "accent", 1.0)]),
    (8.78, 11.20, [("HERE'S THE", "white", 0.42), ("FIX", "accent", 1.0)]),
]
HEADERS_3D = [(26.05, 28.35, [("LET'S", "white", 0.5), ("SEE HOW", "accent", 1.0)], [("LET'S", "white", 0.5), ("SEE HOW", "accent", 1.0)])]

# ---- scenes -------------------------------------------------------------------------------------------
F = lambda t0, t1, z=(1.0, 1.05), name="face": dict(kind="face", t0=t0, t1=t1, zoom=z, name=name)
B = lambda t0, t1, clip, ct=0.0, name=None, cx=0.5: dict(kind="broll", t0=t0, t1=t1, clip=clip, clip_t=ct, cx=cx, reel_cx=cx,
                                                         name=name or f"b{clip}_{t0}")
SCENES = [
    dict(kind="title", t0=0.0, t1=11.20, name="title"),
    F(11.20, 26.05, (1.0, 1.05), "intro"),
    F(26.05, 28.80, (1.08, 1.10), "see-how"),
    B(28.80, 33.20, "42123", 3.0, "android-phone", cx=0.62),
    F(33.20, 37.80, (1.0, 1.04), "simple"),
    dict(kind="phone", t0=37.80, t1=78.50, name="steps"),
    B(78.50, 82.60, "39803", 1.0, "call-1", cx=0.55),
    B(82.60, 85.60, "309", 4.0, "call-2", cx=0.5),
    F(85.60, NARR_END + 1.0, (1.04, 1.08), "outro"),
]
TRANSITIONS = [(11.20, "prism"), (28.80, "push"), (33.20, "push"), (37.80, "push"), (78.50, "push"), (82.60, "scan"), (85.60, "push")]
TRANSITION_SFX = {"prism": ("1491", -0.35, -12), "push": ("1492", -0.30, -15), "scan": ("1491", -0.30, -16)}

# ---- prompts ------------------------------------------------------------------------------------------------
CTAS = [(13.30, "subscribe"), (16.70, "share"), (85.70, "like"), (88.30, "share"), (91.40, "subscribe")]


def _cta_sfx(ctas):
    out = []
    for c in ctas:
        t0, what = c[0], c[1]
        if what == "subscribe":
            out += [(t0 + 1.2, "2354", -11), (t0 + 1.35, "933", -15)]
        elif what in ("like", "share", "comment"):
            out += [(t0 + {"like": 0.8, "share": 1.0, "comment": 0.9}[what], "2350", -15)]
    return out


BASE_SFX = [(0.02, "1485", -12), (4.78, "1492", -15), (8.74, "1492", -15), (STING_T0 - 0.08, "2596", -11), (26.00, "1485", -13)]
EXTRA_SFX = BASE_SFX + _cta_sfx(CTAS)
TAP_SFX = "1109"

# ---- phone screen: narration T -> recording S --------------------------------------------------------------
SCREEN_MAP = [
    (37.80, 7.50), (40.60, 10.95), (41.60, 11.95), (53.30, 31.35), (54.00, 31.45), (54.60, 32.00), (55.60, 34.45),
    (56.20, 34.75), (57.00, 35.90), (59.20, 39.35), (60.60, 40.80), (61.60, 41.80), (62.50, 42.90), (66.90, 52.90),
    (67.30, 53.30), (68.00, 54.00), (71.60, 57.60), (72.00, 57.95), (72.40, 58.40), (78.50, 64.50),
]


def screen_time(T):
    return float(np.interp(T, [p[0] for p in SCREEN_MAP], [p[1] for p in SCREEN_MAP]))


# ---- camera on the whole phone: (T, zoom, u, v) ---------------------------------------------------------
OV = lambda t, z=1.0: (t, z, 0.5, 0.5)
CAMERA = [
    (37.80, 0.94, 0.5, 0.5), OV(38.6), (40.0, 1.35, 0.6, 0.82), (41.2, 1.35, 0.6, 0.82), OV(41.9), OV(42.8),
    (43.5, 1.70, 0.25, 0.15), (53.2, 1.70, 0.25, 0.15), (54.6, 1.25, 0.40, 0.25), (55.0, 1.50, 0.35, 0.20), (56.3, 1.50, 0.35, 0.20),
    OV(57.0), (57.5, 1.45, 0.5, 0.62), (59.4, 1.45, 0.5, 0.62), OV(60.3), OV(62.6), (63.2, 1.55, 0.55, 0.72), (67.6, 1.55, 0.55, 0.72),
    (68.2, 1.25, 0.5, 0.5), (70.3, 1.25, 0.5, 0.5), (70.9, 1.60, 0.70, 0.68), (72.2, 1.60, 0.70, 0.68), (72.8, 1.55, 0.55, 0.72),
    (78.5, 1.50, 0.55, 0.72),
]

# ---- taps (T, u, v) and highlights (T0, T1, (u0, v0, u1, v1), label) --------------------------------------
TAPS = [(40.62, 0.59, 0.893), (54.05, 0.09, 0.081), (55.98, 0.30, 0.226), (59.32, 0.40, 0.633), (67.33, 0.90, 0.720),
        (71.95, 0.755, 0.703)]
TOGGLE = (0.04, 0.685, 0.97, 0.756)
HIGHLIGHTS = [
    (40.00, 41.00, (0.52, 0.858, 0.67, 0.930), "Phone app"),
    (43.60, 53.40, (0.03, 0.055, 0.15, 0.108), "Menu"),
    (55.20, 56.30, (0.04, 0.200, 0.62, 0.252), "Settings"),
    (57.50, 59.40, (0.03, 0.602, 0.97, 0.664), "Call recording"),
    (63.00, 67.40, TOGGLE, "Play audio tone"),
    (68.40, 70.40, (0.13, 0.262, 0.87, 0.725), "Recording consent"),
    (70.60, 72.00, (0.66, 0.684, 0.85, 0.722), ""),
    (72.60, 78.30, TOGGLE, "Turned on"),
]
STEPS = [
    (37.80, 53.60, 1, "Open the Phone app"),
    (53.60, 56.60, 2, "Menu → Settings"),
    (56.60, 59.60, 3, "Call recording"),
    (59.60, 68.00, 4, "Turn on Play audio tone"),
    (68.00, 78.50, 5, "Tap Agree"),
]
N_STEPS = 5
