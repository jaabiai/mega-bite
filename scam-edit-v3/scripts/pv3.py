"""pv3.py <overlay_dir> <frames> <out.jpg> [cols] [scale] -> overlay PNGs over the bg loop (+ person if work3/person_all exists)"""
import sys, os
from PIL import Image
B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
od, frames, out = sys.argv[1], [int(x) for x in sys.argv[2].split(',')], sys.argv[3]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 2
sc = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
logo = Image.open(B + 'overlay3/assets/logo.png').convert('RGBA').resize((120, 120), Image.LANCZOS)
tiles = []
for f in frames:
    bg = Image.open(B + f'bgv3/seq/{f % 600:04d}.png').convert('RGBA')
    pp = B + f'work3/pvperson/{f:05d}.png'
    if os.path.exists(pp):
        p = Image.open(pp).convert('RGBA'); bg.alpha_composite(p)
    bg.alpha_composite(logo, (1920 - 120 - 44, 34))
    ov = Image.open(f'{od}/{f:05d}.png').convert('RGBA')
    t = Image.alpha_composite(bg, ov).convert('RGB')
    tiles.append(t.resize((int(1920 * sc), int(1080 * sc)), Image.LANCZOS))
w, h = tiles[0].size
rows = (len(tiles) + cols - 1) // cols
sh = Image.new('RGB', (w * cols, h * rows))
for i, t in enumerate(tiles):
    sh.paste(t, ((i % cols) * w, (i // cols) * h))
sh.save(out, quality=88); print(sh.size)
