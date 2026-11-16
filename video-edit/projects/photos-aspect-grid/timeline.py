"""Timeline for the V Create video "see the real shape of every photo: Photos > View Options > Aspect Ratio Grid" -
Pop style (render_pop.py).  All times are narration seconds T (= output time of the 16:9 edit).  Screen times S are
seconds of the cleaned 30 fps copy of the 1320x2868 iPhone recording (screen_rules.py)."""
import numpy as np

STYLE = "pop"
FPS = 30
NARR_END = 109.30
TOTAL = NARR_END + 0.30                       # no end card
END_SWELL = 0.0
SCREEN_SIZE = (1320, 2868)
SCREEN_FPS = 30
SCREEN_T0, SCREEN_END = 0.0, 110.40
FACE_ANCHOR = dict(fx=0.586, fy=0.46)
LOGO = "vcreate.png"                           # assets/logo/ (V Create round badge)
LOGO_FILL = 0.98
CHANNEL = "V CREATE"
GRADE = dict(exposure=0.02, temp=0.012, tint=-0.002, dehaze=0.22, contrast=0.30, toe=0.012, shoulder=0.76,
             skin_sat=0.97, skin_warm=0.012, red_sat=0.92, red_val=0.97, green_sat=0.86, green_val=0.93, green_hue=-6.0,
             sky_teal=0.0, split=0.45, vibrance=0.10, sat=1.0, face_lift=0.14, face_contrast=0.08, clarity=0.08,
             halation=0.03, bloom=0.03, vignette=0.12, grain=0.008)
TOPIC_KICKER = "iPHONE · PHOTOS APP"
TOPIC = "Aspect Ratio Grid"

# ---- titles (3D blocks on paper; captions step aside) ---------------------------------------------------
Y, P, Wt, M = (255, 208, 48), (255, 90, 136), (255, 255, 255), (44, 206, 146)
TITLE_BEATS = [
    (-0.20, 1.24, [("iPHONE", Wt, 0.62), ("USERS!", Y, 1.0)], {"kicker": "PHOTOS APP TIP", "cy": 0.48}),
    (1.24, 3.60, [("ASPECT RATIO", Y, 0.80), ("GRID", P, 1.0)], {"kicker": "SEE THE REAL SHAPE", "cy": 0.48}),
]
TITLE_BEATS_REEL = [
    (-0.20, 1.24, [("iPHONE", Wt, 0.62), ("USERS!", Y, 1.0)], {"kicker": "PHOTOS APP TIP", "box": (0.84, 0.30), "cy": 0.46}),
    (1.24, 3.60, [("ASPECT", Y, 0.9), ("RATIO", Y, 0.9), ("GRID", P, 1.0)], {"kicker": "SEE THE REAL SHAPE", "box": (0.80, 0.40), "cy": 0.48}),
]
HEADERS = [                                    # full-frame interstitials: (t0, t1, lines, kicker)
    (60.45, 61.70, [("LET'S", Wt, 0.55), ("TURN IT ON", Y, 1.0)], "VERY SIMPLE"),
]

# ---- scenes -------------------------------------------------------------------------------------------
SCENES = [
    dict(kind="title", t0=0.0, t1=3.60, name="title"),
    dict(kind="face", t0=3.60, t1=24.00, zoom=(1.00, 1.05), name="intro"),
    dict(kind="phone", t0=24.00, t1=33.54, name="square-grid"),
    dict(kind="explain", t0=33.54, t1=49.60, name="which-fits"),
    dict(kind="face", t0=49.60, t1=60.45, zoom=(1.04, 1.08), name="why"),
    dict(kind="header", t0=60.45, t1=61.70, name="lets-go"),
    dict(kind="phone", t0=61.70, t1=100.20, name="steps"),
    dict(kind="face", t0=100.20, t1=NARR_END + 1.0, zoom=(1.03, 1.07), name="outro"),
]
WIPES = [3.60, 24.00, 33.54, 49.60, 60.45, 61.70, 100.20]       # yellow paper wipe centred on each cut
POPS = [76.56, 93.21]                                            # jumps inside the phone footage: punch-in
TRANSITIONS = [(t, "wipe") for t in WIPES] + [(t, "pop") for t in POPS]
TRANSITION_SFX = {"wipe": ("1492", -0.30, -14), "pop": ("1491", -0.20, -17)}

