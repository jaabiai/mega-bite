#!/usr/bin/env python3
"""MEGABYTE – compositor.  Renders the picture track (no audio) frame by frame and pipes it into x264.

usage:
  render.py --out video.mp4 [--start 0 --end 107.7] [--scale 1]
  render.py --frames 1.5,12.8,30 --out-dir previews/     (PNG stills for design checks)
"""
import argparse, math, os, subprocess, sys, time
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))

def _project_dir():
    for i, a in enumerate(sys.argv):
        if a == "--project" and i + 1 < len(sys.argv):
            return os.path.join(HERE, "projects", sys.argv[i + 1])
    sys.exit("--project NAME is required (a folder under projects/)")


sys.path.insert(0, _project_dir())
import brand, grade, scene as scene_mod, graphics as G, graphics_calls as GC, timeline as TL, captions_data as CD, phonescene
from caption import render_caption
from gfx import blend, ease_io, ease_out, clamp01, lerp

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True, help="folder under projects/ with timeline.py, captions_data.py, screen_rules.py")
ap.add_argument("--face", required=True)
ap.add_argument("--screen", required=True, help="cleaned 60 fps screen recording; frame 0 == --screen-t0")
ap.add_argument("--screen-t0", type=float, default=TL.SCREEN_T0)
ap.add_argument("--broll-dir", required=True)
ap.add_argument("--palette", default="volt")
ap.add_argument("--scale", type=int, default=1)
ap.add_argument("--out", default=None)
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float, default=TL.TOTAL)
ap.add_argument("--frames", default=None)
ap.add_argument("--out-dir", default=None)
ap.add_argument("--crf", type=int, default=17)
ap.add_argument("--preset", default="medium")
args = ap.parse_args()

S = args.scale
W, H = 1920 * S, 1080 * S
FPS = TL.FPS
PAL = brand.PALETTES[args.palette]
ACC = np.array(brand.hex2rgb(PAL["accent"]), np.float32) / 255
BG0 = np.array(brand.hex2rgb(PAL["bg0"]), np.float32) / 255


# ---------------------------------------------------------------------------------------------- readers
class SeekReader:
    """Sequential raw-RGB reader that restarts ffmpeg when asked for an out-of-order / far frame."""

    def __init__(self, path, w, h, fps, vf, t_off=0.0, jump=90):
        self.path, self.w, self.h, self.fps, self.vf, self.t_off, self.jump = path, w, h, fps, vf, t_off, jump
        self.proc, self.pos, self.cur = None, -10 ** 9, None
        self.size = w * h * 3

    def _start(self, idx):
        self.close()
        t = self.t_off + idx / self.fps
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", self.path, "-vf", self.vf,
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.size * 2)
        self.pos = idx - 1

    def get(self, idx):
        idx = max(int(idx), 0)
        if idx == self.pos and self.cur is not None:
            return self.cur
        if self.proc is None or idx < self.pos or idx > self.pos + self.jump:
            self._start(idx)
        while self.pos < idx:
            buf = self.proc.stdout.read(self.size)
            if len(buf) < self.size:
                self.pos = idx
                break
            self.cur = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
            self.pos += 1
        return self.cur

    def close(self):
        if self.proc is not None:
            try:
                self.proc.stdout.close()
                self.proc.kill()
                self.proc.wait()
            except Exception:
                pass
            self.proc = None


FACE_W, FACE_H = 2560, 1440
face_reader = SeekReader(args.face, FACE_W, FACE_H, 30.0, f"scale={FACE_W}:{FACE_H}:flags=lanczos")
screen_reader = SeekReader(args.screen, 1320, 2868, 60.0, "null", t_off=0.0, jump=240)
N_SCREEN = int(round((TL.SCREEN_END - args.screen_t0) * 60)) - 1
PHONE_T0 = next(sc["t0"] for sc in TL.SCENES if sc["kind"] == "phone")
_broll = {}


