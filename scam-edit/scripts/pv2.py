"""pv2.py <overlay_dir> <frames comma list> <out.jpg> [cols] -> overlay PNGs composited over the shifted plate (+ watermark)."""
import sys, subprocess, os
from PIL import Image
B='/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
od, frames, out = sys.argv[1], [int(x) for x in sys.argv[2].split(',')], sys.argv[3]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 3
logo = Image.open(B+'overlay/assets/logo.png').convert('RGBA').resize((120,120), Image.LANCZOS)
tiles=[]
for f in frames:
    base=f'/tmp/pv2_{f}.png'
    if not os.path.exists(base):
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(f/30),'-i',B+'work/plate_all2.mov','-frames:v','1','-vf','scale=in_range=tv:out_range=pc,format=rgb24',base],check=True)
    bg=Image.open(base).convert('RGBA')
    bg.alpha_composite(logo,(1920-120-44,34))
    ov=Image.open(f'{od}/{f:05d}.png').convert('RGBA')
    tiles.append(Image.alpha_composite(bg,ov).convert('RGB').resize((960,540),Image.LANCZOS))
rows=(len(tiles)+cols-1)//cols
sheet=Image.new('RGB',(960*cols,540*rows))
for i,t in enumerate(tiles): sheet.paste(t,((i%cols)*960,(i//cols)*540))
sheet.save(out,quality=88); print(sheet.size)
