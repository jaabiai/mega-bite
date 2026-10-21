import wave, json, sys
import numpy as np
from faster_whisper.vad import get_speech_timestamps, VadOptions
wf=wave.open(sys.argv[1],'rb'); a=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)/32768
opts=VadOptions(threshold=0.45, min_speech_duration_ms=120, min_silence_duration_ms=int(sys.argv[3]), speech_pad_ms=60, max_speech_duration_s=14)
ts=get_speech_timestamps(a,opts)
out=[(t['start']/16000,t['end']/16000) for t in ts]
json.dump(out,open(sys.argv[2],'w'))
print(len(out),'speech chunks; total speech %.1fs of %.1fs'%(sum(e-s for s,e in out),len(a)/16000))
prev=0
for i,(s,e) in enumerate(out):
    print(f"{i:3d} {s:7.2f}-{e:7.2f} ({e-s:5.2f}s)  gap_before={s-prev:5.2f}")
    prev=e
