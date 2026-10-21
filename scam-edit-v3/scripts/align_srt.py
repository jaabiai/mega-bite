"""Align the user's Malayalam SRT words to the real speech (ASR word times) -> work3/words_srt.json
Monotonic word-level DP (edit-distance similarity); words without a partner are interpolated by character count."""
import json, re, sys, unicodedata, difflib
import numpy as np
B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
srt = open(B + 'in3/user.srt', encoding='utf-8').read().strip().split('\n\n')
asr = json.load(open(B + 'work3/words_asr.json'))

CHILLU = [('ൻറ', 'ന്റ'), ('‍', ''), ('‌', ''), ('ന്‍', 'ൻ'), ('ള്‍', 'ൾ'), ('ല്‍', 'ൽ'), ('ര്‍', 'ർ'), ('ണ്‍', 'ൺ')]


def norm(s):
    s = unicodedata.normalize('NFC', s)
    for a, b in CHILLU:
        s = s.replace(a, b)
    s = re.sub(r'[.,?!"“”\'()%:;]', '', s)
    s = s.replace('ൂ', 'ു').replace('ീ', 'ി').replace('ൊ', 'െ').replace('ോ', 'േ')   # vowel length is unreliable in the ASR
    s = s.replace('ഒൻപത', 'ഒമ്പത')
    return s.strip()


cues = []
words = []                     # SRT words in order
for blk in srt:
    lines = blk.split('\n')
    t = lines[1]
    text = ' '.join(lines[2:]).strip()
    cues.append(text)
    for w in text.split():
        words.append(dict(w=w, cue=len(cues) - 1, n=norm(w)))
aw = []
for c in asr:
    for w in c['words']:
        aw.append(dict(w=w['w'], s=w['s'], e=w['e'], n=norm(w['w'])))
print(len(words), 'srt words;', len(aw), 'asr words')

N, M = len(words), len(aw)
GAP = -0.55
sc = np.zeros((N + 1, M + 1))
bt = np.zeros((N + 1, M + 1), np.int8)
sc[:, 0] = np.arange(N + 1) * GAP
sc[0, :] = np.arange(M + 1) * GAP
bt[1:, 0] = 1
bt[0, 1:] = 2


def sim(a, b):
    if re.search(r'\d', a):                      # numerals are spoken as words -> neutral
        return 0.15
    if not a or not b:
        return -1
    r = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    return 2.4 * r - 1.0


for i in range(1, N + 1):
    for j in range(1, M + 1):
        m = sc[i - 1, j - 1] + sim(words[i - 1]['n'], aw[j - 1]['n'])
        u = sc[i - 1, j] + GAP
        l = sc[i, j - 1] + GAP
        best = max(m, u, l)
        sc[i, j] = best
        bt[i, j] = 0 if best == m else (1 if best == u else 2)
i, j = N, M
pair = {}
while i > 0 or j > 0:
    if i > 0 and j > 0 and bt[i, j] == 0:
        pair[i - 1] = j - 1
        i -= 1; j -= 1
    elif i > 0 and (j == 0 or bt[i, j] == 1):
        i -= 1
    else:
        j -= 1
matched = 0
for k, w in enumerate(words):
    if k in pair:
        a = aw[pair[k]]
        s = sim(w['n'], a['n'])
        if s > -0.2 or re.search(r'\d', w['n']):
            w['t0'], w['t1'] = a['s'], a['e']
            w['m'] = 1
            matched += 1
print('matched', matched, 'of', N)

# interpolate the rest between matched neighbours (weights = characters)
k = 0
while k < N:
    if 'm' in words[k]:
        k += 1
        continue
    k0 = k
    while k < N and 'm' not in words[k]:
        k += 1
    prev_end = words[k0 - 1]['t1'] if k0 > 0 else 0.0
    next_start = words[k]['t0'] if k < N else aw[-1]['e']
    span = max(next_start - prev_end, 0.12 * (k - k0))
    ws = [len(words[x]['n']) + 1 for x in range(k0, k)]
    tot = sum(ws)
    acc = 0
    for x, wgt in zip(range(k0, k), ws):
        words[x]['t0'] = prev_end + span * acc / tot
        acc += wgt
        words[x]['t1'] = prev_end + span * acc / tot
# monotonic cleanup
for x in range(1, N):
    if words[x]['t0'] < words[x - 1]['t0'] + 0.02:
        words[x]['t0'] = words[x - 1]['t0'] + 0.02
    if words[x]['t1'] < words[x]['t0'] + 0.05:
        words[x]['t1'] = words[x]['t0'] + 0.05
json.dump(dict(cues=cues, words=[{k: v for k, v in w.items() if k in ('w', 'cue', 't0', 't1', 'm')} for w in words]),
          open(B + 'work3/words_srt.json', 'w'), ensure_ascii=False, indent=0)
# report
for c in range(len(cues)):
    ws = [w for w in words if w['cue'] == c]
    print(f"{c + 1:2d} {ws[0]['t0']:7.2f}-{ws[-1]['t1']:7.2f}  matched {sum(1 for w in ws if 'm' in w)}/{len(ws)}  {cues[c][:40]}")
