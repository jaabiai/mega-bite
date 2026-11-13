"""iPhone case review (V Create) - "Showcase" product-film edit.

All times are SOURCE times in Main.mp4 (3840x2160, 30 fps).  WIDE_CUTS / REEL_CUTS list the kept source ranges in order;
the renderer and the mixer map output time through them.  Narration: Malayalam; captions: captions_data.py.
"""
STYLE = "showcase"
FPS = 30
NARR_END = 222.70                      # last spoken word ends
SRC_END = 222.86

# ---- edit decision lists -------------------------------------------------------------------------------------
WIDE_CUTS = [(0.40, 149.97), (150.70, 222.86)]          # drops the opening stutter and a false start before the price
WIDE_JOIN_SFX = False
REEL_CUTS = [            # merged where ranges touch (the reel pads every range by 0.06 s / 0.10 s)
    (0.40, 9.02),          # hook: looking for a case? an excellent one - great look, really useful
    (27.39, 54.50),        # this iPhone case, killer look, camera design, five colours, iPhone 13 onwards
    (54.68, 85.50),        # action button covered, drop protection, camera protection
    (97.81, 109.40),       # raised border - no scratches
    (117.69, 119.74),      # MagSafe
    (141.92, 144.90),      # button grip
    (145.95, 149.95),      # overall
    (150.72, 161.25),      # price
    (181.17, 198.15),      # heat vents
    (199.61, 203.65),      # link in the description
]
REEL_JOIN_SFX = False

# ---- grade (lib/grade_cine.py params) ------------------------------------------------------------------------
GRADE = {}

