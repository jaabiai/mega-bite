"""Timeline for the V Create video "Equal AI: an AI assistant that answers spam and promotional calls for you" - Mist
style (render_mist.py).  All times are narration seconds T (= output time of the 16:9 edit, which keeps the whole talk).
Screen times S are seconds of the joined, cleaned 30 fps copy of the three iPhone recordings (screen_rules.py):
recording 1 (onboarding) from S 0, recording 2 from S O2, recording 3 from S O3."""
import numpy as np

STYLE = "mist"
FPS = 30
NARR_END = 318.15
TOTAL = NARR_END + 0.35                        # no end card
END_SWELL = 0.0
SCREEN_SIZE = (1320, 2868)
SCREEN_FPS = 30
O1, O2, O3 = 0.0, 2713 / 30, (2713 + 9136) / 30
SCREEN_T0, SCREEN_END = 0.0, 17245 / 30
FACE_ANCHOR = dict(fx=0.538, fy=0.43)
LOGO = "vcreate.png"
CHANNEL = "V CREATE"

# Varathan-style moody green grade (lib/grade_moody.py): misty grey-green window, darker cabin, muted skin kept warm
GRADE_MOODY = dict(knee=0.44, roll=2.8, mist=0.55, mist_rgb=(0.74, 0.86, 0.80), sat=0.72, skin_keep=0.38,
                   lift=(-0.016, 0.028, 0.018), gamma=(0.95, 1.05, 0.985), gain=(0.95, 0.99, 0.93), shadow_green=0.026,
                   base=dict(exposure=-0.40, green_hue=10.0, green_sat=0.58, vignette=0.60, skin_sat=0.80, face_lift=0.24,
                             contrast=0.55, halation=0.12, bloom=0.11, clarity=0.06, dehaze=0.16))
BROLL_GRADE = dict(exposure=-0.30, vignette=0.50, clarity=0.04)

s1 = lambda t: O1 + t
s2 = lambda t: O2 + t
s3 = lambda t: O3 + t

# ---- opening title (left column; the face stays clear) ------------------------------------------------------------
TITLE_BEATS = [(-0.20, 3.25, [("SPAM CALLS?", "bone", 1.0), ("LET AI ANSWER", "red", 0.86)],
                {"kicker": "V CREATE  ·  AI CALL ASSISTANT", "sub": "Equal AI picks up for you"})]
TITLE_BEATS_REEL = [(-0.20, 3.25, [("SPAM CALLS?", "bone", 1.0), ("LET AI ANSWER", "red", 0.86)],
                     {"kicker": "V CREATE  ·  AI CALL ASSISTANT", "sub": "Equal AI picks up for you"})]

# ---- chapters: (T0, T1, n, title) - slate at T0, rail line fills from T0 to T1 --------------------------------------
CHAPTERS = [
    (46.35, 59.10, 1, "Get the app"),
    (59.10, 107.40, 2, "Set it up"),
    (107.40, 162.50, 3, "Instructions"),
    (162.50, 197.30, 4, "Which calls"),
    (197.30, 249.85, 5, "Languages"),
    (249.85, 268.00, 6, "Voice"),
    (268.00, 282.10, 7, "Silent mode"),
    (282.10, NARR_END, 8, "Try it"),
]
CHAPTER_SLATE = 3.2

# ---- scenes -----------------------------------------------------------------------------------------------------
F = lambda t0, t1, z=(1.0, 1.04), tx=0.58, name=None: dict(kind="face", t0=t0, t1=t1, zoom=z, tx=tx, name=name or f"f{t0}")
C = lambda t0, t1, name=None: F(t0, t1, (1.15, 1.19), 0.62, name)              # close framing
B = lambda t0, t1, clip, ct=0.0, cx=0.5, rcx=0.5, name=None: dict(kind="broll", t0=t0, t1=t1, clip=clip, clip_t=ct, cx=cx,
                                                                  reel_cx=rcx, name=name or f"b{clip}_{t0}")
