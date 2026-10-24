#!/usr/bin/env python3
"""Stills of the vertical (9:16) Reel layout for layout review.  Usage: make_reel_stills.py OUT.jpg [t1,t2,...]"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_timeline  # noqa: E402
import render_base  # noqa: E402
from common import ROOT, WORK, sh, style_for  # noqa: E402
from edl import base_shots  # noqa: E402

OUT = sys.argv[1]
TIMES = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else \
    [2.2, 4.8, 8.9, 15.0, 20.5, 38.4, 46.9, 56.0, 61.0, 80.5, 98.4, 107.0, 102.6, 111.0]
D = os.path.join(WORK, "stills/reel")
os.makedirs(D, exist_ok=True)

tl = build_timeline.build(layout="vertical")
json.dump(tl, open(f"{D}/tl.json", "w"))
json.dump(style_for("C_magenta", "montserrat"), open(f"{D}/style.json", "w"))
names = [f"t{t:07.3f}".replace(".", "_") for t in TIMES]
sh(f'node "{ROOT}/render/render_overlay.js" --tl "{D}/tl.json" --style "{D}/style.json" --out "{D}/ov" '
   f'--times {",".join(str(t) for t in TIMES)} --names {",".join(names)} --workers 3', cwd=f"{ROOT}/render")

shots = base_shots("vertical")
cells = []
for t, n in zip(TIMES, names):
    shot = next(s for s in shots if s["start"] <= t < s["end"])
    seg = render_base.render_shot(shot, t, t + 1 / 30, "vertical")
    jpg = f"{D}/base_{n}.jpg"
    sh(f'ffmpeg -v error -y -i "{seg}" -frames:v 1 -q:v 2 "{jpg}"')
    base = Image.open(jpg).convert("RGBA")
    base.alpha_composite(Image.open(f"{D}/ov/{n}.png").convert("RGBA"))
    im = base.convert("RGB")
    d = ImageDraw.Draw(im)
    # Instagram / Shorts UI safe zones (dashed guides): top 230, bottom 340
    for y in (230, 1580):
        for x in range(0, 1080, 40):
            d.line([(x, y), (x + 20, y)], fill=(255, 255, 0), width=2)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    d.rounded_rectangle((12, 12, 150, 56), 10, fill=(0, 0, 0)); d.text((22, 18), f"{t:g}s", font=f, fill=(255, 235, 80))
    cells.append(im.resize((405, 720), Image.LANCZOS))
cols = 7
rows = (len(cells) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 413 + 8, rows * 728 + 8), (24, 24, 28))
for i, im in enumerate(cells):
    sheet.paste(im, (8 + (i % cols) * 413, 8 + (i // cols) * 728))
sheet.save(OUT, quality=90)
print("wrote", OUT, sheet.size)
