"""Edit decision list for the 9:16 Reels / Shorts cut (~57 s) of the 'free AI video generator' episode.

The reel re-uses the long video's narration (cut at word boundaries), screen-recording time-warp and highlight list.
Times in CLIPS are *source* (narration) times; the reel timeline is their concatenation.
"""
from mbedit.common import Align, FPS
from mbedit.reel import ReelTH, ReelBroll, ReelDemo, EndCard, RW, RH
from mbedit.overlays import Headline, CountUp, SubscribeCTA, Logo, Dim
from mbedit.captions import build_chunks, CaptionRenderer
from mbedit.timeline import Timeline
import edl

A = edl.A
WORDS = A.words                                  # time ordered
TAIL = 1.9                                       # silent end-card hold after the last word

# kind, (approx) source start/end, options.   join=True -> starts exactly where the previous clip ended
CLIPS = [
    dict(kind="th", a=0.0, b=3.19, zoom=(1.0, 1.07), cx=0.5),                            # hook: "Ningalkku AI upayogichu free aayi niravadhi videokal generate cheyyano"
    dict(kind="broll", a=3.19, b=5.85, join=True, clip="99786", start=0.4),              # "Innu atharathilulla oru website aanu"
    dict(kind="th", a=23.9, b=27.85, zoom=(1.0, 1.07), cx=0.5),                          # "Oru thavana login cheythu kazhinjal 100 videokalolam"
    dict(kind="demo", a=57.36, b=59.9),                                                  # site name
    dict(kind="demo", a=68.8, b=74.3),                                                   # sign up with Google
    dict(kind="demo", a=107.4, b=109.9),                                                 # select Generate videos
    dict(kind="demo", a=113.8, b=118.4),                                                 # free, 100 videos per day
    dict(kind="demo", a=122.2, b=125.75),                                                # sign-in + commercial use
    dict(kind="demo", a=142.55, b=147.85),                                               # prompt + image made with ChatGPT, pasted
    dict(kind="demo", a=154.6, b=156.6),                                                 # add the photo
    dict(kind="demo", a=159.3, b=162.9),                                                 # Fast / Quality
    dict(kind="demo", a=195.2, b=200.0),                                                 # click Generate
    dict(kind="demo", a=204.4, b=207.9),                                                 # 6 min 30 sec
    dict(kind="demo", a=219.1, b=223.75),                                                # the result
    dict(kind="th", a=243.7, b=247.35, zoom=(1.0, 1.1), cx=0.52, last=True),             # subscribe, thank you
]


def _snap_start(a):
    i = min(range(len(WORDS)), key=lambda k: abs(WORDS[k]["start"] - a))
    w = WORDS[i]
    gap = w["start"] - WORDS[i - 1]["end"] if i > 0 else 0.2
    return max(w["start"] - min(0.07, max(gap / 2, 0.0)), 0.0)


def _snap_end(b):
    i = min(range(len(WORDS)), key=lambda k: abs(WORDS[k]["end"] - b))
    w = WORDS[i]
    gap = WORDS[i + 1]["start"] - w["end"] if i + 1 < len(WORDS) else 0.3
    return w["end"] + min(0.14, max(gap / 2, 0.0))


def plan():
    out, r = [], 0.0
    for k, c in enumerate(CLIPS):
        a = out[-1]["b"] if c.get("join") else _snap_start(c["a"])
        b = _snap_end(c["b"])
        d = dict(c, a=a, b=b, r0=r, r1=r + (b - a), k=k)
        out.append(d)
        r += b - a
    return out, r


PLAN, SPEECH_END = plan()
TOTAL = SPEECH_END + TAIL


def rt(src_t):
    """source time -> reel time (within the clip that contains it)"""
    for c in PLAN:
        if c["a"] - 1e-6 <= src_t <= c["b"] + 1e-6:
            return c["r0"] + (src_t - c["a"])
    raise ValueError(src_t)