P = lambda t0, t1, name: dict(kind="phone", t0=t0, t1=t1, name=name)
SCENES = [
    dict(kind="title", t0=0.0, t1=3.25, zoom=(1.10, 1.12), tx=0.70, name="title"),     # zoomed so the face sits right
    B(3.25, 7.14, "39790", 1.0, 0.5, 0.36),
    F(7.14, 13.40),
    C(13.40, 18.60),
    F(18.60, 23.30),
    B(23.30, 27.05, "39776", 2.0, 0.5, 0.30),
    C(27.05, 30.70),
    F(30.70, 39.60),
    C(39.60, 46.35),
    F(46.35, 52.20),
    C(52.20, 59.10),
    F(59.10, 68.40),
    C(68.40, 73.80),
    F(73.80, 79.80),
    P(79.80, 162.50, "setup+instructions"),
    P(162.50, 189.40, "calls"),
    F(189.40, 197.30),
    P(197.30, 229.35, "languages"),
    F(229.35, 237.50),
    B(237.50, 243.40, "10452", 0.0, 0.5, 0.45),
    C(243.40, 249.85),
    P(249.85, 283.00, "voice+silent"),
    F(283.00, 288.35),
    P(288.35, 311.28, "help+premium"),
    C(311.28, NARR_END + 1.0),
]
MIXES = [sc["t0"] for sc in SCENES[1:]]                 # film-burn dissolve on every cut after the title
TRANSITIONS = [(t, "burn") for t in MIXES]
TRANSITION_SFX = {"burn": ("1492", -0.30, -19)}

# ---- highlights ----------------------------------------------------------------------------------------------------
KEY_WORDS = ["spam", "promotional", "automatically", "rejects", "forwards", "ai", "otp", "permissions", "microphone",
             "privacy", "profile", "instructions", "busy", "business", "voice", "message", "unknown", "confirm",
             "languages", "primary", "malayalam", "hindi", "silent", "free", "upgrade", "link", "iphone", "android",
             "subscribe", "share", "edit"]
KEY_POINTS = [                                          # (T0, T1, phrase) - face shots, left column
    (8.60, 13.20, "Your phone answers the call itself"),
    (48.90, 52.00, "Works on iPhone and Android"),
    (53.00, 58.80, "Download link in the description"),
    (74.00, 79.60, "Sign in: phone number + OTP"),
    (190.00, 197.00, "The AI screens the call before you pick up"),
    (231.00, 236.90, "It greets callers in your primary language"),
    (243.60, 249.50, "...then answers in the caller's language"),
    (285.40, 288.20, "Link in the description"),
]

# ---- prompts ----------------------------------------------------------------------------------------------------
CTAS = [(33.40, "subscribe"), (36.30, "share"), (313.00, "subscribe")]
REEL_CTAS = [(313.00, "follow")]

