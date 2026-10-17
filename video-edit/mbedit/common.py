"""Shared constants, easing helpers and script-timing lookups."""
import json
import math
import os
import re

import numpy as np

# Heavy intermediates (downloaded sources, mattes, renders) live outside the repo.
WORK = os.environ.get("MB_WORK", "/tmp/claude-0/-home-user-mega-bite/26b38b71-aae3-52a4-87d9-dbcdd593f3c0/scratchpad")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

W, H, FPS = 1920, 1080, 30
DUR = 247.6                       # length of the main video / narration
NF = int(round(DUR * FPS))        # 7428 frames

FONT_DIR = "/usr/share/fonts/opentype/inter"
FONT_BLACK = os.path.join(FONT_DIR, "Inter-Black.otf")
FONT_XBOLD = os.path.join(FONT_DIR, "Inter-ExtraBold.otf")
FONT_BOLD = os.path.join(FONT_DIR, "Inter-Bold.otf")
FONT_SEMI = os.path.join(FONT_DIR, "Inter-SemiBold.otf")

# brand palette (taken from the logo)
CYAN = (46, 214, 255)
BLUE = (30, 123, 255)
NAVY = (5, 12, 32)
SILVER = (222, 230, 240)


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t ** 3


def ease_in_out(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def ease_out_back(t, s=1.70158):
    t = clamp(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def ramp(t, t0, t1):
    """0 before t0, 1 after t1, linear in between"""
    return clamp((t - t0) / max(t1 - t0, 1e-9))


# ------------------------------------------------------------------ script timing
class Align:
    """Word-level timings of the Manglish script, force-aligned to the narration audio."""

    def __init__(self, path=None):
        d = json.load(open(path or os.path.join(DATA, "align.json"), encoding="utf8"))
        self.cues = {c["idx"]: c for c in d["cues"]}
        self.words = d["words"]
        self.by_cue = {}
        for w in self.words:
            self.by_cue.setdefault(w["cue"], []).append(w)

    def cue_range(self, cue):
        ws = self.by_cue[cue]
        return ws[0]["start"], ws[-1]["end"]

    def find(self, cue, pattern, nth=0, end=False):
        """start (or end) time of the nth word of `cue` containing `pattern` (case-insensitive)"""
        hits = [w for w in self.by_cue[cue] if pattern.lower() in re.sub(r"[^\w\-']", "", w["text"].lower()) or pattern.lower() in w["text"].lower()]
        if not hits:
            raise KeyError(f"cue {cue}: no word like {pattern!r}")
        w = hits[nth]
        return w["end"] if end else w["start"]


def rgb_to_bgr(c):
    return (c[2], c[1], c[0])
