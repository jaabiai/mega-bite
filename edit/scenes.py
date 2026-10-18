"""Scene specs for the two iPhone screen-recording demos.

Times are on the MAIN video timeline (seconds). `r` is time inside the screen recording.
Anchors come from the forced-aligned narration (edit/data/words_aligned.json): every tap / toggle / swipe is placed
on the word that describes it. Segments are (main_t0, main_t1, r0, speed); jumps only skip idle/identical UI.
"""
SRC_H = 2868


def V(x, y, z, ay=0.38):
    """camera (cx, cy, z) that puts source point (x, y) at `ay` of the window height"""
    return (x, y + (0.5 - ay) * SRC_H / z, z)


FULL = (660, 1434, 1.0)


def K(t, view):
    return (t, *view)


# ---- element rects (source px of the 1320x2868 recording) ---------------------------------------
STAR_ROW = (30, 955, 1290, 1150)
CLOCK = (950, 946, 1118, 1114)
MENU1_PRESETS = (380, 1125, 1090, 1539)
MENU1_LATER = (370, 1539, 1090, 1677)
NR_DT_CARD = (60, 1000, 1260, 1630)
NR_DATE = (60, 1000, 1260, 1195)
NR_TIME = (60, 1205, 1260, 1425)
NR_URGENT_L1 = (60, 1450, 1260, 1645)
NR_URGENT_L2 = (60, 1485, 1260, 1690)
NR_REPEAT = (60, 1940, 1260, 2105)
NR_REPEAT_MENU = (444, 490, 1196, 2040)
NR_LIST = (60, 2290, 1260, 2465)
NR_CHECK = (1126, 246, 1262, 382)
MENU2_EDIT = (380, 1130, 1090, 1262)
MENU2_MARK = (380, 1262, 1090, 1396)

S1 = dict(
    name="S1_reminder",
    t0=29.60, t1=108.70,
    segs=[
        (29.60, 33.60, 6.30, 1),      # home idle -> tap Phone r9.2 -> Contacts
        (33.60, 36.45, 18.70, 1),     # Contacts idle -> tap Recents r19.9 -> Recents
        (36.45, 51.90, 21.55, 1),     # idle Recents while the missed call is explained
        (51.90, 56.00, 46.27, 1),     # swipe r48.17-50.37 on "idathuvashaththekk swipe cheythu"
        (56.00, 58.60, 52.67, 1),     # idle swiped row ("clock icon kaanaan sadhikkum")
        (58.60, 66.00, 55.27, 1),     # tap clock r55.27 -> Callback Reminder menu
        (66.00, 70.52, 63.95, 1),     # tap "Remind Me Later..." r67.4 -> New Reminder r68.47
        (70.52, 76.00, 68.47, 1),     # New Reminder: date / time
        (76.00, 81.60, 90.87, 1),     # Urgent toggle r92.47 on "enable"
        (81.60, 83.60, 97.80, 1),     # list bounce (real motion, no cut)
        (83.60, 93.03, 99.80, 1),     # Repeat menu r100.4, List r103.75 -> back, tick
        (93.03, 95.30, 113.40, 1),    # tick -> sheet closes r114.87 (discard dialog r111-113 skipped)
        (95.30, 99.90, 129.20, 1),    # idle Recents
        (99.90, 100.90, 133.80, 1),   # 2nd swipe r133.8
        (100.90, 108.70, 137.87, 1),  # tap clock r138.87 -> Edit / Mark as Completed menu
    ],
    camera=[
        K(29.6, FULL), K(41.5, FULL),
        K(42.2, V(660, 1050, 1.06, 0.42)), K(53.4, V(660, 1050, 1.06, 0.42)),
        K(54.2, V(860, 1040, 1.35, 0.42)), K(56.0, V(860, 1040, 1.35, 0.42)),
        K(56.7, V(1034, 1030, 2.1, 0.40)), K(58.7, V(1034, 1030, 2.1, 0.40)),
        K(59.4, V(733, 1330, 1.5, 0.42)), K(69.7, V(733, 1330, 1.5, 0.42)),
        K(70.5, V(660, 1300, 1.12, 0.45)), K(73.4, V(660, 1300, 1.12, 0.45)),
        K(74.2, V(660, 1320, 1.25, 0.45)), K(75.1, V(660, 1320, 1.25, 0.45)),
        K(75.8, V(700, 1550, 1.45, 0.40)), K(77.7, V(700, 1550, 1.45, 0.40)),
        K(78.5, V(660, 1560, 1.25, 0.45)), K(83.2, V(660, 1560, 1.25, 0.45)),
        K(84.0, FULL), K(86.4, FULL),
        K(86.8, V(660, 2376, 1.3, 0.55)), K(87.7, V(660, 2376, 1.3, 0.55)),
        K(88.1, FULL), K(90.0, FULL),
        K(90.7, (860, 700, 1.6)), K(94.2, (860, 700, 1.6)),
        K(94.9, FULL), K(95.5, FULL),
        K(96.8, V(660, 1050, 1.06, 0.42)), K(99.7, V(660, 1050, 1.06, 0.42)),
        K(100.1, V(860, 1040, 1.35, 0.42)), K(100.9, V(860, 1040, 1.35, 0.42)),
        K(101.5, V(1034, 1030, 2.1, 0.40)), K(102.0, V(1034, 1030, 2.1, 0.40)),
        K(102.7, V(733, 1190, 1.6, 0.40)), K(108.7, V(733, 1190, 1.6, 0.40)),
    ],
    focus=[
        dict(t0=43.4, t1=46.4, rect=STAR_ROW, radius=40, dim=0.38),
        dict(t0=56.45, t1=58.55, rect=CLOCK, radius=84, pad=10, dim=0.45),
        dict(t0=59.8, t1=64.1, rect=MENU1_PRESETS, radius=30, pad=8, dim=0.40),
        dict(t0=66.6, t1=69.45, rect=MENU1_LATER, radius=30, pad=8, dim=0.45),
        dict(t0=70.8, t1=73.7, rect=NR_DT_CARD, radius=50, pad=10, dim=0.30),
        dict(t0=73.7, t1=74.35, rect=NR_DATE, radius=40, pad=6, dim=0.42),
        dict(t0=74.35, t1=75.2, rect=NR_TIME, radius=40, pad=6, dim=0.42),
        dict(t0=75.35, t1=77.5, rect=NR_URGENT_L1, radius=40, pad=6, dim=0.42),
        dict(t0=77.75, t1=83.0, rect=NR_URGENT_L2, radius=40, pad=6, dim=0.42),
        dict(t0=83.7, t1=84.25, rect=NR_REPEAT, radius=40, pad=6, dim=0.40),
        dict(t0=84.6, t1=85.8, rect=NR_REPEAT_MENU, radius=60, pad=6, dim=0.30),
        dict(t0=86.6, t1=87.5, rect=NR_LIST, radius=40, pad=6, dim=0.42),
        dict(t0=90.2, t1=94.15, rect=NR_CHECK, radius=80, pad=10, dim=0.45),
        dict(t0=96.6, t1=99.85, rect=STAR_ROW, radius=40, dim=0.38),
        dict(t0=101.0, t1=101.8, rect=CLOCK, radius=84, pad=10, dim=0.45),
        dict(t0=104.0, t1=105.9, rect=MENU2_EDIT, radius=30, pad=8, dim=0.42),
        dict(t0=105.9, t1=108.6, rect=MENU2_MARK, radius=30, pad=8, dim=0.42),
    ],
    taps=[
        dict(t=32.45, x=224, y=2640),    # Phone dock icon
        dict(t=34.75, x=516, y=2705),    # Recents tab
        dict(t=58.55, x=1034, y=1030),   # clock icon
        dict(t=69.45, x=720, y=1608),    # Remind Me Later...
        dict(t=77.55, x=1104, y=1550),   # Urgent toggle
        dict(t=84.20, x=700, y=2022),    # Repeat
        dict(t=87.55, x=700, y=2376),    # List
        dict(t=94.20, x=1194, y=314),    # tick
        dict(t=101.85, x=1034, y=1030),  # clock icon (2nd time)
    ],
    swipes=[
        dict(t0=53.8, t1=56.0, x0=1190, x1=870, y=1040),
        dict(t0=99.9, t1=100.9, x0=1190, x1=870, y=1040),
    ],
)

