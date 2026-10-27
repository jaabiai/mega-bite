"""Edit decision data: scene order, screen-recording re-timing, camera, taps, highlights, steps.

T = output (narration) time in seconds, S = time inside the screen recording.
"""
import numpy as np

FPS = 30
NARR_END = 101.72
END_CARD = 6.0
TOTAL = NARR_END + END_CARD

# screen recording: recording-time of the first frame of screen_clean60.mp4 and of the last usable frame
SCREEN_T0, SCREEN_END = 8.0, 87.7

# on-screen furniture (output times, seconds)
TITLE_T = (0.35, 3.5)                                   # hook title
TITLE_LINES = [("LOCK YOUR GOOGLE", False), ("SEARCH HISTORY", True)]
REVEAL_T0 = 17.45                                       # logo sting ("Welcome to MEGABYTE")
SUBSCRIBE_T = (19.9, 22.95)                             # subscribe button
SHARE_T = (22.95, 26.6)                                 # share button
FACE_ANCHOR = dict(fx=0.54, fy=0.36)                    # face centre in the source frame (for framing + grade window)

# project-specific sound effects (time, mixkit id, gain dB) on top of the generic transition / tap / step ones
EXTRA_SFX = [(0.55, "3124", -15), (17.50, "3005", -13), (19.45, "1489", -16),
             (14.38, "2856", -8), (14.52, "2852", -15),              # padlock closes
             (21.05, "2354", -10), (21.18, "933", -13),              # subscribe click + bell
             (23.95, "2354", -10),                                   # share
             (78.40, "2852", -13)]                                   # Save -> locked

# ---- scenes -----------------------------------------------------------------------------------------
# kind: face | broll | graphic | phone | end
SCENES = [
    dict(kind="face",    t0=0.00,   t1=3.88,   zoom=(1.20, 1.27), reel_zoom=(1.0, 1.10), name="hook"),
    dict(kind="broll",   t0=3.88,   t1=6.50,   clip="39782", clip_t=2.0, name="browsing"),
    dict(kind="broll",   t0=6.50,   t1=8.34,   clip="25451", clip_t=1.5, name="safe-keypad"),
    dict(kind="broll",   t0=8.34,   t1=11.88,  clip="144",   clip_t=0.5, name="phone-in-hand"),
    dict(kind="graphic", t0=11.88,  t1=15.88,  name="search-lock"),
    dict(kind="face",    t0=15.88,  t1=21.50,  zoom=(1.18, 1.24), reel_zoom=(1.0, 1.10), name="welcome"),
    dict(kind="face",    t0=21.50,  t1=26.58,  zoom=(1.30, 1.24), reel_zoom=(1.14, 1.04), name="share"),
    dict(kind="phone",   t0=26.58,  t1=91.90,  name="phone"),
    dict(kind="face",    t0=91.90,  t1=96.60,  zoom=(1.22, 1.28), reel_zoom=(1.0, 1.10), name="outro-a"),
    dict(kind="face",    t0=96.60,  t1=NARR_END, zoom=(1.34, 1.28), reel_zoom=(1.16, 1.06), name="outro-b"),
    dict(kind="end",     t0=NARR_END, t1=TOTAL, name="end-card"),
]

# transitions between scenes: (time, kind). kinds: wipe (lime bar), zoom, flash
TRANSITIONS = [
    (3.88, "wipe"), (6.50, "zoom"), (8.34, "zoom"), (11.88, "wipe"), (15.88, "wipe"),
    (21.50, "zoom"), (26.58, "wipe"), (91.90, "wipe"), (96.60, "zoom"), (NARR_END, "wipe"),
]

# ---- screen recording re-timing (T -> S), piecewise linear, monotonic ---------------------------------
SCREEN_MAP = [
    (26.58, 8.40), (30.60, 10.20), (30.90, 10.50), (31.90, 11.50),
    (35.85, 21.60), (36.10, 21.85), (37.00, 22.75),
    (37.45, 28.25), (40.35, 36.00), (40.80, 36.45), (41.60, 37.20),
    (48.50, 37.85), (49.90, 37.88), (51.30, 38.50),
    (55.00, 41.60), (55.20, 41.80), (55.90, 42.50),
    (61.50, 48.50), (61.80, 48.80), (63.50, 51.20), (65.80, 54.90),
    (69.20, 61.50), (69.50, 61.80), (70.10, 62.40),
    (76.20, 69.00), (76.50, 69.30), (77.10, 70.00),
    (78.20, 70.90), (78.30, 71.00), (80.80, 73.70), (81.80, 74.60),
    (91.90, 87.00),
]