# ---- phone: narration T -> screen S (rows <= 0.02 s apart are cuts) ------------------------------------------------
SCREEN_MAP = [
    # set-up (recording 1): instructions -> tutorial -> copy code page (privacy note) -> verify -> all set -> home
    (79.80, s1(0.2)), (83.45, s1(3.5)), (84.30, s1(4.35)), (88.50, s1(9.35)),
    (88.51, s1(12.0)), (91.25, s1(14.6)), (96.45, s1(21.95)), (98.00, s1(23.5)),
    (98.01, s1(30.6)), (100.60, s1(33.2)),
    (100.61, s1(66.6)), (101.90, s1(67.9)), (103.30, s1(71.2)), (105.40, s1(74.0)), (107.39, s1(76.0)),
    # instructions (recording 2): You tab -> profile (toggle) -> Your Instructions -> presets -> Everyday -> Apply
    (107.40, s2(3.65)), (108.85, s2(4.70)), (109.60, s2(5.45)), (119.75, s2(8.15)), (120.40, s2(8.80)),
    (125.80, s2(13.90)), (133.20, s2(14.10)),
    (133.21, s2(108.30)), (133.80, s2(108.90)), (134.50, s2(109.60)), (142.15, s2(116.05)), (143.10, s2(116.90)),
    # add new instruction: Active Instructions -> Add new -> mic permission -> voice note -> or type a message
    (143.11, s2(13.95)), (143.50, s2(14.30)), (144.20, s2(15.00)), (145.40, s2(16.20)), (146.20, s2(17.00)),
    (147.20, s2(18.00)), (147.21, s2(25.70)), (148.60, s2(26.30)), (149.95, s2(27.05)), (150.60, s2(27.70)),
    (153.90, s2(31.00)), (153.91, s2(50.80)), (155.30, s2(52.20)),
    (155.31, s2(82.40)), (157.30, s2(86.00)), (158.60, s2(89.50)), (159.20, s2(90.35)), (159.90, s2(91.10)),
    (161.20, s2(94.30)), (162.49, s2(95.50)),
    # which calls (recording 3): profile -> Your Call Preferences -> Only unknown numbers -> confirm
    (162.50, s3(1.40)), (167.45, s3(5.55)), (168.20, s3(6.30)), (175.25, s3(21.15)), (176.00, s3(22.60)),
    (186.75, s3(25.45)), (187.50, s3(26.20)), (189.40, s3(28.10)),
    # languages (recording 3): profile -> Voice & Language -> Edit -> pick 3 -> confirm -> primary -> confirm
    (197.30, s3(38.90)), (199.00, s3(40.60)), (199.60, s3(41.30)), (202.95, s3(46.35)), (203.60, s3(47.10)),
    (205.20, s3(51.00)), (208.80, s3(52.85)), (209.50, s3(53.60)), (216.90, s3(61.00)), (220.30, s3(67.35)),
    (221.00, s3(68.10)), (226.20, s3(76.20)), (226.90, s3(82.55)), (227.70, s3(83.40)), (229.40, s3(85.10)),
    # voice (recording 2): Assistant Preference -> Edit -> browse voices -> confirm; then Silent Mode page
    (249.85, s2(216.80)), (257.55, s2(221.85)), (258.20, s2(222.60)), (259.20, s2(224.00)), (260.00, s2(224.60)),
    (260.01, s2(231.90)), (262.00, s2(233.90)), (262.01, s2(238.40)), (263.90, s2(240.30)),
    (263.91, s2(251.60)), (264.40, s2(252.10)), (268.00, s2(254.10)), (268.80, s2(255.00)), (270.55, s2(256.65)),
    (271.30, s2(257.50)), (283.00, s2(266.30)),
    # help + premium: Talk to Equal (recording 1) -> "Equal now makes calls for you" (2) -> free / premium card (3)
    (288.35, s1(79.0)), (293.00, s1(86.05)), (294.60, s1(86.75)),
    (294.61, s2(296.30)), (302.90, s2(301.75)),
    (302.91, s3(132.30)), (311.30, s3(139.60)),
]


def screen_time(T):
    """Linear between rows; two rows at most 0.02 s apart are a cut (the earlier S holds until the later T)."""
    for (t0, s0), (t1, s1_) in zip(SCREEN_MAP[:-1], SCREEN_MAP[1:]):
        if t1 - t0 <= 0.02 and t0 <= T < t1:
            return s0
    return float(np.interp(T, [p[0] for p in SCREEN_MAP], [p[1] for p in SCREEN_MAP]))


