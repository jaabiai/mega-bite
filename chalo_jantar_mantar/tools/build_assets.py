"""Pre-compute reusable assets from the ORIGINAL footage + procedural art."""
import os, subprocess, sys, numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(__file__))
import art
T = os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")
A = T + "assets/"
SRC = T + "src/original.mp4"
os.makedirs(A, exist_ok=True)

# 1) low-res colour field of the original footage (10 fps, 108x192) -> memmap
FW, FH = 108, 192
if not os.path.exists(A + "field.u8"):
    cmd = ["ffmpeg", "-v", "error", "-i", SRC, "-an", "-vf", f"scale={FW}:{FH}:flags=area,format=rgb24", "-f", "rawvideo", A + "field.u8", "-y"]
    subprocess.run(cmd, check=True)
n = os.path.getsize(A + "field.u8") // (FW * FH * 3)
print("field frames", n)

# 2) cover tile (static art in the original frames) -> RGBA with rounded alpha
subprocess.run(["ffmpeg", "-v", "error", "-ss", "31", "-i", SRC, "-frames:v", "1", A + "_f31.png", "-y"], check=True)
fr = Image.open(A + "_f31.png").convert("RGB")
x0, y0, x1, y1 = 272, 380, 552, 760
tile = fr.crop((x0, y0, x1, y1))
m = Image.new("L", tile.size, 0)
from PIL import ImageDraw
ImageDraw.Draw(m).rounded_rectangle([0, 0, tile.width - 1, tile.height - 1], radius=15, fill=255)
# trim 2px of the soft edge so no background halo survives
m = m.filter(ImageFilter.GaussianBlur(0.6))
t_rgba = tile.convert("RGBA"); t_rgba.putalpha(m)
t_rgba.save(A + "tile.png"); print("tile", tile.size)

# 3) source credit marks ("by @..." and "MADE WITH SUNO") lifted as alpha masks
def lift(box, name):
    c = fr.crop(box).convert("L")
    a = np.asarray(c).astype(np.float32)
    bg = gaussian_filter(a, 7)
    r = np.clip(a - bg, 0, None)
    r = r / (np.percentile(r, 99.8) + 1e-6)
    al = np.clip(r * 1.6, 0, 1)
    al[al < 0.18] = 0
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = (al * 255).astype(np.uint8)
    Image.fromarray(rgba).save(A + name); print(name, rgba.shape)
lift((300, 318, 524, 344), "credit_by.png")
lift((270, 1070, 556, 1112), "credit_suno.png")

# 4) crowd rows, flags anchors, Jantar Mantar, chakra
rows = [dict(scale=0.78, base=170, density=0.95, color=(38, 31, 66), raised_prob=0.20, pole_prob=0.55),
        dict(scale=1.08, base=250, density=1.0, color=(20, 16, 40), raised_prob=0.20, pole_prob=0.5),
        dict(scale=1.5, base=350, density=1.05, color=(6, 6, 16), raised_prob=0.16, pole_prob=0.4)]
strips, flags = art.crowd_strip(1500 + 400, 600, rows)
for i, s in enumerate(strips):
    Image.fromarray(s).save(A + f"crowd{i}.png")
import json
json.dump([[list(map(float, p)) for p in f] for f in flags], open(A + "flags.json", "w"))
Image.fromarray(art.jantar_mantar(1500, 520, (7, 8, 20))).save(A + "jantar.png")
Image.fromarray(art.chakra_ring(1000, (255, 255, 255), 24, 4)).save(A + "chakra.png")
print("assets done")
