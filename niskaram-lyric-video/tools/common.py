"""Shared helpers: paths, EDL -> per-shot spans on the master timeline."""
import json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work'))

def load_timeline():
    return json.load(open(WORK / 'timeline.json'))

def snap_to_onsets(shots, song_offset, window=0.3, strong_pct=70):
    """Move each non-anchored cut so the transition midpoint lands on the strongest nearby musical onset."""
    path = WORK / 'onsets.json'
    if not path.exists():
        return shots
    raw = json.load(open(path))
    cut = sorted(o[1] for o in raw)[int(len(raw) * strong_pct / 100)]      # only the strongest accents count
    onsets = [(o[0] + song_offset, o[1]) for o in raw if o[1] >= cut]
    out = []
    for i, s in enumerate(shots):
        s = dict(s)
        if s.get('anchor') or s['t'] < song_offset + 1.5:
            out.append(s); continue
        cands = [(f * (1 - abs(t - s["t"]) / (window * 1.4)), t) for t, f in onsets if abs(t - s['t']) <= window]
        if cands:
            s['t_planned'] = s['t']; s['t'] = round(max(cands)[1], 3)
        out.append(s)
    # keep order and a sane minimum shot length after snapping
    for i in range(1, len(out)):
        need = out[i - 1]['t'] + 2.0 + (out[i]['trd'] + out[i - 1]['trd']) / 2
        if out[i]['t'] < need:
            out[i]['t'] = round(need, 3)
    return out

def load_edl():
    edl = json.load(open(ROOT / 'edl.json'))
    try:
        off = load_timeline()['song_offset']
        edl['shots'] = snap_to_onsets(edl['shots'], off)
    except FileNotFoundError:
        pass
    return edl

def shot_spans(shots, total):
    """Each shot is shown from (t - trd/2) of its own incoming transition to
    (next.t + next.trd/2) of the following one.  Returns list of dicts with
    start/end/length on the master timeline."""
    spans = []
    for i, s in enumerate(shots):
        start = 0.0 if i == 0 else s['t'] - s['trd'] / 2
        if i + 1 < len(shots):
            nxt = shots[i + 1]
            end = nxt['t'] + nxt['trd'] / 2
        else:
            end = total
        spans.append(dict(s, start=start, end=end, length=end - start, idx=i))
    return spans
