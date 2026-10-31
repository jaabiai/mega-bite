"""Edit decision data for "shoot 48 MP photos on iPhone" (Settings > Camera > Formats, then Camera app > Aspect / Format).

T = output (narration) time in seconds, S = time inside the screen recording.
"""
import numpy as np

FPS = 30
NARR_END = 149.07
END_CARD = 6.0
TOTAL = NARR_END + END_CARD

# screen recording: recording-time of the first frame of screen_clean60.mp4 and of the last usable frame
SCREEN_T0, SCREEN_END = 2.0, 196.0

# on-screen furniture (output times, seconds)
TITLE_T = (0.35, 3.6)                                   # hook title
TITLE_LINES = [("SHOOT 48 MP PHOTOS", False), ("ON YOUR IPHONE", True)]
REVEAL_T0 = 21.00                                       # logo sting ("Welcome to MEGABYTE")
SUBSCRIBE_T = (16.80, 19.80)                            # subscribe button
SHARE_T = [(13.40, 16.75), (141.90, 145.55)]            # share button (early ask + closing ask)
FACE_ANCHOR = dict(fx=0.50, fy=0.24)                    # face centre in the source frame (for framing + grade window)

# colour grade overrides for this footage (bright window, beige shirt): gentle local contrast / split-tone
GRADE = dict(clarity=0.05, face_lift=0.14, tint=0.35)

# project-specific sound effects (time, mixkit id, gain dB) on top of the generic transition / tap / step ones
EXTRA_SFX = [(0.55, "3124", -15),
             (17.95, "2354", -10), (18.08, "933", -13),               # subscribe click + bell
             (14.35, "2354", -10),                                    # share
             (21.05, "3005", -13),                                    # logo sting
             (88.00, "3005", -12), (89.05, "2852", -12),              # 48 MP lands
             (142.85, "2354", -10)]                                   # share (closing)

# ---- scenes -----------------------------------------------------------------------------------------
# kind: face | broll | graphic | phone | end     (broll: clip = landscape id, reel_clip = vertical id)
SCENES = [
    dict(kind="face",    t0=0.00,   t1=4.72,   zoom=(1.10, 1.17), name="hook"),
    dict(kind="broll",   t0=4.72,   t1=7.40,   clip="41181", clip_t=1.0, reel_clip="5052", reel_clip_t=1.0, name="phone-camera"),
    dict(kind="face",    t0=7.40,   t1=13.35,  zoom=(1.16, 1.10), name="feature"),
    dict(kind="face",    t0=13.35,  t1=16.75,  zoom=(1.12, 1.19), name="share"),
    dict(kind="face",    t0=16.75,  t1=19.20,  zoom=(1.20, 1.14), name="subscribe"),
    dict(kind="face",    t0=19.20,  t1=24.30,  zoom=(1.12, 1.20), name="welcome"),
    dict(kind="phone",   t0=24.30,  t1=86.00,  name="settings-and-camera"),
    dict(kind="graphic", t0=86.00,  t1=96.90,  graphic="megapixel", name="48mp"),
    dict(kind="face",    t0=96.90,  t1=101.50, zoom=(1.18, 1.12), name="until-you-do"),
    dict(kind="phone",   t0=101.50, t1=131.40, name="photos"),
    dict(kind="face",    t0=131.40, t1=137.90, zoom=(1.12, 1.20), name="great-resolution"),
    dict(kind="face",    t0=137.90, t1=141.60, zoom=(1.20, 1.13), name="useful"),
    dict(kind="face",    t0=141.60, t1=146.40, zoom=(1.13, 1.20), name="share-2"),
    dict(kind="face",    t0=146.40, t1=NARR_END, zoom=(1.20, 1.12), name="outro"),
    dict(kind="end",     t0=NARR_END, t1=TOTAL, name="end-card"),
]

# transitions between scenes (and punches over the two hard cuts inside the first phone scene): (time, kind)
TRANSITIONS = [
    (4.72, "wipe"), (7.40, "zoom"), (13.35, "zoom"), (16.75, "zoom"), (19.20, "zoom"), (24.30, "wipe"),
    (57.56, "zoom"), (61.31, "zoom"),
    (86.00, "wipe"), (96.90, "zoom"), (101.50, "wipe"), (131.40, "wipe"),
    (137.90, "zoom"), (141.60, "zoom"), (146.40, "zoom"), (NARR_END, "wipe"),
]

