"""Edit decision data for "hide WhatsApp calls from the iPhone call log" (Require Face ID on WhatsApp).

T = output (narration) time in seconds, S = time inside the screen recording.
"""
import numpy as np

FPS = 30
NARR_END = 87.37
END_CARD = 6.0
TOTAL = NARR_END + END_CARD

# screen recording: recording-time of the first frame of screen_clean60.mp4 and of the last usable frame
SCREEN_T0, SCREEN_END = 70.0, 108.4

# on-screen furniture (output times, seconds)
TITLE_T = (0.35, 3.5)                                   # hook title
TITLE_LINES = [("HIDE WHATSAPP", False), ("FROM CALL LOG", True)]
REVEAL_T0 = 23.80                                       # logo sting ("Welcome to MEGABYTE")
SUBSCRIBE_T = (11.70, 14.70)                            # subscribe button
SHARE_T = [(14.70, 18.35), (80.45, 84.10)]              # share button (twice: early ask + closing ask)
FACE_ANCHOR = dict(fx=0.55, fy=0.30)                    # face centre in the source frame (for framing + grade window)

# project-specific sound effects (time, mixkit id, gain dB) on top of the generic transition / tap / step ones
EXTRA_SFX = [(0.55, "3124", -15),
             (10.20, "2852", -13), (10.35, "1489", -16),              # Face ID ok -> WhatsApp rows leave the list
             (12.85, "2354", -10), (12.98, "933", -13),               # subscribe click + bell
             (15.70, "2354", -10),                                    # share
             (23.85, "3005", -13),                                    # logo sting
             (63.40, "2852", -13), (63.55, "2856", -9),               # Face ID ok -> padlock opens
             (81.45, "2354", -10)]                                    # share (closing)

# ---- scenes -----------------------------------------------------------------------------------------
# kind: face | broll | graphic | phone | end     (broll: clip = landscape id, reel_clip = vertical id)
SCENES = [
    dict(kind="face",    t0=0.00,   t1=3.90,   zoom=(1.12, 1.18), name="hook"),
    dict(kind="broll",   t0=3.90,   t1=7.30,   clip="41165", clip_t=3.0, reel_clip="41173", reel_clip_t=1.0, name="calls-together"),
    dict(kind="graphic", t0=7.30,   t1=12.00,  graphic="call-log", name="call-log"),
    dict(kind="face",    t0=12.00,  t1=14.70,  zoom=(1.14, 1.20), name="subscribe"),
    dict(kind="face",    t0=14.70,  t1=18.95,  zoom=(1.22, 1.14), name="share"),
    dict(kind="broll",   t0=18.95,  t1=22.55,  clip="4805", clip_t=1.0, reel_clip="49939", reel_clip_t=0.5, name="simple-fix"),
    dict(kind="face",    t0=22.55,  t1=28.90,  zoom=(1.14, 1.22), name="welcome"),
    dict(kind="phone",   t0=28.90,  t1=57.30,  name="phone"),
    dict(kind="face",    t0=57.30,  t1=59.95,  zoom=(1.12, 1.18), name="small-catch"),
    dict(kind="graphic", t0=59.95,  t1=65.70,  graphic="face-unlock", name="face-unlock"),
    dict(kind="broll",   t0=65.70,  t1=70.60,  clip="4915", clip_t=2.0, reel_clip="39833", reel_clip_t=1.0, name="passcode"),
    dict(kind="face",    t0=70.60,  t1=75.40,  zoom=(1.16, 1.12), name="solved-a"),
    dict(kind="face",    t0=75.40,  t1=80.45,  zoom=(1.12, 1.20), name="solved-b"),
    dict(kind="face",    t0=80.45,  t1=84.00,  zoom=(1.20, 1.14), name="share-2"),
    dict(kind="face",    t0=84.00,  t1=NARR_END, zoom=(1.14, 1.22), name="outro"),
    dict(kind="end",     t0=NARR_END, t1=TOTAL, name="end-card"),
]

# transitions between scenes: (time, kind). kinds: wipe (lime bar), zoom, flash
TRANSITIONS = [
    (3.90, "wipe"), (7.30, "zoom"), (12.00, "wipe"), (14.70, "zoom"), (18.95, "wipe"), (22.55, "zoom"),
    (28.90, "wipe"), (57.30, "wipe"), (59.95, "zoom"), (65.70, "zoom"), (70.60, "wipe"),
    (75.40, "zoom"), (80.45, "zoom"), (84.00, "zoom"), (NARR_END, "wipe"),
]

