"""Reel v2 - overview of ALL THREE iOS 27 features in one short reel.

Structure (every excerpt is a whole spoken sentence or two, cut on the quietest point between sentences):
  hook   : "iPhone upayogikkunnavarkku moonnu kidilan feature-ukalaanu ..."          (what the video is about)
  F1     : Miss Call Reminder   - swipe left -> clock icon -> pick a time
  F2     : Voice Isolation      - noisy place problem  +  "only your voice is heard"
  F3     : Hold Assist          - call on hold problem +  "it rings when unheld, accept and talk"
  outro  : "these three options are all very useful"  +  "subscribe"

Between excerpts the picture changes with a chapter transition (push-in dissolve + 01/02/03 card), never a hard cut,
and the narration is never cut inside a sentence.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
FR = 1600           # samples per 30 fps frame
FPS = 30

CHAPTERS = ["", "MISS CALL REMINDER", "VOICE ISOLATION", "HOLD ASSIST", ""]
FEATURES = [("01", "MISS CALL REMINDER"), ("02", "VOICE ISOLATION"), ("03", "HOLD ASSIST")]

EXCERPT_SETS = {
    # v2: every feature as a short demo walk-through
    "reel2": [
        dict(id="hook",  cues=[1],             chapter=0),
        dict(id="f1",    cues=[15, 16, 17, 18], chapter=1),
        dict(id="f2a",   cues=[31, 32],        chapter=2),
        dict(id="f2b",   cues=[42],            chapter=2),
        dict(id="f3a",   cues=[46],            chapter=3),
        dict(id="f3b",   cues=[59],            chapter=3),
        dict(id="recap", cues=[61],            chapter=4),
        dict(id="cta",   cues=[63],            chapter=4),
    ],
    # v3: the lines where he announces each feature ("first ...", "next ...", "third ...") + one result line, no demo
    "reel3": [
        dict(id="hook",  cues=[1],             chapter=0),
        dict(id="f1a",   cues=[11, 12],        chapter=1),
        dict(id="f1b",   cues=[24],            chapter=1),
        dict(id="f2a",   cues=[30, 31],        chapter=2),
        dict(id="f2b",   cues=[34],            chapter=2),
        dict(id="f2c",   cues=[42],            chapter=2),
        dict(id="f3a",   cues=[45, 46],        chapter=3),
        dict(id="f3b",   cues=[59],            chapter=3),
        dict(id="recap", cues=[61],            chapter=4),
        dict(id="cta",   cues=[63],            chapter=4),
    ],
}
TAG = os.environ.get("REEL_TAG", "reel2")      # which reel the tools work on: data/<TAG>_*.json, scratch/<TAG>/...
EXCERPTS = EXCERPT_SETS[TAG]

# gap (seconds) between the last word of one excerpt and the first word of the next
GAP_CHAPTER = 0.46
GAP_SAME = 0.34
TAIL = 1.25          # end-card tail after the last word
XF = 9               # frames of the push-in dissolve
LAYOUT_FILE = f"{HERE}/data/{TAG}_layout.json"


def load_cuts():
    return json.load(open(f"{HERE}/data/{TAG}_cuts.json"))


def build_layout():
    """frame/sample placement of every excerpt on the reel timeline"""
    cuts = load_cuts()
    lay = []
    prev = None
    for ex in EXCERPTS:
        c = cuts[ex["id"]]
        s0, s1 = c["s0"], c["s1"]
        f0 = round(s0 / FR)                       # source frame shown at reel frame F
        if prev is None:
            F = 0
        else:
            gap = GAP_CHAPTER if ex["chapter"] != prev["chapter"] else GAP_SAME
            # words of the previous excerpt end at (A + last_word - s0); keep `gap` seconds before the next first word
            prev_last = prev["A"] + (prev["last_word_end"] * SR - prev["s0"])
            need_first = prev_last + gap * SR
            # A_next = F*FR + (s0 - f0*FR);  first word at A_next + (first_word*SR - s0)
            off = s0 - f0 * FR
            F = int(-(-(need_first - (c["first_word"] * SR - s0) - off) // FR))
        A = F * FR + (s0 - f0 * FR)
        item = dict(ex, s0=s0, s1=s1, f0=f0, F=F, A=A, first_word=c["first_word"], last_word_end=c["last_word_end"])
        item["D"] = (A - s0) / SR                 # reel_seconds = main_seconds + D
        lay.append(item)
        prev = item
    last = lay[-1]
    audio_end = last["A"] + (last["s1"] - last["s0"])
    n_frames = int(-(-(audio_end + TAIL * SR) // FR))
    for i, it in enumerate(lay):
        it["F_end"] = lay[i + 1]["F"] if i + 1 < len(lay) else n_frames
    out = dict(excerpts=lay, n_frames=n_frames, duration=n_frames / FPS)
    json.dump(out, open(LAYOUT_FILE, "w"), indent=1)
    return out


def load_layout():
    return json.load(open(LAYOUT_FILE))


if __name__ == "__main__":
    L = build_layout()
    print("frames", L["n_frames"], "duration %.2f s" % L["duration"])
    for e in L["excerpts"]:
        print(f"  {e['id']:6s} F {e['F']:5d}-{e['F_end']:5d} ({e['F'] / 30:6.2f}-{e['F_end'] / 30:6.2f} s)  src frame {e['f0']:5d}  D={e['D']:+8.3f}")
