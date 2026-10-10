"""Shot list for the landscape video: 29 distinct procedural shots aligned to the 92.66 BPM bar grid, mapped to the song's sections."""
from hl_common import PHASE, BAR

DUR = 267.2


def bar_t(k):
    return PHASE + k * BAR


# ---- cloud presets ----------------------------------------------------------------------------------------------------
def cirrus(**k):
    d = dict(tex="c2", tex2="c3", sc=1.1, speed=4, y0=.03, y1=.40, c0=.56, cover=.45, edge=.09, op=.55, par=.1, silver=1.2, k=12, fade_top=.12)
    d.update(k); return d


def bank(**k):
    d = dict(tex="c1", tex2="c3", sc=1.25, speed=7, y0=.18, y1=.62, c0=.55, cover=.42, op=.95, par=.3, silver=1.1, k=12)
    d.update(k); return d


def storm(**k):
    d = dict(tex="c1", tex2="c3", sc=1.0, speed=9, y0=.02, y1=.62, c0=.50, cover=.62, op=.97, dark=.75, par=.25, silver=.5, k=10)
    d.update(k); return d


def fast(**k):                       # time-lapse clouds
    d = dict(speed=26, cover=.5)
    d.update(k)
    return bank(**d)


# ---- grades (hl_post.grade params) ------------------------------------------------------------------------------------
GRADES = {
    "night":   dict(exp=1.15, sat=1.00, contrast=1.05, shadow=(0.00, 0.05, 0.14), shadow_amt=0.55, high=(0.95, 1.0, 1.1), vig=0.85),
    "cool":    dict(exp=1.05, sat=1.05, contrast=1.04, shadow=(0.02, 0.05, 0.13), shadow_amt=0.5, high=(1.05, 1.0, 0.95), vig=0.8),
    "warm":    dict(exp=1.00, sat=1.10, contrast=1.05, shadow=(0.02, 0.04, 0.10), shadow_amt=0.45, high=(1.10, 1.0, 0.88), vig=0.8),
    "dusk":    dict(exp=1.05, sat=1.12, contrast=1.06, shadow=(0.03, 0.02, 0.10), shadow_amt=0.5, high=(1.10, 0.98, 0.9), vig=0.85),
    "golden":  dict(exp=0.98, sat=1.10, contrast=1.04, shadow=(0.02, 0.04, 0.09), shadow_amt=0.4, high=(1.12, 1.02, 0.88), vig=0.75),
    "glory":   dict(exp=0.95, sat=1.14, contrast=1.06, shadow=(0.02, 0.04, 0.10), shadow_amt=0.4, high=(1.10, 1.03, 0.90), vig=0.7),
    "red":     dict(exp=1.00, sat=1.12, contrast=1.10, shadow=(0.08, 0.0, 0.03), shadow_amt=0.55, high=(1.12, 0.95, 0.85), vig=0.9),
    "storm":   dict(exp=1.05, sat=0.95, contrast=1.10, shadow=(0.0, 0.04, 0.10), shadow_amt=0.6, high=(1.05, 0.98, 0.95), vig=0.95),
    "blue":    dict(exp=1.10, sat=1.05, contrast=1.06, shadow=(0.0, 0.05, 0.14), shadow_amt=0.55, high=(0.98, 1.0, 1.08), vig=0.85),
    "candle":  dict(exp=1.20, sat=1.05, contrast=1.04, shadow=(0.02, 0.02, 0.08), shadow_amt=0.5, high=(1.12, 1.0, 0.82), vig=0.95),
    "soft":    dict(exp=1.02, sat=1.02, contrast=1.00, shadow=(0.02, 0.04, 0.10), shadow_amt=0.4, high=(1.06, 1.0, 0.94), vig=0.7, fade=0.04),
}

N = lambda *a, **k: dict(*a, **k)

