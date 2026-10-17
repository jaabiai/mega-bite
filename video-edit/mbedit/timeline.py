"""Assemble scenes + transitions + overlays + captions + logo into final frames."""
import bisect

import numpy as np

from .common import FPS, NF, W, H
from .scenes import transition, DemoScene


class Timeline:
    def __init__(self, scenes, trans, layers, captions, logo, tfn=None):
        """scenes: sorted by t0; trans[i] = (kind, duration) for the boundary between scene i-1 and i (centred on scenes[i].t0)"""
        self.scenes, self.trans, self.layers, self.captions, self.logo = scenes, trans, layers, captions, logo
        self.tfn = tfn or transition
        self.starts = [s.t0 for s in scenes]

    def zone_at(self, t):
        for s in self.scenes:
            if isinstance(s, DemoScene) and s.t0 <= t < s.t1:
                return "left"
        return "full"

    def _scene_frame(self, ctx, t):
        k = max(bisect.bisect_right(self.starts, t) - 1, 0)
        # transition towards the next scene (second half of its window) ...
        if k + 1 < len(self.scenes):
            kind, d = self.trans.get(k + 1, ("cut", 0.0))
            ts = self.scenes[k + 1].t0 - d / 2
            if d > 0 and t >= ts:
                a = self.scenes[k].render(ctx, t)
                b = self.scenes[k + 1].render(ctx, t)
                return self.tfn(kind, a, b, (t - ts) / d)
        # ... or away from the previous scene (first half of this scene's window)
        if k > 0:
            kind, d = self.trans.get(k, ("cut", 0.0))
            ts = self.scenes[k].t0 - d / 2
            if d > 0 and t < ts + d:
                a = self.scenes[k - 1].render(ctx, t)
                b = self.scenes[k].render(ctx, t)
                return self.tfn(kind, a, b, (t - ts) / d)
        return self.scenes[k].render(ctx, t)

    def frame(self, ctx, i):
        t = i / FPS
        f = self._scene_frame(ctx, t)
        f = np.array(f) if not f.flags.writeable else f
        for lay in self.layers:
            if lay.active(t):
                f = lay.draw(f, t)
        f = self.captions.draw(f, t)
        f = self.logo.draw(f, t)
        ctx.gc(t, self.scenes)
        return f
