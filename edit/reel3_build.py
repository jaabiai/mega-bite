"""Reel v3 builder ("announcement" cut: hook + the line where he introduces each feature + one result line, no screen demo).
From the layout (excerpt placement) derive
   data/reel3_shots.json     every picture layer (speaker / original phone shot / B-roll) with frame ranges
   data/reel3_timeline.json  overlay events + caption pages (reel seconds)
   data/reel3_words.json     narration words in reel time (for the music ducking)
   data/reel3_sfx.json       sound-effect cues
All numbers derive from the narration cut points, so picture, text and sound stay locked together."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("REEL_TAG", "reel3")
import reel2_plan as P  # noqa: E402  (generic plan code, excerpt set chosen by REEL_TAG)
import timeline as tl  # noqa: E402  (split_sentence, aligned words)

assert P.TAG == "reel3"

FPS, FR, SR, XF = P.FPS, P.FR, P.SR, P.XF
L = P.load_layout()
EX = {e["id"]: e for e in L["excerpts"]}
N_FRAMES = L["n_frames"]


def rt(main_t, ex):
    """reel seconds of a MAIN-timeline moment inside excerpt `ex` (frame-exact)"""
    return round((ex["F"] + main_t * FPS - ex["f0"]) / FPS, 3)


def fr_of(main_t, ex):
    return int(round(ex["F"] + main_t * FPS - ex["f0"]))


SHOTS, EVENTS, SFX = [], [], []


def src_frames_avail(ex, F0):
    """source frames of this excerpt's footage that still belong to the narration (the rest is frozen)"""
    last = (ex["s1"] - ex["f0"] * FR) / FR
    return max(int(math.ceil(last)) - (F0 - ex["F"]), 1)


def shot(id_, kind, F0, F1, ext=0, fade=0, entrance="none", ex=None, **kw):
    s = dict(id=id_, kind=kind, F0=F0, F1=F1, ext=ext, fade=fade, entrance=entrance, **kw)
    if kind in ("spk", "orig"):
        s["src_n"] = min(F1 - F0, src_frames_avail(ex, F0))
        s["src_f0"] = ex["f0"] + (F0 - ex["F"])
    SHOTS.append(s)
    return s


def ev(type_, t0, t1, **kw):
    EVENTS.append(dict(type=type_, t0=round(t0, 3), t1=round(t1, 3), **kw))


# -------------------------------------------------------------------------------------------------- shots
# hook ------------------------------------------------------------------------------------------------
e = EX["hook"]
shot("hook_spk", "spk", e["F"], e["F_end"], ext=XF, ex=e, tracked=True, zoom=[1.0, 1.06])

# F1 : "the first one" - speaker, then B-roll while the problem is described, then the result on an alarm clock ---
e = EX["f1a"]
b1 = fr_of(35.40, e)
shot("f1a_spk", "spk", e["F"], b1, ext=6, fade=XF, entrance="zoom", ex=e, tracked=True, zoom=[1.0, 1.04])
shot("f1a_b41165", "broll", b1, e["F_end"], ext=XF, fade=6, clip=41165, src_in=4.0, cx=0.34, zoom=[1.00, 1.10])
e = EX["f1b"]
shot("f1b_b28902", "broll", e["F"], e["F_end"], ext=XF, fade=8, clip=28902, src_in=1.0, cx=0.5, zoom=[1.00, 1.10])

# F2 : "next one" - speaker, busy-place B-roll, the one-line fix, then the result ---------------------------------
e = EX["f2a"]
b1 = fr_of(114.85, e)
b2 = fr_of(117.45, e)
shot("f2a_spk", "spk", e["F"], b1, ext=6, fade=XF, entrance="zoom", ex=e, tracked=True, zoom=[1.0, 1.04])
shot("f2a_b4401", "broll", b1, b2, ext=6, fade=6, clip=4401, src_in=3.2, cx=0.50, zoom=[1.00, 1.12])
shot("f2a_b309", "broll", b2, e["F_end"], ext=XF, fade=6, clip=309, src_in=5.2, cx=0.43, zoom=[1.02, 1.14])
e = EX["f2b"]
shot("f2b_spk", "spk", e["F"], e["F_end"], ext=XF, fade=8, entrance="none", ex=e, tracked=True, zoom=[1.04, 1.09])
e = EX["f2c"]
c1 = fr_of(161.85, e)
shot("f2c_b4332", "broll", e["F"], c1, ext=6, fade=8, clip=4332, src_in=0.8, cx=0.60, zoom=[1.00, 1.10])
shot("f2c_b39791", "broll", c1, e["F_end"], ext=XF, fade=6, clip=39791, src_in=2.0, cx=0.50, zoom=[1.00, 1.08])

