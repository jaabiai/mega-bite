"""Reel v2 builder: from the layout (excerpt placement) derive
   data/reel2_shots.json     every picture layer (speaker / original phone shots / iPhone demo / B-roll) with frame ranges
   data/reel2_timeline.json  overlay events + caption pages (reel seconds)
   data/reel2_words.json     narration words in reel time (for the music ducking)
   data/reel2_sfx.json       sound-effect cues
All numbers derive from the narration cut points, so picture, text and sound stay locked together."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reel2_plan as P  # noqa: E402
import timeline as tl  # noqa: E402  (split_sentence, aligned words)
import scenes  # noqa: E402

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


# -------------------------------------------------------------------------------------------------- camera / scene data
S1_CAMERA = [(50.40, 660, 1100, 1.00), (53.00, 700, 1085, 1.06), (54.00, 860, 1060, 1.25), (56.20, 900, 1050, 1.30),
             (58.60, 1000, 1040, 1.36), (59.60, 733, 1330, 1.10), (66.00, 733, 1330, 1.10)]
S1_FOCUS_EXTRA = [dict(t0=50.45, t1=53.8, rect=scenes.STAR_ROW, radius=40, dim=0.38)]
sys.path.insert(0, os.path.join(HERE, "tools"))
import reel_scene as rs  # noqa: E402  (only for its CAMERA table; geometry patching is harmless here)
S2_CAMERA = [list(k) for k in rs.CAMERA]

# -------------------------------------------------------------------------------------------------- shots
# hook ------------------------------------------------------------------------------------------------
e = EX["hook"]
shot("hook_spk", "spk", e["F"], e["F_end"], ext=XF, ex=e, tracked=True, zoom=[1.0, 1.06])

# F1 : miss call reminder (iPhone demo, window = the narration's own time) ---------------------------------
e = EX["f1"]
m0 = e["f0"] / FPS
shot("f1_scene", "scene", e["F"], e["F_end"], ext=XF, fade=XF, entrance="zoom", scene="S1", m0=m0,
     camera=S1_CAMERA, focus_extra=S1_FOCUS_EXTRA)

# F2a : problem (speaker -> B-roll call -> B-roll noise) ------------------------------------------------------
e = EX["f2a"]
b1 = fr_of(117.45, e)
b2 = fr_of(119.67, e)
shot("f2a_spk", "spk", e["F"], b1, ext=6, fade=XF, entrance="zoom", ex=e, tracked=True, zoom=[1.0, 1.04])
shot("f2a_b309", "broll", b1, b2, ext=6, fade=6, clip=309, src_in=5.2, cx=0.43, zoom=[1.02, 1.14])
shot("f2a_b4401", "broll", b2, e["F_end"], ext=XF, fade=6, clip=4401, src_in=3.2, cx=0.50, zoom=[1.00, 1.12])

# F2b : the setting (demo) + result (B-roll) ------------------------------------------------------------------
e = EX["f2b"]
c1 = e["F"] + 68
c2 = e["F"] + 110
shot("f2b_scene", "scene", e["F"], c1, ext=6, fade=0, entrance="slide", scene="S2", m0=150.9,
     camera=S2_CAMERA, focus_extra=[])
shot("f2b_b4332", "broll", c1, c2, ext=6, fade=6, clip=4332, src_in=0.8, cx=0.60, zoom=[1.00, 1.10])
shot("f2b_b39791", "broll", c2, e["F_end"], ext=XF, fade=6, clip=39791, src_in=2.0, cx=0.50, zoom=[1.00, 1.08], portrait=True)

# F3a / F3b : original phone footage ---------------------------------------------------------------------------
e = EX["f3a"]
shot("f3a_orig", "orig", e["F"], e["F_end"], ext=XF, fade=XF, entrance="zoom", ex=e, tracked=False,
     cx=0.47 * 1920, fg_dy=-60, zoom=[1.0, 1.05])
e = EX["f3b"]
shot("f3b_orig", "orig", e["F"], e["F_end"], ext=XF, fade=8, entrance="zoom", ex=e, tracked=False,
     cx=0.49 * 1920, fg_dy=-190, zoom=[1.0, 1.04])

# outro -------------------------------------------------------------------------------------------------------
e = EX["recap"]
shot("recap_spk", "spk", e["F"], e["F_end"], ext=8, fade=XF, entrance="zoom", ex=e, tracked=True, zoom=[1.0, 1.05])
e = EX["cta"]
shot("cta_spk", "spk", e["F"], N_FRAMES, ext=0, fade=8, entrance="none", ex=e, tracked=True, zoom=[1.03, 1.08],
     tail=True)

# -------------------------------------------------------------------------------------------------- overlay events
CH_NAMES = {1: "MISS CALL REMINDER", 2: "VOICE ISOLATION", 3: "HOLD ASSIST"}


def chapter(n, F, end_t):
    t = F / FPS
    ev("chapter", t + 0.06, t + 1.62, n=n, title=CH_NAMES[n])
    ev("chip", t + 1.0, end_t, n=n, title=CH_NAMES[n])
    SFX.append(dict(type="impact", t=t + 0.10, gain=0.50, big=False))
    SFX.append(dict(type="pop", t=t + 0.30, gain=0.26))


e = EX["hook"]
ev("hook", rt(0.25, e), e["F_end"] / FPS - 0.02, kicker="iOS 27  •  MUST WATCH", lines=["3 KIDILAN", "iPHONE FEATURES"])
ev("features", rt(2.1, e), e["F_end"] / FPS - 0.02, items=P.FEATURES, kicker="IN THIS VIDEO")
SFX += [dict(type="impact", t=0.22, gain=0.55, big=False), dict(type="whoosh", t=0.18, dur=0.55, up=True, gain=0.30)]
for k in range(3):
    SFX.append(dict(type="pop", t=rt(2.1, e) + 0.12 + 0.30 * k, gain=0.20))

e = EX["f1"]
chapter(1, e["F"], e["F_end"] / FPS)
for n, (a, b, title, sub) in enumerate([(52.00, 53.75, "PICK THE CALL", "ethu call-aano vendathu"),
                                         (53.75, 56.30, "SWIPE LEFT", "idathuvashaththekk swipe"),
                                         (56.30, 59.40, "TAP THE CLOCK", "clock icon select cheyyuka"),
                                         (59.40, 64.10, "PICK A TIME", "samayam select cheythu reminder set")], 1):
    ev("step", rt(a, e), min(rt(b, e), e["F_end"] / FPS - 0.02), n=n, total=4, text=title, sub=sub)
    SFX.append(dict(type="pop", t=rt(a, e) + 0.06, gain=0.20))
SFX.append(dict(type="swish", t=rt(53.9, e), dur=0.5, gain=0.22))
SFX.append(dict(type="tap", t=rt(58.55, e), gain=0.22))

e = EX["f2a"]
chapter(2, e["F"], EX["f2b"]["F_end"] / FPS)
ev("kp", rt(116.55, e), rt(119.60, e), kicker="PROBLEM", text="NOISY PLACE?", sub="call varumbol surrounding noise")
ev("kp", rt(119.75, e), rt(122.78, e), kicker="PROBLEM", text="SURROUNDING NOISE", sub="call-il shallyam")
for t in (rt(116.55, e), rt(119.75, e)):
    SFX.append(dict(type="pop", t=t + 0.05, gain=0.18))

e = EX["f2b"]
t0 = e["F"] / FPS
ev("path", t0 + 0.18, t0 + 2.2, kicker="THE SETTING", lines=["Settings › Accessibility", "Audio & Visual › Voice Isolation"])
ev("voice", t0 + 3.62, e["F_end"] / FPS - 0.02, kicker="THE RESULT", text="ONLY YOUR VOICE", sub="ningal parayunna shabdam mathram")
SFX.append(dict(type="pop", t=t0 + 0.25, gain=0.22))
SFX.append(dict(type="tap", t=t0 + (152.10 - 150.9), gain=0.26))
SFX.append(dict(type="toggle", t=t0 + (152.10 - 150.9), gain=0.34))
SFX.append(dict(type="chime", t=t0 + (152.12 - 150.9) + 0.05, gain=0.24))
SFX.append(dict(type="riser", t0=t0 + 2.9, t1=t0 + 3.62, gain=0.30))
SFX.append(dict(type="impact", t=t0 + 3.62, gain=0.50, big=False))

e = EX["f3a"]
chapter(3, e["F"], EX["f3b"]["F_end"] / FPS)
ev("kp", rt(174.60, e), rt(177.35, e), kicker="PROBLEM", text="CALL ON HOLD?", sub="avar unhold cheyyunnathu vare...")
ev("kp", rt(177.50, e), rt(180.95, e), kicker="THE IDEA", text="NO NEED TO WAIT", sub="kaathirikkendathilla")
for t in (rt(174.60, e), rt(177.50, e)):
    SFX.append(dict(type="pop", t=t + 0.05, gain=0.18))

e = EX["f3b"]
ev("kp", rt(229.05, e), rt(231.75, e), kicker="THE SETTING", text="HOLD ASSIST", sub="More › Hold Assist")
ev("kp", rt(231.90, e), rt(234.50, e), kicker="THE RESULT", text="ACCEPT & TALK", sub="unhold aakumbol ring cheyyum")
for t in (rt(229.05, e), rt(231.90, e)):
    SFX.append(dict(type="pop", t=t + 0.05, gain=0.20))

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

# joins: whoosh centred in the transition
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
                   enumerate([("f1", "f1"), ("f2a", "f2b"), ("f3a", "f3b")], 1)])
json.dump(D, open(f"{HERE}/data/reel2_timeline.json", "w"), ensure_ascii=False, indent=1)
json.dump(dict(duration=L["duration"], words=words_out), open(f"{HERE}/data/reel2_words.json", "w"), indent=1)
json.dump(SHOTS, open(f"{HERE}/data/reel2_shots.json", "w"), indent=1)
json.dump(SFX, open(f"{HERE}/data/reel2_sfx.json", "w"), indent=1)
if __name__ == "__main__":
    print("shots", len(SHOTS), "events", len(EVENTS), "caption pages", len(pages), "sfx cues", len(SFX), "words", len(words_out))
    for s in SHOTS:
        print(f"  {s['id']:12s} {s['kind']:6s} F {s['F0']:5d}-{s['F1']:5d} (+{s['ext']}) {s['F0'] / 30:6.2f}-{s['F1'] / 30:6.2f} s  entrance={s['entrance']} fade={s['fade']}")
