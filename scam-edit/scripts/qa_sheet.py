import subprocess, sys
from PIL import Image, ImageDraw
vid, out, step = sys.argv[1], sys.argv[2], float(sys.argv[3])
dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',vid],capture_output=True,text=True).stdout)
ts=[i*step+1.0 for i in range(int(dur/step))]
tw,th=480,270; cols=4
rows=(len(ts)+cols-1)//cols
sh=Image.new('RGB',(tw*cols,th*rows)); d=ImageDraw.Draw(sh)
for i,t in enumerate(ts):
    p=f'/tmp/qa_{i}.png'
    subprocess.run(['ffmpeg','-y','-v','error','-ss',f'{t:.2f}','-i',vid,'-frames:v','1','-vf',f'scale={tw}:{th}:flags=lanczos',p])
    sh.paste(Image.open(p),((i%cols)*tw,(i//cols)*th)); d.text(((i%cols)*tw+4,(i//cols)*th+4),f'{t:.0f}s',fill=(255,255,0))
sh.save(out,quality=85); print(sh.size,len(ts))
