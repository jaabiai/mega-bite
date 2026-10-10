"""Shot list of the Reel (song seconds 104.0 - 155.0): five of the landscape video's procedural shots, re-composed for a vertical frame.

Same moods and cut points (bar grid, 92.66 BPM) as the landscape video - red protest dusk -> storm -> saffron fists -> dark smoke + flags ->
Jantar-Mantar sunrise - but every spec is re-framed for 720x1280 (taller sky, bigger skyline / crowd / flag sprites, sun and monuments placed
for a 9:16 composition).  All imagery is generated in code (no stock or third-party footage).
"""
import rl_common  # noqa: F401  (must be first)
from rl_common import *
from hl_common import PHASE, BAR
import hl_timeline as T

N = T.N
storm, cirrus, bank = T.storm, T.cirrus, T.bank
GRADES = T.GRADES
MY = 90                                     # hl_scenes.MY: frame offset inside the sprite canvases
WHK = C.WH


def bar_t(k):
    return PHASE + k * BAR


def crowd_rows(scales=(1.1, 1.6, 2.3), bases=(.775, .87, 1.0), raised=(.30, .28, .20), poles=(.62, .55, .35)):
    return [dict(scale=s, base=MY + b * WHK, density=d, raised_prob=r, pole_prob=p)
            for s, b, d, r, p in zip(scales, bases, (0.95, 1.0, 1.05), raised, poles)]


SHOTS = [
    # ---- 1  (landscape s12) verse 2 opens: red protest dusk, flash on the first hit -------------------------------------------------
    dict(name="r1_red_protest", src="s12_red_protest", b0=40, b1=44, grade="red", seed=12, spec=dict(
        pal="red", horizon=0.62, sun=dict(x=.50, y=.47, i=1.05, r=.036, glow=1.1), rays=.85,
        clouds=[storm(op=.95, y1=.60)],
        layers=[("city", N(n=2, ground=.77, hmax=290, hmin=60, lit=.34, rim=.45, density=1.15)),
                ("crowd", N(rim=.9, rows=crowd_rows())),
                ("smoke", N(kind="red", amount=.55, y0=.52, y1=1.0, blend="screen", bright=.5))],
        cam=dict(pan=(3, 0), zoom=(1.0, 1.10)), flashes=[(1.8, .5)])),
    # ---- 2  (s13) storm over the city, lightning --------------------------------------------------------------------------------
    dict(name="r2_storm_lightning", src="s13_storm_lightning", b0=44, b1=48, grade="storm", seed=13, spec=dict(
        pal="storm", horizon=0.64, sun=dict(x=.28, y=.52, i=.75, r=.034, glow=.8), rays=.35,
        clouds=[storm(cover=.70, op=.98, y1=.64), storm(tex="c2", sc=1.1, cover=.5, op=.6, y0=.0, y1=.35)],
        layers=[("city", N(n=2, ground=.88, hmax=360, hmin=70, lit=.6, rim=.3, density=1.1, monuments=[("jama", .60, 1.7)])),
                ("bokeh", N(n=26, y0=.74, y1=.97, colors=[(1.0, .72, .38), (.62, .76, 1.0)], gain=.5)),
                ("smoke", N(kind="dark", amount=.45, y0=.66, y1=1.0, fade=.2))],
        cam=dict(pan=(-4, 0), zoom=(1.0, 1.10)), flashes=[(1.2, .9), (1.45, .5), (6.0, .8), (8.4, .7)])),
    # ---- 3  (s14) fists against a saffron sky ----------------------------------------------------------------------------------
    dict(name="r3_fists_saffron", src="s14_fists_saffron", b0=48, b1=52, grade="red", seed=14, spec=dict(
        pal="red", horizon=0.62, sun=dict(x=.62, y=.46, i=1.25, r=.042, glow=1.15), rays=1.05,
        clouds=[storm(cover=.5, op=.9, y1=.60)],
        layers=[("mountains", N(n=3, y_far=.70, y_near=.80, mist=.45, rim=.25, amp_far=.03, amp_near=.05)),
                ("crowd", N(rim=1.1, rows=crowd_rows(scales=(1.05, 1.5, 2.15)))),
                ("smoke", N(kind="saffron", amount=.62, y0=.50, y1=1.0, blend="screen", bright=.55))],
        cam=dict(pan=(-3, 0), zoom=(1.0, 1.12)))),
    # ---- 4  (s15) flags in dark smoke, big foreground flag ---------------------------------------------------------------------
    dict(name="r4_flags_dark_smoke", src="s15_flags_dark_smoke", b0=52, b1=56, grade="red", seed=15, spec=dict(
        pal="dusk", horizon=0.62, sun=dict(x=.38, y=.50, i=1.15, r=.040, glow=1.05), rays=.95,
        clouds=[storm(cover=.55, op=.92, dark=.9, y1=.60)],
        layers=[("city", N(n=2, ground=.77, hmax=280, hmin=60, lit=.30, rim=.5, density=1.1)),
                ("crowd", N(rim=.95, rows=crowd_rows())),
                ("smoke", N(kind="dark", amount=.55, y0=.42, y1=1.0)),
                ("bigflag", N(pos=(-.04, .02), size=(900, 560), scale=.62, blur=4, bright=.85, op=.95, amp=34, flip=True))],
        cam=dict(pan=(3, 0), zoom=(1.0, 1.10)))),
    # ---- 5  (s16) the hook: Jantar-Mantar at sunrise ---------------------------------------------------------------------------
    dict(name="r5_jantar_sunrise", src="s16_jantar_sunrise", b0=56, b1=60, grade="golden", seed=16, spec=dict(
        pal="golden", horizon=0.66, sun=dict(x=.34, y=(.60, .50), i=1.35, r=.044, glow=1.25), rays=1.25, daylight=.5,
        clouds=[cirrus(cover=.5, y1=.50), bank(op=.9, y1=.62)],
        layers=[("city", N(n=1, ground=.78, hmax=140, hmin=40, lit=.05, rim=.65, monuments=[("jantar", .56, 2.15)])),
                ("crowd", N(rim=1.05, flags=True, rows=crowd_rows())),
                ("birds", N(flocks=2))],
        cam=dict(pan=(-4, 0), zoom=(1.0, 1.12)))),
]

# transition INTO shot i from shot i-1: (kind, seconds).  "vwhip" = whip pan along the vertical axis (the landscape cut used a horizontal whip).
TRANS = {1: ("vwhip", 0.5), 2: ("dissolve", 0.8), 3: ("vwhip", 0.5), 4: ("flash", 0.8)}


def shot_times(i):
    s = SHOTS[i]
    return bar_t(s["b0"]), bar_t(s["b1"])


def transitions():
    """(a, b, kind, t_start, t_end) in song seconds; the cut lands on the bar line at 60 % of the transition (as in the landscape video)."""
    out = []
    for i in range(1, len(SHOTS)):
        kind, d = TRANS[i]
        tb = shot_times(i)[0]
        out.append((i - 1, i, kind, tb - 0.6 * d, tb + 0.4 * d))
    return out