def broll_reader(name, clip, clip_t):
    if name not in _broll:
        path = os.path.join(args.broll_dir, f"{clip}.mp4")
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos:in_color_matrix=bt709,"
              f"crop={W}:{H},fps=30")
        _broll[name] = SeekReader(path, W, H, 30.0, vf, t_off=clip_t, jump=60)
    return _broll[name]


# ---------------------------------------------------------------------------------------------- assets
ps = phonescene.PhoneScene(S, PAL, W, H)
bg_plain = scene_mod.background(W, H, PAL, glow_center=(0.70, 0.5))
bg_end = scene_mod.background(W, H, PAL, glow_center=(0.30, 0.45), glow_r=0.7, seed=9)
_scrim_cache = {}


def left_scrim(fr, strength=0.80, width=0.52):
    key = (fr.shape[1], strength, width)
    if key not in _scrim_cache:
        xs = np.linspace(0, 1, fr.shape[1], dtype=np.float32)
        _scrim_cache[key] = (np.clip(1 - xs / width, 0, 1) ** 1.5 * strength)[None, :, None]
    a = _scrim_cache[key]
    fr[:] = fr * (1 - a) + BG0[None, None, :] * a
    return fr


# ---------------------------------------------------------------------------------------------- scenes
FACE_ANCHOR = dict(fx=TL.FACE_ANCHOR["fx"], fy=TL.FACE_ANCHOR["fy"], tx=0.665, ty=0.44)


def scene_face(T, sc):
    z0, z1 = sc["zoom"]
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = lerp(z0, z1, ease_io(prog))
    src = face_reader.get(int(round(T * 30)))
    a = FACE_ANCHOR
    x0 = min(max(a["fx"] - a["tx"] / z, 0.0), 1 - 1 / z)
    y0 = min(max(a["fy"] - a["ty"] / z, 0.0), 1 - 1 / z)
    sc_ = z * W / FACE_W
    M = np.array([[sc_, 0, -x0 * FACE_W * sc_], [0, sc_, -y0 * FACE_H * sc_]], np.float32)
    out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC if sc_ >= 0.98 else cv2.INTER_LINEAR)
    fr = out.astype(np.float32) / 255.0
    cx, cy = (a["fx"] - x0) * z, (a["fy"] - y0) * z
    fr = grade.grade(fr, grain=0.010, rng=np.random.default_rng(int(T * 30)), face=(cx, cy - 0.03, 0.22, 0.36), **getattr(TL, "GRADE", {}))
    left_scrim(fr, 0.80, 0.52)
    return fr


def scene_broll(T, sc):
    rd = broll_reader(sc["name"], sc["clip"], sc["clip_t"])
    src = rd.get(int(round((T - sc["t0"]) * 30)))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = 1.04 + 0.08 * prog
    M = np.array([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H / 2]], np.float32)
    out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    fr = out.astype(np.float32) / 255.0
    luma = (fr * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    fr = fr * 0.55 + luma * 0.45                              # calm the colours
    fr = np.clip((fr - 0.5) * 1.08 + 0.5 - 0.04, 0, 1)
    tint = np.array(brand.hex2rgb(PAL["bg1"]), np.float32) / 255
    fr = fr * (1 - 0.22 * (1 - luma)) + tint[None, None, :] * 0.22 * (1 - luma)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.45 * np.clip((np.hypot((xx / W - 0.5) * 1.15, (yy / H - 0.5)) - 0.35) / 0.6, 0, 1) ** 1.4
    fr = fr * vig[..., None]
    left_scrim(fr, 0.78, 0.55)
    return np.clip(fr, 0, 1)


def scene_phone(T):
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - args.screen_t0) * 60)), 0), N_SCREEN)
    screen = screen_reader.get(idx)
    cam = phonescene.cam_at(T, TL.CAMERA)
    enter = ease_out((T - PHONE_T0) / 0.75)
    g = ps.geometry(cam, extra=((1 - enter) * 0.30 * W, 0.0))
    sway = 4.0 * S * math.sin(2 * math.pi * T / 6.5)
    fr = ps.render(screen, g, opacity=min(1.0, enter * 1.6), sway=sway)
    g["sway"] = sway
    return fr, g