# ---- screen recording re-timing (T -> S), piecewise linear, monotonic ---------------------------------
#  S 2-6.5 home | 6.6 Settings opens | 10.2 tap Camera | 15.3 tap Formats | 36.3 Photo Mode picker (12 / 24 MP) | 46.7 ProRAW picker |
#  70.4 home | 73 Camera app | 76.6-79.8 NOTIFICATION CENTRE (bank messages: skipped) | 89.4 controls | 100.2 Aspect 4:3 |
#  110.2 controls | 115.6 Format picker (24 / 48 MP) | 150-196 Photos: 8 MP (food) 12 MP (macro) 24 MP (school record: blurred)
SCREEN_MAP = [
    (24.30, 2.00), (27.90, 6.30), (28.10, 6.60), (28.45, 7.00),
    (30.55, 10.15), (31.20, 10.55), (33.20, 13.00), (34.60, 15.30), (34.95, 15.60),
    (45.70, 36.30), (46.25, 37.00), (47.45, 41.20), (47.65, 41.50),
    (50.90, 46.60), (51.35, 47.00), (57.00, 56.30), (57.55, 56.70),
    (57.56, 70.30),                                                     # cut: back to the home screen
    (59.80, 72.70), (60.10, 73.00), (60.60, 73.50), (61.30, 76.30),
    (61.31, 79.90),                                                     # cut: over the Notification Centre
    (65.15, 89.30), (65.50, 90.00), (70.95, 100.20), (71.80, 101.00), (75.90, 108.40),
    (77.40, 110.20), (77.90, 111.00), (80.90, 115.60), (81.30, 116.00), (84.50, 118.60), (86.00, 122.00),
    (101.50, 151.00), (104.00, 153.00), (105.20, 154.60), (106.40, 156.80), (107.00, 157.10),
    (107.01, 176.20),                                                   # same state (info panel up), a calmer stretch of the recording
    (112.70, 178.60), (113.10, 179.00), (113.60, 180.00), (114.60, 181.60), (115.30, 182.60), (116.00, 183.20),
    (118.10, 185.20), (119.00, 187.20), (119.70, 188.60), (120.30, 189.50),
    (127.00, 193.30), (131.40, 193.60),
    (149.07, 193.60),
]


def screen_time(T):
    ts = [p[0] for p in SCREEN_MAP]
    ss = [p[1] for p in SCREEN_MAP]
    return float(np.interp(T, ts, ss))


# ---- camera on the phone: keyframes (T, zoom, u, v) – screen point (u,v) is pulled to the anchor -----------
CAMERA = [
    # scene 1: Settings > Camera > Formats
    (24.30, 0.80, 0.50, 0.50), (25.10, 1.00, 0.50, 0.50), (25.90, 1.00, 0.50, 0.50),
    (26.90, 1.55, 0.60, 0.68), (28.00, 1.55, 0.60, 0.68),                                  # Settings icon
    (28.60, 1.10, 0.50, 0.50), (29.60, 1.10, 0.50, 0.50),
    (30.20, 1.45, 0.45, 0.62), (31.00, 1.45, 0.45, 0.62),                                  # Camera row
    (31.60, 1.20, 0.50, 0.50), (33.00, 1.20, 0.50, 0.50),
    (33.40, 1.50, 0.45, 0.78), (34.90, 1.50, 0.45, 0.78),                                  # Formats row
    (35.40, 1.25, 0.50, 0.30), (39.50, 1.25, 0.50, 0.30),                                  # High Efficiency
    (40.50, 1.35, 0.50, 0.52), (45.70, 1.35, 0.50, 0.52),                                  # Photo Mode
    (46.10, 1.25, 0.50, 0.25), (47.40, 1.25, 0.50, 0.25),                                  # 12 / 24 MP picker
    (47.90, 1.35, 0.50, 0.55), (50.90, 1.35, 0.50, 0.55),                                  # ProRAW Format
    (51.30, 1.25, 0.50, 0.28), (56.90, 1.25, 0.50, 0.28),                                  # JPEG Lossless
    (57.30, 1.00, 0.50, 0.50), (58.80, 1.00, 0.50, 0.50),
    (59.30, 1.45, 0.42, 0.62), (59.95, 1.45, 0.42, 0.62),                                  # Camera icon
    (60.50, 1.10, 0.50, 0.50), (62.50, 1.00, 0.50, 0.50),
    (63.90, 1.45, 0.80, 0.80), (65.30, 1.45, 0.80, 0.80),                                  # controls button
    (65.80, 1.35, 0.62, 0.70), (70.80, 1.35, 0.65, 0.66),                                  # controls panel / Aspect
    (71.30, 1.40, 0.50, 0.86), (75.80, 1.40, 0.50, 0.86),                                  # Aspect 4:3
    (76.50, 1.20, 0.50, 0.70), (77.10, 1.35, 0.80, 0.80), (77.50, 1.35, 0.80, 0.80),
    (77.95, 1.35, 0.68, 0.76), (80.80, 1.35, 0.70, 0.78),                                  # Format tile
    (81.20, 1.40, 0.55, 0.88), (84.90, 1.40, 0.55, 0.88),                                  # 24 / 48 MP
    (86.00, 1.10, 0.50, 0.55),
    # scene 2: Photos
    (101.50, 0.80, 0.50, 0.50), (102.30, 1.00, 0.50, 0.50), (105.00, 1.00, 0.50, 0.50),
    (106.00, 1.35, 0.50, 0.76), (112.80, 1.35, 0.50, 0.76),                                # 8 MP line
    (113.50, 1.10, 0.50, 0.50), (115.60, 1.10, 0.50, 0.50),
    (116.20, 1.35, 0.50, 0.76), (118.00, 1.35, 0.50, 0.76),                                # 12 MP line
    (118.60, 1.10, 0.50, 0.50), (120.00, 1.10, 0.50, 0.50),
    (120.70, 1.35, 0.50, 0.80), (131.40, 1.35, 0.50, 0.80),                                # 24 MP line
]