# ---- camera on the phone: (T, zoom, u, v) ---------------------------------------------------------------------------
O = lambda t: (t, 1.0, 0.5, 0.5)
CAMERA = [
    O(79.80), (80.60, 1.30, 0.5, 0.33), (83.00, 1.30, 0.5, 0.33), O(83.90), O(88.60), (89.40, 1.40, 0.5, 0.36),
    (91.60, 1.40, 0.5, 0.36), (92.40, 1.55, 0.5, 0.48), (96.90, 1.55, 0.5, 0.48), O(97.80), O(98.10),
    (98.80, 1.25, 0.5, 0.64), (100.50, 1.25, 0.5, 0.64), (101.10, 1.40, 0.5, 0.80), (103.40, 1.40, 0.5, 0.80), O(104.00),
    O(107.40), O(109.70), (110.40, 1.50, 0.5, 0.42), (115.20, 1.50, 0.5, 0.42), (116.00, 1.30, 0.5, 0.55),
    (119.90, 1.30, 0.5, 0.55), O(120.60), O(123.80), (124.80, 1.40, 0.5, 0.62), (133.00, 1.40, 0.5, 0.62), O(133.60),
    (135.00, 1.45, 0.5, 0.30), (142.60, 1.45, 0.5, 0.30), O(143.20), O(148.20), (148.90, 1.35, 0.5, 0.58),
    (150.40, 1.35, 0.5, 0.58), (151.20, 1.25, 0.5, 0.74), (153.80, 1.25, 0.5, 0.74), (154.30, 1.40, 0.5, 0.48),
    (155.20, 1.40, 0.5, 0.48), O(155.60), (156.40, 1.30, 0.5, 0.62), (159.40, 1.30, 0.5, 0.62), (160.40, 1.45, 0.5, 0.66),
    (162.50, 1.45, 0.5, 0.66),
    O(162.50), (164.40, 1.35, 0.5, 0.60), (167.40, 1.35, 0.5, 0.60), O(168.20), (168.90, 1.35, 0.5, 0.61),
    (175.20, 1.35, 0.5, 0.61), (176.30, 1.30, 0.5, 0.72), (186.90, 1.30, 0.5, 0.72), (187.60, 1.35, 0.5, 0.61),
    (189.40, 1.35, 0.5, 0.61),
    O(197.30), (199.40, 1.35, 0.5, 0.66), (202.90, 1.35, 0.5, 0.66), O(203.60), (205.40, 1.40, 0.5, 0.48),
    (208.80, 1.40, 0.5, 0.48), O(209.60), (210.40, 1.20, 0.5, 0.45), (220.00, 1.20, 0.5, 0.45), O(220.60),
    (221.60, 1.35, 0.5, 0.42), (226.00, 1.35, 0.5, 0.42), O(226.70), O(229.40),
    O(249.85), (250.80, 1.35, 0.5, 0.24), (257.40, 1.35, 0.5, 0.24), O(258.20), (258.90, 1.15, 0.5, 0.45),
    (263.80, 1.15, 0.5, 0.45), O(264.60), O(268.70), (269.20, 1.30, 0.5, 0.62), (270.50, 1.30, 0.5, 0.62), O(271.40),
    (272.40, 1.30, 0.5, 0.36), (275.80, 1.45, 0.5, 0.48), (279.30, 1.45, 0.5, 0.48), (280.20, 1.35, 0.5, 0.68),
    (283.00, 1.35, 0.5, 0.68),
    O(288.35), (289.40, 1.35, 0.5, 0.76), (293.30, 1.35, 0.5, 0.76), O(294.00), O(294.70), (295.60, 1.30, 0.5, 0.60),
    (302.60, 1.30, 0.5, 0.60), O(303.10), (304.00, 1.50, 0.5, 0.26), (311.30, 1.50, 0.5, 0.26),
]

# ---- taps (T, u, v) and highlights (T0, T1, (u0, v0, u1, v1), label) ---------------------------------------------------
TAPS = [(83.45, 0.50, 0.872), (96.45, 0.78, 0.455), (101.90, 0.18, 0.846), (103.30, 0.50, 0.902),
        (108.85, 0.597, 0.948), (119.80, 0.50, 0.565), (133.80, 0.50, 0.649), (142.15, 0.81, 0.233),
        (143.50, 0.35, 0.40), (145.40, 0.50, 0.929), (149.95, 0.667, 0.646), (159.20, 0.90, 0.597),
        (167.45, 0.50, 0.636), (175.25, 0.95, 0.707), (186.75, 0.50, 0.861),
        (202.95, 0.50, 0.788), (208.80, 0.86, 0.388), (220.30, 0.50, 0.905), (226.90, 0.50, 0.905),
        (257.55, 0.86, 0.169), (264.40, 0.50, 0.905), (268.05, 0.09, 0.087), (270.55, 0.50, 0.715),
        (293.00, 0.20, 0.792)]