GRAPHIC_LAY = {
    "call-log": dict(cx=1290, top=190, card_w=640, row_h=92, head_h=112, rows=6),
    "face-unlock": dict(cx=1290, cy=480, tile=270, face=260, gap=250, pill_size=32),
}


def scene_graphic(T, sc):
    t, g = T - sc["t0"], sc.get("graphic", "search-lock")
    if g == "call-log":
        return GC.render_call_log(t, S, PAL, bg_plain, lay=GRAPHIC_LAY[g])
    if g == "face-unlock":
        return GC.render_face_unlock(t, S, PAL, bg_plain, lay=GRAPHIC_LAY[g])
    return G.render_search_lock(t, S, PAL, bg_plain)


def _spans(v):
    return v if isinstance(v[0], (tuple, list)) else [v]


def scene_at(T):
    for sc in TL.SCENES:
        if sc["t0"] <= T < sc["t1"]:
            return sc
    return TL.SCENES[-1]


# ---------------------------------------------------------------------------------------------- overlays
CHUNK_STARTS = [c[0] for c in CD.CHUNKS]
REVEAL_T0 = TL.REVEAL_T0          # logo sting


def active_chunk(T):
    best = None
    for i, c in enumerate(CD.CHUNKS):
        if c[0] - 0.02 <= T:
            best = i
    if best is None:
        return None
    c = CD.CHUNKS[best]
    nxt = CD.CHUNKS[best + 1][0] if best + 1 < len(CD.CHUNKS) else 1e9
    if T > c[1] + 0.30 and T < nxt:
        return None
    return best


def draw_caption_overlay(fr, T, kind):
    i = active_chunk(T)
    if i is None or kind == "end":
        return
    c = CD.CHUNKS[i]
    wt = CD.word_times(c)
    words = [w for w, _, _ in wt]
    act = -1
    age = 1.0
    for k, (_, ws, we) in enumerate(wt):
        if T >= ws:
            act, age = k, T - ws
    fin = clamp01((T - c[0] + 0.02) / 0.16)
    fout = 1.0 - clamp01((T - (c[1] + 0.12)) / 0.18)
    nxt_start = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
    if nxt_start - c[0] < 0.5:
        fout = 1.0
    pop = 1.0 + 0.11 * max(0.0, 1 - age / 0.17)
    if kind == "phone":
        size, mw, top = 66, 700, 440
    else:
        size, mw, top = 64, 580, 560 if T < TL.TITLE_T[1] + 0.4 else 430
    img, ox, oy, bh = render_caption(words, act if act >= 0 else -1, PAL, S=S, max_w=mw, size=size, pop=pop)
    slide = (1 - ease_out(fin)) * 16 * S
    blend(fr, img, 96 * S + ox, top * S + oy + slide, fin * fout)


