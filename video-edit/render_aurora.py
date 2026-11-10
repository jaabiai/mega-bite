#!/usr/bin/env python3
"""V Create "Aurora" compositor (16:9 YouTube or 9:16 reel) for projects whose timeline sets STYLE = "aurora".

Look: the picture runs full-bleed and every caption lives in its own dock (a bar under the picture in 16:9, a header above
the picture window in the reel), so text never sits on the presenter.  The topic opens as a full-screen extruded 3D title.
Orchid / rose / amber gradient accents, Anton + Outfit type, prism and light-sweep transitions.  No end card.

usage:
  render_aurora.py --project NAME --format wide|reel --face main.mp4 --screen screen_clean60.mp4 --broll-dir DIR --out x.mp4 [--start --end]
  render_aurora.py ... --frames 1.5,20,40 --out-dir stills/
"""
import argparse, json, math, os, subprocess, sys, time
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
import grade, cine as C, aurora as A, timeline as TL, captions_data as CD, phonescene
from gfx import ease_io, ease_out, clamp01, lerp, blend

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--format", choices=["wide", "reel"], default="wide")
ap.add_argument("--face", required=True)
ap.add_argument("--screen", default=None, help="cleaned screen recording (TL.SCREEN_FPS, default 60); frame 0 == TL.SCREEN_T0")
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
TAIL = 0.30                                                     # fade to black after the last word; no end card
CUTS = None
if REEL and getattr(TL, "REEL_CUTS", None):                     # reel = a few whole blocks of the narration, in order
    PRE, POST = 0.06, 0.10
    CUTS, u = [], 0.0
    for a, b in TL.REEL_CUTS:
        a, b = max(a - PRE, 0.0), min(b + POST, TL.NARR_END)
        CUTS.append((u, a, b))
        u += b - a
    REEL_NARR = u
NARR = REEL_NARR if CUTS else TL.NARR_END
TOTAL = NARR + TAIL
END_T = args.end if args.end is not None else TOTAL

# ---- layout: the picture window and the caption dock ---------------------------------------------------------
if REEL:
    HEAD = 560                                                  # header above the picture: logo, captions, prompts
    PW, PH, PY0 = W, H - HEAD, HEAD
    L = dict(bug=(56, 214, 62), cap=(540, 412, 62, 968, 2), cta=(1024, 208, 0.86), step=(1024, PY0 + 36, 30),
             sting=(540, 246, 128, False), tag=(56, PY0 + 40))
    L["step"] = (1024, PY0 + 36, 30, "r")
else:
    DOCK = 132                                                  # bar under the picture: captions only
    PW, PH, PY0 = W, H - DOCK, 0
    L = dict(bug=(48, 34, 60), cap=(960, PH + DOCK / 2 + 2, 46, 1760, 1), cta=(70, 150, 1.0), step=(1872, 40, 26),
             sting=(330, 430, 250, True), tag=(70, 130))
    L["step"] = (80, 300, 32, "l")                              # phone scenes: the empty left side carries the step


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


FW, FH = 2560, 1440
face_reader = SeekReader(args.face, FW, FH, 30.0, f"scale={FW}:{FH}:flags=lanczos", jump=60)
SFPS = float(getattr(TL, "SCREEN_FPS", 60))
screen_reader = SeekReader(args.screen, 1320, 2868, SFPS, "null", jump=int(4 * SFPS)) if args.screen else None
N_SCREEN = int(round((TL.SCREEN_END - TL.SCREEN_T0) * SFPS)) - 1 if args.screen else 0
_broll = {}


def broll_reader(name, clip, clip_t, speed=1.0, cx=0.5):
    if name not in _broll:
        sp = f"setpts=PTS/{speed}," if speed != 1.0 else ""
        vf = (f"{sp}scale={PW}:{PH}:force_original_aspect_ratio=increase:flags=lanczos:in_color_matrix=bt709,"
              f"crop={PW}:{PH}:(iw-{PW})*{cx}:(ih-{PH})/2,fps=30")
        _broll[name] = SeekReader(os.path.join(args.broll_dir, f"{clip}.mp4"), PW, PH, 30.0, vf, t_off=clip_t, jump=60)
    return _broll[name]


# ---- assets ---------------------------------------------------------------------------------------------------
MG = int(0.08 * PW)
BACK = A.backdrop(PW + 2 * MG, PH + 2 * MG, seed=4)
TITANIUM = ((196, 190, 206), (104, 98, 116))
if REEL:
    ps = phonescene.PhoneScene(1, None, PW, PH, layout="reel", hb_frac=0.70, anchor=(0.5, 0.46), titanium=TITANIUM, bg=BACK)
    HEAD_BG = A.dock_panel(W, HEAD, line="none")
    WIN_MASK, WIN_RIM = A.window_edge(PW, 120, 44)
