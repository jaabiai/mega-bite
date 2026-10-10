"""Frame compositor for the Hinglish landscape lyric video (1920x1080, 30 fps): procedural shots + transitions + grade + typography."""
import json, math, os, sys
from collections import OrderedDict
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hl_common import *
import hl_scenes as SC, hl_post as PP, hl_timeline as T
from hl_text import TextEngine
from hl_audio import Audio, compute as compute_audio

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))                  # chalo_jantar_mantar/
TIMING = os.environ.get("HL_TIMING", os.path.join(ROOT, "output_hinglish_landscape", "lyric_timing_hinglish.json"))
WORK = os.environ.get("HL_WORK", os.path.join(ROOT, "work_hl"))
SOURCE = os.environ.get("HL_SOURCE_MP4", os.path.join(ROOT, "src", "original.mp4"))


def translate(img, dx, dy):
    dx, dy = int(round(dx)), int(round(dy))
    if dx == 0 and dy == 0:
        return img
    out = np.roll(img, (dy, dx), axis=(0, 1))
    return out


def lerp_grade(a, b, k):
    out = {}
    for key in set(a) | set(b):
        va, vb = a.get(key), b.get(key)
        if va is None: va = vb
        if vb is None: vb = va
        if isinstance(va, tuple):
            out[key] = tuple(va[i] + (vb[i] - va[i]) * k for i in range(len(va)))
        else:
            out[key] = va + (vb - va) * k
    return out


class Renderer:
    def __init__(self, timing=TIMING, audio_npz=None):
        d = json.load(open(timing, encoding="utf-8"))
        self.lines = d["lines"]
        self.text = TextEngine(self.lines)
        os.makedirs(WORK, exist_ok=True)
        audio_npz = audio_npz or os.path.join(WORK, "audio_features.npz")
        if not os.path.exists(audio_npz):
            compute_audio(SOURCE, audio_npz)
        self.audio = Audio(audio_npz)
        self.trans = T.transitions()
        self._scenes = OrderedDict()

    def scene(self, i):
        if i not in self._scenes:
            if len(self._scenes) >= 3:
                self._scenes.popitem(last=False)
            self._scenes[i] = SC.Scene(T.SHOTS[i]["spec"], seed=i + 1)
        else:
            self._scenes.move_to_end(i)
        return self._scenes[i]

    def shot_index(self, t):
        for i in range(len(T.SHOTS)):
            t0, t1 = T.shot_times(i)
            if t0 <= t < t1 or i == len(T.SHOTS) - 1:
                return i
        return 0

    def _render_shot(self, i, t, kick):
        t0, t1 = T.shot_times(i)
        tl = t - t0
        u = clamp(tl / max(0.1, t1 - t0))
        return self.scene(i).render(tl, u, kick)

    def background(self, t, kick):
        """Returns (float image at working res, grade dict)."""
        for a, b, kind, ts, te in self.trans:
            if ts <= t < te:
                p = (t - ts) / (te - ts)
                ia = self._render_shot(a, t, kick)
                ib = self._render_shot(b, t, kick)
                img = PP.transition(ia, ib, kind, p, t)
                g = lerp_grade(T.GRADES[T.SHOTS[a]["grade"]], T.GRADES[T.SHOTS[b]["grade"]], smooth(p))
                return img, g
        i = self.shot_index(t)
        return self._render_shot(i, t, kick), T.GRADES[T.SHOTS[i]["grade"]]

    def render_frame(self, n):
        t = n / FPS
        kick = self.audio.kick(t)
        fx = self.text.effects(t)
        img, g = self.background(t, kick)
        g = dict(g)
        # ---- hook effects on the background -----------------------------------------------------------------------------
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
            g["vig"] = g.get("vig", 0.8) + 0.5 * fx["vig_red"]
        # bloom (beat-reactive, stronger during hooks)
        img = PP.bloom(img, 0.72, 0.26 + 0.10 * kick + 0.5 * fx["bloom"], streak=0.18 + 0.4 * fx["bloom"])
        img = PP.grade(img, g)
        frame = PP.upscale(PP.to_uint8_dither(img, n))
        # ---- typography (full resolution) -------------------------------------------------------------------------------
        self.text.draw(frame, t, fx["shake"])
        self.text.apply_bars(frame, fx["bars"])
        return frame


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "preview":
        out = sys.argv[2]
        os.makedirs(out, exist_ok=True)
        r = Renderer()
        import time
        for tt in sys.argv[3:]:
            t = float(tt)
            s = time.time()
            fr = r.render_frame(int(round(t * FPS)))
            Image.fromarray(fr).save(f"{out}/f_{t:08.3f}.png")
            print(f"t={t:8.3f}s  {time.time()-s:5.2f}s")


if __name__ == "__main__":
    main()
