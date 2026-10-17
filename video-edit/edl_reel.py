"""Edit decision list for the 9:16 Reels / Shorts cut.

One continuous take of the narration (source 0 - 60 s) with a single invisible edit: the second "subscribe" sentence
(source 11.66 - 14.52 s, "Appol anganeyullava labhikkanayi ippol thanne subscribe cheythu vecholoo.") is removed.
Both splice points sit in true room-tone silence (-55 dBFS) and the B-roll change lands exactly on the splice, so it reads as
a normal sentence break.  The on-screen follow message the creator asked for is shown at the (single) subscribe moment.

All times below are written in SOURCE time (the long video's timeline) and mapped to reel time with S().
"""
from mbedit.common import FPS
from mbedit.reel import ReelTH, ReelBroll, ReelDemo, ReelEnd, EndCard, vtransition, RW, RH
from mbedit.overlays import Headline, CountUp, SubscribeCTA, SpriteCard, Logo, Dim, TitleCard, LinkBelow
from mbedit.captions import build_chunks, CaptionRenderer
from mbedit.timeline import Timeline
import edl

A = edl.A

CUT_A, CUT_B = 11.66, 14.52        # removed span of the narration (source time)
SHIFT = CUT_B - CUT_A              # 2.86 s
SPEECH_END_SRC = 60.0              # last word ends 59.88; true silence 59.95-60.20
AUDIO_END_SRC = 60.08
END_CARD = 2.6
GAIN_DB = 4.0                      # louder than the original by this much (peak limiter only, no compression)


def S(t):
    """source time -> reel time"""
    return t if t <= CUT_A + 1e-9 else t - SHIFT


def T(cue, word, nth=0, end=False):
    return S(A.find(cue, word, nth, end))


SPEECH_END = S(SPEECH_END_SRC)
TOTAL = SPEECH_END + END_CARD


def audio_cuts():
    """narration spans (source time) that are kept, in order"""
    return [[0.0, CUT_A], [CUT_B, AUDIO_END_SRC]]


# --------------------------------------------------------------------------- scenes: (kind, src t0, src t1, options, transition INTO the scene)
SCENES = [
    ("th",    0.00, 3.26, dict(zoom=(1.0, 1.07)),                                   None),
    ("broll", 3.26, 5.78, dict(clip="99786", start=0.4, zoom=(1.0, 1.1)),           ("zoom", 0.45)),
    ("th",    5.78, 14.64, dict(zoom=(1.0, 1.09), hold_src=CUT_A),                  ("push", 0.45)),      # ends on the splice
    ("broll", 14.64, 20.88, dict(clip="1781", start=0.6, zoom=(1.0, 1.12), cx=0.45), ("swipe", 0.5)),
    ("th",    20.88, 27.84, dict(zoom=(1.12, 1.02)),                                ("fade", 0.4)),
    ("broll", 27.84, 31.20, dict(clip="4908", start=0.6, zoom=(1.0, 1.1), cx=0.4),  ("push", 0.45)),
    ("th",    31.20, 34.50, dict(zoom=(1.08, 1.16)),                                ("fade", 0.35)),
    ("broll", 34.50, 39.28, dict(clip="44074", start=2.0, zoom=(1.0, 1.1), cx=0.55), ("zoom", 0.45)),
    ("th",    39.28, 50.15, dict(zoom=(1.0, 1.12)),                                 ("fade", 0.4)),
    ("broll", 50.15, 54.14, dict(clip="41279", start=1.0, zoom=(1.35, 1.45), cx=0.3, cy=0.72), ("swipe", 0.5)),   # swipe hides the camera cut in the footage at 50.4 s
    ("demo",  54.14, SPEECH_END_SRC, dict(),                                        ("zoom", 0.55)),
    ("end",   SPEECH_END_SRC, None, dict(freeze=47.6),                              ("fade", 0.55)),
]

PLAN = []
for _i, (_k, _a, _b, _o, _tr) in enumerate(SCENES):
    PLAN.append(dict(kind=_k, r0=S(_a), r1=(S(_b) if _b is not None else TOTAL), k=_i))

TITLES = {"THERE'S AN AI FOR THAT": ("THE WEBSITE", "THE SITE NAME")}


class _Words:
    """aligned words of the kept script cues, in reel time (the removed sentence, cue 5, is dropped)"""

    def __init__(self):
        self.by_cue = {}
        for c, ws in A.by_cue.items():
            if ws[-1]["end"] > SPEECH_END_SRC or (ws[0]["start"] >= CUT_A - 0.05 and ws[-1]["end"] <= CUT_B + 0.05):
                continue                                    # past the take, or inside the removed sentence
            self.by_cue[c] = [dict(text=w["text"], start=S(w["start"]), end=S(w["end"])) for w in ws]