else:
    ps = phonescene.PhoneScene(1, None, PW, PH, layout="wide", hb_frac=0.82, anchor=(0.665, 0.50), x_min=760,
                               titanium=TITANIUM, bg=BACK)
    DOCK_BG = A.dock_panel(W, DOCK, line="top")
PHONE_SCENES = [sc for sc in TL.SCENES if sc["kind"] == "phone"]
GR = getattr(TL, "GRADE", {})
TITLE = A.Title3D(W, H, TL.TITLE_BEATS_REEL if REEL else TL.TITLE_BEATS, box=(0.88, 0.46) if REEL else (0.86, 0.60))
HEADERS = [(h[0], h[1], A.Title3D(W, H, [(0.0, h[1] - h[0], h[3] if REEL and len(h) > 3 else h[2])],
                                  box=(0.84, 0.30) if REEL else (0.70, 0.42)))
           for h in getattr(TL, "HEADERS_3D", [])]
_cache = {}


def vgrad(fr, y0, y1, strength, from_top=False):
    key = ("vg", fr.shape[0], y0, y1, strength, from_top)
    if key not in _cache:
        ys = np.arange(fr.shape[0], dtype=np.float32)
        a = np.clip((ys - y0) / max(y1 - y0, 1), 0, 1) if not from_top else np.clip((y1 - ys) / max(y1 - y0, 1), 0, 1)
        _cache[key] = ((a * a * (3 - 2 * a)) * strength)[:, None, None]
    fr *= 1 - _cache[key]


def corner_scrim(fr, strength=0.42, radius=620):
    """Darkens the top-left corner of the 16:9 picture so the logo and prompts read over a bright window."""
    key = ("cs", fr.shape[0], fr.shape[1], strength, radius)
    if key not in _cache:
        yy, xx = np.mgrid[0:fr.shape[0], 0:fr.shape[1]].astype(np.float32)
        d = np.hypot(xx / 1.25, yy) / radius
        _cache[key] = (np.clip(1 - d, 0, 1) ** 1.5 * strength)[..., None]
    fr *= 1 - _cache[key]


# ---- scenes ---------------------------------------------------------------------------------------------------
FA = TL.FACE_ANCHOR
_ft_path = os.path.join(_project_dir(), "face_track.json")
_FT = json.load(open(_ft_path)) if os.path.exists(_ft_path) else None


def face_at(T):
    if _FT is None:
        return FA["fx"], FA["fy"]
    return float(np.interp(T, _FT["t"], _FT["x"])), float(np.interp(T, _FT["t"], _FT["y"]))


def face_crop(T, w, h, zoom=1.0, tx=0.5, ty=0.42):
    """w x h crop of the face-cam that keeps the tracked face at (tx, ty) of the crop; returns (frame, face centre in the crop)."""
    src = face_reader.get(int(round(T * 30)))
    fx, fy = face_at(T)
    s_ = max(w / FW, h / FH) * zoom
    x0 = min(max(fx * FW * s_ - tx * w, 0.0), FW * s_ - w)
    y0 = min(max(fy * FH * s_ - ty * h, 0.0), FH * s_ - h)
    M = np.array([[s_, 0, -x0], [0, s_, -y0]], np.float32)
    interp = cv2.INTER_AREA if s_ < 0.8 else (cv2.INTER_LINEAR if s_ < 1.0 else cv2.INTER_CUBIC)
    fr = cv2.warpAffine(src, M, (w, h), flags=interp).astype(np.float32) / 255.0
    return fr, ((fx * FW * s_ - x0) / w, (fy * FH * s_ - y0) / h)


def scene_face(T, sc, w=None, h=None):
    w, h = w or PW, h or PH
    z0, z1 = sc.get("zoom", (1.0, 1.05))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = lerp(z0, z1, ease_io(prog))
    tx, ty = (0.5, 0.40) if REEL else (sc.get("tx", 0.56), 0.44)
    fr, (cx, cy) = face_crop(T, w, h, z, tx, ty)
    rng = np.random.default_rng(int(T * 30))
    fr = grade.grade(fr, grain=0.0, rng=rng, face=(cx, cy - 0.02, 0.30 if REEL else 0.20, 0.26 if REEL else 0.36), **GR)
    if not REEL and w == PW:
        corner_scrim(fr)
    return C.film_grain(fr, 0.014, rng)


