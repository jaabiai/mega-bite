"""Audio/video sync check: correlate the voice envelope with mouth-region motion in the finished video."""
import subprocess, sys, json
import numpy as np
B='/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
vid=sys.argv[1]
W,H=192,108
raw=subprocess.run(['ffmpeg','-v','error','-i',vid,'-vf',f'fps=30,scale={W}:{H}:flags=area,format=gray','-f','rawvideo','-'],capture_output=True).stdout
fr=np.frombuffer(raw,np.uint8).reshape(-1,H,W).astype(np.float32)
print('decoded',len(fr),'frames')
# mouth / lower-face region (full-frame speaker scenes only)
y0,y1,x0,x1=int(H*0.30),int(H*0.50),int(W*0.40),int(W*0.62)
mot=np.abs(np.diff(fr[:,y0:y1,x0:x1],axis=0)).mean((1,2)); mot=np.r_[0,mot]
voice=np.load(B+'work/audio/voice_edit.npy').astype(np.float64); voice=np.pad(voice,(0,max(0,len(fr)*1600-len(voice))))
env=np.array([np.sqrt(np.mean(voice[i*1600:(i+1)*1600]**2)) for i in range(len(fr))])
# only plain talking-head segments
ok=np.zeros(len(fr),bool)
for a,b in [(16.6,23.8),(26.9,74.2),(90.2,107.6),(174.0,202.4)]: ok[int(a*30):int(b*30)]=True
def norm(x): x=x-np.convolve(x,np.ones(15)/15,'same'); return x/(x.std()+1e-9)
m=norm(mot); e=norm(np.log(env+1e-6))
best=[]
for lag in range(-8,9):
    if lag>=0: a_,b_=m[lag:],e[:len(e)-lag]; k=ok[lag:]
    else: a_,b_=m[:lag],e[-lag:]; k=ok[:lag]
    n=min(len(a_),len(b_)); k=k[:n]
    best.append((lag,float(np.corrcoef(a_[:n][k],b_[:n][k])[0,1])))
for lag,c in best: print(f'lag {lag:+d} frames ({lag*33.3:+.0f} ms): corr {c:.3f}')
print('best lag:',max(best,key=lambda t:t[1]))