def draw_overlays(fr, T, sc, geo):
    kind = sc["kind"]
    if kind != "end":
        bug_a = ease_out((T - 0.15) / 0.5)
        r0 = REVEAL_T0
        if r0 <= T < r0 + 2.6:                         # logo sting: bug hidden while the big logo is on screen
            bug_a = ease_io((T - (r0 + 1.95)) / 0.6) if T > r0 + 1.95 else 0.0
        G.draw_logo_bug(fr, S, PAL, alpha=bug_a)
        G.draw_logo_reveal(fr, S, PAL, T - REVEAL_T0)
    if T < TL.TITLE_T[1]:
        G.draw_title(fr, S, PAL, T - TL.TITLE_T[0], lay=dict(lines=TL.TITLE_LINES))
    # step chip + highlights + taps
    if kind == "phone":
        for (t0, t1, n, label) in TL.STEPS:
            if t0 <= T < t1:
                fin = ease_out((T - t0) / 0.35)
                fout = 1 - ease_io((T - (t1 - 0.25)) / 0.25)
                G.draw_step_chip(fr, S, PAL, n, TL.N_STEPS, label, x=96, y=336, alpha=min(fin, fout), slide=(1 - fin) * -40)
        for (t0, t1, (u0, v0, u1, v1)) in TL.HIGHLIGHTS:
            if t0 - 0.2 <= T <= t1 + 0.25:
                x0, y0 = ps.to_out(geo, u0, v0)
                x1, y1 = ps.to_out(geo, u1, v1)
                y0 += geo.get("sway", 0); y1 += geo.get("sway", 0)
                a = ease_out((T - (t0 - 0.2)) / 0.3) * (1 - ease_io((T - t1) / 0.25))
                G.draw_ring(fr, S, PAL, (x0, y0, x1, y1), T - t0, alpha=a)
        for (tt, u, v) in TL.TAPS:
            if tt - 0.35 <= T <= tt + 0.9:
                x, y = ps.to_out(geo, u, v)
                G.draw_tap(fr, S, PAL, x, y + geo.get("sway", 0), T - tt)
    for (a, b) in _spans(TL.SUBSCRIBE_T):
        if a <= T < b:
            G.draw_subscribe(fr, S, PAL, T - a, x=96, y=870)
    for (a, b) in _spans(TL.SHARE_T):
        if a <= T < b:
            G.draw_share(fr, S, PAL, T - a, x=96, y=870)
    draw_caption_overlay(fr, T, kind)


# ---------------------------------------------------------------------------------------------- frame
def render_frame(T):
    sc = scene_at(T)
    kind = sc["kind"]
    geo = None
    if kind == "face":
        fr = scene_face(T, sc)
    elif kind == "broll":
        fr = scene_broll(T, sc)
    elif kind == "graphic":
        fr = scene_graphic(T, sc)
    elif kind == "phone":
        fr, geo = scene_phone(T)
    else:
        fr = G.render_end_card(T - sc["t0"], S, PAL, bg_end)
    draw_overlays(fr, T, sc, geo)
    for (tt, tk) in TL.TRANSITIONS:
        if tk == "wipe" and tt - 0.30 <= T <= tt + 0.30:
            G.apply_wipe(fr, (T - (tt - 0.30)) / 0.60, PAL, S)
        if tk == "zoom" and abs(T - tt) < 0.16:
            fr = G.zoom_punch(fr, 0.22 * (1 - abs(T - tt) / 0.16) ** 2)
    return np.clip(fr, 0, 1)


def main():
    if args.frames:
        os.makedirs(args.out_dir, exist_ok=True)
        for t in [float(x) for x in args.frames.split(",")]:
            t0 = time.time()
            fr = render_frame(t)
            cv2.imwrite(os.path.join(args.out_dir, f"f_{t:07.3f}.png"), cv2.cvtColor((fr * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
            print(f"T={t:7.3f}  {time.time() - t0:5.2f}s", flush=True)
        return
    n0, n1 = int(round(args.start * FPS)), int(round(args.end * FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-pix_fmt", "yuv420p",
                            "-profile:v", "high", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    t_start = time.time()
    for n in range(n0, n1):
        T = n / FPS
        fr = render_frame(T)
        enc.stdin.write((fr * 255 + 0.5).astype(np.uint8).tobytes())
        if (n - n0) % 60 == 0:
            el = time.time() - t_start
            done = n - n0 + 1
            eta = el / done * (n1 - n0 - done)
            print(f"T={T:7.2f}  {done}/{n1 - n0}  elapsed {el:6.0f}s  eta {eta:6.0f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    print("done", args.out)


if __name__ == "__main__":
    main()
