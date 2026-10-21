import json, sys, wave
import numpy as np, onnx_asr
wav, vad, out = sys.argv[1:4]
wf=wave.open(wav,"rb"); A=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)/32768.0
sr=16000; chunks=json.load(open(vad))
m=onnx_asr.load_model("nemo-conformer-ctc", path="/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/assets/indic_ml").with_timestamps()
res=[]
PAD=0.2
for i,(s,e) in enumerate(chunks):
    a=max(0,int((s-PAD)*sr)); b=min(len(A),int((e+PAD)*sr)); off=a/sr
    r=m.recognize(A[a:b], sample_rate=sr)
    words=[]; cur=None
    for tok,t,lp in zip(r.tokens,r.timestamps,r.logprobs):
        if tok.startswith(' ') or cur is None:
            if cur: words.append(cur)
            cur=dict(w=tok.strip(),s=off+t,e=off+t,lp=[lp])
            # a lone ' ' token marks a word start too
        else:
            cur['w']+=tok; cur['e']=off+t; cur['lp'].append(lp)
    if cur: words.append(cur)
    words=[w for w in words if w['w']]
    for k,w in enumerate(words):
        w['e']=max(w['e']+0.04, w['s']+0.04)
        w['conf']=float(np.exp(np.mean(w['lp']))); del w['lp']
    res.append(dict(i=i,start=s,end=e,text=r.text,words=words))
json.dump(res,open(out,'w'),ensure_ascii=False,indent=1)
print('chunks',len(res),'words',sum(len(c['words']) for c in res))
