"""Refine line boundaries using real pauses in the 1-4 kHz (voice-formant) band."""
import numpy as np
from envview import band_env

_E = None
def env():
    global _E
    if _E is None:
        _E = band_env(1000, 4000, 0.02)
    return _E

def find_gap(S, back=0.8, fwd=1.2, search=3.4, win=10.0, qfrac=0.22, min_gap=0.30, E=None):
    """Return (gap_start, onset) of the first pause that begins near boundary S, else None."""
    e, hop = env() if E is None else E
    a, b = max(0, int((S - win) / hop)), min(len(e), int((S + win) / hop))
    seg = e[a:b]
    floor, top = np.percentile(seg, 5), np.percentile(seg, 99)
    thr = floor + qfrac * (top - floor)
    i0, i1 = max(0, int((S - back) / hop)), min(len(e), int((S + search) / hop))
    q = e[i0:i1] < thr
    # light closing: bridge single-frame blips so tiny spikes don't split a pause
    q2 = q.copy()
    for j in range(1, len(q) - 1):
        if not q[j] and q[j - 1] and q[j + 1]:
            q2[j] = True
    q = q2
    j = 0
    n = len(q)
    while j < n:
        if q[j]:
            k = j
            while k < n and q[k]:
                k += 1
            gs, ge = (i0 + j) * hop, (i0 + k) * hop
            if ge - gs >= min_gap and (S - back) <= gs <= (S + fwd) and k < n:
                return gs, ge
            j = k
        else:
            j += 1
    return None


def bursts(t0, t1, qfrac=0.30, min_len=0.12, merge=0.18, win=10.0):
    """List of (start,end) active intervals of the 1-4 kHz band within [t0,t1]."""
    e, hop = env()
    c = (t0 + t1) / 2
    a, b = max(0, int((c - win - (t1 - t0) / 2) / hop)), min(len(e), int((c + win + (t1 - t0) / 2) / hop))
    seg = e[a:b]
    floor, top = np.percentile(seg, 5), np.percentile(seg, 99)
    thr = floor + qfrac * (top - floor)
    i0, i1 = int(t0 / hop), int(t1 / hop)
    act = e[i0:i1] >= thr
    out = []
    j = 0
    n = len(act)
    while j < n:
        if act[j]:
            k = j
            while k < n and act[k]:
                k += 1
            out.append([(i0 + j) * hop, (i0 + k) * hop])
            j = k
        else:
            j += 1
    # merge small holes
    m = []
    for s_, e_ in out:
        if m and s_ - m[-1][1] < merge:
            m[-1][1] = e_
        else:
            m.append([s_, e_])
    return [(round(s_, 2), round(e_, 2)) for s_, e_ in m if e_ - s_ >= min_len]
