#!/usr/bin/env python3
"""V Create cinematic compositor (16:9 YouTube or 9:16 reel) for projects whose timeline sets STYLE = "cine".

Look: letterboxed 2.29:1 frame, chrome / champagne-gold Cinzel titles, centred subtitles with a gold active word,
whole-phone camera moves with spotlight highlights and callout labels, light-leak / whip / dip transitions,
subscribe / like / comment / share prompts through the video.

usage:
  render_cine.py --project NAME --format wide|reel --face main.mp4 --screen screen_clean60.mp4 --broll-dir DIR --out x.mp4 [--start --end]
  render_cine.py ... --frames 1.5,20,40 --out-dir stills/
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
import grade, cine as C, timeline as TL, captions_data as CD, phonescene
from gfx import ease_io, ease_out, clamp01, lerp

try:
    import screens as APP                     # project's illustrated app screens (optional)
except ImportError:
    APP = None

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--format", choices=["wide", "reel"], default="wide")
ap.add_argument("--face", required=True)
ap.add_argument("--screen", default=None, help="cleaned 60 fps screen recording; frame 0 == TL.SCREEN_T0")
ap.add_argument("--broll-dir", required=True)
ap.add_argument("--out", default=None)
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float, default=None)
ap.add_argument("--frames", default=None)
ap.add_argument("--out-dir", default=None)
ap.add_argument("--crf", type=int, default=17)
ap.add_argument("--preset", default="medium")
args = ap.parse_args()

REEL = args.format == "reel"
W, H = (1080, 1920) if REEL else (1920, 1080)
FPS = TL.FPS
OUTRO = 3.4
TOTAL = TL.NARR_END + OUTRO if REEL else TL.TOTAL
END_T = args.end if args.end is not None else TOTAL
LB = 0 if REEL else TL.LETTERBOX
P = C.PAL

# ---- layout ---------------------------------------------------------------------------------------------------
if REEL:
    L = dict(bug=(60, 150, 64), cap=(540, 1200, 62, 960), cap_phone=(540, 395, 58, 960), cta=(70, 1300),
             cta_phone=(70, 490), title=(540, 270, 64, "center"), step=(1020, 232), sting=(540, 784, 330),
             band_y=480, chip=(540, 476))
else:
    L = dict(bug=(40, 26, 66), cap=(960, H - LB / 2 - 2, 50, 1720), cap_phone=(960, H - LB / 2 - 2, 50, 1720),
             cta=(110, H - LB - 118), cta_phone=(110, H - LB - 118), title=(100, 370, 62, "left"), step=(1880, 34),
             sting=(960, 500, 330), chip=(470, LB + 26))


# ---- readers --------------------------------------------------------------------------------------------------
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


FW, FH = (3840, 2160) if REEL else (2560, 1440)
face_reader = SeekReader(args.face, FW, FH, 30.0, "null" if REEL else f"scale={FW}:{FH}:flags=lanczos", jump=60)
screen_reader = SeekReader(args.screen, 1320, 2868, 60.0, "null", jump=240) if args.screen else None
N_SCREEN = int(round((TL.SCREEN_END - TL.SCREEN_T0) * 60)) - 1 if args.screen else 0
_broll = {}


def broll_reader(name, clip, clip_t, speed=1.0, cx=0.5):
    if name not in _broll:
        sp = f"setpts=PTS/{speed}," if speed != 1.0 else ""
        vf = (f"{sp}scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos:in_color_matrix=bt709,"
              f"crop={W}:{H}:(iw-{W})*{cx}:(ih-{H})/2,fps=30")
        _broll[name] = SeekReader(os.path.join(args.broll_dir, f"{clip}.mp4"), W, H, 30.0, vf, t_off=clip_t, jump=60)
    return _broll[name]


# ---- assets ---------------------------------------------------------------------------------------------------
MG = int(0.08 * W)
BOKEH = C.bokeh_bg(W + 2 * MG, H + 2 * MG, seed=4, centre=(0.5, 0.56) if REEL else (0.64, 0.5))
BG_END = C.bokeh_bg(W, H, seed=11, centre=(0.5, 0.42) if REEL else (0.32, 0.45))
TITANIUM = ((214, 215, 219), (118, 120, 126))
if REEL:
    ps = phonescene.PhoneScene(1, None, W, H, layout="reel", hb_frac=0.55, anchor=(0.5, 0.60), titanium=TITANIUM, bg=BOKEH)
else:
    ps = phonescene.PhoneScene(1, None, W, H, layout="wide", hb_frac=0.70, anchor=(0.665, 0.50), x_min=780,
                               titanium=TITANIUM, bg=BOKEH)
PHONE_SCENES = [sc for sc in TL.SCENES if sc["kind"] == "phone"]
GR = getattr(TL, "GRADE", {})
_cache = {}


def scrim_left(fr, strength, width):
    key = ("sl", strength, width)
    if key not in _cache:
        xs = np.linspace(0, 1, W, dtype=np.float32)
        _cache[key] = (np.clip(1 - xs / width, 0, 1) ** 1.6 * strength)[None, :, None]
    fr *= 1 - _cache[key]


def vgrad(fr, y0, y1, strength, from_top=False):
    key = ("vg", y0, y1, strength, from_top)
    if key not in _cache:
        ys = np.arange(H, dtype=np.float32)
        a = np.clip((ys - y0) / max(y1 - y0, 1), 0, 1) if not from_top else np.clip((y1 - ys) / max(y1 - y0, 1), 0, 1)
        _cache[key] = ((a * a * (3 - 2 * a)) * strength)[:, None, None]
    fr *= 1 - _cache[key]


# ---- scenes ---------------------------------------------------------------------------------------------------
FA = TL.FACE_ANCHOR
_ft_path = os.path.join(_project_dir(), "face_track.json")
if os.path.exists(_ft_path):                                      # tools/face_track.py output: the crop follows the face
    import json
    _FT = json.load(open(_ft_path))
else:
    _FT = None


def face_at(T):
    if _FT is None:
        return FA["fx"], FA["fy"]
    return float(np.interp(T, _FT["t"], _FT["x"])), float(np.interp(T, _FT["t"], _FT["y"]))


def scene_face(T, sc):
    src = face_reader.get(int(round(T * 30)))
    rng = np.random.default_rng(int(T * 30))
    fx, fy = face_at(T)
    if REEL:
        bw, bh = W, int(W * 9 / 16)
        card = cv2.resize(src, (bw, bh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        card = grade.grade(card, grain=0.0, rng=rng, face=(fx, fy - 0.02, 0.18, 0.30), **GR)
        small = cv2.resize(card, (W // 10, int(W // 10 * bh / bw)), interpolation=cv2.INTER_AREA)
        sc_ = max(W / small.shape[1], H / small.shape[0])
        big = cv2.resize(small, (int(small.shape[1] * sc_) + 2, int(small.shape[0] * sc_) + 2), interpolation=cv2.INTER_CUBIC)
        oy, ox = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
        fr = cv2.GaussianBlur(big[oy:oy + H, ox:ox + W], (0, 0), 6) * 0.32
        fr = np.ascontiguousarray(fr, dtype=np.float32)
        y0 = L["band_y"]
        fr[y0:y0 + bh] = card
        line = np.array(P["steel"], np.float32) / 255
        fr[y0 - 2:y0] = line * 0.55
        fr[y0 + bh:y0 + bh + 2] = line * 0.55
        return C.film_grain(fr, 0.014, rng)
    z0, z1 = sc["zoom"]
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = lerp(z0, z1, ease_io(prog))
    tx, ty = 0.62, 0.50
    x0 = min(max(fx - tx / z, 0.0), 1 - 1 / z)
    y0 = min(max(fy - ty / z, 0.0), 1 - 1 / z)
    s_ = z * W / FW
    M = np.array([[s_, 0, -x0 * FW * s_], [0, s_, -y0 * FH * s_]], np.float32)
    fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC if s_ >= 0.98 else cv2.INTER_LINEAR).astype(np.float32) / 255.0
    cx, cy = (fx - x0) * z, (fy - y0) * z
    fr = grade.grade(fr, grain=0.0, rng=rng, face=(cx, cy - 0.03, 0.22, 0.36), **GR)
    boost = 0.0                                                    # darker left side while a title / chapter is up
    if TL.TITLE_T[0] - 0.3 <= T < TL.TITLE_T[1] + 0.3:
        boost = 1.0 - ease_io((T - (TL.TITLE_T[1] - 0.4)) / 0.6)
    for (c0, c1, _, _) in getattr(TL, "CHAPTERS", []):
        if c0 - 0.3 <= T < c1 + 0.3:
            boost = max(boost, ease_out((T - (c0 - 0.3)) / 0.4) * (1 - ease_io((T - (c1 - 0.2)) / 0.5)))
    scrim_left(fr, 0.55, 0.50)
    if boost > 0:
        scrim_left(fr, 0.45 * boost, 0.58)
    return C.film_grain(fr, 0.016, rng)


def scene_broll(T, sc):
    clip, ct = (sc["reel_clip"], sc.get("reel_clip_t", 0.0)) if REEL else (sc["clip"], sc.get("clip_t", 0.0))
    spd = sc.get("reel_speed", 1.0) if REEL else sc.get("speed", 1.0)
    rd = broll_reader(sc["name"], clip, ct, spd, sc.get("reel_cx", 0.5) if REEL else 0.5)
    src = rd.get(int(round((T - sc["t0"]) * 30)))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = 1.03 + 0.07 * prog
    M = np.array([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H / 2]], np.float32)
    fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255.0
    fr = grade.grade(fr, grain=0.0, rng=None, face=(0.5, 0.45, 0.6, 0.6), clarity=0.04, face_lift=0.0, tint=1.1)
    luma = (fr * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    fr = fr * 0.80 + luma * 0.20
    if REEL:
        vgrad(fr, 1120, 1560, 0.70)
        vgrad(fr, 80, 520, 0.55, from_top=True)
    return C.film_grain(fr, 0.016, np.random.default_rng(int(T * 30)))


def screen_frame(T):
    src = TL.screen_source(T)
    if src == "app":
        return APP.render(T)
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - TL.SCREEN_T0) * 60)), 0), N_SCREEN)
    return screen_reader.get(idx)


def phone_scene_of(T):
    for sc in PHONE_SCENES:
        if sc["t0"] <= T < sc["t1"]:
            return sc
    return PHONE_SCENES[0]


def scene_phone(T, sc):
    screen = screen_frame(T)
    cam = phonescene.cam_at(T, TL.CAMERA)
    enter = ease_out((T - sc["t0"]) / 0.8)
    g = ps.geometry(cam, extra=((1 - enter) * (0.35 if REEL else 0.25) * W, 0.0))
    sway = 3.0 * math.sin(2 * math.pi * T / 7.0)
    fr = ps.render(screen, g, opacity=min(1.0, enter * 1.6), sway=sway)
    g["sway"] = sway
    if REEL:
        vgrad(fr, 160, 560, 0.92, from_top=True)
    return C.film_grain(fr, 0.010, np.random.default_rng(int(T * 30))), g


def scene_at(T):
    for sc in TL.SCENES:
        if sc["t0"] <= T < sc["t1"]:
            return sc
    return TL.SCENES[-1]


# ---- overlays -------------------------------------------------------------------------------------------------
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


def draw_captions(fr, T, kind):
    i = active_chunk(T)
    if i is None or kind in ("end", "outro"):
        return
    c = CD.CHUNKS[i]
    wt = CD.word_times(c)
    words = [w for w, _, _ in wt]
    act, age = -1, 1.0
    for k, (_, ws, we) in enumerate(wt):
        if T >= ws:
            act, age = k, T - ws
    fin = clamp01((T - c[0] + 0.02) / 0.14)
    fout = 1.0 - clamp01((T - (c[1] + 0.12)) / 0.16)
    nxt = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
    if nxt - c[0] < 0.5:
        fout = 1.0
    cx, cy, size, mw = L["cap_phone"] if kind == "phone" else L["cap"]
    if REEL and kind == "graphic":
        cy = 1430
    C.draw_caption(fr, words, act, age, cx, cy, size, mw, alpha=fin * fout, rise=(1 - ease_out(fin)) * 10,
                   lines_max=2 if REEL else 1)


def spans(v):
    return v if isinstance(v[0], (tuple, list)) else [v]


def draw_ctas(fr, T, kind):
    x, y = L["cta_phone"] if kind == "phone" else L["cta"]
    s = 1.0
    for cta in TL.CTAS:
        t0, what = cta[0], cta[1]
        dur = cta[2] if len(cta) > 2 else None
        t = T - t0
        if what == "subscribe":
            C.cta_subscribe(fr, t, x, y, scale=s)
        elif what == "like":
            C.cta_like(fr, t, x, y, scale=s)
        elif what == "share":
            C.cta_share(fr, t, x, y, scale=s)
        elif what == "comment":
            C.cta_comment(fr, t, x, y, scale=s)
        elif what == "engage":
            kw = {"dur": dur} if dur else {}
            if REEL:
                C.cta_engage(fr, t, x, y, grid=True, scale=0.86, **kw)
            else:
                C.cta_engage(fr, t, x, y - 92, grid=True, scale=0.95, **kw)


def draw_phone_marks(fr, T, geo):
    def rect_of(u0, v0, u1, v1):
        x0, y0 = ps.to_out(geo, u0, v0)
        x1, y1 = ps.to_out(geo, u1, v1)
        sw = geo.get("sway", 0)
        return (x0, y0 + sw, x1, y1 + sw)
    for h in TL.HIGHLIGHTS:
        t0, t1, (u0, v0, u1, v1) = h[:3]
        label = h[3] if len(h) > 3 else ""
        if t0 - 0.25 <= T <= t1 + 0.3:
            a = ease_out((T - (t0 - 0.25)) / 0.3) * (1 - ease_io((T - t1) / 0.3))
            r = rect_of(u0, v0, u1, v1)
            C.spotlight(fr, r, a, radius=22)
            C.draw_frame_box(fr, r, T - t0, a)
            if label:
                C.draw_callout(fr, r, label, T - t0, a, size=24 if not REEL else 30, min_x=40 if REEL else 60,
                               left_edge=None if REEL else geo["X0"] - 60)
    for (tt, u, v) in TL.TAPS:
        if tt - 0.3 <= T <= tt + 0.95:
            x, y = ps.to_out(geo, u, v)
            C.draw_tap(fr, x, y + geo.get("sway", 0), T - tt)


def draw_overlays(fr, T, sc, geo):
    kind = sc["kind"]
    if kind in ("end", "outro"):
        return
    # letterbox opens over the first 0.8 s
    if not REEL:
        C.letterbox(fr, LB * (0.35 + 0.65 * ease_out(T / 0.8)))
    if kind == "phone":
        draw_phone_marks(fr, T, geo)
        if TL.screen_source(T) == "app":
            C.draw_chip(fr, "ILLUSTRATION  ·  the app blocks screen recording", *L["chip"][:2],
                        alpha=ease_out((T - sc["t0"] - 0.5) / 0.4) * 0.95)
    # bug (hidden while the sting plays)
    bx, by, bs = L["bug"]
    a = ease_out((T - 0.3) / 0.6)
    s0 = TL.STING_T0
    if s0 <= T < s0 + 2.9:
        a = 0.0 if T < s0 + 2.75 else 1.0
    C.draw_bug(fr, bx, by, a, size=bs)
    # step HUD (phone scenes)
    for (t0, t1, n, label) in TL.STEPS:
        if t0 <= T < t1 and kind == "phone":
            fa = ease_out((T - t0) / 0.35) * (1 - ease_io((T - (t1 - 0.25)) / 0.25))
            if REEL:
                C.draw_step(fr, n, TL.N_STEPS, label, fa, L["step"][0], L["step"][1], size=34)
            else:
                C.draw_step(fr, n, TL.N_STEPS, label, fa, L["step"][0], L["step"][1], size=27)
    # hook title
    tx, ty, ts, al = L["title"]
    C.draw_title(fr, T - TL.TITLE_T[0], TL.TITLE_LINES, tx, ty, size=ts, dur=TL.TITLE_T[1] - TL.TITLE_T[0], align=al)
    # chapter kickers
    for (t0, t1, kick, title) in getattr(TL, "CHAPTERS", []):
        if t0 <= T < t1:
            ka = ease_out((T - t0) / 0.4) * (1 - ease_io((T - (t1 - 0.4)) / 0.4))
            if REEL:
                C.draw_kicker(fr, kick, 70, 330, ka, size=24)
                m, base = C.text_mask(title, C.font("display", 54), tracking=4)
                from gfx import blend as _b
                _b(fr, C.fill_mask(m, C.CHROME), 64, 370 - base + 40, ka)
            else:
                C.draw_kicker(fr, kick, 112, 700, ka, size=18)
                m, base = C.text_mask(title, C.font("display", 48), tracking=4)
                from gfx import blend as _b
                _b(fr, C.fill_mask(m, C.CHROME), 104, 745 - base + 30, ka)
    draw_ctas(fr, T, kind)
    sx, sy, ss = L["sting"]
    C.draw_sting(fr, T - s0, sx, sy, size=ss, bug=(bx, by, bs))
    draw_captions(fr, T, kind)


# ---- frame ----------------------------------------------------------------------------------------------------
def render_frame(T):
    sc = scene_at(T)
    kind = sc["kind"]
    geo = None
    if REEL and T >= TL.NARR_END:
        kind = "outro"
        fr = C.render_reel_outro(T - TL.NARR_END, W, H, BG_END)
    elif kind == "face":
        fr = scene_face(T, sc)
    elif kind == "broll":
        fr = scene_broll(T, sc)
    elif kind == "phone":
        fr, geo = scene_phone(T, sc)
    elif kind == "graphic":
        fr = C.render_deadline(T - sc["t0"], W, H, BG_END, **sc.get("args", {}))
        fr = C.film_grain(fr, 0.010, np.random.default_rng(int(T * 30)))
    else:
        fr = C.render_end(T - sc["t0"], W, H, BG_END)
    fr = np.ascontiguousarray(fr, dtype=np.float32)
    for (tt, tk) in TL.TRANSITIONS:
        p = (T - tt) / 0.32
        if -1 < p < 1:
            if tk == "flash":
                fr = C.flash(fr, p)
            elif tk == "whip":
                fr = C.whip(fr, p, 1)
            elif tk == "dip":
                fr = C.dip(fr, p)
    fr = np.ascontiguousarray(np.clip(fr, 0, 1), dtype=np.float32)
    draw_overlays(fr, T, dict(sc, kind=kind), geo)            # UI stays crisp: drawn after the transition effects
    return np.clip(fr, 0, 1)


def main():
    if args.frames:
        os.makedirs(args.out_dir, exist_ok=True)
        for t in [float(x) for x in args.frames.split(",")]:
            t0 = time.time()
            fr = render_frame(t)
            cv2.imwrite(os.path.join(args.out_dir, f"{'r' if REEL else 'w'}_{t:07.3f}.png"), cv2.cvtColor((fr * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
            print(f"T={t:7.3f}  {time.time() - t0:5.2f}s", flush=True)
        return
    n0, n1 = int(round(args.start * FPS)), int(round(END_T * FPS))
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
