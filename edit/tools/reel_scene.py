"""9:16 version of the "Voice Isolation" iPhone demo (scene S2).

Re-uses the narration-synced retiming, highlights, tracked rows and taps of scenes.S2 and only swaps the staging:
the recording is shown in a large rounded viewport (920x820) with a virtual camera that pushes in on whatever is being
tapped, on the brand background, with room above for the step card and below for the captions.

usage: reel_scene.py render <out.mp4>
       reel_scene.py dump <outdir> t1 t2 ...          (main-timeline seconds)
"""
import copy
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import screen_scene as ss  # noqa: E402
import scenes  # noqa: E402

CW, CH = 1080, 1920
WIN_W, WIN_H = 920, 820
WIN_X, WIN_Y = 80, 440
RADIUS = 58

ss.CW, ss.CH = CW, CH
ss.WIN_W, ss.WIN_H, ss.WIN_X, ss.WIN_Y = WIN_W, WIN_H, WIN_X, WIN_Y
ss.UI = 1.55
ss._YY, ss._XX = np.mgrid[0:WIN_H, 0:WIN_W].astype(np.float32)

SRC_W, SRC_H = ss.SRC_W, ss.SRC_H


def K(t, cx, cy, z):
    return (t, cx, cy, z)


CAMERA = [
    K(131.60, 660, 1950, 1.00),
    K(132.25, 770, 2000, 1.14),      # tap Settings
    K(133.30, 660, 2050, 1.00),
    K(135.40, 660, 2050, 1.00),
    K(136.15, 660, 2046, 1.14),      # tap Accessibility
    K(137.20, 660, 2100, 1.00),
    K(140.00, 660, 2250, 1.00),
    K(140.90, 660, 2290, 1.10),      # Audio & Visual highlighted
    K(144.05, 660, 2300, 1.14),      # tap Audio & Visual
    K(145.20, 660, 1960, 1.00),
    K(150.20, 660, 1960, 1.00),
    K(151.40, 640, 2070, 1.08),      # Voice Isolation row
    K(152.10, 620, 2100, 1.15),      # toggle
    K(154.95, 620, 2100, 1.18),
]


def spec():
    sp = copy.deepcopy(scenes.S2)
    sp["t1"] = 155.20                 # hold the final state so the next B-roll can cross-fade in over it
    sp["camera"] = CAMERA
    sp["pip"] = False
    return sp


def make_background():
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    top, bot = np.array([13, 14, 22], np.float32), np.array([6, 7, 11], np.float32)
    g = (yy / CH)[..., None]
    bg = top * (1 - g) + bot * g

    def glow(cx, cy, rx, ry, col, a):
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        return np.exp(-d)[..., None] * (np.array(col, np.float32) * a)

    bg += glow(120, 360, 700, 520, (255, 150, 20), 0.17)
    bg += glow(980, 1500, 760, 620, (255, 40, 110), 0.15)
    bg += glow(540, 960, 600, 900, (40, 60, 120), 0.10)
    bg += ((xx % 40 < 2) & (yy % 40 < 2)).astype(np.float32)[..., None] * 9
    return np.clip(bg, 0, 255).astype(np.uint8)


