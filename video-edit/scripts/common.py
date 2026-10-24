"""Shared paths + the talking-head grade used by every script."""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# heavy intermediates (downloaded sources, frame sequences, renders) live outside git
WORK = os.environ.get("MB_WORK", "/tmp/claude-0/-home-user-mega-bite/191d1682-9e7f-56cd-92b6-2a5029aca8c1/scratchpad")
MAIN = os.path.join(WORK, "dl_main/main.mp4")
SCREEN = os.path.join(WORK, "dl_screen/screen.mp4")
LOGO = os.path.join(ROOT, "assets/logo.png")
FONT_DIR = os.path.join(ROOT, "assets/fonts")

# HDR (PQ / BT.2020) screen recording -> SDR BT.709.  The recording encodes UI white
# at ~100 nit, so 100 nit is mapped to SDR white (a normal 203-nit mapping looks grey).
SCREEN_TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=clip:desat=0,"
                  "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")

# Talking-head grade: gentle S-curve (lifts the backlit face, rolls the blown window off),
# warm skin, a touch of vibrance, light sharpening after the 4K -> 1080p downscale.
GRADE = ("curves=all='0/0 0.10/0.08 0.28/0.285 0.50/0.55 0.72/0.745 0.88/0.87 1/0.955',"
         "colorbalance=rs=0.01:bs=-0.015:rm=0.03:gm=0.004:bm=-0.028,"
         "eq=saturation=1.10:contrast=1.04,vibrance=intensity=0.18,"
         "unsharp=5:5:0.5:5:5:0.0")


def url(path):
    return "file://" + os.path.abspath(path)


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, check=True, **kw)


def load_styles():
    return json.load(open(os.path.join(ROOT, "config/styles.json")))


def style_for(palette, font):
    s = load_styles()
    return {"palette": s["palettes"][palette],
            "font": {"label": s["fonts"][font]["label"], "file": url(os.path.join(FONT_DIR, s["fonts"][font]["file"]))}}
