import os
import sys, json, numpy as np, soundfile as sf, scipy.signal as sg
from PIL import Image, ImageDraw, ImageFont
T=os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")
_x=None
def load():
    global _x
    if _x is None: _x,_=sf.read(T+"work/audio16k.wav",dtype="float32")
    return _x
def plot(t0,t1,marks,out,fmax=6000,pxs=240,H=420,grid=None,labels=None):
    """marks: list of (time,color,label) ; grid: (P,phi) beats"""
    x=load(); sr=16000
    a0=max(0.0,t0-0.1); seg=x[int(a0*sr):int((t1+0.1)*sr)]
    f,t,S=sg.spectrogram(seg,sr,nperseg=512,noverlap=512-64,window="hann")  # 4ms hop,~31Hz bins
    m=f<=fmax; S=10*np.log10(S[m]+1e-12)
    S=np.clip((S-np.percentile(S,30))/(np.percentile(S,99.7)-np.percentile(S,30)),0,1)
    t=t+a0
    Wp=int((t1-t0)*pxs); img=np.zeros((S.shape[0],Wp),np.float32)
    cols=((t-t0)*pxs).astype(int)
    for c,j in zip(cols,range(S.shape[1])):
        if 0<=c<Wp: img[:,c]=np.maximum(img[:,c],S[:,j])
    im=Image.fromarray((img[::-1]*255).astype(np.uint8)).convert("RGB").resize((Wp,H))
    pad=40; canvas=Image.new("RGB",(Wp,H+pad),(10,10,10)); canvas.paste(im,(0,pad))
    d=ImageDraw.Draw(canvas); fnt=ImageFont.truetype(T+"fonts/Hind-Bold.ttf",13)
    for s in range(int(np.ceil(t0)),int(t1)+1):
        x_=int((s-t0)*pxs); d.line([(x_,pad-8),(x_,pad)],fill=(255,255,0)); d.text((x_+2,2),str(s),fill=(255,255,0),font=fnt)
    if grid:
        P,phi=grid
        k=int(np.ceil((t0-phi)/P))
        while phi+k*P<t1:
            tt=phi+k*P; x_=int((tt-t0)*pxs)
            col=(255,255,255) if k%4==0 else (90,90,90)
            d.line([(x_,pad),(x_,pad+H)],fill=col,width=1 if k%4 else 2); k+=1
    for (tm,col,lab) in marks:
        if t0<=tm<=t1:
            x_=int((tm-t0)*pxs); d.line([(x_,pad),(x_,pad+H)],fill=col,width=2); d.text((x_+3,pad+2),str(lab),fill=col,font=fnt)
    canvas.save(out)
