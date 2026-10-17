"""Edit decision list for the 9:16 Reels / Shorts cut: ONE continuous take of the narration (0 - 60 s), no audio cuts.

The window starts with the hook and ends on the sentence "'There Is An AI For That' ennaanu sitinte peru." followed by a
true-silence gap in the recording (59.95-60.20 s), so both the start and the end are natural.  Visuals change with smooth
transitions; after the last word a ~2.6 s end card says "full video on YouTube - MEGA BYTE".
"""
from mbedit.common import FPS
from mbedit.reel import ReelTH, ReelBroll, ReelDemo, ReelEnd, EndCard, vtransition, RW, RH
from mbedit.overlays import Headline, CountUp, SubscribeCTA, Logo, Dim, TitleCard, LinkBelow
from mbedit.captions import build_chunks, CaptionRenderer
from mbedit.timeline import Timeline
import edl

A = edl.A
T = edl.T

SPEECH_END = 60.0                 # last word ends 59.88; true silence 59.95-60.20
AUDIO_END = 60.08                 # audio cut point (inside the silence)
END_CARD = 2.6
TOTAL = SPEECH_END + END_CARD


def audio_cuts():
    """the only cut: end of the take (start is 0.0 - the recording starts on the first word)"""
    return [[0.0, AUDIO_END]]


# --------------------------------------------------------------------------- scenes: (kind, t0, t1, options, transition INTO the scene)
SCENES = [
    ("th",    0.00, 3.26, dict(zoom=(1.0, 1.07)),                                   None),
    ("broll", 3.26, 5.78, dict(clip="99786", start=0.4, zoom=(1.0, 1.1)),           ("zoom", 0.45)),
    ("th",    5.78, 14.64, dict(zoom=(1.0, 1.13)),                                  ("push", 0.45)),
    ("broll", 14.64, 20.88, dict(clip="1781", start=0.6, zoom=(1.0, 1.12), cx=0.45), ("swipe", 0.5)),
    ("th",    20.88, 27.84, dict(zoom=(1.12, 1.02)),                                ("fade", 0.4)),
    ("broll", 27.84, 31.20, dict(clip="4908", start=0.6, zoom=(1.0, 1.1), cx=0.4),  ("push", 0.45)),
    ("th",    31.20, 34.50, dict(zoom=(1.08, 1.16)),                                ("fade", 0.35)),
    ("broll", 34.50, 39.28, dict(clip="44074", start=2.0, zoom=(1.0, 1.1), cx=0.55), ("zoom", 0.45)),
    ("th",    39.28, 50.15, dict(zoom=(1.0, 1.12)),                                 ("fade", 0.4)),
    ("broll", 50.15, 54.14, dict(clip="41279", start=1.0, zoom=(1.35, 1.45), cx=0.3, cy=0.72), ("swipe", 0.5)),   # swipe hides the camera cut in the footage at 50.4 s
    ("demo",  54.14, SPEECH_END, dict(),                                            ("zoom", 0.55)),
    ("end",   SPEECH_END, TOTAL, dict(freeze=47.6),                                 ("fade", 0.55)),
]

PLAN = [dict(kind=k, r0=a, r1=b, k=i) for i, (k, a, b, o, tr) in enumerate(SCENES)]

TITLES = {"THERE'S AN AI FOR THAT": ("THE WEBSITE", "THE SITE NAME")}


class _CueSubset:
    """aligned words of the script cues that fall inside the take (1..17), same time base as the source"""

    def __init__(self):
        self.by_cue = {c: ws for c, ws in A.by_cue.items() if ws[-1]["end"] <= SPEECH_END}