SHOTS = [
 # ---- INTRO: night -> pre-dawn -> sunrise (spoken, emotional) ------------------------------------------------------
 dict(name="s01_night_stars", b0=0, b1=4, grade="night", spec=dict(pal="night", horizon=0.72, stars=1.0,
      clouds=[cirrus(op=.35, dark=.8, cover=.30)], layers=[("mountains", N(n=5, y_far=.64, y_near=.88, amp_far=.035, amp_near=.10, mist=.8, rim=.0))],
      cam=dict(pan=(4, 0), zoom=(1.0, 1.06), shake=.5))),
 dict(name="s02_predawn_ridges", b0=4, b1=8, grade="cool", spec=dict(pal="predawn", horizon=0.70, sun=dict(x=.6, y=(.74, .64), i=.9, r=.03, glow=.9, disc=.7), rays=.5,
      clouds=[bank(c0=.56, op=.85, par=.15), cirrus()], layers=[("mountains", N(n=6, y_far=.60, y_near=.90, amp_far=.04, amp_near=.10, mist=.7, rim=.3)), ("birds", N(flocks=1))],
      cam=dict(pan=(5, 0), zoom=(1.0, 1.08)))),
 dict(name="s03_sunrise", b0=8, b1=12, grade="warm", spec=dict(pal="sunrise", horizon=0.72, sun=dict(x=.64, y=(.66, .55), i=1.1, r=.034, glow=1.0), rays=.9, daylight=.3,
      clouds=[cirrus(), bank(op=.92)], layers=[("mountains", N(n=4, y_far=.66, y_near=.90, mist=.6, rim=.3)), ("birds", N(flocks=2))],
      cam=dict(pan=(6, 0), zoom=(1.0, 1.10)))),
 # ---- BEAT BEGINS (chant) -------------------------------------------------------------------------------------------
 dict(name="s04_dusk_city_jantar", b0=12, b1=14, grade="dusk", spec=dict(pal="dusk", horizon=0.70, sun=dict(x=.30, y=.66, i=.9, r=.03, glow=.9), rays=.4,
      clouds=[bank(op=.85, par=.2)], layers=[("city", N(n=2, ground=.90, hmax=170, lit=.5, rim=.35, monuments=[("jantar", .70, 1.25), ("india_gate", .28, 1.1)])),
                                             ("smoke", N(kind="dark", amount=.35, y0=.55, y1=1.0))],
      cam=dict(pan=(-5, 0), zoom=(1.0, 1.08)))),
 dict(name="s05_march_crowd", b0=14, b1=16, grade="dusk", spec=dict(pal="dusk", horizon=0.66, sun=dict(x=.5, y=.60, i=1.0, r=.036, glow=1.0), rays=.8,
      clouds=[bank(op=.9)], layers=[("mountains", N(n=2, y_far=.64, y_near=.74, mist=.5, rim=.2)), ("crowd", N(rim=1.0)),
                                    ("smoke", N(kind="tricolor", amount=.55, y0=.55, y1=1.0, blend="screen", bright=.5))],
      cam=dict(pan=(3, 0), zoom=(1.0, 1.08)))),
 # ---- VERSE 1 -------------------------------------------------------------------------------------------------------
 dict(name="s06_golden_fort", b0=16, b1=20, grade="golden", spec=dict(pal="golden", horizon=0.70, sun=dict(x=.72, y=.64, i=1.0, r=.03, glow=.9), rays=.5, daylight=.5,
      clouds=[cirrus(), bank(op=.9)], layers=[("city", N(n=2, ground=.90, hmax=150, lit=.18, rim=.5, monuments=[("jama", .40, 1.1), ("parliament", .72, 1.0)])),
                                              ("birds", N(flocks=2))], cam=dict(pan=(-6, 0), zoom=(1.0, 1.10)))),
 dict(name="s07_fists_backlight", b0=20, b1=24, grade="golden", spec=dict(pal="sunrise", horizon=0.66, sun=dict(x=.35, y=.56, i=1.25, r=.04, glow=1.1), rays=1.0, daylight=.4,
      clouds=[bank(op=.9, c0=.57)], layers=[("mountains", N(n=3, y_far=.62, y_near=.76, mist=.5, rim=.3)), ("crowd", N(rim=1.2)),
                                            ("smoke", N(kind="saffron", amount=.4, y0=.6, y1=1.0, blend="screen", bright=.4))], cam=dict(pan=(4, 0), zoom=(1.0, 1.10)))),
 dict(name="s08_india_gate_rose", b0=24, b1=28, grade="dusk", spec=dict(pal="dusk", horizon=0.70, sun=dict(x=.62, y=.66, i=.95, r=.032, glow=.95), rays=.6,
      clouds=[fast(c0=.55, cover=.45, op=.9)], layers=[("city", N(n=2, ground=.90, hmax=160, lit=.45, rim=.45, monuments=[("india_gate", .5, 1.55), ("parliament", .15, 0.9)]))],
      cam=dict(pan=(5, 0), zoom=(1.0, 1.12)))),
 # ---- PRE-CHORUS --------------------------------------------------------------------------------------------------------
 dict(name="s09_rising_clouds", b0=28, b1=32, grade="warm", spec=dict(pal="sunrise", horizon=0.70, sun=dict(x=.5, y=(.72, .58), i=1.2, r=.036, glow=1.1), rays=1.1, daylight=.3,
      clouds=[fast(cover=.55, c0=.54, op=.95), cirrus(speed=14)], layers=[("mountains", N(n=4, y_far=.64, y_near=.88, mist=.75, rim=.45)), ("birds", N(flocks=2)),
                                                                          ("smoke", N(kind="tricolor", amount=.3, y0=.62, y1=1.0, blend="screen", bright=.35, speed=8))],
      cam=dict(pan=(5, 0), zoom=(1.0, 1.16)))),
 # ---- CHORUS ----------------------------------------------------------------------------------------------------------
 dict(name="s10_chorus_hills_flag", b0=32, b1=36, grade="glory", spec=dict(pal="golden", horizon=0.68, sun=dict(x=.45, y=.55, i=1.3, r=.04, glow=1.15), rays=1.2, daylight=.6,
      clouds=[cirrus(cover=.5), bank(op=.9, cover=.38)], layers=[("mountains", N(n=5, y_far=.62, y_near=.90, mist=.6, rim=.5)), ("birds", N(flocks=2)),
                                                                 ("bigflag", N(pos=(.60, -.05), scale=.85, blur=2.0, bright=1.0, op=1.0, amp=36, flip=False))],
      cam=dict(pan=(-4, 0), zoom=(1.0, 1.10)))),
 dict(name="s11_chorus_crowd", b0=36, b1=40, grade="glory", spec=dict(pal="sunrise", horizon=0.66, sun=dict(x=.5, y=.56, i=1.35, r=.042, glow=1.2), rays=1.3, daylight=.5,
      clouds=[bank(op=.9, c0=.56)], layers=[("mountains", N(n=2, y_far=.62, y_near=.74, mist=.5, rim=.3)), ("crowd", N(rim=1.3, flags=True)),
                                            ("smoke", N(kind="tricolor", amount=.7, y0=.5, y1=1.0, blend="screen", bright=.6))], cam=dict(pan=(3, 0), zoom=(1.0, 1.12)))),
 # ---- VERSE 2 (hard-hitting, red) ---------------------------------------------------------------------------------------
 dict(name="s12_red_protest", b0=40, b1=44, grade="red", spec=dict(pal="red", horizon=0.68, sun=dict(x=.5, y=.62, i=1.0, r=.03, glow=1.0), rays=.7,
      clouds=[storm(op=.95)], layers=[("city", N(n=2, ground=.88, hmax=140, lit=.3, rim=.4)), ("crowd", N(rim=.8)),
                                      ("smoke", N(kind="red", amount=.5, y0=.5, y1=1.0, blend="screen", bright=.45))], cam=dict(pan=(3, 0), zoom=(1.0, 1.10)), flashes=[(1.8, .5)])),
 dict(name="s13_storm_lightning", b0=44, b1=48, grade="storm", spec=dict(pal="storm", horizon=0.70, sun=dict(x=.25, y=.64, i=.7, r=.03, glow=.7), rays=.3,
      clouds=[storm(cover=.7, op=.98), storm(tex="c2", sc=1.1, cover=.5, op=.6, y0=.0, y1=.35)], layers=[("city", N(n=2, ground=.90, hmax=170, lit=.55, rim=.25, monuments=[("jama", .62, 1.2)]))],
      cam=dict(pan=(-4, 0), zoom=(1.0, 1.10)), flashes=[(1.2, .9), (1.45, .5), (6.0, .8), (8.4, .7)])),
 dict(name="s14_fists_saffron", b0=48, b1=52, grade="red", spec=dict(pal="red", horizon=0.66, sun=dict(x=.7, y=.60, i=1.2, r=.04, glow=1.1), rays=1.0,
      clouds=[storm(cover=.5, op=.9)], layers=[("mountains", N(n=2, y_far=.64, y_near=.74, mist=.4, rim=.2)), ("crowd", N(rim=1.1)),
                                               ("smoke", N(kind="saffron", amount=.6, y0=.45, y1=1.0, blend="screen", bright=.5))], cam=dict(pan=(-3, 0), zoom=(1.0, 1.12)))),
 dict(name="s15_flags_dark_smoke", b0=52, b1=56, grade="red", spec=dict(pal="dusk", horizon=0.68, sun=dict(x=.35, y=.62, i=1.1, r=.036, glow=1.0), rays=.9,
      clouds=[storm(cover=.55, op=.92, dark=.9)], layers=[("city", N(n=2, ground=.90, hmax=130, lit=.25, rim=.5)), ("crowd", N(rim=.9)),
                                                          ("smoke", N(kind="dark", amount=.5, y0=.4, y1=1.0)),
                                                          ("bigflag", N(pos=(.02, -.02), scale=.78, blur=4, bright=.8, op=.95, amp=34, flip=True))], cam=dict(pan=(3, 0), zoom=(1.0, 1.10)))),
 # ---- HOOK -------------------------------------------------------------------------------------------------------------
 dict(name="s16_jantar_sunrise", b0=56, b1=60, grade="golden", spec=dict(pal="golden", horizon=0.70, sun=dict(x=.40, y=(.68, .58), i=1.3, r=.04, glow=1.2), rays=1.2, daylight=.5,
      clouds=[cirrus(cover=.5), bank(op=.9)], layers=[("city", N(n=1, ground=.90, hmax=100, lit=.05, rim=.6, monuments=[("jantar", .62, 1.9)])), ("crowd", N(rim=1.0, flags=True, rows=None))],
      cam=dict(pan=(-4, 0), zoom=(1.0, 1.12)))),
 # ---- VERSE 3 (fast rap, quick cuts, cool/blue) -----------------------------------------------------------------------
 dict(name="s17_night_city_lights", b0=60, b1=62, grade="blue", spec=dict(pal="blue", horizon=0.70, stars=.4, sun=None,
      clouds=[cirrus(op=.35, dark=.8)], layers=[("city", N(n=3, ground=.90, hmax=190, lit=.8, rim=0.0, density=1.2)), ("bokeh", N(n=36, y0=.5, y1=.95, colors=[(1.0, .75, .4), (.5, .7, 1.0)], gain=.5))],
      cam=dict(pan=(8, 0), zoom=(1.0, 1.08)))),
 dict(name="s18_crowd_blue_magenta", b0=62, b1=64, grade="blue", spec=dict(pal="dusk", horizon=0.66, sun=dict(x=.55, y=.60, i=.9, r=.034, glow=.9), rays=.7,
      pal_over=dict(top=(.03, .05, .17), mid=(.30, .14, .40)), clouds=[bank(op=.9)], layers=[("crowd", N(rim=1.0)), ("smoke", N(kind="white", amount=.35, y0=.6, y1=1.0, blend="screen", bright=.3))],
      cam=dict(pan=(-6, 0), zoom=(1.0, 1.12)))),
 dict(name="s19_blue_hour_monuments", b0=64, b1=66, grade="blue", spec=dict(pal="blue", horizon=0.72, sun=dict(x=.2, y=.7, i=.7, r=.03, glow=.7), rays=.3,
      clouds=[cirrus(op=.5)], layers=[("city", N(n=2, ground=.90, hmax=150, lit=.6, rim=.2, monuments=[("india_gate", .35, 1.3), ("jama", .75, 1.0)]))],
      cam=dict(pan=(6, 0), zoom=(1.0, 1.10)))),
 dict(name="s20_flags_teal_orange", b0=66, b1=68, grade="cool", spec=dict(pal="sunrise", horizon=0.68, sun=dict(x=.7, y=.60, i=1.1, r=.038, glow=1.0), rays=.9,
      pal_over=dict(top=(.04, .16, .26)), clouds=[bank(op=.9)], layers=[("mountains", N(n=3, y_far=.64, y_near=.82, mist=.5, rim=.4)),
                                                                           ("smoke", N(kind="tricolor", amount=.5, y0=.5, y1=1.0, blend="screen", bright=.45)),
                                                                           ("bigflag", N(pos=(.55, -.04), scale=.8, blur=3, bright=.95, op=.95, amp=34))], cam=dict(pan=(4, 0), zoom=(1.0, 1.12)))),
 dict(name="s21_ascending_clouds", b0=68, b1=70, grade="soft", spec=dict(pal="predawn", horizon=0.70, sun=dict(x=.5, y=.7, i=.9, r=.03, glow=.9, disc=.6), rays=.6,
      clouds=[fast(speed=34, cover=.55), cirrus()], layers=[("mountains", N(n=4, y_far=.64, y_near=.88, mist=.7, rim=.3))], cam=dict(pan=(0, 3), zoom=(1.0, 1.12)))),
 # ---- BRIDGE (vigil) ---------------------------------------------------------------------------------------------------
 dict(name="s22_diyas_vigil", b0=70, b1=74, grade="candle", spec=dict(pal="night", horizon=0.74, stars=.8, sun=None,
      clouds=[cirrus(op=.3, dark=.8)], layers=[("mountains", N(n=3, y_far=.70, y_near=.84, mist=.7, rim=0.0)), ("bokeh", N(n=44, y0=.35, y1=.95, colors=[(1.0, .62, .25), (1.0, .8, .45)], gain=.6)),
                                                ("diyas", N(n=16, y=.88))], cam=dict(pan=(2, 0), zoom=(1.0, 1.06), shake=.4))),
 dict(name="s23_mist_dawn", b0=74, b1=78, grade="soft", spec=dict(pal="predawn", horizon=0.72, sun=dict(x=.55, y=(.76, .66), i=.9, r=.03, glow=.9, disc=.7), rays=.6,
      clouds=[cirrus(cover=.5, op=.6)], layers=[("mountains", N(n=6, y_far=.62, y_near=.90, amp_far=.04, amp_near=.10, mist=.95, rim=.3)), ("birds", N(flocks=1))],
      cam=dict(pan=(3, 0), zoom=(1.0, 1.08), shake=.5))),
 # ---- FINAL CHORUS ----------------------------------------------------------------------------------------------------
 dict(name="s24_grand_sunrise", b0=78, b1=82, grade="glory", spec=dict(pal="glow", horizon=0.68, sun=dict(x=.5, y=(.62, .50), i=1.5, r=.05, glow=1.4), rays=1.5, daylight=.8,
      clouds=[cirrus(cover=.5), bank(op=.85, cover=.4)], layers=[("mountains", N(n=5, y_far=.62, y_near=.90, mist=.6, rim=.6)), ("birds", N(flocks=2)),
                                                                 ("bigflag", N(pos=(.58, -.06), scale=.9, blur=1.6, bright=1.05, op=1.0, amp=38))], cam=dict(pan=(0, 0), zoom=(1.0, 1.14)))),
 dict(name="s25_crowd_peak", b0=82, b1=86, grade="glory", spec=dict(pal="glow", horizon=0.66, sun=dict(x=.5, y=.54, i=1.5, r=.05, glow=1.3), rays=1.4, daylight=.7,
      clouds=[bank(op=.85)], layers=[("mountains", N(n=2, y_far=.62, y_near=.74, mist=.5, rim=.3)), ("crowd", N(rim=1.4, flags=True)),
                                     ("smoke", N(kind="tricolor", amount=.85, y0=.45, y1=1.0, blend="screen", bright=.7))], cam=dict(pan=(2, 0), zoom=(1.0, 1.14)))),
 # ---- FINAL RAP ----------------------------------------------------------------------------------------------------------
 dict(name="s26_red_sky_fists", b0=86, b1=90, grade="red", spec=dict(pal="red", horizon=0.66, sun=dict(x=.45, y=.58, i=1.2, r=.04, glow=1.2), rays=1.0,
      clouds=[storm(cover=.6, op=.95)], layers=[("city", N(n=2, ground=.88, hmax=130, lit=.25, rim=.5)), ("crowd", N(rim=1.0)),
                                                ("smoke", N(kind="red", amount=.65, y0=.45, y1=1.0, blend="screen", bright=.55))], cam=dict(pan=(-3, 0), zoom=(1.0, 1.12)), flashes=[(2.5, .6)])),
 dict(name="s27_skyline_lightning", b0=90, b1=94, grade="storm", spec=dict(pal="storm", horizon=0.70, sun=dict(x=.7, y=.62, i=.9, r=.03, glow=.9), rays=.5,
      pal_over=dict(hor=(.95, .42, .14)), clouds=[storm(cover=.7, op=.98)], layers=[("city", N(n=3, ground=.90, hmax=200, lit=.6, rim=.4, monuments=[("india_gate", .3, 1.4)])),
                                                                                    ("smoke", N(kind="saffron", amount=.4, y0=.6, y1=1.0, blend="screen", bright=.4))],
      cam=dict(pan=(4, 0), zoom=(1.0, 1.12)), flashes=[(0.8, .8), (5.6, .9), (8.0, .6)])),
 # ---- OUTRO / FINAL VOICE -------------------------------------------------------------------------------------------------
 dict(name="s28_golden_calm", b0=94, b1=98, grade="golden", spec=dict(pal="golden", horizon=0.70, sun=dict(x=.35, y=.62, i=1.0, r=.034, glow=.95), rays=.6, daylight=.5,
      clouds=[cirrus(cover=.5), bank(op=.8, cover=.35)], layers=[("mountains", N(n=5, y_far=.62, y_near=.88, mist=.9, rim=.4)),
                                                                 ("smoke", N(kind="tricolor", amount=.35, y0=.5, y1=1.0, blend="screen", bright=.4, speed=8))], cam=dict(pan=(3, 0), zoom=(1.0, 1.08)))),
 dict(name="s29_dawn_over_india", b0=98, b1=103.1, grade="glory", spec=dict(pal="glow", horizon=0.70, sun=dict(x=.52, y=(.66, .52), i=1.4, r=.05, glow=1.3), rays=1.3, daylight=.8,
      clouds=[cirrus(cover=.5), bank(op=.8, cover=.35)], layers=[("mountains", N(n=3, y_far=.66, y_near=.80, mist=.6, rim=.5)),
                                                                 ("city", N(n=1, ground=.90, hmax=90, lit=.0, rim=.7, monuments=[("jantar", .50, 2.2)])), ("birds", N(flocks=2))],
      cam=dict(pan=(0, 0), zoom=(1.0, 1.10)))),
]

