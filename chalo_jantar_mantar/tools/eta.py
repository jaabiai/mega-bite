"""Event-triggered average of onset flux around line starts -> systematic timing bias estimate."""
import os
import sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_check import flux, sf, T
def eta(timing, lo=300, hi=4000, sel=None, half=1.0):
    x,sr=sf.read(T+"work/audio16k.wav",dtype="float32")
    d,hop=flux(x,lo=lo,hi=hi)
    # smooth flux a little (30 ms) so peak location is stable
    k=np.ones(3)/3; ds=np.convolve(d,k,mode="same")
    lines=json.load(open(timing,encoding="utf-8"))["lines"]
    n=int(half/hop)
    acc=[]
    for l in lines:
        if sel and not sel(l): continue
        i=int(l["start"]/hop)
        if i-n<0 or i+n>=len(ds): continue
        seg=ds[i-n:i+n+1]
        acc.append(seg/ (seg.mean()+1e-9))
    A=np.mean(acc,axis=0); t=(np.arange(-n,n+1))*hop
    return t,A,len(acc)
if __name__=="__main__":
    timing=sys.argv[1]
    for name,sel in (("all lines",None),
                     ("rap/chorus lines (start>40s)",lambda l:l["start"]>40),
                     ("intro lines (<32s, burst-based)",lambda l:l["start"]<32)):
        t,A,n=eta(timing,sel=sel)
        # peak within +-0.6 s
        m=(t>=-0.6)&(t<=0.6); j=np.argmax(A[m]); 
        # centroid of the top region
        print(f"{name:34s} n={n:3d}  peak at {t[m][j]:+.2f}s  (height {A[m][j]:.2f} vs mean 1.00)")
        # coarse profile every 0.1s
        prof=" ".join(f"{A[(t>=a-0.05)&(t<a+0.05)].mean():.2f}" for a in np.arange(-0.5,0.51,0.1))
        print("   profile -0.5..+0.5 step 0.1:",prof)
