#!/usr/bin/env python3
"""Word-level timing for every lyric line (forced alignment).

Uses the MMS-300m forced-aligner (wav2vec2 CTC, 1130 languages, ONNX int8) on the *song* audio:
the Malayalam lines are romanised with `uroman`, each cue window (cue +-1.2 s) is run through the
network and the characters are Viterbi-aligned to the frame posteriors.  A wildcard "star" token before and
after the line absorbs humming / instruments that are not part of the text.

Output  $WORK/words.json :  [ {cue, start, end, text, words:[{w, t0, t1}]} , ... ]   (song time, seconds)

Needs:  pip install onnxruntime numpy uroman   and the model from
        https://huggingface.co/Corvo007/mms-300m-1130-forced-aligner-int8   (model.onnx, vocab.json)
Usage:  align_words.py <model_dir> [--global]      (--global: ignore the SRT times, align the whole text to the whole song)
"""
import json, os, pathlib, re, subprocess, sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work')); WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from prep import parse_srt, lyric_lines

SR = 16000
STRIDE = 320          # samples per output frame (20 ms)
PAD = 1.2             # context around each cue (s)

def load_audio():
    # emphasise the voice band a little so drums / bass do not dominate the posteriors
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(ROOT / 'inputs' / 'song.mp3'), '-af', 'highpass=f=120,lowpass=f=5000',
                          '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)

def romanise(text):
    import uroman
    u = getattr(romanise, '_u', None) or uroman.Uroman(); romanise._u = u
    out = []
    for w in text.split():
        lc = 'ara' if re.search(r'[؀-ۿ]', w) else 'mal'
        r = u.romanize_string(w, lcode=lc).lower()
        r = re.sub(r"[^a-z']", '', r)
        out.append(r)
    return out

def log_softmax(x):
    x = x - x.max(-1, keepdims=True)
    return x - np.log(np.exp(x).sum(-1, keepdims=True))

def viterbi_ctc(logp, tokens, blank=0):
    """Standard CTC forced alignment (frame -> token index in `tokens`, -1 = blank)."""
    T, C = logp.shape; L = len(tokens)
    S = 2 * L + 1
    ext = np.full(S, blank, dtype=np.int64); ext[1::2] = tokens
    NEG = -1e30
    dp = np.full((T, S), NEG, dtype=np.float32); bp = np.zeros((T, S), dtype=np.int8)
    dp[0, 0] = logp[0, blank]
    if S > 1: dp[0, 1] = logp[0, ext[1]]
    skip_ok = np.zeros(S, dtype=bool)
    skip_ok[3::2] = ext[3::2] != ext[1:-2:2]          # may skip a blank only between different tokens
    for t in range(1, T):
        prev = dp[t - 1]
        c0 = prev
        c1 = np.concatenate([[NEG], prev[:-1]])
        c2 = np.concatenate([[NEG, NEG], prev[:-2]]); c2 = np.where(skip_ok, c2, NEG)
        stack = np.stack([c0, c1, c2]); best = stack.argmax(0)
        dp[t] = stack.max(0) + logp[t, ext]; bp[t] = best
    # end in the last token or the trailing blank
    s = S - 1 if dp[T - 1, S - 1] >= dp[T - 1, S - 2] else S - 2
    path = np.zeros(T, dtype=np.int64)
    for t in range(T - 1, -1, -1):
        path[t] = s; s -= int(bp[t, s])
    return path, ext

def align_cue(sess, vocab, audio, cue, win=None):
    if win is None:
        a = max(0.0, cue['start'] - PAD); b = min(len(audio) / SR, cue['end'] + PAD)
    else:
        a, b = max(0.0, win[0]), min(len(audio) / SR, win[1])
    x = audio[int(a * SR):int(b * SR)]
    x = (x - x.mean()) / (x.std() + 1e-7)
    logits = sess.run(None, {'input_values': x[None].astype(np.float32)})[0][0]
    lp = log_softmax(logits)
    T = len(lp)
    # star token = a wildcard column appended to the emissions (value = best non-blank score each frame)
    star_col = lp[:, 4:].max(1, keepdims=True)
    lp2 = np.concatenate([lp, star_col], 1); STAR = lp.shape[1]
    words = romanise(cue['text'])
    toks, owner = [STAR], [-1]
    for wi, w in enumerate(words):
        for ch in w:
            if ch in vocab:
                toks.append(vocab[ch]); owner.append(wi)
    toks.append(STAR); owner.append(-1)
    if len(toks) - 2 < 3 or T < len(toks) * 2:
        return None
    path, ext = viterbi_ctc(lp2, np.array(toks))
    # first / last frame at which each real token is emitted (odd positions = tokens)
    first = {}; last = {}
    for t, s in enumerate(path):
        if s % 2 == 1:
            k = s // 2
            if owner[k] >= 0:
                first.setdefault(k, t); last[k] = t
    # alignment confidence: mean best-frame log-probability of every real character (0 = perfect, more negative = worse)
    sc = [lp[first[k], toks[k]] for k in first if owner[k] >= 0]
    score = float(np.mean(sc)) if sc else -99.0
    times = []
    for wi in range(len(words)):
        ks = [k for k in first if owner[k] == wi]
        if not ks: times.append(None); continue
        times.append((a + first[min(ks)] * STRIDE / SR, a + (last[max(ks)] + 1) * STRIDE / SR))
    return words, times, score

