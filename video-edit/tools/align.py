"""Forced-align the user's Manglish script to the narration audio with the MMS CTC model (ONNX)."""
import sys, re, json, numpy as np, onnxruntime as ort
from scipy.io import wavfile
import ctc_forced_aligner as cfa
from ctc_forced_aligner import generate_emissions, forced_align, ensure_onnx_model, MODEL_URL
import os
SP, wav, srt, out = sys.argv[1:5]
# --- parse SRT (cue blocks may or may not be separated by blank lines)
raw = open(srt, encoding="utf8").read().replace("\r", "")
pat = re.compile(r"^\s*(\d+)\s*\n(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)\s*\n(.*?)(?=^\s*\d+\s*\n\d\d:\d\d:\d\d,\d\d\d -->|\Z)", re.S | re.M)
def ts(s):
    h, m, r = s.split(":"); sec, ms = r.split(",")
    return int(h)*3600 + int(m)*60 + int(sec) + int(ms)/1000
cues = [dict(idx=int(m.group(1)), srt_start=ts(m.group(2)), srt_end=ts(m.group(3)), text=" ".join(m.group(4).split())) for m in pat.finditer(raw)]
assert len(cues) == 54, len(cues)
# spoken-form substitutions for digits (script shows digits; speaker says the words)
SPOKEN = [(r"\b100 videos per day\b", "hundred videos per day"), (r"\b100\b", "nooru"), (r"\b6 minute 30 second\b", "aaru minute muppathu second")]
def spoken(t):
    for p, r in SPOKEN: t = re.sub(p, r, t)
    return t
words = []   # (cue_idx, word_idx_in_cue, display, letters)
for c in cues:
    toks = c["text"].split()
    c["words"] = []
    for wi, w in enumerate(toks):
        sp = spoken(w) if not re.fullmatch(r"\d+", w) else w
        words.append((c["idx"], wi, w))
        c["words"].append(dict(w=w))
# build target letters with word map, applying spoken forms at the text level per cue
VOC = cfa.VOCAB_DICT
targets, tmap = [], []   # tmap: (global_word_id)
gw = 0; wordlist = []
for c in cues:
    txt = c["text"]
    for p, r in SPOKEN: txt = re.sub(p, r, txt)
    # tokenise by whitespace on ORIGINAL to keep 1:1 with display words; handle digits specially
    disp = c["text"].split()
    # map spoken replacements onto display words
    j = 0; spoken_words = []
    stxt = txt.split()
    # simple approach: align display words to spoken words by consuming replacements
    di = 0; si = 0
    while di < len(disp):
        d = disp[di]
        if d == "100" and disp[di:di+4] == ["100","videos","per","day"]:
            spoken_words.append(("hundred", di)); spoken_words.append(("videos", di+1)); spoken_words.append(("per", di+2)); spoken_words.append(("day", di+3)); di += 4
        elif d == "100": spoken_words.append(("nooru", di)); di += 1
        elif disp[di:di+4] == ["6","minute","30","second"]:
            for k, s in enumerate(["aaru","minute","muppathu","second"]): spoken_words.append((s, di+k))
            di += 4
        else: spoken_words.append((d, di)); di += 1
    for s, di in spoken_words:
        letters = [ch for ch in re.sub(r"[^a-z']", "", s.lower().replace("'", "")) if ch in VOC]
        if not letters: continue
        wordlist.append(dict(cue=c["idx"], wi=di, text=disp[di], n=len(letters)))
        for ch in letters: targets.append(VOC[ch])
        gw += 1
print("words", len(wordlist), "letters", len(targets), flush=True)
sr, a = wavfile.read(wav); assert sr == 16000
a = a.astype(np.float32) / 32768.0
a = (a - a.mean()) / (a.std() + 1e-7)
mp = os.path.join(os.path.expanduser("~"), "ctc_forced_aligner", "model.onnx")
ensure_onnx_model(mp, MODEL_URL)
so = ort.SessionOptions(); so.intra_op_num_threads = 2
sess = ort.InferenceSession(mp, so, providers=["CPUExecutionProvider"])
if os.path.exists(out + ".emissions.npy"):
    em = np.load(out + ".emissions.npy"); stride = 20
else:
    em, stride = generate_emissions(sess, a, window_length=30, context_length=2, batch_size=2)
print("emissions", em.shape, "stride ms", stride, flush=True)
np.save(out + ".emissions.npy", em)
tg = np.asarray([targets], dtype=np.int64)
path, scores = forced_align(np.expand_dims(em, 0), tg, blank=0)
path = path.squeeze(); scores = scores.squeeze()
# merge to token spans (one span per target letter, in order)
spans = []; t = 0; T = len(path)
while t < T:
    if path[t] == 0: t += 1; continue
    s = t
    while t < T and path[t] == path[s]: t += 1
    spans.append((s, t, float(np.mean(np.exp(scores[s:t])))))
print("spans", len(spans), "targets", len(targets), flush=True)
assert len(spans) == len(targets), "span/target mismatch"
fs = stride / 1000.0
k = 0; res = []
for w in wordlist:
    sp_ = spans[k:k+w["n"]]; k += w["n"]
    res.append(dict(cue=w["cue"], wi=w["wi"], text=w["text"], start=sp_[0][0]*fs, end=sp_[-1][1]*fs, conf=float(np.mean([x[2] for x in sp_]))))
json.dump(dict(cues=cues, words=res, stride_ms=stride), open(out, "w"), indent=1, ensure_ascii=False)
print("first", res[0]); print("last", res[-1])