# ---- phone screen: narration T -> recording S ------------------------------------------------------------
SCREEN_MAP = [
    (24.00, 10.00), (33.60, 19.60),                                    # square grid (static)
    (61.70, 0.00), (62.70, 0.40), (63.45, 1.15), (66.60, 4.30),   # home screen, Photos opens
    (66.61, 51.90), (68.30, 53.60),                                    # tap the menu (S 52.6)
    (71.30, 56.35), (72.40, 57.45),                                    # tap View Options (S 56.45)
    (75.05, 67.50), (76.55, 69.00),                                    # tap Aspect Ratio Grid (S 67.6) - grid re-flows
    (76.56, 96.30), (77.40, 97.14), (93.20, 100.00),                   # menu closes on the new grid (static after)
    (93.21, 87.40), (94.50, 88.45), (95.40, 89.35), (95.72, 90.06), (96.46, 90.80),   # zoom in, zoom out
    (96.47, 93.40), (98.95, 96.40), (100.30, 97.75),                   # menu closes again
]


def screen_time(T):
    """Linear between rows; two rows at most 0.02 s apart are a cut (the earlier S holds until the later T), so no frame
    can land inside a jump and show the footage in between."""
    for (t0, s0), (t1, s1) in zip(SCREEN_MAP[:-1], SCREEN_MAP[1:]):
        if t1 - t0 <= 0.02 and t0 <= T < t1:
            return s0
    return float(np.interp(T, [p[0] for p in SCREEN_MAP], [p[1] for p in SCREEN_MAP]))


CAMERA = [(0.0, 1.0, 0.5, 0.5), (200.0, 1.0, 0.5, 0.5)]               # the phone stays whole; the loupe does the zooming

# ---- taps (T, u, v) -------------------------------------------------------------------------------------
TAPS = [(62.80, 0.610, 0.246), (67.30, 0.678, 0.087), (71.40, 0.420, 0.533), (75.13, 0.380, 0.418),
        (94.53, 0.380, 0.296), (95.72, 0.380, 0.419)]
TAP_SFX = "1109"

# ---- loupes: (T0, T1, (u, v) centre on the screen, half-width in u, label) -------------------------------
LOUPES = [
    (61.95, 62.84, (0.610, 0.246), 0.15, "Photos"),
    (63.70, 67.36, (0.690, 0.100), 0.10, "Menu"),
    (68.45, 71.42, (0.440, 0.533), 0.29, "View Options"),
    (72.30, 75.18, (0.450, 0.418), 0.29, "Aspect Ratio Grid"),
    (93.35, 94.55, (0.420, 0.296), 0.26, "Zoom In"),
    (94.95, 95.76, (0.420, 0.419), 0.26, "Zoom Out"),
]

# ---- marker rings on the phone (T0, T1, (u0, v0, u1, v1)) and stickers on thumbnails --------------------------
TILE_NABI = (0.335, 0.148, 0.665, 0.287)
TILE_232 = (0.335, 0.290, 0.665, 0.440)
TILE_WATER = (0.000, 0.290, 0.330, 0.440)
RINGS = [(30.79, 33.40, TILE_232), (31.67, 33.40, TILE_NABI)]
THUMB_TAGS = [                                   # (T0, T1, (u, v), text, colour)
    (28.95, 33.40, (0.500, 0.218), "1:1", Y), (29.25, 33.40, (0.165, 0.365), "1:1", Y), (29.55, 33.40, (0.500, 0.365), "1:1", Y),
    (79.99, 93.10, (0.171, 0.225), "9:16", Y), (80.45, 93.10, (0.829, 0.225), "16:9", P),
    (80.95, 93.10, (0.500, 0.376), "9:16", Y), (81.40, 93.10, (0.828, 0.376), "9:16", Y),
]
SIDE_NOTES = [                                   # stickers in the free zone beside the phone: (T0, T1, text, colour, row)
    (24.60, 33.40, "EVERYTHING IS CROPPED", Wt, 0),
    (27.40, 33.40, "TO A SQUARE", Y, 1),
    (77.00, 93.10, "NOW: THE REAL SHAPE", Y, 0),
    (83.65, 93.10, "SEE EVERY ASPECT RATIO", Wt, 1),
    (89.34, 93.10, "9:16 = STATUS ✓", M, 2),
    (89.86, 93.10, "9:16 = REELS ✓", M, 3),
    (96.60, 100.10, "SET IT YOUR WAY", Y, 0),
]
STEPS = [                                        # checklist (wide) / step sticker (reel): (T0, T1, n, label)
    (61.70, 66.50, 1, "Open Photos"),
    (66.50, 68.32, 2, "Tap the menu"),
    (68.32, 72.20, 3, "View Options"),
    (72.20, 76.40, 4, "Aspect Ratio Grid"),
    (93.21, 98.95, 5, "Zoom in / out (optional)"),
]
N_STEPS = 5