HIGHLIGHTS = [
    (80.40, 83.20, (0.03, 0.150, 0.97, 0.245), "Set-up instructions"),
    (89.30, 91.10, (0.03, 0.255, 0.97, 0.330), "Copy · dial · return"),
    (92.30, 95.90, (0.02, 0.488, 0.98, 0.518), "Safe and secure"),
    (96.00, 96.45, (0.70, 0.437, 0.92, 0.474), ""),
    (98.70, 100.50, (0.05, 0.495, 0.95, 0.595), "Why a code?"),
    (101.00, 101.90, (0.05, 0.830, 0.95, 0.864), ""),
    (102.50, 103.30, (0.06, 0.880, 0.94, 0.925), "Verify"),
    (104.00, 105.40, (0.20, 0.380, 0.80, 0.640), "All set"),
    (108.00, 108.85, (0.53, 0.915, 0.67, 0.978), "You"),
    (110.40, 115.00, (0.04, 0.448, 0.96, 0.510), "AI Assistant on / off"),
    (117.00, 119.80, (0.04, 0.540, 0.96, 0.595), "Your Instructions"),
    (126.30, 127.60, (0.04, 0.530, 0.96, 0.585), "Busy"),
    (127.60, 129.80, (0.04, 0.625, 0.96, 0.680), "Everyday calls"),
    (130.70, 133.00, (0.04, 0.720, 0.96, 0.775), "Business"),
    (135.00, 141.50, (0.03, 0.215, 0.97, 0.420), "A ready-made rule"),
    (141.60, 142.15, (0.74, 0.215, 0.90, 0.250), ""),
    (144.40, 145.40, (0.03, 0.905, 0.97, 0.955), "Add new instruction"),
    (148.80, 149.95, (0.51, 0.625, 0.83, 0.668), "Allow microphone"),
    (154.00, 155.20, (0.03, 0.525, 0.95, 0.578), "Your voice instruction"),
    (157.60, 159.20, (0.03, 0.575, 0.85, 0.618), "Or type it"),
    (160.60, 162.40, (0.08, 0.680, 0.95, 0.800), "Rule added"),
    (164.60, 167.45, (0.04, 0.610, 0.96, 0.665), "Your Call Preferences"),
    (169.00, 170.50, (0.03, 0.475, 0.97, 0.552), "All calls"),
    (170.50, 172.40, (0.03, 0.572, 0.97, 0.648), "All calls except"),
    (172.50, 175.25, (0.03, 0.668, 0.97, 0.745), "Only unknown numbers"),
    (177.00, 185.60, (0.05, 0.715, 0.95, 0.815), "Unknown callers only"),
    (185.70, 186.75, (0.06, 0.840, 0.94, 0.885), "Confirm"),
    (187.40, 189.30, (0.03, 0.668, 0.97, 0.745), ""),
    (199.20, 202.95, (0.04, 0.762, 0.96, 0.815), "Voice & Language"),
    (205.20, 208.20, (0.03, 0.375, 0.97, 0.700), "Assistant languages"),
    (208.20, 208.80, (0.78, 0.372, 0.96, 0.405), "Edit"),
    (209.90, 216.90, (0.03, 0.270, 0.97, 0.730), "Pick your languages"),
    (217.00, 220.20, (0.03, 0.228, 0.97, 0.262), "Up to 3"),
    (221.50, 226.20, (0.03, 0.315, 0.97, 0.560), "Primary language"),
    (226.30, 226.90, (0.03, 0.885, 0.97, 0.925), ""),
    (250.60, 257.00, (0.03, 0.140, 0.97, 0.330), "Assistant voice"),
    (257.00, 257.55, (0.74, 0.150, 0.93, 0.190), "Edit"),
    (259.30, 263.80, (0.15, 0.400, 0.85, 0.470), "Pick a voice"),
    (263.90, 264.40, (0.03, 0.885, 0.97, 0.925), ""),
    (269.30, 270.55, (0.04, 0.692, 0.96, 0.745), "Silent Mode"),
    (272.00, 276.50, (0.03, 0.440, 0.97, 0.530), "Mute promotional calls"),
    (276.80, 282.60, (0.03, 0.540, 0.97, 0.870), "Loans · cards · jobs · real estate"),
    (289.60, 293.00, (0.03, 0.765, 0.36, 0.845), "Talk to Equal"),
    (296.00, 302.50, (0.05, 0.455, 0.95, 0.570), "It calls you back"),
    (303.60, 310.80, (0.03, 0.200, 0.97, 0.370), "Free plan + Premium"),
]
STEPS = [                                         # step line in the left column: (T0, T1, n, label)
    (79.80, 83.65, 1, "Follow the set-up instructions"),
    (83.65, 91.25, 2, "Allow the permissions it asks for"),
    (91.25, 100.75, 3, "Your privacy stays safe"),
    (100.75, 107.40, 4, "Verify and finish your profile"),
    (107.40, 115.60, 1, "You tab: AI Assistant on / off"),
    (115.60, 130.60, 2, "Open Your Instructions"),
    (130.60, 143.15, 3, "Pick a preset and Apply"),
    (143.15, 155.30, 4, "Add a new instruction by voice"),
    (155.30, 162.50, 5, "...or type it as a message"),
    (162.50, 168.40, 1, "Open Your Call Preferences"),
    (168.40, 186.70, 2, "All / All except / Only unknown"),
    (186.70, 189.40, 3, "Confirm"),
    (197.30, 208.90, 1, "Open Voice & Language"),
    (208.90, 220.35, 2, "Edit: pick up to 3 languages"),
    (220.35, 226.30, 3, "Choose the primary language"),
    (226.30, 229.35, 4, "Confirm"),
    (249.85, 257.60, 1, "Assistant Voice: Edit"),
    (257.60, 264.40, 2, "Pick a voice and Confirm"),
    (264.40, 268.00, 3, "Callers hear this voice"),
    (268.00, 276.60, 4, "Silent Mode: ring or silent"),
    (276.60, 283.00, 5, "Mute promotional calls"),
    (288.35, 294.60, 1, "Doubts? Talk to Equal"),
    (294.60, 302.90, 2, "It calls you and explains"),
    (302.90, 311.28, 3, "Free plan + Premium upgrade"),
]