# ---- camera: (t, cx, cy, zoom) in source-normalised coords; "cut" rows switch instantly ----------------------
# wide uses a 2.39:1 window (zoom 1 = full width, 74% height); the reel a 4:5 window (zoom 1 = full height).
CAM_WIDE = [
    (0.00, 0.50, 0.50, 1.00), (9.0, 0.50, 0.50, 1.02),
    (9.06, 0.55, 0.43, 1.10, "cut"), (14.45, 0.55, 0.43, 1.13),
    (14.50, 0.53, 0.45, 1.00, "cut"), (20.35, 0.54, 0.44, 1.04),
    (20.39, 0.57, 0.40, 1.16, "cut"), (26.05, 0.57, 0.40, 1.18),
    (26.07, 0.52, 0.45, 1.02, "cut"), (29.75, 0.53, 0.45, 1.04),
    (29.78, 0.55, 0.47, 1.00, "cut"), (34.0, 0.57, 0.47, 1.04), (37.62, 0.58, 0.48, 1.07),
    (37.68, 0.56, 0.46, 1.00, "cut"), (44.85, 0.56, 0.46, 1.03),
    (45.17, 0.56, 0.44, 1.10, "cut"), (52.80, 0.56, 0.44, 1.12),
    (52.84, 0.55, 0.43, 1.05, "cut"), (56.58, 0.55, 0.42, 1.10),
    (56.62, 0.50, 0.42, 1.18, "cut"), (62.85, 0.52, 0.42, 1.20),
    (63.56, 0.55, 0.42, 1.06, "cut"), (69.98, 0.55, 0.42, 1.08),
    (70.01, 0.55, 0.47, 1.00, "cut"), (80.95, 0.56, 0.47, 1.04),
    (80.98, 0.58, 0.44, 1.08, "cut"), (88.95, 0.58, 0.45, 1.10),
    (89.00, 0.58, 0.47, 1.00, "cut"), (97.78, 0.58, 0.47, 1.03),
    (97.81, 0.60, 0.49, 1.20, "cut"), (109.40, 0.60, 0.49, 1.24),
    (109.43, 0.58, 0.47, 1.00, "cut"), (116.12, 0.58, 0.47, 1.02),
    (116.16, 0.50, 0.50, 1.00, "cut"), (121.62, 0.50, 0.50, 1.02),
    (121.66, 0.55, 0.40, 1.28, "cut"), (133.62, 0.55, 0.42, 1.30),
    (133.66, 0.58, 0.45, 1.25, "cut"), (141.88, 0.58, 0.45, 1.25),
    (141.92, 0.50, 0.45, 1.00, "cut"), (149.95, 0.52, 0.45, 1.04),
    (150.70, 0.56, 0.42, 1.14, "cut"), (159.40, 0.56, 0.42, 1.16),
    (159.60, 0.53, 0.45, 1.00, "cut"), (167.05, 0.53, 0.45, 1.04),
    (167.08, 0.56, 0.42, 1.14, "cut"), (175.68, 0.56, 0.42, 1.16),
    (175.70, 0.53, 0.46, 1.00, "cut"), (181.15, 0.53, 0.46, 1.02),
    (181.17, 0.50, 0.50, 1.00, "cut"), (198.15, 0.50, 0.50, 1.03),
    (198.21, 0.55, 0.43, 1.10, "cut"), (209.40, 0.55, 0.43, 1.12),
    (209.43, 0.53, 0.45, 1.00, "cut"), (215.30, 0.53, 0.45, 1.02),
    (215.32, 0.57, 0.41, 1.14, "cut"), (223.0, 0.57, 0.41, 1.17),
]
CAM_REEL = [
    (0.00, 0.47, 0.50, 1.00), (9.0, 0.47, 0.50, 1.02),
    (27.39, 0.55, 0.50, 1.00, "cut"), (29.75, 0.56, 0.50, 1.02),
    (29.78, 0.57, 0.50, 1.00, "cut"), (37.62, 0.58, 0.50, 1.04),
    (37.68, 0.57, 0.50, 1.00, "cut"), (44.85, 0.57, 0.50, 1.02),
    (45.17, 0.55, 0.48, 1.08, "cut"), (54.5, 0.55, 0.48, 1.10),
    (54.68, 0.55, 0.50, 1.00, "cut"), (56.58, 0.55, 0.50, 1.02),
    (56.62, 0.42, 0.45, 1.10, "cut"), (62.85, 0.45, 0.45, 1.12),
    (63.56, 0.55, 0.48, 1.00, "cut"), (69.98, 0.55, 0.48, 1.02),
    (70.01, 0.57, 0.50, 1.00, "cut"), (80.95, 0.57, 0.50, 1.02),
    (80.98, 0.60, 0.48, 1.04, "cut"), (85.50, 0.60, 0.48, 1.06),
    (97.81, 0.60, 0.50, 1.12, "cut"), (109.40, 0.60, 0.50, 1.15),
    (117.69, 0.44, 0.50, 1.00, "cut"), (119.74, 0.44, 0.50, 1.02),
    (141.92, 0.40, 0.48, 1.00, "cut"), (144.90, 0.40, 0.48, 1.02),
    (145.95, 0.53, 0.48, 1.00, "cut"), (149.95, 0.53, 0.48, 1.02),
    (150.72, 0.56, 0.46, 1.08, "cut"), (161.25, 0.56, 0.46, 1.10),
    (181.17, 0.52, 0.50, 1.00, "cut"), (188.4, 0.48, 0.52, 1.00), (198.15, 0.47, 0.52, 1.02),
    (199.61, 0.55, 0.48, 1.06, "cut"), (204.0, 0.55, 0.48, 1.08),
]

# ---- opening 3D title (full frame, footage dimmed behind) -----------------------------------------------------
TITLE_BEATS = [
    (0.40, 3.18, [("NEED A NEW", "white", 0.62), ("iPHONE CASE?", "accent", 1.0)]),
    (3.20, 5.62, [("THIS ONE IS", "white", 0.62), ("EXCELLENT", "accent", 1.0)]),
]
TITLE_BEATS_REEL = [          # three lines each, centred above the Reels button column (safe zone)
    (0.40, 3.18, [("NEED A NEW", "white", 0.55), ("iPHONE", "accent", 1.0), ("CASE?", "accent", 1.0)], {"cy": 0.38}),
    (3.20, 5.62, [("AN", "white", 0.50), ("EXCELLENT", "accent", 1.0), ("CASE", "white", 0.80)], {"cy": 0.38}),
]
REEL_ZOOM = 1.12
TITLE_END = 5.66

