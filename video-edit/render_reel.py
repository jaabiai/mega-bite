#!/usr/bin/env python3
"""MEGABYTE – vertical 9:16 compositor (Instagram Reels / YouTube Shorts), 1080x1920.

Same timeline, captions, graphics and screen clean-up as render.py, re-laid-out for a phone screen:
captions sit clear of the platform UI (top 150 px / bottom ~400 px / right 120 px), the phone scenes are
stacked (steps + captions on top, big phone below), B-roll becomes a rounded card on a blurred backdrop.

usage:
  render_reel.py --face main.mp4 --screen screen_clean60.mp4 --broll-dir broll/ --out reel.mp4 [--start 0 --end 104.9]
  render_reel.py ... --frames 1.6,30,60 --out-dir stills/
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
import brand, grade, scene as scene_mod, graphics as G, timeline as TL, captions_data as CD, phonescene
from caption import render_caption
from gfx import blend, blend_glow, glow_of, ease_io, ease_out, clamp01, lerp, aa_shape

OUTRO = 3.2
TOTAL = TL.NARR_END + OUTRO
TL.SCENES[-1] = dict(kind="outro", t0=TL.NARR_END, t1=TOTAL, name="outro")

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True, help="folder under projects/")
ap.add_argument("--face", required=True)
ap.add_argument("--screen", required=True)
ap.add_argument("--screen-t0", type=float, default=TL.SCREEN_T0)
ap.add_argument("--broll-dir", required=True)
ap.add_argument("--palette", default="volt")
ap.add_argument("--out", default=None)
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float, default=TOTAL)
ap.add_argument("--frames", default=None)
ap.add_argument("--out-dir", default=None)
ap.add_argument("--crf", type=int, default=17)
ap.add_argument("--preset", default="medium")
args = ap.parse_args()

S = 1
W, H = 1080, 1920
FPS = TL.FPS
PAL = brand.PALETTES[args.palette]
BG0 = np.array(brand.hex2rgb(PAL["bg0"]), np.float32) / 255

# ---- layout constants (px in the 1080x1920 frame) --------------------------------------------------------------
BUG = (56, 120)
CAP_X, CAP_W = 64, 880
CAP_TOP_MAIN, CAP_SIZE_MAIN = 1230, 78
CAP_TOP_PHONE, CAP_SIZE_PHONE = 362, 70
CHIP_XY = (64, 238)
CTA_XY = (64, 256)
TITLE = dict(lines=TL.TITLE_LINES, size=84, step=96, x=70, y0=318)
LOCK = dict(cx=540, lock_y=380, lock_size=300, bar_y=900, bar_w=900, bar_h=124)
REVEAL = dict(big=300, x=64, y=250)
FACE_CARD = dict(x=28, y=520, w=1024, h=576, r=34)         # the main video, complete and uncropped (16:9)


class SeekReader:
    def __init__(self, path, w, h, fps, vf, t_off=0.0, jump=90):
        self.path, self.w, self.h, self.fps, self.vf, self.t_off, self.jump = path, w, h, fps, vf, t_off, jump
        self.proc, self.pos, self.cur = None, -10 ** 9, None
        self.size = w * h * 3

    def _start(self, idx):
        self.close()
        t = self.t_off + idx / self.fps
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", self.path, "-vf", self.vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
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
                self.proc.stdout.close(); self.proc.kill(); self.proc.wait()
            except Exception:
                pass
            self.proc = None


FW, FH = 3840, 2160
face_reader = SeekReader(args.face, FW, FH, 30.0, "null", jump=60)
screen_reader = SeekReader(args.screen, 1320, 2868, 60.0, "null", jump=240)
N_SCREEN = int(round((TL.SCREEN_END - args.screen_t0) * 60)) - 1
PHONE_T0 = next(sc["t0"] for sc in TL.SCENES if sc["kind"] == "phone")
_broll = {}


def broll_reader(name, clip, clip_t):
    """Vertical stock clip, scaled to cover the whole 1080x1920 frame."""
    if name not in _broll:
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos:in_color_matrix=bt709,"
              f"crop={W}:{H},fps=30")
        _broll[name] = SeekReader(os.path.join(args.broll_dir, f"{clip}.mp4"), W, H, 30.0, vf, t_off=clip_t, jump=60)
    return _broll[name]


ps = phonescene.PhoneScene(S, PAL, W, H, layout="reel")
bg_lock = scene_mod.background(W, H, PAL, glow_center=(0.5, 0.42))
bg_outro = scene_mod.background(W, H, PAL, glow_center=(0.5, 0.40), glow_r=0.8, seed=9)
_cache = {}


def vscrim(fr, y0, y1, strength, from_top=False):
    key = (fr.shape[0], y0, y1, strength, from_top)
    if key not in _cache:
        ys = np.arange(fr.shape[0], dtype=np.float32)
        a = np.clip((ys - y0) / max(y1 - y0, 1), 0, 1) if not from_top else np.clip((y1 - ys) / max(y1 - y0, 1), 0, 1)
        _cache[key] = ((a ** 1.4) * strength)[:, None, None]
    a = _cache[key]
    fr[:] = fr * (1 - a) + BG0[None, None, :] * a
    return fr


def header_band(fr, hold=560, end=730, strength=0.94):
    """Solid dark header (bug, step chip, captions) that fades out below `hold` – keeps text legible over a zoomed phone."""
    key = ("hb", fr.shape[0], hold, end, strength)
    if key not in _cache:
        ys = np.arange(fr.shape[0], dtype=np.float32)
        a = np.clip((end - ys) / max(end - hold, 1), 0, 1)
        _cache[key] = ((a * a * (3 - 2 * a)) * strength)[:, None, None]
    a = _cache[key]
    fr[:] = fr * (1 - a) + BG0[None, None, :] * a
    return fr


def card_mask(w, h, r):
    key = ("mask", w, h, r)
    if key not in _cache:
        m = aa_shape((w, h), lambda d, k: d.rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=r * k, fill=255))
        mm = np.asarray(m, np.float32)[..., None] / 255.0
        pad = 90
        big = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
        big[pad:pad + h, pad:pad + w] = mm[..., 0]
        _cache[key] = (mm, cv2.GaussianBlur(big, (0, 0), 28) * 0.6)
    return _cache[key]


# ---------------------------------------------------------------------------------------------- scenes
def backdrop_from(card, y_dark=0.42):
    """Blurred, darkened full-frame backdrop made from a card image (any aspect)."""
    h, w = card.shape[:2]
    scale = max(W / w, H / h)
    sw, sh = int(round(w * scale / 8)), int(round(h * scale / 8))
    small = cv2.resize(card, (max(sw, W // 8), max(sh, H // 8)), interpolation=cv2.INTER_AREA)
    ox, oy = (small.shape[1] - W // 8) // 2, (small.shape[0] - H // 8) // 2
    small = cv2.GaussianBlur(small[oy:oy + H // 8, ox:ox + W // 8], (0, 0), 4)
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC) * y_dark + BG0[None, None, :] * 0.30


def paste_card(bg, card, c):
    """Rounded card with drop shadow and a thin accent outline onto a float frame."""
    x, y, w, h, r = c["x"], c["y"], c["w"], c["h"], c["r"]
    mask, shadow = card_mask(w, h, r)
    pad = 90
    y0s, x0s = y - pad, x - pad
    sy0, sx0 = max(-y0s, 0), max(-x0s, 0)
    sy1, sx1 = min(shadow.shape[0], H - y0s), min(shadow.shape[1], W - x0s)
    bg[y0s + sy0:y0s + sy1, x0s + sx0:x0s + sx1] *= (1 - shadow[sy0:sy1, sx0:sx1, None])
    bg[y:y + h, x:x + w] = bg[y:y + h, x:x + w] * (1 - mask) + card * mask
    outline = np.clip(cv2.GaussianBlur(mask, (0, 0), 1.2)[..., None] - mask, 0, 1)
    acc = np.array(brand.hex2rgb(PAL["accent"]), np.float32) / 255
    bg[y:y + h, x:x + w] += outline * acc[None, None, :] * 0.5
    return bg


def scene_face(T, sc):
    """The main video stays complete (no crop): full 16:9 frame in a card, blurred copy of it as backdrop."""
    src = face_reader.get(int(round(T * 30)))
    c = FACE_CARD
    card = cv2.resize(src, (c["w"], c["h"]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    fx, fy = TL.FACE_ANCHOR["fx"], TL.FACE_ANCHOR["fy"]
    card = grade.grade(card, grain=0.008, rng=np.random.default_rng(int(T * 30)), face=(fx, fy - 0.02, 0.18, 0.30))
    bg = backdrop_from(card)
    paste_card(bg, card, c)
    return np.clip(bg, 0, 1)


def scene_broll(T, sc):
    """Vertical stock footage, full-bleed, graded to sit with the brand colours."""
    rd = broll_reader(sc["name"], sc["reel_clip"], sc.get("reel_clip_t", 0.0))
    src = rd.get(int(round((T - sc["t0"]) * 30)))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = 1.0 + 0.07 * prog
    M = np.array([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H / 2]], np.float32)
    fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255.0
    luma = (fr * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    fr = fr * 0.62 + luma * 0.38
    fr = np.clip((fr - 0.5) * 1.08 + 0.5 - 0.03, 0, 1)
    tint = np.array(brand.hex2rgb(PAL["bg1"]), np.float32) / 255
    fr = fr * (1 - 0.20 * (1 - luma)) + tint[None, None, :] * 0.20 * (1 - luma)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.40 * np.clip((np.hypot((xx / W - 0.5) * 1.5, (yy / H - 0.5) * 0.9) - 0.30) / 0.6, 0, 1) ** 1.4
    fr = fr * vig[..., None]
    vscrim(fr, 1050, 1560, 0.68)                       # calm area for the captions
    vscrim(fr, 100, 460, 0.55, from_top=True)
    return np.clip(fr, 0, 1)


def scene_phone(T):
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - args.screen_t0) * 60)), 0), N_SCREEN)
    screen = screen_reader.get(idx)
    cam = phonescene.cam_at(T, TL.CAMERA)
    enter = ease_out((T - PHONE_T0) / 0.75)
    g = ps.geometry(cam, extra=((1 - enter) * 0.40 * W, 0.0))
    sway = 4.0 * math.sin(2 * math.pi * T / 6.5)
    fr = ps.render(screen, g, opacity=min(1.0, enter * 1.6), sway=sway)
    g["sway"] = sway
    header_band(fr)                                     # readable caption area over a zoomed-in phone
    return fr, g


def scene_at(T):
    for sc in TL.SCENES:
        if sc["t0"] <= T < sc["t1"]:
            return sc
    return TL.SCENES[-1]


# ---------------------------------------------------------------------------------------------- overlays
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
    if i is None or kind == "outro":
        return
    c = CD.CHUNKS[i]
    wt = CD.word_times(c)
    words = [w for w, _, _ in wt]
    act, age = -1, 1.0
    for k, (_, ws, we) in enumerate(wt):
        if T >= ws:
            act, age = k, T - ws
    fin = clamp01((T - c[0] + 0.02) / 0.16)
    fout = 1.0 - clamp01((T - (c[1] + 0.12)) / 0.18)
    nxt_start = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
    if nxt_start - c[0] < 0.5:
        fout = 1.0
    pop = 1.0 + 0.11 * max(0.0, 1 - age / 0.17)
    size, top = (CAP_SIZE_PHONE, CAP_TOP_PHONE) if kind == "phone" else (CAP_SIZE_MAIN, CAP_TOP_MAIN)
    img, ox, oy, bh = render_caption(words, act, PAL, S=S, max_w=CAP_W, size=size, pop=pop)
    blend(fr, img, CAP_X + ox, top + oy + (1 - ease_out(fin)) * 18, fin * fout)


REVEAL_T0 = TL.REVEAL_T0


def draw_overlays(fr, T, sc, geo):
    kind = sc["kind"]
    if kind != "outro":
        bug_a = ease_out((T - 0.15) / 0.5)
        if REVEAL_T0 <= T < REVEAL_T0 + 2.6:
            bug_a = ease_io((T - (REVEAL_T0 + 1.95)) / 0.6) if T > REVEAL_T0 + 1.95 else 0.0
        G.draw_logo_bug(fr, S, PAL, alpha=bug_a, x=BUG[0], y=BUG[1])
        G.draw_logo_reveal(fr, S, PAL, T - REVEAL_T0, big=REVEAL["big"], x=REVEAL["x"], y=REVEAL["y"], bug=BUG)
    if T < TL.TITLE_T[1]:
        G.draw_title(fr, S, PAL, T - TL.TITLE_T[0], lay=TITLE)
    if kind == "phone":
        for (t0, t1, n, label) in TL.STEPS:
            if t0 <= T < t1:
                fin = ease_out((T - t0) / 0.35)
                fout = 1 - ease_io((T - (t1 - 0.25)) / 0.25)
                G.draw_step_chip(fr, S, PAL, n, TL.N_STEPS, label, x=CHIP_XY[0], y=CHIP_XY[1], alpha=min(fin, fout), slide=(1 - fin) * -40)
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
    if TL.SUBSCRIBE_T[0] <= T < TL.SUBSCRIBE_T[1]:
        G.draw_subscribe(fr, S, PAL, T - TL.SUBSCRIBE_T[0], x=CTA_XY[0], y=CTA_XY[1])
    if TL.SHARE_T[0] <= T < TL.SHARE_T[1]:
        G.draw_share(fr, S, PAL, T - TL.SHARE_T[0], x=CTA_XY[0], y=CTA_XY[1])
    draw_caption_overlay(fr, T, kind)


def render_frame(T):
    sc = scene_at(T)
    kind = sc["kind"]
    geo = None
    if kind == "face":
        fr = scene_face(T, sc)
    elif kind == "broll":
        fr = scene_broll(T, sc)
    elif kind == "graphic":
        fr = G.render_search_lock(T - sc["t0"], S, PAL, bg_lock, lay=LOCK)
    elif kind == "phone":
        fr, geo = scene_phone(T)
    else:
        fr = G.render_reel_outro(T - sc["t0"], S, PAL, bg_outro)
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
            cv2.imwrite(os.path.join(args.out_dir, f"r_{t:07.3f}.png"), cv2.cvtColor((fr * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
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
        enc.stdin.write((render_frame(T) * 255 + 0.5).astype(np.uint8).tobytes())
        if (n - n0) % 60 == 0:
            el = time.time() - t_start
            done = n - n0 + 1
            print(f"T={T:7.2f}  {done}/{n1 - n0}  elapsed {el:6.0f}s  eta {el / done * (n1 - n0 - done):6.0f}s", flush=True)
    enc.stdin.close(); enc.wait()
    print("done", args.out)


if __name__ == "__main__":
    main()