# ---- taps: (T, u, v) on the screen --------------------------------------------------------------------
TAPS = [
    (27.95, 0.60, 0.70),       # Settings
    (30.50, 0.30, 0.638),      # Camera
    (34.60, 0.30, 0.786),      # Formats
    (45.70, 0.50, 0.516),      # Photo Mode
    (50.90, 0.50, 0.575),      # ProRAW Format
    (59.80, 0.38, 0.59),       # Camera app
    (65.15, 0.867, 0.838),     # controls button
    (70.95, 0.79, 0.62),       # Aspect
    (77.40, 0.867, 0.838),     # controls button
    (80.90, 0.79, 0.88),       # Format
    (84.50, 0.67, 0.93),       # 48 MP
]

# ---- highlight rings: (T0, T1, (u0, v0, u1, v1)) --------------------------------------------------------
HIGHLIGHTS = [
    (25.60, 28.00, (0.49, 0.650, 0.71, 0.770)),      # Settings icon
    (33.40, 34.80, (0.04, 0.755, 0.96, 0.820)),      # Formats row
    (36.10, 39.00, (0.07, 0.185, 0.96, 0.245)),      # High Efficiency
    (42.60, 45.60, (0.07, 0.487, 0.96, 0.545)),      # Photo Mode (24 MP)
    (46.30, 47.30, (0.05, 0.200, 0.96, 0.255)),      # 24 MP in the picker
    (48.60, 50.80, (0.07, 0.552, 0.96, 0.635)),      # ProRAW Format
    (51.50, 54.50, (0.05, 0.185, 0.96, 0.245)),      # JPEG Lossless (Most Compatible)
    (64.30, 65.30, (0.79, 0.800, 0.945, 0.875)),     # controls button
    (68.00, 71.00, (0.69, 0.550, 0.92, 0.700)),      # Aspect
    (73.00, 75.80, (0.27, 0.890, 0.40, 0.950)),      # 4:3
    (79.00, 81.00, (0.69, 0.830, 0.90, 0.960)),      # Format
    (82.20, 84.80, (0.57, 0.905, 0.78, 0.955)),      # 48 MP
    (106.60, 112.80, (0.03, 0.725, 0.97, 0.795)),    # 8 MP
    (116.30, 118.40, (0.03, 0.740, 0.97, 0.805)),    # 12 MP
    (120.60, 127.00, (0.03, 0.800, 0.97, 0.870)),    # 24 MP
]

# ---- step chips in the phone scenes: (T0, T1, n, label) ---------------------------------------------------
STEPS = [
    (24.30, 31.30, 1, "Open Settings > Camera"),
    (31.30, 35.00, 2, "Tap Formats"),
    (35.00, 47.60, 3, "High Efficiency + 24 MP"),
    (47.60, 57.50, 4, "ProRAW: JPEG Lossless"),
    (57.50, 76.00, 5, "Camera app > Aspect 4:3"),
    (76.00, 86.00, 6, "Format > 48 MP"),
    (101.50, 131.40, 7, "Check the result in Photos"),
]
N_STEPS = 7