# ---- chapters (top-bar label; feature title card when `card`) -------------------------------------------------
CHAPTERS = [
    (29.78, "Design", None),
    (41.66, "Colours & models", None),
    (54.68, "Action button", "ACTION\nBUTTON"),
    (70.01, "Drop protection", "DROP\nPROTECTION"),
    (80.98, "Camera protection", "CAMERA\nPROTECTION"),
    (112.56, "Grip & MagSafe", None),
    (119.77, "Ports & buttons", "PORTS &\nBUTTONS"),
    (145.95, "Price", None),
    (164.41, "Look & feel", None),
    (181.17, "Heat vents", "HEAT\nVENTS"),
    (198.21, "Where to buy", None),
]
CARD_POS_WIDE = {"left": (70, 190)}      # feature title card (x, y in output px of the 1920x1080 frame)

# ---- tracked callouts: (t0, t1, track, idx, label, sub, side, (dx, dy)) ------------------------------------------
CALLOUTS = [
    (34.10, 38.30, "camera", 1, "Camera island", "Sculpted, perfectly finished", "left", (190, -40)),
    (57.50, 62.80, "action", 2, "Action button", "Covered - not left open", "left", (170, -60)),
    (100.00, 103.00, "lip", 3, None, None, None, ((592, 290), (540, 222))),   # pinned to the lip diagram (wide, reel)
    (118.00, 119.60, "magsafe", 3, "MagSafe", "Supported", "left", (180, 40)),
    (124.10, 127.40, "port", 4, "Charging port", "Precise cut-out", "left", (190, 80)),
    (124.50, 127.40, "speaker", 5, "Speaker grille", "Sound stays clear", "right", (190, 90)),
    (134.10, 137.95, "charger", 6, "Charger fits", "No need to take the case off", "right", (200, 80)),
    (143.00, 145.70, "buttons", 7, "Button grip", "Firm, clicky press", "right", (230, 20)),
    (189.10, 194.30, "vent1", 8, "Heat vents", "Let warm air escape", "left", (170, -110)),
]
HEAT_WAVES = [(189.4, 194.3, "vent1"), (189.4, 194.3, "vent2")]   # animated warm-air wisps over the vents

# ---- graphics (source times) ----------------------------------------------------------------------------------
NOT_SPONSORED = (9.10, 14.45)                         # chip: not a promotion, my own experience
NAME_TAG = (26.07, 29.70, "JABIR VARIKKODAN", "V CREATE")
STING_T0 = 23.30
INFO_CARD = (41.70, 54.50)                            # 5 colours / iPhone 13 and newer / link in description
LENS_CARD = (89.00, 97.78)                            # why skip a lens protector
LIP_DIAGRAM = (99.11, 109.40)                         # side-view schematic: raised border keeps lenses off the table
PRICE = (150.72, 161.25, "₹1,999", "₹520", "onwards · varies by model")
SUMMARY = (198.21, 214.95, "Why I like it", [
    "Action button covered", "Built to take a fall", "Raised camera lip", "MagSafe support",
    "Precise port & speaker cut-outs", "Heat vents"],
    "5 colours + transparent  ·  iPhone 13 and newer  ·  from ₹520")

# ---- prompts in the top bar -------------------------------------------------------------------------------------
CTAS = [(17.07, "subscribe"), (18.90, "share"), (215.32, "like"), (217.19, "subscribe")]
REEL_CTAS_SRC = [(199.70, "follow")]

# ---- sound ------------------------------------------------------------------------------------------------------
TRANSITIONS = []                      # hard cuts only; chapter whooshes come from CHAPTER_SFX
TRANSITION_SFX = {}
TAPS = []
STEPS = []
TAP_SFX = "1109"


def _cta_sfx(ctas):
    out = []
    for t0, what in ctas:
        if what == "subscribe":
            out += [(t0 + 1.2, "2354", -12), (t0 + 1.35, "933", -16)]
        elif what in ("like", "share"):
            out += [(t0 + 0.9, "2350", -15)]
    return out


CHAPTER_SFX = [(c[0] - 0.30, "1492", -16) for c in CHAPTERS]
CALLOUT_SFX = [(c[0] + 0.02, "3005", -18) for c in CALLOUTS]
BASE_SFX = [(0.42, "1485", -12), (3.20, "1485", -14), (TITLE_END - 0.25, "1491", -14), (STING_T0 - 0.08, "2596", -12),
            (151.25, "1485", -17)] + CHAPTER_SFX + CALLOUT_SFX
EXTRA_SFX = BASE_SFX + _cta_sfx(CTAS)
REEL_EXTRA_SFX = []
END_SWELL = 0.0