# F3 : "the third one" - speaker (the footage itself cuts to the phone at 172.93), worried-on-hold B-roll, phone ----
e = EX["f3a"]
b1 = fr_of(172.933, e)          # first frame of the phone shot in the source footage
b2 = fr_of(177.40, e)
shot("f3a_spk", "spk", e["F"], b1, ext=6, fade=XF, entrance="zoom", ex=e, tracked=True, zoom=[1.0, 1.05])
shot("f3a_b39790", "broll", b1, b2, ext=6, fade=8, clip=39790, src_in=1.0, cx=0.42, zoom=[1.00, 1.12])
shot("f3a_orig", "orig", b2, e["F_end"], ext=XF, fade=8, entrance="none", ex=e, tracked=False,
     cx=0.47 * 1920, fg_dy=-60, zoom=[1.0, 1.05])
e = EX["f3b"]
shot("f3b_orig", "orig", e["F"], e["F_end"], ext=XF, fade=8, entrance="none", ex=e, tracked=False,
     cx=0.49 * 1920, fg_dy=-190, zoom=[1.0, 1.04])

# outro -------------------------------------------------------------------------------------------------------
e = EX["recap"]
shot("recap_spk", "spk", e["F"], e["F_end"], ext=8, fade=XF, entrance="zoom", ex=e, tracked=True, zoom=[1.0, 1.05])
e = EX["cta"]
shot("cta_spk", "spk", e["F"], N_FRAMES, ext=0, fade=8, entrance="none", ex=e, tracked=True, zoom=[1.03, 1.08],
     tail=True)

# -------------------------------------------------------------------------------------------------- overlay events
CH_NAMES = {1: "MISS CALL REMINDER", 2: "VOICE ISOLATION", 3: "HOLD ASSIST"}
CH_LAST = {1: "f1b", 2: "f2c", 3: "f3b"}


def chapter(n, F, end_t):
    t = F / FPS
    ev("chapter", t + 0.06, t + 1.62, n=n, title=CH_NAMES[n])
    ev("chip", t + 1.0, end_t, n=n, title=CH_NAMES[n])
    SFX.append(dict(type="impact", t=t + 0.10, gain=0.50, big=False))
    SFX.append(dict(type="pop", t=t + 0.30, gain=0.26))


def cards(e, spec):
    """spec: (main_t0, main_t1, kicker, text, sub) -> kp cards locked to the narration (+ a pop on each)"""
    for a, b, kicker, text, sub in spec:
        ev("kp", rt(a, e), min(rt(b, e), e["F_end"] / FPS - 0.02), kicker=kicker, text=text, sub=sub)
        SFX.append(dict(type="pop", t=rt(a, e) + 0.05, gain=0.18))


e = EX["hook"]
ev("hook", rt(0.25, e), e["F_end"] / FPS - 0.02, kicker="iOS 27  •  MUST WATCH", lines=["3 KIDILAN", "iPHONE FEATURES"])
ev("features", rt(2.1, e), e["F_end"] / FPS - 0.02, items=P.FEATURES, kicker="IN THIS VIDEO")
SFX += [dict(type="impact", t=0.22, gain=0.55, big=False), dict(type="whoosh", t=0.18, dur=0.55, up=True, gain=0.30)]
for k in range(3):
    SFX.append(dict(type="pop", t=rt(2.1, e) + 0.12 + 0.30 * k, gain=0.20))

e = EX["f1a"]
chapter(1, e["F"], EX[CH_LAST[1]]["F_end"] / FPS)
cards(e, [(36.10, 38.95, "PROBLEM", "MISSED A CALL?", "miss call nalki"),
          (39.00, 41.80, "PROBLEM", "CALL BACK LATER", "pinneedu call back cheyyanam")])
e = EX["f1b"]
cards(e, [(90.15, 93.25, "THE RESULT", "GET REMINDED", "aa samayathu notification")])
SFX.append(dict(type="chime", t=rt(92.2, e), gain=0.26))

e = EX["f2a"]
chapter(2, e["F"], EX[CH_LAST[2]]["F_end"] / FPS)
cards(e, [(115.25, 119.65, "PROBLEM", "NOISY PLACE?", "call varumbol surrounding noise")])
e = EX["f2b"]
cards(e, [(129.25, 131.60, "THE FIX", "ONE SIMPLE SETTING", "athinum oru solution undu")])
e = EX["f2c"]
cards(e, [(158.70, 161.85, "THE RESULT", "NOISE ISOLATED", "surrounding shabdam poorrnnamayi")])
t0 = rt(162.0, e)
ev("voice", t0, e["F_end"] / FPS - 0.02, kicker="THE RESULT", text="ONLY YOUR VOICE", sub="ningal parayunna shabdam mathram")
SFX.append(dict(type="riser", t0=t0 - 0.7, t1=t0, gain=0.30))
SFX.append(dict(type="impact", t=t0, gain=0.50, big=False))

