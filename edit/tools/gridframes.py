"""Dump screen-recording frames with a labelled coordinate grid (source pixels) to read UI element rects."""
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out, *times = sys.argv[1:]
W, H, SC = 1320, 2868, 0.5
font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 15)
tiles = []
for t in times:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", t, "-i", src, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    im = Image.fromarray(np.frombuffer(raw, np.uint8).reshape(H, W, 3)).resize((int(W * SC), int(H * SC)))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 100):
        d.line([(x * SC, 0), (x * SC, H * SC)], fill=(255, 0, 90) if x % 500 == 0 else (255, 120, 160), width=1)
        if x % 200 == 0:
            d.text((x * SC + 2, 2), str(x), fill=(220, 0, 60), font=font)
    for y in range(0, H, 100):
        d.line([(0, y * SC), (W * SC, y * SC)], fill=(0, 120, 255) if y % 500 == 0 else (120, 180, 255), width=1)
        if y % 200 == 0:
            d.text((2, y * SC + 2), str(y), fill=(0, 70, 220), font=font)
    d.text((W * SC - 90, H * SC - 24), "r=" + t, fill=(0, 0, 0), font=font)
    tiles.append(im)
canvas = Image.new("RGB", (sum(t.width for t in tiles) + 8 * (len(tiles) - 1), tiles[0].height), (40, 40, 40))
x = 0
for t in tiles:
    canvas.paste(t, (x, 0)); x += t.width + 8
canvas.save(out)