def fill_gaps(ws, lo, hi):
    """make word start times complete and strictly increasing (interpolate missing / non-monotone ones)"""
    n = len(ws); t0 = [w['t0'] for w in ws]
    for k in range(n):
        bad = t0[k] is None or (k and t0[k] <= t0[k - 1] + 0.05)
        if bad: t0[k] = None
    known = [k for k in range(n) if t0[k] is not None]
    if not known:
        for k in range(n): t0[k] = lo + (hi - lo) * k / n
    else:
        for k in range(n):
            if t0[k] is None:
                pk = max([j for j in known if j < k], default=None); nk = min([j for j in known if j > k], default=None)
                if pk is None: t0[k] = max(lo, t0[nk] - 0.4 * (nk - k))
                elif nk is None: t0[k] = t0[pk] + 0.4 * (k - pk)
                else: t0[k] = t0[pk] + (t0[nk] - t0[pk]) * (k - pk) / (nk - pk)
    return t0

def encoder_logits(sess, audio, chunk=30.0, ctx=3.0):
    """wav2vec2 posteriors for the whole song, in overlapping chunks (frames are 20 ms)."""
    T = int(np.ceil(len(audio) / STRIDE)); out = None; pos = 0.0
    while pos < len(audio) / SR:
        a = max(0.0, pos - ctx); b = min(len(audio) / SR, pos + chunk + ctx)
        x = audio[int(a * SR):int(b * SR)]; x = (x - x.mean()) / (x.std() + 1e-7)
        lg = sess.run(None, {'input_values': x[None].astype(np.float32)})[0][0]
        if out is None: out = np.zeros((T + 8, lg.shape[1]), dtype=np.float32)
        f0 = int(round(a * SR / STRIDE)); lo = int(round((pos - a) * SR / STRIDE)); hi = int(round((min(pos + chunk, len(audio) / SR) - a) * SR / STRIDE))
        n = max(0, min(hi - lo, len(lg) - lo, len(out) - f0 - lo))
        out[f0 + lo:f0 + lo + n] = lg[lo:lo + n]
        pos += chunk
    return out[:T]

def main_global(model_dir):
    """Align the complete lyric text to the complete song in one pass (no SRT times needed).  A wildcard token between
    lines absorbs humming / instrumental parts."""
    import onnxruntime as ort
    sess = ort.InferenceSession(str(model_dir / 'model.onnx'), providers=['CPUExecutionProvider'])
    vocab = json.load(open(model_dir / 'vocab.json'))
    audio = load_audio()
    lines = lyric_lines(json.load(open(ROOT / 'project.json')))
    lp = log_softmax(encoder_logits(sess, audio))
    star_col = lp[:, 4:].max(1, keepdims=True); lp2 = np.concatenate([lp, star_col], 1); STAR = lp.shape[1]
    toks, owner = [STAR], [(-1, -1)]
    for li, text in enumerate(lines):
        for wi, w in enumerate(romanise(text)):
            for ch in w:
                if ch in vocab: toks.append(vocab[ch]); owner.append((li, wi))
        toks.append(STAR); owner.append((-1, -1))
    print(f'{len(lines)} lines, {len(toks)} tokens, {len(lp)} frames', flush=True)
    path, ext = viterbi_ctc(lp2, np.array(toks))
    first, last = {}, {}
    for t, s in enumerate(path):
        if s % 2 == 1:
            k = s // 2
            if owner[k][0] >= 0: first.setdefault(k, t); last[k] = t
    # ---- pass 1 result: first word + last frame of every line
    p1 = []
    for li, text in enumerate(lines):
        ks = [k for k in first if owner[k][0] == li]
        s0 = min((first[k] for k in ks), default=0) * STRIDE / SR
        e0 = (max((last[k] for k in ks), default=0) + 1) * STRIDE / SR
        p1.append((s0, e0))
    # ---- pass 2: every line again inside its own window, which starts after the previous line has finished (a long word
    #      such as "mannarakkullil" would otherwise grab the humming of the previous line's final "m") and ends at the next
    out = []
    n_lines = len(lines)
    for li, text in enumerate(lines):
        s_i = p1[li][0]
        prev_end = p1[li - 1][1] + 0.35 if li else 0.0
        nxt = p1[li + 1][0] if li + 1 < n_lines else None
        lo = max(s_i - 0.9, prev_end - 0.1)
        hi = (nxt - 0.05) if (nxt is not None and nxt - s_i < 7.5) else s_i + 6.4
        cue = {'start': lo, 'end': hi, 'text': text}
        r = align_cue(sess, vocab, audio, cue, win=(lo, hi))
        words = text.split(); n = len(words)
        if r is None:
            t0 = fill_gaps([{'t0': None} for _ in words], lo, hi); score = -99.0; t_last = None
        else:
            _, times, score = r
            t0 = fill_gaps([{'t0': (None if times[k] is None else times[k][0])} for k in range(n)], lo, hi)
            t_last = times[-1][1] if times[-1] else None
        t0 = [max(lo, min(t, hi - 0.15)) for t in t0]
        for k in range(1, n): t0[k] = max(t0[k], t0[k - 1] + 0.12)
        out.append({'cue': li + 1, 'text': text, 'score': round(score, 2), 'start': round(t0[0], 3),
                    'words': [{'w': w, 't0': round(t0[k], 3)} for k, w in enumerate(words)], '_last': t_last, '_hi': hi})
    # a word is sung until the next one starts; the last word of a line until its last frame (+ tail) or the next line
    for i, c in enumerate(out):
        nxt = out[i + 1]['start'] if i + 1 < len(out) else 1e9
        end = min((c['_last'] if c['_last'] else c['words'][-1]['t0'] + 0.8) + 0.35, nxt - 0.05, c['_hi'])
        end = max(end, c['words'][-1]['t0'] + 0.35)
        for k, w in enumerate(c['words']): w['t1'] = round(c['words'][k + 1]['t0'] if k + 1 < len(c['words']) else end, 3)
        c['end'] = round(end, 3); del c['_last'], c['_hi']
        print(c['cue'], f"[{c['score']:.2f}]", ' | '.join(f"{w['w']} {w['t0']}" for w in c['words']), f"-> {end:.2f}", flush=True)
    json.dump(out, open(WORK / 'words.json', 'w'), ensure_ascii=False, indent=1)