e = EX["f3a"]
chapter(3, e["F"], EX[CH_LAST[3]]["F_end"] / FPS)
cards(e, [(173.70, 177.40, "PROBLEM", "CALL ON HOLD?", "avar unhold cheyyunnathu vare..."),
          (177.50, 181.00, "THE IDEA", "NO NEED TO WAIT", "kaathirikkendathilla")])
e = EX["f3b"]
cards(e, [(229.05, 231.75, "THE SETTING", "HOLD ASSIST", "More \u203a Hold Assist"),
          (231.90, 234.50, "THE RESULT", "ACCEPT & TALK", "unhold aakumbol ring cheyyum")])

e = EX["recap"]
ev("kp", rt(237.10, e), e["F_end"] / FPS - 0.02, kicker="RECAP", text="3 KIDILAN FEATURES", sub="moonnum valare useful")
ev("features", rt(237.9, e), e["F_end"] / FPS - 0.02, items=P.FEATURES, kicker="")
for k in range(3):
    SFX.append(dict(type="pop", t=rt(237.9, e) + 0.12 + 0.28 * k, gain=0.20))

e = EX["cta"]
click = rt(246.62, e)
ev("endcard", e["F"] / FPS + 0.10, N_FRAMES / FPS, at=click, lines=["FULL VIDEO", "ON MEGA BYTE"])
SFX.append(dict(type="whoosh", t=e["F"] / FPS + 0.08, dur=0.55, up=True, gain=0.32))
SFX.append(dict(type="tap", t=click, gain=0.34))
SFX.append(dict(type="chime", t=click + 0.03, gain=0.40))
SFX.append(dict(type="chime", t=click + 0.40, gain=0.20))

# joins: whoosh centred in the transition (chapter changes get the stronger one)
for i, e in enumerate(L["excerpts"][1:], 1):
    SFX.append(dict(type="whoosh", t=e["F"] / FPS + 0.04, dur=0.5, up=True, gain=0.34))
# B-roll shot starts inside excerpts
for s in SHOTS:
    if s["kind"] == "broll":
        SFX.append(dict(type="whoosh", t=s["F0"] / FPS + 0.02, dur=0.36, up=True, gain=0.16))

# -------------------------------------------------------------------------------------------------- captions + words
pages, words_out = [], []
for e in L["excerpts"]:
    a, b = e["s0"] / SR, e["s1"] / SR
    ws = [w for w in tl.WORDS if w["cue"] in e["cues"]]
    sents, cur = [], []
    for w in ws:
        cur.append(w)
        if w["text"].endswith(tl.SENT_END):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    pgs = []
    for s in sents:
        pgs.extend(tl.split_sentence(s, max_chars=34, max_words=5))
    end_lim = e["F_end"] / FPS
    for i, p in enumerate(pgs):
        t0 = p[0]["start"] + e["D"] - 0.08
        nxt = pgs[i + 1][0]["start"] + e["D"] - 0.08 if i + 1 < len(pgs) else p[-1]["end"] + e["D"] + 0.30
        t1 = min(nxt, p[-1]["end"] + e["D"] + 0.40, end_lim)
        pages.append({"t0": round(max(t0, e["F"] / FPS), 3), "t1": round(t1, 3),
                      "words": [{"t": w["text"], "a": round(w["start"] + e["D"], 3), "b": round(w["end"] + e["D"], 3)} for w in p]})
    for w in ws:
        words_out.append({"text": w["text"], "start": round(w["start"] + e["D"], 3), "end": round(w["end"] + e["D"], 3)})

D = dict(duration=L["duration"], n_frames=N_FRAMES, captions=pages, events=EVENTS,
         chapters=[dict(n=n, t0=EX[i]["F"] / FPS, t1=EX[j]["F_end"] / FPS) for n, (i, j) in
                   enumerate([("f1a", "f1b"), ("f2a", "f2c"), ("f3a", "f3b")], 1)])
json.dump(D, open(f"{HERE}/data/reel3_timeline.json", "w"), ensure_ascii=False, indent=1)
json.dump(dict(duration=L["duration"], words=words_out), open(f"{HERE}/data/reel3_words.json", "w"), indent=1)
json.dump(SHOTS, open(f"{HERE}/data/reel3_shots.json", "w"), indent=1)
json.dump(SFX, open(f"{HERE}/data/reel3_sfx.json", "w"), indent=1)
if __name__ == "__main__":
    print("shots", len(SHOTS), "events", len(EVENTS), "caption pages", len(pages), "sfx cues", len(SFX), "words", len(words_out))
    for s in SHOTS:
        print(f"  {s['id']:12s} {s['kind']:6s} F {s['F0']:5d}-{s['F1']:5d} (+{s['ext']}) {s['F0'] / 30:6.2f}-{s['F1'] / 30:6.2f} s  entrance={s['entrance']} fade={s['fade']}")