def scene_broll(T, sc):
    clip, ct = (sc.get("reel_clip", sc["clip"]), sc.get("reel_clip_t", sc.get("clip_t", 0.0))) if REEL else (sc["clip"], sc.get("clip_t", 0.0))
    spd = sc.get("speed", 1.0)
    rd = broll_reader(sc["name"], clip, ct, spd, sc.get("reel_cx", 0.5) if REEL else 0.5)
    src = rd.get(int(round((T - sc["t0"]) * 30)))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = 1.03 + 0.06 * prog
    M = np.array([[z, 0, (1 - z) * PW / 2], [0, z, (1 - z) * PH / 2]], np.float32)
    fr = cv2.warpAffine(src, M, (PW, PH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255.0
    fr = grade.grade(fr, grain=0.0, rng=None, face=(0.5, 0.45, 0.6, 0.6), clarity=0.04, face_lift=0.0, tint=0.5)
    vgrad(fr, int(PH * 0.72), PH, 0.30)
    if not REEL:
        corner_scrim(fr)
    return C.film_grain(fr, 0.014, np.random.default_rng(int(T * 30)))


def screen_frame(T):
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - TL.SCREEN_T0) * SFPS)), 0), N_SCREEN)
    return screen_reader.get(idx)


def scene_phone(T, sc):
    screen = screen_frame(T)
    cam = phonescene.cam_at(T, TL.CAMERA)
    enter = ease_out((T - sc["t0"]) / 0.8)
    g = ps.geometry(cam, extra=((1 - enter) * (0.30 if REEL else 0.22) * PW, 0.0))
    sway = 3.0 * math.sin(2 * math.pi * T / 7.0)
    fr = ps.render(screen, g, opacity=min(1.0, enter * 1.6), sway=sway)
    g["sway"] = sway
    return C.film_grain(fr, 0.008, np.random.default_rng(int(T * 30))), g


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


def draw_captions(fr, T):
    i = active_chunk(T)
    if i is None:
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
    cx, cy, size, mw, nl = L["cap"]
    A.draw_caption(fr, words, act, age, cx, cy, size, mw, alpha=fin * fout, rise=(1 - ease_out(fin)) * 8, lines_max=nl)


def draw_ctas(fr, T, u=None):
    x, y, s = L["cta"]
    ctas, now = (TL.REEL_CTAS, u) if (CUTS and u is not None and hasattr(TL, "REEL_CTAS")) else (TL.CTAS, T)
    for cta in ctas:
        t0, what = cta[0], cta[1]
        t = now - t0
        if t < 0 or t > 9:
            continue
        seq = [("like", 2.3), ("share", 2.3), ("subscribe", 3.4)] if what == "engage" else [(what, None)]
        if what == "engage" and not REEL:
            C.cta_engage(fr, t, x, y, grid=True, scale=0.95)
            continue
        for name, dur in seq:
            fn = {"subscribe": C.cta_subscribe, "like": C.cta_like, "share": C.cta_share, "comment": C.cta_comment,
                  "save": A.cta_save}[name]
            if REEL:                                             # right-aligned in the header row, beside the logo
                wd = {"subscribe": 500, "like": 205, "share": 225, "comment": 470, "save": 210}[name] * s
                fn(fr, t, x - wd, y, scale=s)
            else:
                fn(fr, t, x, y, scale=s)
            if dur:
                t -= dur


def draw_phone_marks(pic, T, geo):
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
            C.spotlight(pic, r, a, radius=22, dim=0.58)
            C.draw_frame_box(pic, r, T - t0, a)
            if label:
                C.draw_callout(pic, r, label, T - t0, a, size=30 if REEL else 24, min_x=40 if REEL else 60,
                               left_edge=None if REEL else geo["X0"] - 60)
    for (tt, u, v) in TL.TAPS:
        if tt - 0.3 <= T <= tt + 0.95:
            x, y = ps.to_out(geo, u, v)
            C.draw_tap(pic, x, y + geo.get("sway", 0), T - tt)


def draw_overlays(fr, T, sc, u=None):
    kind = sc["kind"]
    if kind == "title":
        return
    bx, by, bs = L["bug"]
    s0 = getattr(TL, "STING_T0", -99.0)
    a = 1.0
    if s0 <= T < s0 + 2.9:
        a = 0.0 if T < s0 + 2.75 else 1.0
    A.draw_bug(fr, bx, by, a, size=bs)
    for (t0, t1, n, label) in TL.STEPS:
        if t0 <= T < t1 and kind == "phone":
            fa = ease_out((T - t0) / 0.35) * (1 - ease_io((T - (t1 - 0.25)) / 0.25))
            A.draw_step(fr, n, TL.N_STEPS, label, fa, L["step"][0], L["step"][1], size=L["step"][2], anchor=L["step"][3])
    for (t0, t1, text) in getattr(TL, "TAGS", []):
        if t0 <= T < t1 and kind != "phone":
            ta = ease_out((T - t0) / 0.4) * (1 - ease_io((T - (t1 - 0.35)) / 0.35))
            A.draw_tag(fr, text, L["tag"][0], L["tag"][1], ta, size=30 if REEL else 26)
    draw_ctas(fr, T, u)
    sx, sy, ss, sname = L["sting"]                                # beside the presenter (16:9) or in the header (reel)
    A.draw_sting(fr, T - s0, sx, sy, size=ss, bug=(bx, by, bs), name=sname)
    draw_captions(fr, T)


