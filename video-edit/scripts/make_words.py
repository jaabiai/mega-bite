#!/usr/bin/env python3
"""SRT -> per-word caption timings (captions/words.json).

The SRT only gives phrase level timing, so each cue is refined in two steps:

1. Move every cue boundary onto the real pause nearest to it in the audio
   envelope (within +-0.45 s of the SRT time), so a word never shows while the
   speaker is silent and a cue never starts before its first word is spoken.
2. Spread the words of the cue across that speech span, weighted by syllable
   count, with a small extra pause after punctuation.

Tiny function words ("a", "to", "of", "I" ...) are attached to the neighbouring
content word so they do not flash for 100 ms; every on-screen "chunk" is one
content word (plus its attached function words) and lasts >= MIN_CHUNK s.

Usage: make_words.py captions/en.srt envelope.npy out.json captions/boundaries.json
"""
import json
import re
import sys

import numpy as np

HOP = 0.02  # envelope hop in seconds (20 ms)
SNAP = 0.45  # how far a cue edge may be moved to hit the speech
MIN_CHUNK = 0.28

FUNCTION_WORDS = {
    "a", "an", "the", "to", "of", "it", "is", "in", "on", "at", "as", "or", "and", "so",
    "i", "we", "you", "me", "my", "do", "be", "by", "if", "up", "us", "am", "its",
    "it's", "i'll", "i'm", "let", "me", "are", "for", "can", "will", "with", "them",
    "they", "that", "this", "your", "how", "now",
}


def ts(s):
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def parse_srt(path):
    cues = []
    for block in re.split(r"\n\s*\n", open(path, encoding="utf-8").read().strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        a, b = lines[1].split(" --> ")
        cues.append(dict(idx=int(lines[0]), start=ts(a), end=ts(b), text=" ".join(lines[2:])))
    return cues


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(1, n)


def speech_mask(env_db):
    """True where the (smoothed) envelope is above an adaptive speech floor."""
    sm = np.convolve(env_db, np.ones(5) / 5, mode="same")
    floor = np.percentile(sm, 12)
    peak = np.percentile(sm, 90)
    thr = floor + 0.35 * (peak - floor)
    return sm > thr


def find_gap(mask, boundary):
    """Pause (run of non-speech frames) closest to a cue boundary, or None."""
    n = len(mask)
    lo = max(int(round((boundary - SNAP) / HOP)), 0)
    hi = min(int(round((boundary + SNAP) / HOP)), n - 1)
    best, i = None, lo
    while i <= hi:
        if not mask[i]:
            j = i
            while j + 1 < n and not mask[j + 1]:
                j += 1
            a, b = i * HOP, (j + 1) * HOP
            if b - a >= 0.08:
                dist = 0.0 if a <= boundary <= b else min(abs(a - boundary), abs(b - boundary))
                score = dist - 0.5 * min(b - a, 0.5)
                if best is None or score < best[0]:
                    best = (score, a, b)
            i = j + 1
        else:
            i += 1
    return best


def refine_cues(cues, mask, hints):
    """Return (onset, offset) per cue; every shared boundary sits on a real pause.

    `hints` (captions/boundaries.json) gives the approximate real-speech time of
    each cue boundary because the delivered SRT timing does not follow the audio.
    """
    n = len(mask)
    bounds = []
    for a, b in zip(cues[:-1], cues[1:]):
        h = hints["between"][f"{a['idx']}|{b['idx']}"]
        g = find_gap(mask, h)
        if g:
            _, ga, gb = g
            pad = min(0.04, (gb - ga) / 4)
            bounds.append((ga + pad, gb - pad))
        else:
            bounds.append((h, h))
    first = hints["first_onset"]
    for i in range(int(max(first - 0.1, 0) / HOP), min(int((first + 0.8) / HOP), n - 1)):
        if mask[i] and mask[i:i + 5].all():
            first = i * HOP
            break
    last = hints["last_end"]
    for i in range(min(int((last + 0.3) / HOP), n - 1), int((last - 0.5) / HOP), -1):
        if mask[i] and mask[max(i - 4, 0):i + 1].all():
            last = (i + 1) * HOP
            break
    out = []
    for k in range(len(cues)):
        onset = first if k == 0 else bounds[k - 1][1]
        offset = last if k == len(cues) - 1 else bounds[k][0]
        out.append((onset, offset))
    return out


def spread(weights, span):
    """Split `span` seconds by weight, but never give a chunk < MIN_CHUNK."""
    n = len(weights)
    floor = min(MIN_CHUNK, span / n)
    fixed = [False] * n
    durs = [0.0] * n
    while True:
        free = [i for i in range(n) if not fixed[i]]
        rest = span - floor * sum(fixed)
        wsum = sum(weights[i] for i in free)
        changed = False
        for i in free:
            durs[i] = rest * weights[i] / wsum
        for i in free:
            if durs[i] < floor:
                fixed[i] = True
                durs[i] = floor
                changed = True
        if not changed:
            return durs


def chunk_words(tokens):
    """Group tokens so every chunk contains exactly one content word."""
    chunks, pending = [], []
    for tok in tokens:
        bare = re.sub(r"[^a-z']", "", tok.lower())
        if bare in FUNCTION_WORDS and not re.search(r"[.!?,:;—]$", tok):
            pending.append(tok)
            continue
        chunks.append(pending + [tok])
        pending = []
    if pending:
        if chunks:
            chunks[-1].extend(pending)
        else:
            chunks.append(pending)
    return chunks


def main(srt, env_path, out, hints_path):
    cues = parse_srt(srt)
    hints = json.load(open(hints_path))
    mask = speech_mask(np.load(env_path))
    words = []
    for cue, (onset, offset) in zip(cues, refine_cues(cues, mask, hints)):
        text = cue["text"].replace("—", "— ").replace("  ", " ")
        tokens = text.split()
        chunks = chunk_words(tokens)
        weights = []
        for ch in chunks:
            w = sum(syllables(t) for t in ch) + 0.35 * (len(ch) - 1)
            last = ch[-1]
            if re.search(r"[.!?]\W*$", last):
                w += 0.9
            elif re.search(r"[,:;—]\W*$", last):
                w += 0.5
            weights.append(w)
        span = offset - onset
        durs = spread(weights, span)
        t = onset
        for ch, dur in zip(chunks, durs):
            words.append(dict(
                text=" ".join(ch),
                start=round(t, 3),
                end=round(t + dur, 3),
                cue=cue["idx"],
            ))
            t += dur
    spans = {}
    for wd in words:
        spans.setdefault(wd["cue"], [wd["start"], wd["end"]])[1] = wd["end"]
    for c in cues:
        c["real_start"], c["real_end"] = spans[c["idx"]]
    json.dump(dict(cues=cues, words=words), open(out, "w"), indent=1)
    def fmt(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    srt_out = out.replace(".json", ".retimed.srt")
    with open(srt_out, "w", encoding="utf-8") as f:
        for c in cues:
            f.write(f"{c['idx']}\n{fmt(c['real_start'])} --> {fmt(c['real_end'])}\n{c['text']}\n\n")
    print(f"{len(cues)} cues -> {len(words)} caption chunks, "
          f"last word ends {words[-1]['end']:.2f}s")


if __name__ == "__main__":
    main(*sys.argv[1:5])