def main():
    model_dir = pathlib.Path(sys.argv[1])
    if '--global' in sys.argv: return main_global(model_dir)
    import onnxruntime as ort
    sess = ort.InferenceSession(str(model_dir / 'model.onnx'), providers=['CPUExecutionProvider'])
    vocab = json.load(open(model_dir / 'vocab.json'))
    audio = load_audio()
    cues = parse_srt(open(ROOT / 'inputs' / 'lyrics.srt', encoding='utf8').read())
    n = len(cues)

    # ---- pass 1: generous windows around the SRT times
    first = []
    for i, c in enumerate(cues):
        r = align_cue(sess, vocab, audio, c)
        t = r[1][0][0] if r and r[1] and r[1][0] else None
        first.append(t)
    # lines are sung on a 2-bar grid; the SRT grid may be a constant offset away from the real singing, so
    # estimate that offset from the lines pass 1 is most sure about (median) and use it to repair outliers
    d = [first[i] - cues[i]['start'] for i in range(n) if first[i] is not None]
    off = float(np.median(d))
    starts = [first[i] if first[i] is not None and abs(first[i] - (cues[i]['start'] + off)) <= 0.5 else cues[i]['start'] + off for i in range(n)]
    print(f'pass 1: sung lines start {off:+.2f} s from the SRT times (median); {sum(1 for i in range(n) if first[i] is None or abs(first[i] - (cues[i]["start"] + off)) > 0.5)} lines repaired')

    # ---- pass 2: window = this line's start .. next line's start, so words cannot leak into the neighbour
    out = []
    for i, c in enumerate(cues):
        s_i = starts[i]
        nxt = starts[i + 1] if i + 1 < n else None
        hi = (nxt - 0.05) if (nxt is not None and nxt - s_i < 7.0) else s_i + 6.4
        r = align_cue(sess, vocab, audio, c, win=(s_i - 0.9, hi))
        mal = c['text'].split()
        if r is None:
            t0 = fill_gaps([{'t0': None} for _ in mal], s_i, hi); score = -99.0
        else:
            words, times, score = r
            t0 = fill_gaps([{'t0': (None if times[k] is None else times[k][0])} for k in range(len(mal))], s_i, hi)
        t0 = [max(s_i - 0.05, min(t, hi - 0.15)) for t in t0]
        for k in range(1, len(t0)):
            t0[k] = max(t0[k], t0[k - 1] + 0.12)
        # a word is sung until the next one starts; the last one until the line ends (sustained vowel) or the next line starts
        gap_after = (nxt - hi) if nxt is not None else 9
        last_end = min(hi, (r[1][-1][1] if r and r[1] and r[1][-1] else t0[-1] + 0.8) + 0.35)
        last_end = max(last_end, t0[-1] + 0.35)
        ws = []
        for k, w in enumerate(mal):
            ws.append({'w': w, 't0': round(float(t0[k]), 3), 't1': round(float(t0[k + 1] if k + 1 < len(mal) else last_end), 3)})
        out.append({'cue': i + 1, 'text': c['text'], 'start': round(float(t0[0]), 3), 'end': round(float(last_end), 3), 'score': round(score, 2), 'words': ws})
        print(i + 1, f'[{score:.2f}]', ' | '.join(f"{w['w']} {w['t0']}" for w in ws), f"-> {last_end:.2f}", flush=True)
    json.dump(out, open(WORK / 'words.json', 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
