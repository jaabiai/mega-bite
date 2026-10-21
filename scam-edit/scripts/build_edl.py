"""Build the edit decision list from the word-timed transcript.

Every kept piece is cut on the 30 fps frame grid, only in genuinely quiet frames, so the video cut
and the audio cut happen at the same instant and never inside a word or on top of a noise burst.
"""
import json
import numpy as np

S = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/work/'
FPS = 30.0
SR = 48000
PAD = 0.06                # silero pads each VAD chunk by this much on both sides
QUIET = -38.0             # dB (30 ms RMS) counted as "room tone"
SRC_DUR = 343.3667

W = json.load(open(S + 'words_indic.json'))
VAD = json.load(open(S + 'vad_300.json'))
mono = np.load(S + 'audio/mono48.npy')
chunks = {c['i']: c for c in W}

# (chunk, [(first_word, last_word|None), ...], lead_in, tail_out)
# several pieces in one chunk = internal splice (a stumble was removed).
# lead/tail are the *maximum* seconds of real room tone kept around the speech; they set the pause
# between phrases (clamped to the silence that really exists and to quiet frames only).
KEEP = [
    (1,  [(0, None)],            0.12, 0.35),   # hook: GPay 9th anniversary, Rs 6000/9000/10000
    (2,  [(0, None)],            0.10, 0.32),
    (3,  [(3, 3), (6, None)],    0.00, 0.45),   # drop "athallenkil facebook ok" + "ethenkilum sca" stumbles
    (4,  [(0, 0)],               0.10, 0.22),
    (5,  [(0, None)],            0.10, 0.20),
    (6,  [(0, None)],            0.10, 0.75),   # "ennal ithu sathyamano?"  -> dramatic beat
    (7,  [(0, 0)],               0.12, 0.40),   # "orikkalumalla"
    (8,  [(0, None)],            0.10, 0.28),
    (9,  [(0, None)],            0.10, 0.25),
    (10, [(0, None)],            0.10, 0.20),
    (11, [(0, 0)],               0.10, 0.14),
    (12, [(0, None)],            0.10, 0.45),
    (13, [(1, None)],            0.00, 0.45),   # drop stutter "ingale"
    (14, [(7, None)],            0.00, 0.30),   # keep 2nd (complete) take
    (16, [(0, 4)],               0.10, 0.20),   # "... nigalude data"   (retake of the tail follows)
    (18, [(0, None)],            0.10, 0.20),   # "mananashtam dhananashtam"
    (19, [(0, None)],            0.10, 0.45),
    (20, [(0, 9)],               0.10, 0.16),   # drop dangling "aalukal"
    (21, [(0, None)],            0.10, 0.30),
    (22, [(0, 0)],               0.10, 0.20),   # "sookshikkanam"   (drop false start "athaarkkum")
    (23, [(0, None)],            0.10, 0.50),
    (30, [(0, None)],            0.10, 0.12),   # best take of "ithrathilulla vyaja linkukal vazhi"
    (31, [(0, 0)],               0.10, 0.16),   # "thattippukar"
    (34, [(0, None)],            0.10, 0.20),
    (35, [(0, None)],            0.10, 0.45),
    (36, [(0, None)],            0.10, 0.45),
    (37, [(0, None)],            0.10, 0.35),
    (38, [(0, None)],            0.10, 0.10),
    (39, [(0, None)],            0.10, 0.12),
    (40, [(0, None)],            0.10, 0.50),
    (42, [(0, None)],            0.10, 0.45),
    (43, [(0, None)],            0.10, 0.30),
    (44, [(0, None)],            0.10, 0.30),
    (45, [(0, None)],            0.10, 0.30),
    (46, [(0, None)],            0.10, 0.25),
    (47, [(0, None)],            0.10, 0.25),
    (48, [(0, None)],            0.10, 0.55),
    (51, [(0, None)],            0.10, 0.35),   # complete GPay take (49/50 were aborted)
    (52, [(0, None)],            0.10, 0.14),
    (53, [(0, None)],            0.10, 0.55),
    (54, [(0, None)],            0.10, 0.25),
    (55, [(0, None)],            0.10, 0.14),
    (56, [(0, None)],            0.10, 0.14),
    (57, [(0, None)],            0.10, 0.55),
    (59, [(0, None)],            0.10, 0.12),
    (60, [(0, 3), (5, None)],    0.10, 0.45),   # drop stumble "udanadathi"
    (61, [(0, None)],            0.10, 0.40),
    (62, [(0, None)],            0.10, 0.40),
]


def db_at(t, half=0.015):
    a, b = int((t - half) * SR), int((t + half) * SR)
    seg = mono[max(a, 0):max(b, a + 1)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)


def dbk(k):
    return db_at(k / FPS)


def quiet(k):
    return dbk(k) < QUIET


def valley(t0, t1):
    """Quietest frame-grid time in [t0, t1] (used for cuts inside continuous speech)."""
    k0, k1 = int(np.ceil(t0 * FPS)), int(np.floor(t1 * FPS))
    if k1 < k0:
        k0 = k1 = int(round((t0 + t1) / 2 * FPS))
    cands = list(range(k0, k1 + 1))
    mid = (k0 + k1) / 2
    score = [dbk(k) + 0.05 * abs(k - mid) for k in cands]
    return cands[int(np.argmin(score))]


