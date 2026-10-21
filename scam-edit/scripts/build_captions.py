"""Turn captions_spec + EDL timing into overlay/captions.json (+ a Manglish .srt)."""
import json, re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/scripts')
from captions_spec import CAPS

B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
edl = json.load(open(B + 'work/edl.json'))
P = edl['pieces']
FPS = edl['fps']
MARK = {'*': 'amt', '!': 'bad', '+': 'ok'}


def parse(phrase):
    toks, open_ch = [], None
    for raw in phrase.split():
        t = raw
        if open_ch is None and len(t) > 1 and t[0] in MARK:
            open_ch = t[0]
            t = t[1:]
        kind = MARK[open_ch] if open_ch else None
        if open_ch and len(t) > 1 and t[-1] == open_ch:
            t = t[:-1]
            open_ch = None
        toks.append(dict(s=t, k=kind))
    return toks


groups = []
for pi, items in CAPS.items():
    p = P[pi]
    out_of = {w['i']: w['out'] for w in p['words']}
    core_end = p['out_a'] / FPS + (p['off'] - p['a'] / FPS)
    for gi, (anchor, phrase) in enumerate(items):
        t0 = out_of[anchor] - 0.04
        t1 = out_of[items[gi + 1][0]] - 0.04 if gi + 1 < len(items) else core_end
        toks = parse(phrase)
        wts = [len(t['s'].strip('.,?')) + 1.6 for t in toks]
        tot = sum(wts)
        acc = 0
        for t, w in zip(toks, wts):
            t['t'] = round(t0 + (t1 - t0) * acc / tot, 3)
            acc += w
        groups.append(dict(piece=pi, a=t0 - 0.03, speech_end=t1, words=toks))

# on/off windows: hold briefly after speech, hand over to the next phrase without overlap
for i, g in enumerate(groups):
    nxt = groups[i + 1] if i + 1 < len(groups) else None
    hold = g['speech_end'] + 0.28
    if nxt and nxt['a'] < hold:
        hold = nxt['a']
    g['b'] = round(max(hold, g['speech_end']), 3)
    g['a'] = round(g['a'], 3)
    g['speech_end'] = round(g['speech_end'], 3)

json.dump(groups, open(B + 'overlay/captions.json', 'w'), ensure_ascii=False, indent=1)
print(len(groups), 'caption groups;', sum(len(g['words']) for g in groups), 'words')


def ts(t):
    h, r = divmod(max(t, 0), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


INS_T, DLT = 719 / 30, 84 / 30
SH = lambda g: DLT if g['piece'] >= 8 else 0              # overlay timeline is shifted in overlay.js; the .srt is shifted here
with open(B + 'work/captions_manglish.srt', 'w', encoding='utf-8') as f:
    for i, g in enumerate(groups, 1):
        text = ' '.join(t['s'] for t in g['words'])
        f.write(f"{i}\n{ts(g['a'] + 0.03 + SH(g))} --> {ts(g['b'] + SH(g))}\n{text}\n\n")
print('wrote srt')
