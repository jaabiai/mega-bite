"""Frame compositor for the vertical Reel (1080x1920, 30 fps, song seconds 104.0 - 155.0).

frame n  ->  reel time n/30  ->  song time 104.0 + n/30.   A frame is a pure function of n (deterministic, chunkable).
Pipeline per frame: vertical procedural scene(s) at 720x1280 -> hook effects (shake / flash / chroma / red vignette) -> bloom -> grade
-> 1.5x upscale to 1080x1920 -> vertical typography at full resolution -> 0.2 s fade-in / 0.3 s fade-out of the PICTURE only.
"""
import rl_common  # noqa: F401  (must be first)
import json
import math
import os
import sys
from collections import OrderedDict

import numpy as np
from PIL import Image

from rl_common import CLIP_START, CLIP_END, FPS, NFRAMES, ROOT
from hl_common import W, H, WW, WH, clamp, smooth
import hl_scenes as SC
import hl_post as PP
from hl_audio import Audio, compute as compute_audio
import rl_timeline as T
from rl_text import ReelText

TIMING = os.environ.get("RL_TIMING", os.path.join(ROOT, "output_hinglish_landscape", "lyric_timing_hinglish.json"))   # read-only
WORK = os.environ.get("RL_WORK", os.path.join(ROOT, "reels", "work"))
SOURCE = os.environ.get("RL_SOURCE_MP4", os.path.join(ROOT, "output_hinglish_landscape", "Chalo_Jantar_Mantar_Hinglish_Landscape_1080p.mp4"))
FADE_IN, FADE_OUT = 0.20, 0.30


def translate(img, dx, dy):
    dx, dy = int(round(dx)), int(round(dy))
    return img if (dx == 0 and dy == 0) else np.roll(img, (dy, dx), axis=(0, 1))


def lerp_grade(a, b, k):
    out = {}
    for key in set(a) | set(b):
        va, vb = a.get(key), b.get(key)
        va = vb if va is None else va
        vb = va if vb is None else vb
        out[key] = tuple(va[i] + (vb[i] - va[i]) * k for i in range(len(va))) if isinstance(va, tuple) else va + (vb - va) * k
    return out


def vwhip(a, b, p, t):
    """Whip pan along the vertical axis (a slides up and out, b slides up in) with vertical motion blur."""
    d = int(smooth(p) * WH)
    if d <= 0:
        out = a.copy()
    elif d >= WH:
        out = b.copy()
    else:
        out = np.empty_like(a)
        out[:WH - d] = a[d:]
        out[WH - d:] = b[:d]
    amt = math.sin(math.pi * clamp(p))
    if amt > 0.05:
        out = PP.box_blur_h(out.transpose(1, 0, 2), 1 + int(amt * 110)).transpose(1, 0, 2)
        out = out * (1.0 + 0.25 * amt)
    return out


class Reel:
    def __init__(self, timing=TIMING):
        d = json.load(open(timing, encoding="utf-8"))
        self.lines = d["lines"]
        self.text = ReelText(self.lines, CLIP_START, CLIP_END)
        os.makedirs(WORK, exist_ok=True)
        npz = os.path.join(WORK, "audio_features.npz")
        if not os.path.exists(npz):
            compute_audio(SOURCE, npz)
        self.audio = Audio(npz)
        self.trans = T.transitions()
        self._scenes = OrderedDict()

    def scene(self, i):
        if i not in self._scenes:
            if len(self._scenes) >= 3:
                self._scenes.popitem(last=False)
            self._scenes[i] = SC.Scene(T.SHOTS[i]["spec"], seed=T.SHOTS[i]["seed"])
        else:
            self._scenes.move_to_end(i)
        return self._scenes[i]

    def shot_index(self, t):
        for i in range(len(T.SHOTS)):
            t0, t1 = T.shot_times(i)
            if t0 <= t < t1:
                return i
        return len(T.SHOTS) - 1 if t >= T.shot_times(len(T.SHOTS) - 1)[0] else 0

    def _render_shot(self, i, t, kick):
        t0, t1 = T.shot_times(i)
        return self.scene(i).render(t - t0, clamp((t - t0) / max(0.1, t1 - t0)), kick)

    def background(self, t, kick):
        for a, b, kind, ts, te in self.trans:
            if ts <= t < te:
                p = (t - ts) / (te - ts)
                ia, ib = self._render_shot(a, t, kick), self._render_shot(b, t, kick)
                img = vwhip(ia, ib, p, t) if kind == "vwhip" else PP.transition(ia, ib, kind, p, t)
                g = lerp_grade(T.GRADES[T.SHOTS[a]["grade"]], T.GRADES[T.SHOTS[b]["grade"]], smooth(p))
                return img, g
        i = self.shot_index(t)
        return self._render_shot(i, t, kick), T.GRADES[T.SHOTS[i]["grade"]]

    def render_frame(self, n):
        tr = n / FPS
        t = CLIP_START + tr
        kick = self.audio.kick(t)
        fx = self.text.effects(t)
        img, g = self.background(t, kick)
        g = dict(g)
        if fx["flash"]:
            r, gg, b, a = fx["flash"]
            img = img + np.array([r, gg, b], np.float32) / 255.0 * a * 1.6
        shx, shy = fx["shake"]
        if abs(shx) > 0.4 or abs(shy) > 0.4:
            img = translate(img, shx * (WW / W), shy * (WH / H))
        if fx["chroma"]:
            img = PP.chroma(img, int(fx["chroma"]))
        if fx["vig_red"] > 0.01:
            g["tint"] = (1.0 + 0.35 * fx["vig_red"], 1.0 - 0.18 * fx["vig_red"], 1.0 - 0.22 * fx["vig_red"])
            g["vig"] = g.get("vig", 0.8) + 0.22 * fx["vig_red"]
        img = PP.bloom(img, 0.72, 0.26 + 0.10 * kick + 0.5 * fx["bloom"], streak=0.07 + 0.2 * fx["bloom"])
        img = PP.grade(img, g)
        frame = PP.upscale(PP.to_uint8_dither(img, n))
        self.text.draw(frame, t, fx["shake"])
        # picture fade (the audio is never touched): in over the first 0.2 s, out over the last 0.3 s - text included
        fade = smooth(tr / FADE_IN) * (1.0 - smooth((tr - (CLIP_END - CLIP_START - FADE_OUT)) / FADE_OUT))
        if fade < 0.999:
            frame = (frame.astype(np.float32) * fade).astype(np.uint8)
        return frame


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "preview":
        out = sys.argv[2]
        os.makedirs(out, exist_ok=True)
        r = Reel()
        import time
        for tt in sys.argv[3:]:
            t = float(tt)                                   # SONG seconds
            s = time.time()
            n = int(round((t - CLIP_START) * FPS))
            fr = r.render_frame(n)
            Image.fromarray(fr).save(f"{out}/r_{t:08.3f}.png")
            print(f"song t={t:8.3f}s (frame {n})  {time.time() - s:5.2f}s  {fr.shape}")


if __name__ == "__main__":
    main()