# ---- screen recording re-timing (T -> S), piecewise linear, monotonic ---------------------------------
#  S 70-77 idle home screen | 77.5 context menu | 83.9 tap "Require Face ID" | 84.5-87.6 dialog | 87.5 blue button |
#  87.9-89.8 Face ID scan | 90-94.8 idle | 94.9 Phone app opens | 95.45-95.70 the two WhatsApp rows leave the list
SCREEN_MAP = [
    (28.90, 70.00), (34.30, 77.00), (40.20, 83.90), (43.10, 87.50), (45.20, 89.90),
    (46.70, 94.80), (46.90, 94.93), (47.70, 95.33),                 # Phone app opens (half speed)
    (47.75, 95.38), (51.00, 95.38),                                 # list with the WhatsApp rows, held
    (51.80, 95.78), (52.00, 95.80),                                 # rows leave (half speed, 60 fps source -> 30 fps)
    (57.30, 100.00), (60.00, 108.40),
]


def screen_time(T):
    ts = [p[0] for p in SCREEN_MAP]
    ss = [p[1] for p in SCREEN_MAP]
    return float(np.interp(T, ts, ss))


# ---- camera on the phone: keyframes (T, zoom, u, v) – screen point (u,v) is pulled to the anchor -----------
CAMERA = [
    (28.90, 0.80, 0.50, 0.50), (29.70, 1.00, 0.50, 0.50),
    (30.20, 1.00, 0.50, 0.50), (31.10, 1.70, 0.72, 0.74), (34.00, 1.70, 0.72, 0.74),     # WhatsApp icon in the dock
    (35.40, 1.45, 0.62, 0.66), (40.00, 1.45, 0.62, 0.66),                               # context menu
    (40.90, 1.30, 0.50, 0.52), (43.00, 1.30, 0.50, 0.52),                               # confirmation dialog
    (43.50, 2.20, 0.50, 0.10), (45.00, 2.20, 0.50, 0.10),                               # Face ID scan in the island
    (45.90, 1.55, 0.30, 0.80), (46.90, 1.55, 0.30, 0.80),                               # Phone icon
    (47.70, 1.20, 0.50, 0.50), (48.50, 1.20, 0.50, 0.50),                               # Recents opens
    (49.10, 1.65, 0.50, 0.36), (51.90, 1.65, 0.50, 0.36),                               # the two WhatsApp rows
    (52.80, 1.15, 0.50, 0.50), (57.30, 1.15, 0.50, 0.50),
]

# ---- taps: (T, u, v) on the screen --------------------------------------------------------------------
TAPS = [
    (34.25, 0.827, 0.920),      # press & hold WhatsApp
    (40.20, 0.620, 0.548),      # Require Face ID (menu)
    (43.10, 0.500, 0.567),      # Require Face ID (blue button)
    (46.80, 0.167, 0.923),      # Phone app
]

# ---- highlight rings: (T0, T1, (u0, v0, u1, v1)) --------------------------------------------------------
HIGHLIGHTS = [
    (30.20, 34.30, (0.745, 0.885, 0.915, 0.958)),     # WhatsApp icon
    (36.20, 40.30, (0.360, 0.523, 0.905, 0.575)),     # "Require Face ID" menu row
    (41.50, 43.20, (0.165, 0.536, 0.835, 0.598)),     # blue "Require Face ID" button
    (43.50, 45.00, (0.240, 0.010, 0.760, 0.072)),     # Face ID scan in the Dynamic Island
    (45.90, 46.90, (0.085, 0.885, 0.250, 0.958)),     # Phone icon
    (49.10, 51.10, (0.030, 0.245, 0.970, 0.395)),     # the two WhatsApp rows (before they disappear)
]

# ---- step chips in the phone scene: (T0, T1, n, label) ---------------------------------------------------
STEPS = [
    (28.90, 35.60, 1, "Press & hold WhatsApp"),
    (35.60, 40.80, 2, "Choose Require Face ID"),
    (40.80, 46.60, 3, "Confirm Require Face ID"),
    (46.60, 57.30, 4, "Check your call log"),
]
N_STEPS = 4

# colour grade overrides for this footage (already crisp, cool shadows): less local contrast / split-tone than the default
GRADE = dict(clarity=0.04, face_lift=0.14, tint=0.35)