def build():
    hls_all = sorted((h for st in edl.DEMO_STEPS for h in st.hls), key=lambda h: h.t0)
    scenes, trans = [], {}
    for i, (kind, a, b, o, tr) in enumerate(SCENES):
        r0 = S(a)
        r1 = S(b) if b is not None else TOTAL
        if kind == "th":
            scenes.append(ReelTH(r0, r1, a, zoom=o.get("zoom", (1.0, 1.06)), cx=o.get("cx", 0.5), hold_src=o.get("hold_src")))
        elif kind == "broll":
            scenes.append(ReelBroll(r0, r1, o["clip"], start=o.get("start", 0.4), zoom=o.get("zoom", (1.0, 1.1)), cx=o.get("cx", 0.5), cy=o.get("cy", 0.5)))
        elif kind == "demo":
            scenes.append(ReelDemo(r0, r1, a, edl.DEMO, hls_all, cam=(), titles=TITLES))
        else:
            scenes.append(ReelEnd(r0, r1, o["freeze"]))
        if tr:
            trans[i] = tr

    C = RW / 2
    s_ = S
    L = []
    # ---- hook
    L.append(Headline(0.12, 3.3, [[("AI", 1), ("FREE", 0)], [("VIDEOS", 1)]], size=140, anchor="center", cx=C, y=200, shade=0,
                      delays=[T(1, "AI"), T(1, "free"), T(1, "videokal") - 0.05]))
    L.append(Headline(3.3, 5.85, [[("NEW", 0), ("AI", 1)], [("WEBSITE", 1)]], size=150, anchor="center", cx=C, y=640, shade=0,
                      delays=[3.38, 3.75, T(2, "website")]))
    L.append(Headline(6.2, 8.9, [[("USEFUL", 1)], [("VIDEOS", 0)]], size=140, anchor="center", cx=C, y=200, shade=0,
                      delays=[T(3, "useful"), T(3, "videokal")]))
    # ---- the one and only subscribe moment: FOLLOW button + the creator's follow message (on screen)
    ts = T(3, "subscribe")
    L.append(SubscribeCTA(ts - 1.25, ts + 2.0, cx=C, cy=985, scale=0.74, click=1.25, normal="cta_follow", done="cta_following"))
    L.append(SpriteCard("reel_follow_ml", ts + 0.05, CUT_A - 0.05, cx=C, cy=1215, scale=1.0))
    L.append(Headline(9.7, 11.6, [[("MANY", 0), ("MORE", 1)], [("VIDEOS", 0)]], size=120, anchor="center", cx=C, y=200, shade=0,
                      delays=[10.0, 10.2, 10.36]))
    # ---- what makes it different
    L.append(Headline(s_(15.2), s_(20.9), [[("DIFFERENT", 1)], [("FROM OTHER", 0)], [("PLATFORMS", 1)]], size=118, anchor="center", cx=C, y=540, shade=0,
                      delays=[s_(15.2), s_(16.7), s_(17.12)]))
    L.append(CountUp(s_(25.45), s_(28.0), 100, size=240, x=C, y=200))
    L.append(Headline(s_(25.9), s_(28.0), [[("VIDEOS", 0), ("PER LOGIN", 1)]], size=80, anchor="center", cx=C, y=300, shade=0,
                      delays=[T(8, "videokalolam"), T(8, "videokalolam") + 0.3]))
    L.append(Headline(s_(28.1), s_(31.3), [[("MANY", 0), ("ACCOUNTS", 1)], [("MANY", 0), ("VIDEOS", 1)]], size=96, anchor="center", cx=C, y=600, shade=0,
                      delays=[s_(28.1), T(9, "accountukal"), s_(29.5), T(9, "niravadhi", 1)]))
    L.append(Headline(s_(33.2), s_(34.6), [[("HIGH", 0)], [("QUALITY", 1)]], size=150, anchor="center", cx=C, y=215, shade=0,
                      delays=[T(9, "high"), T(9, "qualityil")]))
    L.append(Headline(s_(35.2), s_(39.3), [[("GOOGLE", 1), ("FLOW", 1)], [("& OTHER SITES", 0)]], size=100, anchor="center", cx=C, y=560, shade=0,
                      delays=[T(10, "google"), T(10, "flow"), T(10, "websitilokke") - 0.4]))
    L.append(Headline(s_(39.4), s_(43.7), [[("SAME", 0)], [("QUALITY", 1)], [("OR", 0), ("BETTER", 1)]], size=112, anchor="center", cx=C, y=200, shade=0,
                      delays=[s_(39.4), T(11, "qualityil"), T(11, "athinekkal"), T(11, "mikachathu")]))
    L.append(Headline(s_(44.7), s_(46.6), [[("HOW", 0), ("TO USE", 1)], [("IT?", 1)]], size=140, anchor="center", cx=C, y=200, shade=0,
                      delays=[s_(44.8), s_(45.1), s_(45.7)]))
    # ---- welcome (logo flies to the top while "Welcome to Mega Byte" is said)
    L.append(Dim(s_(46.4), s_(49.5), 0.5))
    L.append(TitleCard(s_(46.75), s_(49.5), "WELCOME TO", "MEGA BYTE", y=1190, cx=C, scale=0.95))
    # ---- link in description
    L.append(Headline(s_(51.0), s_(54.15), [[("LINK IN", 0)], [("DESCRIPTION", 1)]], size=112, anchor="center", cx=C, y=300, shade=0,
                      delays=[T(15, "link"), T(15, "descriptionil")]))
    L.append(LinkBelow(s_(52.0), s_(54.15), cx=C, cy=860, scale=0.9))
    # ---- end card (no second subscribe prompt: just the channel name + "full video on YouTube")
    e0 = SPEECH_END + 0.1
    L.append(EndCard(e0, TOTAL))

    logo = Logo(reveal=[(s_(46.4), s_(49.1), (C, 270, 330)), (e0 + 0.15, 9999, (C, 330, 330))], corner=(105, 160), corner_size=132)
    chunks = build_chunks(_Words(), lambda t: "reel", max_words=3)
    chunks[-1].t1_disp = min(chunks[-1].t1_disp, SPEECH_END)           # nothing but the end card after the last word
    return Timeline(scenes, trans, L, CaptionRenderer(chunks), logo, tfn=vtransition)