# transition INTO shot i from shot i-1: (kind, duration seconds)
TRANS = {1: ("dissolve", 1.4), 2: ("dissolve", 1.2), 3: ("flash", 0.7), 4: ("whip", 0.5), 5: ("smoke", 0.9), 6: ("dissolve", 0.8), 7: ("whip", 0.5),
         8: ("smoke", 0.9), 9: ("flash", 0.8), 10: ("dissolve", 0.8), 11: ("smoke", 0.9), 12: ("whip", 0.5), 13: ("dissolve", 0.8), 14: ("whip", 0.5),
         15: ("flash", 0.8), 16: ("smoke", 0.9), 17: ("whip", 0.4), 18: ("whip", 0.4), 19: ("dissolve", 0.5), 20: ("whip", 0.4), 21: ("dip", 1.4),
         22: ("dissolve", 1.6), 23: ("flash", 0.9), 24: ("dissolve", 0.8), 25: ("smoke", 1.0), 26: ("whip", 0.5), 27: ("dissolve", 1.5), 28: ("dissolve", 1.5)}


def shot_times(i):
    s = SHOTS[i]
    t0 = 0.0 if i == 0 else bar_t(s["b0"])
    t1 = DUR if i == len(SHOTS) - 1 else bar_t(s["b1"])
    return t0, t1


def transitions():
    """List of (shot_a, shot_b, kind, t_start, t_end): the cut lands on the bar line at 60 % of the transition."""
    out = []
    for i in range(1, len(SHOTS)):
        kind, d = TRANS[i]
        tb = shot_times(i)[0]
        out.append((i - 1, i, kind, tb - 0.6 * d, tb + 0.4 * d))
    return out
