#!/usr/bin/env python3
"""1280x720 YouTube thumbnail from the face-cam + brand elements.

usage: make_thumbnail.py <face.mp4> <t_seconds> <out.jpg> [--palette volt]
"""
import argparse, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import brand, grade, graphics as G, scene as scene_mod
from caption import font
from gfx import blend, blend_glow, glow_of, rrect, with_mask, aa_shape

ap = argparse.ArgumentParser()
ap.add_argument("face"); ap.add_argument("t", type=float); ap.add_argument("out")
ap.add_argument("--palette", default="volt")
a = ap.parse_args()
PAL = brand.PALETTES[a.palette]
ACC = brand.hex2rgb(PAL["accent"]); DARK = brand.hex2rgb(PAL["on_accent"])
W, H = 1280, 720
S = W / 1920.0

raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a.t), "-i", a.face, "-frames:v", "1", "-vf", "scale=2560:1440:flags=lanczos",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
src = np.frombuffer(raw, np.uint8).reshape(1440, 2560, 3)
z, fx, fy, tx, ty = 1.42, 0.54, 0.36, 0.77, 0.50                      # tight crop, face on the right
x0 = min(max(fx - tx / z, 0), 1 - 1 / z); y0 = min(max(fy - ty / z, 0), 1 - 1 / z)
sc = z * W / 2560
M = np.array([[sc, 0, -x0 * 2560 * sc], [0, sc, -y0 * 1440 * sc]], np.float32)
fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC).astype(np.float32) / 255
fr = grade.grade(fr, grain=0.006, face=((fx - x0) * z, (fy - y0) * z - 0.03, 0.22, 0.38))
fr = np.clip((fr - 0.5) * 1.10 + 0.52, 0, 1)                           # a little extra punch for small sizes
# dark gradient from the left for the title
xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
al = np.clip(1 - xs / 0.62, 0, 1) ** 1.25 * 0.92
bg0 = np.array(brand.hex2rgb(PAL["bg0"]), np.float32) / 255
fr = fr * (1 - al) + bg0 * al
# lime rim light on the right edge of the frame
rim = np.clip((xs - 0.90) / 0.10, 0, 1) ** 2 * 0.22
fr = fr + np.array(ACC, np.float32) / 255 * rim

# title
def text_layer(txt, size, fill, w=None):
    f = font("title", size)
    wd = int(f.getlength(txt)) + 40
    lay = Image.new("RGBA", (wd, int(size * 1.35)), (0, 0, 0, 0))
    sh = Image.new("L", lay.size, 0); ImageDraw.Draw(sh).text((10, 10), txt, font=f, fill=210)
    sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(9)), np.uint8)
    sl = np.zeros((lay.height, lay.width, 4), np.uint8); sl[..., 3] = sh
    lay = Image.alpha_composite(lay, Image.fromarray(sl, "RGBA"))
    ImageDraw.Draw(lay).text((10, 6), txt, font=f, fill=tuple(fill) + (255,))
    return lay
y = 112
for txt, hot, size in (("LOCK YOUR", False, 104), ("GOOGLE", False, 104), ("SEARCH", True, 104), ("HISTORY", True, 104)):
    lay = text_layer(txt, size, ACC if hot else (255, 255, 255))
    blend(fr, lay, 54, y, 1.0)
    y += 98
# padlock badge
lk = G.lock_icon(170, (245, 247, 245), body_rgb=ACC, open_amt=0.0)
blend_glow(fr, glow_of(lk, 20, 1.4), 395, 505, 0.85)
blend(fr, lk, 395, 505, 1.0)
# kicker + brand bug
G.draw_logo_bug(fr, 1.0, PAL, 1.0)
img = (np.clip(fr, 0, 1) * 255).astype(np.uint8)
Image.fromarray(img).save(a.out, quality=93)
print("wrote", a.out)