# ---- frame ----------------------------------------------------------------------------------------------------
def picture(T, sc):
    kind = sc["kind"]
    geo = None
    if kind == "face":
        pic = scene_face(T, sc)
    elif kind == "broll":
        pic = scene_broll(T, sc)
    else:
        pic, geo = scene_phone(T, sc)
    pic = np.ascontiguousarray(pic, dtype=np.float32)
    if geo is not None:
        draw_phone_marks(pic, T, geo)
    return pic


def transitions(fr, T, u):
    for (tt, tk) in TL.TRANSITIONS:
        p = (T - tt) / 0.30
        if -1 < p < 1:
            fr = {"prism": A.prism, "sweep": A.sweep, "dip": A.dip}[tk](fr, p)
    if CUTS and u is not None:                                   # the reel's few joins
        for (us, a, b) in CUTS[1:]:
            p = (u - us) / 0.30
            if -1 < p < 1:
                fr = A.prism(fr, p)
    return fr


def render_frame(T, u=None):
    """T = narration time. u = output time of the reel edit (CUTS), None for the full timeline."""
    sc = scene_at(T)
    kind = sc["kind"]
    if kind == "title":                                            # full-screen 3D title over the blurred live picture
        base, _ = face_crop(T, W, H, 1.0, 0.5, 0.42)
        fr = TITLE.background(base, T)
        TITLE.draw(fr, T)
        fr = transitions(np.ascontiguousarray(fr), T, u)
    else:
        fr = np.zeros((H, W, 3), np.float32)
        pic = transitions(picture(T, sc), T, u)
        if REEL:
            fr[:HEAD] = HEAD_BG
            fr[PY0:] = pic
            top = fr[PY0:PY0 + 120]
            top[:] = top * WIN_MASK + HEAD_BG[-1:, :, :] * (1 - WIN_MASK)
            blend(fr, WIN_RIM, 0, PY0)
        else:
            fr[:PH] = pic
            fr[PH:] = DOCK_BG
        t_end = TITLE.span()[1]
        if 0 <= T - t_end < 0.5:                                   # the dock / header slide in after the title
            k = 1 - ease_out((T - t_end) / 0.5)
            if REEL:
                fr[:HEAD] *= 1 - 0.6 * k
            else:
                fr[PH:] *= 1 - 0.6 * k
    fr = np.ascontiguousarray(np.clip(fr, 0, 1), dtype=np.float32)
    draw_overlays(fr, T, sc, u)
    for (t0, t1, hd) in HEADERS:
        if t0 - 0.05 <= T < t1 + 0.4:
            k = ease_out((T - t0) / 0.3) * (1 - ease_io((T - t1) / 0.36))
            fr *= 1 - 0.62 * k
            hd.draw(fr, T - t0)
    now = u if (CUTS and u is not None) else T
    fade = 1 - clamp01((now - NARR) / (TAIL - 0.04))             # the first frame is already the title: no fade-in
    return np.clip(fr * fade, 0, 1)


def u_to_T(u):
    for us, a, b in CUTS:
        if u < us + (b - a):
            return a + (u - us)
    return CUTS[-1][2] + (u - REEL_NARR)


def frame_at(t_out):
    if CUTS:
        return render_frame(u_to_T(t_out), t_out)
    return render_frame(t_out)


def main():
    if args.frames:
        os.makedirs(args.out_dir, exist_ok=True)
        for t in [float(x) for x in args.frames.split(",")]:
            t0 = time.time()
            fr = frame_at(t)
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
        enc.stdin.write((frame_at(T) * 255 + 0.5).astype(np.uint8).tobytes())
        if (n - n0) % 60 == 0:
            el = time.time() - t_start
            done = n - n0 + 1
            print(f"T={T:7.2f}  {done}/{n1 - n0}  elapsed {el:6.0f}s  eta {el / done * (n1 - n0 - done):6.0f}s", flush=True)
    enc.stdin.close(); enc.wait()
    print("done", args.out)


if __name__ == "__main__":
    main()
