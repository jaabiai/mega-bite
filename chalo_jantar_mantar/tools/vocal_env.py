import os
import numpy as np, soundfile as sf, scipy.signal as sg
T=os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")
HOP=0.01
def speech_env(lo=300,hi=5000):
    """Speech-band energy in dB, 10 ms hop (30 ms window)."""
    x,sr=sf.read(T+"work/audio16k.wav",dtype="float32")
    b,a=sg.butter(4,[lo,hi],btype="band",fs=sr)
    y=sg.filtfilt(b,a,x)
    h=int(sr*HOP); w=int(sr*0.03)
    n=(len(y)-w)//h
    idx=np.arange(w)[None,:]+h*np.arange(n)[:,None]
    e=(y[idx]**2).mean(1)
    return 10*np.log10(e+1e-12)
def onsets_after(E, t_from, t_to, win=6.0, quiet_frac=0.30, min_gap=0.30):
    """Find first vocal onset in [t_from,t_to]. Returns (onset, gap_len) or (None,0).
    quiet = below low+quiet_frac*(high-low) of local percentiles."""
    c=(t_from+t_to)/2
    a=int(max(0,c-win)/HOP); b=int(min(len(E)*HOP,c+win)/HOP)
    lo,hi=np.percentile(E[a:b],[8,92])
    thr=lo+quiet_frac*(hi-lo)
    i0=int(t_from/HOP); i1=min(len(E),int(t_to/HOP))
    q=E[i0:i1]<thr
    # smooth: require sustained
    k=int(min_gap/HOP)
    run=0; gap_start=None
    for j in range(len(q)):
        if q[j]:
            run+=1
            if run==k: gap_start=j-k+1
        else:
            if gap_start is not None:
                return (i0+j)*HOP,(j-gap_start)*HOP
            run=0
    return None,0.0