# ---- face-scene stickers (right column in 16:9, over the card's top in 9:16) -------------------------------
FACE_NOTES = [                                   # (T0, T1, text, colour)
    (50.84, 56.70, "9:16 ?", Y), (51.40, 56.70, "16:9 ?", P), (51.90, 56.70, "1:1 ?", Wt),
]
TIP_STAMP = (53.56, 56.70, "ONE SIMPLE TIP")
CTAS = [(11.70, "share"), (16.60, "subscribe"), (19.95, "like"), (21.30, "comment"), (56.80, "share"),
        (102.40, "share"), (105.60, "subscribe")]

# ---- explainer (33.54 - 49.60): use-case stickers, then square tiles nobody can read the shape of ----------
EXPLAIN = dict(
    uses=[(33.98, "WhatsApp Status", "chat", M), (35.64, "Reels", "play", P), (36.88, "Anything else", "star", Wt)],
    tiles_t=39.27, question_t=40.21, hard_t=45.95, out_t=49.45,
)


def _cta_sfx(ctas):
    out = []
    for t0, what in ctas:
        out += [(t0, "2350", -16), (t0 + 1.15, "2354", -12)]
        if what == "subscribe":
            out += [(t0 + 1.25, "933", -16)]
    return out


BASE_SFX = ([(0.0, "1485", -12), (1.24, "1492", -15), (60.45, "1485", -14)]
            + [(t0, "2350", -18) for t0, *_ in THUMB_TAGS] + [(t0, "2350", -18) for t0, *_ in SIDE_NOTES]
            + [(t0, "2350", -18) for t0, *_ in FACE_NOTES] + [(TIP_STAMP[0], "1485", -18)]
            + [(t, "2350", -17) for t, *_ in EXPLAIN["uses"]] + [(EXPLAIN["tiles_t"], "1492", -17), (EXPLAIN["hard_t"], "1485", -17)]
            + [(t0 + 0.05, "3005", -18) for t0, *_ in LOUPES])
EXTRA_SFX = BASE_SFX + _cta_sfx(CTAS)

# ---- 9:16 reel: the whole talk minus the like / comment request and the first share request --------------------
REEL_CUTS = [(0.00, 19.48), (23.92, 56.80), (59.02, NARR_END)]
REEL_PAD = (0.06, 0.10)                          # as in the renderer / mixer


def reel_time(T):
    """Narration T -> reel output time (None when cut)."""
    u = 0.0
    for a, b in REEL_CUTS:
        a, b = max(a - REEL_PAD[0], 0.0), min(b + REEL_PAD[1], NARR_END)
        if a <= T < b:
            return u + T - a
        u += b - a
    return None


REEL_CTAS = [(11.70, "share"), (16.60, "follow"), (102.40, "share"), (105.60, "follow")]   # narration time
REEL_EXTRA_SFX = [(reel_time(t), n, g) for t, n, g in _cta_sfx(REEL_CTAS) if reel_time(t) is not None]
REEL_JOIN_SFX = False
