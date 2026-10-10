import os
import sys, numpy as np, soundfile as sf, scipy.signal as sg
T=os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")
def band_env(lo,hi,hop=0.02):
    x,sr=sf.read(T+"work/audio16k.wav",dtype="float32")
    b,a=sg.butter(4,[lo,hi],btype="band",fs=sr); y=sg.filtfilt(b,a,x)
    h=int(sr*hop); w=int(sr*0.04); n=(len(y)-w)//h
    idx=np.arange(w)[None,:]+h*np.arange(n)[:,None]
    return 10*np.log10((y[idx]**2).mean(1)+1e-12), hop
def show(t0,t1,lo=1000,hi=4000,step=0.1,floor=None):
    E,hop=band_env(lo,hi)
    seg=E[int(t0/hop):int(t1/hop)]
    fl=np.percentile(seg,5) if floor is None else floor
    top=np.percentile(seg,99)
    print(f"band {lo}-{hi} Hz, range {fl:.0f}..{top:.0f} dB; each row 0.1s; bar=level above floor")
    for t in np.arange(t0,t1,step):
        v=E[int(t/hop):int((t+step)/hop)].max()
        n=int(np.clip((v-fl)/(top-fl),0,1)*40)
        print(f"{t:6.2f} {'#'*n}")
if __name__=="__main__":
    show(float(sys.argv[1]),float(sys.argv[2]),*(int(a) for a in sys.argv[3:5]))