def screen_time(T):
    ts = [p[0] for p in SCREEN_MAP]
    ss = [p[1] for p in SCREEN_MAP]
    return float(np.interp(T, ts, ss))


# ---- camera on the phone: keyframes (T, zoom, u, v) – screen point (u,v) is pulled to the anchor -----------
CAMERA = [
    (26.58, 0.80, 0.50, 0.50), (27.40, 1.00, 0.50, 0.50),
    (29.40, 1.00, 0.50, 0.50), (30.10, 1.90, 0.18, 0.26), (31.60, 1.90, 0.18, 0.26),
    (32.20, 1.15, 0.50, 0.40),
    (33.40, 2.15, 0.88, 0.14), (36.40, 2.15, 0.88, 0.14),
    (37.20, 1.20, 0.50, 0.50),
    (38.00, 1.95, 0.34, 0.22), (41.40, 1.95, 0.34, 0.22),
    (42.40, 1.30, 0.50, 0.24), (48.40, 1.30, 0.50, 0.24),
    (49.80, 1.15, 0.50, 0.50), (52.40, 1.15, 0.50, 0.55),
    (53.00, 1.85, 0.52, 0.72), (56.20, 1.85, 0.52, 0.72),
    (57.00, 1.50, 0.50, 0.50), (58.40, 1.90, 0.52, 0.52), (62.00, 1.90, 0.52, 0.52),
    (62.80, 1.10, 0.50, 0.50), (65.60, 1.10, 0.50, 0.50),
    (66.20, 2.00, 0.40, 0.66), (70.00, 2.00, 0.40, 0.66),
    (70.80, 1.40, 0.50, 0.55), (73.00, 1.40, 0.50, 0.55),
    (73.60, 2.20, 0.40, 0.60), (77.20, 2.20, 0.40, 0.60),
    (77.70, 2.00, 0.80, 0.72), (79.60, 2.00, 0.80, 0.72),
    (80.60, 1.15, 0.50, 0.50), (83.20, 1.15, 0.50, 0.50),
    (84.20, 1.55, 0.50, 0.34), (86.80, 1.55, 0.50, 0.34),
    (87.60, 1.50, 0.50, 0.70), (90.20, 1.50, 0.50, 0.70),
    (91.90, 1.15, 0.50, 0.50),
]

# ---- taps: (T, u, v) on the screen --------------------------------------------------------------------
TAPS = [
    (30.90, 0.15, 0.25), (36.10, 0.923, 0.097), (40.80, 0.34, 0.20), (55.20, 0.50, 0.74),
    (61.80, 0.50, 0.53), (69.50, 0.40, 0.662), (76.50, 0.14, 0.598), (78.30, 0.91, 0.732),
]

# ---- highlight rings: (T0, T1, (u0, v0, u1, v1)) --------------------------------------------------------
HIGHLIGHTS = [
    (29.90, 31.00, (0.04, 0.17, 0.27, 0.33)),
    (33.40, 36.30, (0.865, 0.060, 0.985, 0.135)),
    (38.00, 40.90, (0.05, 0.152, 0.64, 0.300)),
    (52.40, 55.30, (0.03, 0.680, 0.97, 0.800)),
    (58.30, 61.90, (0.03, 0.488, 0.97, 0.575)),
    (66.00, 69.60, (0.13, 0.640, 0.74, 0.690)),
    (73.50, 76.60, (0.08, 0.570, 0.68, 0.625)),
    (77.70, 78.40, (0.80, 0.708, 0.99, 0.758)),
    (84.60, 87.50, (0.03, 0.255, 0.97, 0.400)),
]

# ---- step chips in the phone scene: (T0, T1, n, label) ---------------------------------------------------
STEPS = [
    (26.58, 33.20, 1, "Open the Google app"),
    (33.20, 37.30, 2, "Tap your profile icon"),
    (37.30, 51.00, 3, "Manage your Google Account"),
    (51.00, 58.30, 4, "Data & privacy"),
    (58.30, 65.10, 5, "My Activity"),
    (65.10, 73.40, 6, "Manage My Activity verification"),
    (73.40, 80.50, 7, "Extra verification & Save"),
    (80.50, 91.90, 8, "Your history is now locked"),
]
N_STEPS = 8