class _ReelAlign:
    def __init__(self):
        self.by_cue = {}
        for c in PLAN:
            ws = [dict(text=w["text"], start=c["r0"] + w["start"] - c["a"], end=c["r0"] + w["end"] - c["a"])
                  for w in WORDS if c["a"] - 1e-6 <= w["start"] and w["end"] <= c["b"] + 1e-6]
            if ws:
                self.by_cue[c["k"] * 1000 + 1] = ws


def audio_cuts():
    """merged (a, b) cuts of the narration, in reel order"""
    cuts = []
    for c in PLAN:
        if cuts and c.get("join"):
            cuts[-1][1] = c["b"]
        else:
            cuts.append([c["a"], c["b"]])
    return cuts


TITLES = {"THERE'S AN AI FOR THAT": ("THE WEBSITE", "AI SITE NAME")}
CAMS = [
    (120.9, 127.3, edl.R_B_SIGNIN[:2] + (edl.R_B_COMM[0] + edl.R_B_COMM[2] - edl.R_B_SIGNIN[0], edl.R_B_SIGNIN[3])),      # sign-in + commercial pills side by side
    (112.9, 120.9, (edl.R_B_FREE[0], edl.R_B_FREE[1], edl.R_B_100[0] + edl.R_B_100[2] - edl.R_B_FREE[0], edl.R_B_FREE[3])),  # free + 100 videos per day
]


def build():
    hls_all = sorted((h for st in edl.DEMO_STEPS for h in st.hls), key=lambda h: h.t0)
    scenes = []
    for c in PLAN:
        r0, r1 = c["r0"], c["r1"] + (TAIL if c.get("last") else 0)
        if c["kind"] == "th":
            scenes.append(ReelTH(r0, r1, c["a"], zoom=c.get("zoom", (1.0, 1.06)), cx=c.get("cx", 0.5)))
        elif c["kind"] == "broll":
            scenes.append(ReelBroll(r0, r1, c["clip"], start=c.get("start", 0.4)))
        else:
            scenes.append(ReelDemo(r0, r1, c["a"], edl.DEMO, hls_all, cam=CAMS, titles=TITLES))
    p = {c["k"]: c for c in PLAN}
    layers = []
    # hook
    layers.append(Headline(0.12, p[0]["r1"], [[("FREE", 1)], [("AI VIDEOS", 0)]], size=124, anchor="center", cx=RW / 2, y=215, shade=0,
                           delays=[0.35, rt(A.find(1, "videokal")) - 0.1]))
    layers.append(Headline(p[1]["r0"] + 0.05, p[1]["r1"], [[("NEW", 0), ("AI", 1)], [("WEBSITE", 1)]], size=150, anchor="center", cx=RW / 2, y=640, shade=0,
                           delays=[p[1]["r0"] + 0.12, p[1]["r0"] + 0.4, rt(A.find(2, "website"))]))
    # 100 videos per login
    t100 = rt(A.find(8, "100"))
    layers.append(CountUp(t100 - 0.55, p[2]["r1"], 100, size=300, x=RW / 2, y=400))
    layers.append(Headline(t100 + 0.1, p[2]["r1"], [[("VIDEOS", 0)], [("PER LOGIN", 1)]], size=96, anchor="center", cx=RW / 2, y=670, shade=0,
                           delays=[rt(A.find(8, "videokalolam")), rt(A.find(8, "videokalolam")) + 0.3]))
    # end card
    last = p[len(PLAN) - 1]
    e0 = last["r0"] + 0.15
    layers.append(Dim(e0, TOTAL + 1, 0.5, fade=0.35))
    layers.append(EndCard(e0, TOTAL))
    layers.append(SubscribeCTA(last["r0"] + 0.05, TOTAL + 2, cx=RW / 2, cy=1325, scale=0.62, click=0.8))
    logo = Logo(reveal=(e0, 9999), corner=(105, 160), corner_size=132, center=(RW / 2, 330, 330))
    captions = CaptionRenderer(build_chunks(_ReelAlign(), lambda t: "reel", max_words=3))
    return Timeline(scenes, {}, layers, captions, logo)
