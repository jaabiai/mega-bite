"""Word-level forced alignment of the Manglish SRT text against the real narration.

The SRT timings do not match the recorded audio (SRT ends at 5:27, video is 4:23),
so we ignore its timings and align the *text* to the speech with a CTC model
(MMS, romanised letters), which suits Manglish well.

usage: align_captions.py <audio16k.wav> <captions.srt> <model.onnx> <out.json>
"""
import json
import re
import sys

import numpy as np
import onnxruntime as ort
import soundfile as sf

import ctc_forced_aligner as cfa

STRIDE = 0.02  # model frame hop in seconds (320 samples @ 16 kHz)


def parse_srt(path):
    raw = open(path, encoding="utf-8").read().strip().replace("\r", "")
    cues = []
    for block in re.split(r"\n\s*\n", raw):
        lines = block.strip().split("\n")
        idx = int(lines[0])
        text = " ".join(lines[2:]).strip()
        t0, t1 = [
            sum(float(x) * m for x, m in zip(re.split(r"[:,]", s.strip()), (3600, 60, 1, 0.001)))
            for s in lines[1].split("-->")
        ]
        cues.append({"id": idx, "srt_start": t0, "srt_end": t1, "text": text})
    return cues


NUM_WORDS = {"27": "*"}  # numerals -> wildcard (spoken form is ambiguous)


def align_token(word):
    w = word.lower().replace("&", " and ")
    if w.strip(".,;:!?'\"()") in NUM_WORDS:
        return ["*"]
    w = re.sub(r"[^a-z' ]", "", w)
    return [c for c in w.replace(" ", "") if c]


def main(wav, srt, model_path, out_json):
    audio, sr = sf.read(wav, dtype="float32")
    assert sr == 16000 and audio.ndim == 1
    audio = (audio - audio.mean()) / (audio.std() + 1e-7)

    cues = parse_srt(srt)
    words = []  # display words with cue index
    for c in cues:
        for w in c["text"].split():
            words.append({"cue": c["id"], "text": w})

    vocab = dict(cfa.VOCAB_DICT)
    star = len(vocab)
    vocab["*"] = star

    targets, owner = [], []
    for wi, w in enumerate(words):
        toks = align_token(w["text"])
        w["tok"] = len(toks)
        for t in toks:
            if t in vocab:
                targets.append(vocab[t])
                owner.append(wi)
    targets = np.asarray([targets], dtype=np.int64)
    print(f"{len(words)} words, {targets.shape[1]} tokens", flush=True)

    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    sess = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"])
    emissions, stride_ms = cfa.generate_emissions(sess, audio, window_length=30, context_length=2, batch_size=1)
    print("emissions", emissions.shape, "stride ms", stride_ms, flush=True)

    path, scores = cfa.forced_align(emissions[None], targets, blank=0)
    path = path.squeeze()
    scores = scores.squeeze()

    # frame path -> token occurrences, in order
    occ = []  # (token_id, start_frame, end_frame, mean_score)
    i, T = 0, len(path)
    while i < T:
        if path[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < T and path[j + 1] == path[i]:
            j += 1
        occ.append((int(path[i]), i, j, float(np.mean(scores[i : j + 1]))))
        i = j + 1
    # CTC needs a blank between identical neighbours, so occurrences map 1:1 to targets
    assert len(occ) == targets.shape[1], (len(occ), targets.shape[1])

    for w in words:
        w["_f0"], w["_f1"], w["_sc"] = None, None, []
    for (tid, f0, f1, sc), wi in zip(occ, owner):
        w = words[wi]
        w["_f0"] = f0 if w["_f0"] is None else w["_f0"]
        w["_f1"] = f1
        w["_sc"].append(sc)

    out = []
    for w in words:
        if w["_f0"] is None:
            continue
        out.append(
            {
                "cue": w["cue"],
                "text": w["text"],
                "start": round(w["_f0"] * STRIDE, 3),
                "end": round((w["_f1"] + 1) * STRIDE, 3),
                "score": round(float(np.mean(w["_sc"])), 3),
            }
        )
    json.dump({"duration": len(audio) / sr, "words": out}, open(out_json, "w"), indent=1)
    print("wrote", out_json, len(out), "words")


if __name__ == "__main__":
    main(*sys.argv[1:5])