def _cta_sfx(ctas):
    out = []
    for t0, what in ctas:
        out += [(t0, "1491", -20), (t0 + 1.2, "2354", -13)]
        if what == "subscribe":
            out += [(t0 + 1.3, "933", -17)]
    return out


BASE_SFX = ([(0.0, "1485", -12)] + [(t0, "2596", -15) for t0, *_ in CHAPTERS]
            + [(t0 + 0.1, "3005", -21) for t0, *_ in KEY_POINTS])
EXTRA_SFX = BASE_SFX + _cta_sfx(CTAS)

# ---- 9:16 Short (<= 3:00): the whole how-to, cut only at pauses in the voice -----------------------------------------
# dropped: subscribe / share request, welcome line, "I won't explain it all", OTP sign-in, the privacy aside, profile,
# the preset walk-through, voice-note detail, the long confirm explanation, language step-by-step, voice browsing,
# the "talk to Equal" help, "try it then decide"
REEL_CUTS = [(0.00, 30.44), (39.62, 42.09), (46.30, 56.34), (59.17, 64.73), (79.88, 91.06), (107.62, 123.06),
             (143.71, 152.62), (162.84, 175.56), (186.61, 203.66), (229.58, 249.28), (252.86, 258.81),
             (263.64, 288.24), (303.64, 308.20), (312.72, NARR_END)]
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
REEL_JOIN_SFX = False                          # joins must not be heard: no whoosh, the music runs straight through