def build():
    hls_all = sorted((h for st in edl.DEMO_STEPS for h in st.hls), key=lambda h: h.t0)
    scenes, trans = [], {}
    for i, (kind, a, b, o, tr) in enumerate(SCENES):
        if kind == "th":
            scenes.append(ReelTH(a, b, a, zoom=o.get("zoom", (1.0, 1.06)), cx=o.get("cx", 0.5)))
        elif kind == "broll":
            scenes.append(ReelBroll(a, b, o["clip"], start=o.get("start", 0.4), zoom=o.get("zoom", (1.0, 1.1)), cx=o.get("cx", 0.5), cy=o.get("cy", 0.5)))
        elif kind == "demo":
            scenes.append(ReelDemo(a, b, a, edl.DEMO, hls_all, cam=(), titles=TITLES))
        else:
            scenes.append(ReelEnd(a, b, o["freeze"]))
        if tr:
            trans[i] = tr

    C = RW / 2
    L = []
    # ---- hook
    L.append(Headline(0.12, 3.3, [[("AI", 1), ("FREE", 0)], [("VIDEOS", 1)]], size=140, anchor="center", cx=C, y=200, shade=0,
                      delays=[T(1, "AI"), T(1, "free"), T(1, "videokal") - 0.05]))
    L.append(Headline(3.3, 5.85, [[("NEW", 0), ("AI", 1)], [("WEBSITE", 1)]], size=150, anchor="center", cx=C, y=640, shade=0,
                      delays=[3.38, 3.75, T(2, "website")]))
    L.append(Headline(6.2, 8.9, [[("USEFUL", 1)], [("VIDEOS", 0)]], size=140, anchor="center", cx=C, y=200, shade=0,
                      delays=[T(3, "useful"), T(3, "videokal")]))
    L.append(SubscribeCTA(T(3, "subscribe") - 1.25, T(3, "subscribe") + 1.9, cx=C, cy=1190, scale=0.85))
    L.append(Headline(9.7, 11.7, [[("MANY", 0), ("MORE", 1)], [("VIDEOS", 0)]], size=120, anchor="center", cx=C, y=200, shade=0,
                      delays=[10.0, 10.2, 10.36]))
    L.append(SubscribeCTA(T(5, "subscribe") - 1.25, T(5, "subscribe") + 1.9, cx=C, cy=1190, scale=0.85))
    # ---- what makes it different
    L.append(Headline(15.2, 20.9, [[("DIFFERENT", 1)], [("FROM OTHER", 0)], [("PLATFORMS", 1)]], size=118, anchor="center", cx=C, y=540, shade=0,
                      delays=[15.2, 16.7, 17.12]))
    L.append(CountUp(25.45, 28.0, 100, size=240, x=C, y=200))
    L.append(Headline(25.9, 28.0, [[("VIDEOS", 0), ("PER LOGIN", 1)]], size=80, anchor="center", cx=C, y=300, shade=0,
                      delays=[T(8, "videokalolam"), T(8, "videokalolam") + 0.3]))
    L.append(Headline(28.1, 31.3, [[("MANY", 0), ("ACCOUNTS", 1)], [("MANY", 0), ("VIDEOS", 1)]], size=96, anchor="center", cx=C, y=600, shade=0,
                      delays=[28.1, T(9, "accountukal"), 29.5, T(9, "niravadhi", 1)]))
    L.append(Headline(33.2, 34.6, [[("HIGH", 0)], [("QUALITY", 1)]], size=150, anchor="center", cx=C, y=215, shade=0,
                      delays=[T(9, "high"), T(9, "qualityil")]))
    L.append(Headline(35.2, 39.3, [[("GOOGLE", 1), ("FLOW", 1)], [("& OTHER SITES", 0)]], size=100, anchor="center", cx=C, y=560, shade=0,
                      delays=[T(10, "google"), T(10, "flow"), T(10, "websitilokke") - 0.4]))
    L.append(Headline(39.4, 43.7, [[("SAME", 0)], [("QUALITY", 1)], [("OR", 0), ("BETTER", 1)]], size=112, anchor="center", cx=C, y=200, shade=0,
                      delays=[39.4, T(11, "qualityil"), T(11, "athinekkal"), T(11, "mikachathu")]))
    L.append(Headline(44.7, 46.6, [[("HOW", 0), ("TO USE", 1)], [("IT?", 1)]], size=140, anchor="center", cx=C, y=200, shade=0,
                      delays=[44.8, 45.1, 45.7]))
    # ---- welcome (logo flies to the centre while "Welcome to Mega Byte" is said)
    L.append(Dim(46.4, 49.5, 0.5))
    L.append(TitleCard(46.75, 49.5, "WELCOME TO", "MEGA BYTE", y=1190, cx=C, scale=0.95))
    # ---- link in description
    L.append(Headline(51.0, 54.15, [[("LINK IN", 0)], [("DESCRIPTION", 1)]], size=112, anchor="center", cx=C, y=300, shade=0,
                      delays=[T(15, "link"), T(15, "descriptionil")]))
    L.append(LinkBelow(52.0, 54.15, cx=C, cy=860, scale=0.9))
    # ---- end card
    e0 = SPEECH_END + 0.1
    L.append(EndCard(e0, TOTAL))
    L.append(SubscribeCTA(e0, TOTAL + 2, cx=C, cy=1325, scale=0.62, click=0.9))

    logo = Logo(reveal=[(46.4, 49.1, (C, 270, 330)), (e0 + 0.15, 9999, (C, 330, 330))], corner=(105, 160), corner_size=132)
    chunks = build_chunks(_CueSubset(), lambda t: "reel", max_words=3)
    chunks[-1].t1_disp = min(chunks[-1].t1_disp, SPEECH_END)           # nothing but the end card after the last word
    return Timeline(scenes, trans, L, CaptionRenderer(chunks), logo, tfn=vtransition)