class ReelScene(ss.Scene):
    def __init__(self, sp=None, name="reel_S2"):
        self.sp = sp if sp is not None else spec()
        self.name = name
        self.t0, self.t1 = self.sp["t0"], self.sp["t1"]
        self.N = int(round((self.t1 - self.t0) * ss.FPS))
        self.layers = ss.Layers()
        self.layers.bg = make_background()
        self.layers.win_mask = ss.rounded_mask(WIN_W, WIN_H, RADIUS)[..., None]
        pad = self.layers.pad
        patch = np.zeros((WIN_H + 2 * pad, WIN_W + 2 * pad), np.float32)
        patch[pad:pad + WIN_H, pad:pad + WIN_W] = ss.rounded_mask(WIN_W, WIN_H, RADIUS)
        self.layers.shadow = cv2.GaussianBlur(patch, (0, 0), 30) * 0.8
        self.layers.glow = cv2.GaussianBlur(patch, (0, 0), 22) * 0.9
        grown = cv2.dilate(patch, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        self.layers.rim = np.clip(cv2.GaussianBlur(grown, (0, 0), 0.8) - patch, 0, 1)
        self.tracks = {}
        for key, tr in self.sp.get("tracks", {}).items():
            self.tracks[key] = ss.track_rows(tr["ref_r"], tr["rect"], tr["ra"], tr["rb"])

    def compose(self, src, pip, t, r):
        L = self.layers
        canvas = L.bg.copy()
        px, py = WIN_X - L.pad, WIN_Y - L.pad
        L.blend_patch(canvas, px, py + 18, L.shadow, (0, 0, 0))
        L.blend_patch(canvas, px, py, L.glow * 0.42, ss.AMBER * 0.9)
        win = self.window_image(src, t, r)
        reg = canvas[WIN_Y:WIN_Y + WIN_H, WIN_X:WIN_X + WIN_W].astype(np.float32)
        canvas[WIN_Y:WIN_Y + WIN_H, WIN_X:WIN_X + WIN_W] = (reg * (1 - L.win_mask) + win * L.win_mask).astype(np.uint8)
        L.blend_patch(canvas, px, py, L.rim, ss.AMBER)
        return canvas

    def decode_pip(self):                    # no speaker picture-in-picture in the reel
        while True:
            yield None

    def render(self, out):
        import subprocess
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW}x{CH}",
                                "-r", str(ss.FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
                                "-g", "30", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                                "-color_trc", "bt709", out], stdin=subprocess.PIPE)
        cur, gen = -1, None
        for n in range(self.N):
            t = self.t0 + n / ss.FPS
            i, r = self.seg_at(t)
            if i != cur:
                gen, cur = self.decode_seg_from(i, t), i
            src = next(gen)
            enc.stdin.write(self.compose(src, None, t, r).tobytes())
            if n % 150 == 0:
                print(f"{self.name}: {n}/{self.N}", flush=True)
        enc.stdin.close()
        enc.wait()

    def frames(self):
        """generator of finished RGB frames (so a caller can add effects before encoding)"""
        cur, gen = -1, None
        for n in range(self.N):
            t = self.t0 + n / ss.FPS
            i, r = self.seg_at(t)
            if i != cur:
                gen, cur = self.decode_seg_from(i, t), i
            yield self.compose(next(gen), None, t, r)

    def decode_seg_from(self, i, t_start):
        """like decode_seg, but starts at main time t_start inside segment i (windowed renders)"""
        import subprocess
        a, b, r0, sp = self.sp["segs"][i]
        ts = min(max(t_start, a), b)
        r_start = r0 + (ts - a) * sp
        n = max(int(round((b - ts) * ss.FPS)), 1)
        vf = "scale=990:2151:flags=area"
        vf = (f"setpts=PTS/{sp},fps=30," if abs(sp - 1) > 1e-6 else "fps=30,") + vf
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{r_start:.4f}", "-i", ss.SCREEN, "-frames:v", str(n + 2),
                              "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        fs = 990 * 2151 * 3
        last = None
        while True:
            buf = p.stdout.read(fs)
            if len(buf) < fs:
                break
            last = np.frombuffer(buf, np.uint8).reshape(2151, 990, 3)
            yield last
        while True:
            yield last


def window_scene(name, m0, m1, camera, focus_extra=()):
    """vertical scene for the main-timeline window [m0, m1] of recording scene `name` ('S1' or 'S2')"""
    sp = copy.deepcopy(getattr(scenes, name))
    sp["t0"], sp["t1"], sp["camera"], sp["pip"] = m0, m1, camera, False
    sp["focus"] = list(sp.get("focus", [])) + list(focus_extra)
    return ReelScene(sp, f"reel_{name}")

    def frame_at(self, t):
        i, r = self.seg_at(t)
        import subprocess
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{r:.4f}", "-i", ss.SCREEN, "-frames:v", "1",
                              "-vf", "scale=990:2151:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        src = np.frombuffer(raw, np.uint8).reshape(2151, 990, 3)
        return self.compose(src, None, t, r)


if __name__ == "__main__":
    sc = ReelScene()
    if sys.argv[1] == "render":
        sc.render(sys.argv[2])
    else:
        os.makedirs(sys.argv[2], exist_ok=True)
        for tt in sys.argv[3:]:
            cv2.imwrite(f"{sys.argv[2]}/rS2_{float(tt):07.2f}.png", cv2.cvtColor(sc.frame_at(float(tt)), cv2.COLOR_RGB2BGR))