S2 = dict(
    name="S2_voice_isolation",
    t0=131.60, t1=154.70,
    segs=[
        (131.60, 137.73, 194.67, 1),      # home -> Settings (r195.37) -> scroll -> Accessibility (r199.27)
        (137.73, 140.34, 200.80, 1.65),   # scroll to the hearing section
        (140.34, 145.40, 205.10, 1),      # Audio & Visual visible, tapped r208.83
        (145.40, 151.30, 210.16, 1.72),   # scroll down to Voice Isolation (settles r220.3)
        (151.30, 154.70, 224.40, 1),      # toggle ON r225.2 on "enable"
    ],
    tracks={
        "ACC": dict(ref_r=198.9, rect=(240, 2015, 580, 2085), ra=195.2, rb=200.0),
        "AV": dict(ref_r=205.5, rect=(240, 2325, 620, 2395), ra=200.0, rb=206.0),
        "VI": dict(ref_r=224.0, rect=(110, 2095, 620, 2165), ra=209.0, rb=226.0),
    },
    camera=[
        K(131.6, FULL), K(134.4, FULL),
        K(135.1, V(660, 2046, 1.35, 0.50)), K(136.2, V(660, 2046, 1.35, 0.50)),
        K(136.9, FULL), K(139.8, FULL),
        K(140.9, V(660, 2356, 1.4, 0.55)), K(144.0, V(660, 2356, 1.4, 0.55)),
        K(144.6, FULL), K(151.0, FULL),
        K(151.7, V(660, 2128, 1.15, 0.5)), K(154.7, V(660, 2128, 1.15, 0.5)),
    ],
    focus=[
        dict(t0=131.7, t1=132.25, rect=(700, 1895, 920, 2200), radius=50, pad=10, dim=0.45),
        dict(t0=134.55, t1=136.15, rect=(60, 1960, 1260, 2130), radius=40, pad=6, dim=0.40, track="ACC"),
        dict(t0=140.4, t1=144.0, rect=(60, 2270, 1260, 2440), radius=40, pad=6, dim=0.42, track="AV"),
        dict(t0=147.6, t1=152.0, rect=(60, 2040, 1260, 2220), radius=44, pad=6, dim=0.42, track="VI"),
        dict(t0=152.35, t1=154.65, rect=(1000, 2075, 1214, 2182), radius=60, pad=8, dim=0.45),
    ],
    taps=[
        dict(t=132.25, x=810, y=2016),
        dict(t=136.15, x=660, y=2046),
        dict(t=144.05, x=660, y=2356),
        dict(t=152.10, x=1110, y=2128),
    ],
    swipes=[],
)
