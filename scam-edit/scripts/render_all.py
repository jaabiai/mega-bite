"""Render the whole video as scene-aligned, frame-exact segments (3 in parallel), then join them losslessly."""
import subprocess, sys, os, time
from concurrent.futures import ThreadPoolExecutor
B='/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
FPS=30
OLD=[0,249,374,494,1100,1650,2148,2253,2385,2507,2616,3149,3500,3873,4164,4571,4679,5129,5560,6000,6198]
D=84; I=719
BP=sorted(set([b for b in OLD if b<=I]+[I,I+D]+[b+D for b in OLD if b>I]))   # frame breakpoints (stinger = segment 719-803)
segs=[(i,BP[i],BP[i+1]) for i in range(len(BP)-1)]
os.makedirs(B+'work/seg',exist_ok=True)
extra=sys.argv[1:]      # e.g. --fast
def run(seg):
    i,a,b=seg
    out=B+f'work/seg/s{i:02d}.mp4'
    cmd=['python3','-I',B+'scripts/final2.py','--out',out,'--ss',f'{a/FPS:.6f}','--t',f'{(b-a)/FPS:.6f}','--noaudio']+extra
    t=time.time()
    for attempt in range(3):
        r=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=open(B+f'work/seg/s{i:02d}.log','w'))
        if r.returncode==0: break
        print(f'segment {i:02d} attempt {attempt+1} failed rc={r.returncode}, retrying',flush=True)
    print(f'segment {i:02d} frames {a}-{b} rc={r.returncode} {time.time()-t:.0f}s',flush=True)
    return r.returncode
order=sorted(segs,key=lambda s:-(s[2]-s[1]))          # longest first
with ThreadPoolExecutor(3) as ex:
    rcs=list(ex.map(run,order))
print('all rc:',rcs)
if any(rcs): sys.exit(1)
with open(B+'work/seg/list.txt','w') as f:
    for i,_,_ in segs: f.write(f"file '{B}work/seg/s{i:02d}.mp4'\n")
subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',B+'work/seg/list.txt','-c','copy',B+'work/video_only.mp4'],check=True)
print('joined')
