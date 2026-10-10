"""Quick look-dev harness for single scenes (not part of the final pipeline)."""
import sys, os, time
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hl_common import *
import hl_scenes as SC, hl_post as PP

SPECS = {
 "stars_mist": dict(pal="night", horizon=0.72, stars=1.0, sun=None,
     clouds=[dict(tex="c2", sc=1.1, speed=3, y0=.05, y1=.46, c0=.52, c1=.86, op=.45, dark=.8, par=.1)],
     layers=[("mountains", dict(n=5, y_far=.64, y_near=.88, amp_far=.035, amp_near=.10, mist=.8, rim=0.0)),
             ("birds", dict(flocks=0))], cam=dict(pan=(4, 0), zoom=(1.0, 1.06), shake=0.6)),
 "predawn": dict(pal="predawn", horizon=0.70, sun=dict(x=0.6, y=(0.72, 0.64), i=0.9, r=0.03, glow=0.9, disc=0.7), rays=0.5,
     clouds=[dict(tex="c1", sc=1.3, speed=4, y0=.05, y1=.52, c0=.55, cover=.40, op=.90, par=.15, silver=1.0),
             dict(tex="c2", sc=1.0, speed=7, y0=.10, y1=.58, c0=.52, c1=.86, op=.75, par=.3, dark=.7)],
     layers=[("mountains", dict(n=6, y_far=.60, y_near=.90, amp_far=.04, amp_near=.10, mist=.7, rim=.6))],
     cam=dict(pan=(5, 0), zoom=(1.0, 1.08))),
 "sunrise": dict(pal="sunrise", horizon=0.72, sun=dict(x=0.66, y=(0.66, 0.56), i=1.1, r=0.034, glow=1.0), rays=0.9, daylight=0.3,
     clouds=[dict(tex="c2", tex2="c3", sc=1.1, speed=4, y0=.03, y1=.42, c0=.56, cover=.45, op=.55, par=.1, silver=1.2, k=12),
             dict(tex="c1", tex2="c3", sc=1.25, speed=7, y0=.18, y1=.62, c0=.55, cover=.40, thick=.3, op=.95, par=.3, silver=1.1, k=12)],
     layers=[("mountains", dict(n=4, y_far=.66, y_near=.90, mist=.6, rim=.7)), ("birds", dict(flocks=2))],
     cam=dict(pan=(6, 0), zoom=(1.0, 1.10))),
 "dusk_city": dict(pal="dusk", horizon=0.70, sun=dict(x=0.30, y=0.66, i=0.9, r=0.03, glow=0.9), rays=0.4,
     clouds=[dict(tex="c1", sc=1.3, speed=5, y0=.05, y1=.52, c0=.55, cover=.40, op=.9, par=.2, silver=.9)],
     layers=[("city", dict(n=2, ground=.90, hmax=170, lit=.5, rim=.5, monuments=[("india_gate", .55, 1.25), ("jama", .22, 0.9), ("jantar", .86, 1.2)])),
             ("smoke", dict(kind="dark", amount=.35, y0=.55, y1=1.0, blend="over"))],
     cam=dict(pan=(-5, 0), zoom=(1.0, 1.08))),
 "crowd_flags": dict(pal="sunrise", horizon=0.66, sun=dict(x=0.5, y=0.58, i=1.2, r=0.04, glow=1.0), rays=1.0, daylight=0.3,
     clouds=[dict(tex="c1", sc=1.3, speed=6, y0=.04, y1=.52, c0=.55, cover=.40, op=.92, par=.2, silver=1.1)],
     layers=[("mountains", dict(n=2, y_far=.64, y_near=.74, mist=.5, rim=.5)), ("crowd", dict(rim=1.0)),
             ("smoke", dict(kind="tricolor", amount=.55, y0=.55, y1=1.0, blend="screen", bright=.55))],
     cam=dict(pan=(4, 0), zoom=(1.0, 1.08))),
 "red_protest": dict(pal="red", horizon=0.68, sun=dict(x=0.5, y=0.62, i=1.0, r=0.03, glow=1.0), rays=0.7,
     clouds=[dict(tex="c1", sc=1.2, speed=8, y0=.02, y1=.58, c0=.44, c1=.72, op=.95, par=.2, silver=.6, dark=.8)],
     layers=[("city", dict(n=2, ground=.88, hmax=140, lit=.3, rim=.4)), ("crowd", dict(rim=.8)),
             ("smoke", dict(kind="red", amount=.5, y0=.5, y1=1.0, blend="screen", bright=.45))],
     cam=dict(pan=(3, 0), zoom=(1.0, 1.1)), flashes=[(0.4, .5)]),
}
GRADES = {"default": dict(exp=1.0, sat=1.08, contrast=1.04, shadow=(0.0, 0.05, 0.12), shadow_amt=0.5, high=(1.08, 1.0, 0.9), vig=0.8)}

def render(name, tl, u, seed=3):
    sc = SC.Scene(SPECS[name], seed)
    t0 = time.time()
    img = sc.render(tl, u, kick=0.0)
    img = PP.bloom(img, 0.7, 0.30, streak=0.25)
    img = PP.grade(img, GRADES["default"])
    out = PP.upscale(PP.to_uint8_dither(img, 0))
    return out, time.time() - t0

if __name__ == "__main__":
    outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True)
    for name in sys.argv[2:]:
        t0 = time.time()
        sc = SC.Scene(SPECS[name], 3); tb = time.time() - t0
        tt = time.time()
        img = sc.render(2.0, 0.3, kick=0.0)
        img = PP.bloom(img, 0.7, 0.30, streak=0.25); img = PP.grade(img, GRADES["default"])
        Image.fromarray(PP.upscale(PP.to_uint8_dither(img, 0))).save(f"{outdir}/{name}.png")
        print(f"{name}: build {tb:.1f}s  frame {time.time()-tt:.2f}s")
