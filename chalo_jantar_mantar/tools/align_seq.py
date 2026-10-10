"""Sequential forced alignment of the supplied lyrics against the song audio.

usage: align_seq.py MODEL LEAD OUT.json
  MODEL  whisper model dir name (turbo | large-v3 | small)
  LEAD   seconds of audio before the first not-yet-aligned line at window start
         (varying LEAD gives different window phases -> ensemble)
"""
import os
import sys, json, time
import numpy as np, soundfile as sf

T = os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")
sys.path.insert(0, T + "tools")
from whisper_onnx import Whisper, SR
from lyrics import parse, norm

# Model-facing phonetic variants (display text is never changed).
MODEL_TEXT = {
    "Vote Chori! गद्दी चोर!": " वोट चोरी गद्दी चोर",
}


def model_text(t):
    return MODEL_TEXT.get(t, norm(t))


def main():
    name, lead, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    maxlines = int(sys.argv[4]) if len(sys.argv) > 4 else 14
    L = parse()
    w = Whisper(name)
    x, _ = sf.read(T + "work/audio16k.wav", dtype="float32")
    total = len(x) / SR
    res = {}
    i = 0  # next line index (0-based)
    wstart = 0.0
    t_begin = time.time()
    first_start_hint = 0.0
    while i < len(L):
        wstart = max(0.0, first_start_hint - lead)
        seg = x[int(wstart * SR): int((wstart + 30) * SR)]
        ck, cv = w.encode(seg)
        batch = L[i: i + maxlines]
        r = w.decode_forced(ck, cv, [model_text(l["text"]) for l in batch])
        # accept lines that end before the window edge margin
        limit = min(30.0, total - wstart) - 1.5
        accepted = 0
        for k, (a, b, lp) in enumerate(r):
            if b <= limit and (b - a) > 0.05 and lp > -2.5:
                accepted += 1
            else:
                break
        if accepted == 0:
            accepted = 1  # always make progress
        for k in range(accepted):
            a, b, lp = r[k]
            res[batch[k]["id"]] = {"start": round(wstart + a, 2), "end": round(wstart + b, 2), "lp": round(lp, 3), "win": round(wstart, 2)}
        last = batch[accepted - 1]["id"]
        print(f"win@{wstart:6.2f}  lines {batch[0]['id']}..{last}  elapsed {time.time()-t_begin:5.0f}s", flush=True)
        i += accepted
        if i < len(L):
            first_start_hint = res[last]["end"]  # next line starts ~ where previous ended
        json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    print("done", len(res))


if __name__ == "__main__":
    main()