def env_db(t, h=0.01):
    a, b = int((t - h) * SR), int((t + h) * SR)
    seg = mono[max(a, 0):max(b, a + 1)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)


def core_onset(ci):
    """Where the first word really starts: first frame within 12 dB of the local speech peak
    (rejects the inhale/mouth noise that sits just before many phrases)."""
    t0 = VAD[ci][0]
    ts = np.arange(t0 - 0.10, t0 + 0.60, 0.005)
    e = np.array([env_db(t) for t in ts])
    peak = np.percentile(e[ts >= t0], 95)
    thr = max(peak - 12, -34)
    idx = int(np.argmax((e >= thr) & (ts >= t0 - 0.05)))
    return float(ts[idx]) - 0.07           # keep the soft consonant attack


def core_offset(ci):
    t1 = VAD[ci][1]
    ts = np.arange(t1 - 0.60, t1 + 0.20, 0.005)
    e = np.array([env_db(t) for t in ts])
    peak = np.percentile(e[ts <= t1], 95)
    thr = max(peak - 14, -36)
    ok = np.where((e >= thr) & (ts <= t1 + 0.10))[0]
    return float(ts[ok[-1]]) + 0.05


pieces = []
for seg_id, (ci, parts, lead, tail) in enumerate(KEEP):
    c = chunks[ci]
    w = c['words']
    n = len(parts)
    for pi, (f, l) in enumerate(parts):
        if l is None:
            l = len(w) - 1
        piece = dict(seg=seg_id, chunk=ci, part=pi, parts=n, first=f, last=l)
        if f == 0:
            on = core_onset(ci)
            piece.update(on=on, lead_pad=True, a=int(round((on - lead) * FPS)))
        else:
            lo = w[f - 1]['s'] + 0.18
            a_f = valley(max(w[f]['s'] - 0.28, lo), w[f]['s'] - 0.0)
            piece.update(on=a_f / FPS, lead_pad=False, a=a_f)
        if l == len(w) - 1:
            off = core_offset(ci)
            piece.update(off=off, tail_pad=True, b=int(round((off + tail) * FPS)))
        else:
            nxt = w[l + 1]['s']
            b_f = valley(nxt - 0.30, nxt + 0.02)
            if pi == n - 1:      # end of the segment: dangling words dropped -> pad with room tone
                piece.update(off=b_f / FPS, tail_pad=True, b=int(round((b_f / FPS + tail) * FPS)))
            else:                # internal splice
                piece.update(off=b_f / FPS, tail_pad=False, b=b_f)
        pieces.append(piece)

# source ranges of consecutive pieces must not overlap (no repeated video frames)
for p, q in zip(pieces, pieces[1:]):
    if q['a'] < p['b']:
        mid = (p['b'] + q['a']) // 2
        p['b'] = q['a'] = mid
for p in pieces:                       # cores must lie inside their frame ranges
    p['on'] = max(p['on'], p['a'] / FPS)
    p['off'] = min(p['off'], p['b'] / FPS)

# ------------------------------------------------------------------ timeline
t_out = 0
for p in pieces:
    c = chunks[p['chunk']]
    p['out_a'] = t_out
    p['out_b'] = t_out + (p['b'] - p['a'])
    assert p['b'] > p['a'] and p['off'] > p['on'], p
    p['words'] = [dict(i=wi, ml=c['words'][wi]['w'], conf=round(c['words'][wi]['conf'], 3),
                       src=round(c['words'][wi]['s'], 3),
                       out=round(p['out_a'] / FPS + (c['words'][wi]['s'] - p['a'] / FPS), 3))
                  for wi in range(p['first'], p['last'] + 1)]
    t_out += p['b'] - p['a']

total = t_out
print(f"pieces: {len(pieces)}   speech timeline: {total} frames = {total / FPS:.2f}s  (source {SRC_DUR:.2f}s)")
print("\n  #  chunk p   src_a - src_b      core on - off      out_a - out_b    dur   pause_after")
for i, p in enumerate(pieces):
    nxt = pieces[i + 1] if i + 1 < len(pieces) else None
    pause = ''
    if nxt:
        pause = 'splice' if nxt['seg'] == p['seg'] else f"{((p['b'] / FPS - p['off']) + (nxt['on'] - nxt['a'] / FPS)):.2f}s" \
            + ('  (contiguous src)' if nxt['a'] == p['b'] else '')
    print(f"{i:3d}  {p['chunk']:3d}  {p['part']}  {p['a'] / FPS:7.2f}-{p['b'] / FPS:7.2f}  {p['on']:7.2f}-{p['off']:7.2f}  "
          f"{p['out_a'] / FPS:7.2f}-{p['out_b'] / FPS:7.2f}  {(p['b'] - p['a']) / FPS:5.2f}  {pause}")

json.dump(dict(fps=FPS, total_frames=total, pieces=pieces), open(S + 'edl.json', 'w'), ensure_ascii=False, indent=1)
print('wrote edl.json')
