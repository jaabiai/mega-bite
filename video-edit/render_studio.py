#!/usr/bin/env python3
"""V Create "Studio" compositor (16:9 YouTube or 9:16 reel) for projects whose timeline sets STYLE = "studio".

Broadcast-explainer layout: the picture (face-cam, B-roll or the phone) plays inside a rounded card on a midnight backdrop.
In 16:9 the card is on the right and a sidebar on the left carries the topic label, a transcript-style caption block,
the step number and the prompts; in 9:16 the card is on top and the same elements sit under it.  So no text ever lands on
the presenter.  The topic opens as a full-screen extruded 3D title.  No end card.  The Android recording gets an Android
phone frame (punch-hole camera top-left) when TL.DEVICE == "android".

usage:
  render_studio.py --project NAME --format wide|reel --face main.mp4 --screen screen_clean.mp4 --broll-dir DIR --out x.mp4 [--start --end]
  render_studio.py ... --frames 1.5,20,40 --out-dir stills/
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
import grade, cine as C, studio as S, timeline as TL, captions_data as CD, phonescene
from gfx import ease_io, ease_out, clamp01, lerp, blend

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--format", choices=["wide", "reel"], default="wide")
ap.add_argument("--face", required=True)
ap.add_argument("--screen", default=None, help="cleaned screen recording (TL.SCREEN_SIZE, TL.SCREEN_FPS); frame 0 == TL.SCREEN_T0")
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
TAIL = 0.30
CUTS = None
if REEL and getattr(TL, "REEL_CUTS", None):
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

# ---- layout ---------------------------------------------------------------------------------------------------
if REEL:
    CX, CY, PW, PH = 40, 196, 1000, 1080                         # picture card
    L = dict(bug=(48, 70, 58), topic=(48, 1310, 980, 34), cap=(40, 1430, 980, 54), cta=(48, 1780, 0.86),
             step=(48, 1300, 30, 980), sting=(540, 120, 110, False))
else:
    CX, CY, PW, PH = 650, 56, 1214, 968
    L = dict(bug=(64, 56, 58), topic=(64, 178, 540, 36), cap=(54, 470, 560, 50), cta=(64, 930, 0.92),
             step=(64, 836, 30, 540), sting=(330, 520, 230, True))
CARD = S.Card(W, H, CX, CY, PW, PH, r=28)
BACK_FULL = S.backdrop(W, H)


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
SW_, SH_ = getattr(TL, "SCREEN_SIZE", (1320, 2868))
SFPS = float(getattr(TL, "SCREEN_FPS", 60))
screen_reader = SeekReader(args.screen, SW_, SH_, SFPS, "null", jump=int(4 * SFPS)) if args.screen else None
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
BACK = S.backdrop(PW + 2 * MG, PH + 2 * MG)
RAIL = ((168, 174, 186), (70, 76, 88))
ps = phonescene.PhoneScene(1, None, PW, PH, layout="wide", hb_frac=0.90 if not REEL else 0.88, anchor=(0.5, 0.5), x_min=0,
                           titanium=RAIL, bg=BACK, device=getattr(TL, "DEVICE", "iphone"), src=(SW_, SH_))
PHONE_SCENES = [sc for sc in TL.SCENES if sc["kind"] == "phone"]
GR = getattr(TL, "GRADE", {})
TITLE = S.title3d(W, H, TL.TITLE_BEATS_REEL if REEL else TL.TITLE_BEATS, box=(0.88, 0.46) if REEL else (0.86, 0.58))
HEADERS = [(h[0], h[1], S.title3d(W, H, [(0.0, h[1] - h[0], h[3] if REEL and len(h) > 3 else h[2])],
                                  box=(0.84, 0.30) if REEL else (0.70, 0.42)))
           for h in getattr(TL, "HEADERS_3D", [])]

# ---- scenes ---------------------------------------------------------------------------------------------------
FA = TL.FACE_ANCHOR
_ft_path = os.path.join(_project_dir(), "face_track.json")
_FT = json.load(open(_ft_path)) if os.path.exists(_ft_path) else None


def face_at(T):
    if _FT is None:
        return FA["fx"], FA["fy"]
    return float(np.interp(T, _FT["t"], _FT["x"])), float(np.interp(T, _FT["t"], _FT["y"]))


def face_crop(T, w, h, zoom=1.0, tx=0.5, ty=0.42):
    src = face_reader.get(int(round(T * 30)))
    fx, fy = face_at(T)
    s_ = max(w / FW, h / FH) * zoom
    x0 = min(max(fx * FW * s_ - tx * w, 0.0), FW * s_ - w)
    y0 = min(max(fy * FH * s_ - ty * h, 0.0), FH * s_ - h)
    M = np.array([[s_, 0, -x0], [0, s_, -y0]], np.float32)
    interp = cv2.INTER_AREA if s_ < 0.8 else (cv2.INTER_LINEAR if s_ < 1.0 else cv2.INTER_CUBIC)
    fr = cv2.warpAffine(src, M, (w, h), flags=interp).astype(np.float32) / 255.0
    return fr, ((fx * FW * s_ - x0) / w, (fy * FH * s_ - y0) / h)


def scene_face(T, sc):
    z0, z1 = sc.get("zoom", (1.0, 1.05))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = lerp(z0, z1, ease_io(prog))
    fr, (cx, cy) = face_crop(T, PW, PH, z, 0.5, 0.42)
    rng = np.random.default_rng(int(T * 30))
    fr = grade.grade(fr, grain=0.0, rng=rng, face=(cx, cy - 0.02, 0.28, 0.32), **GR)
    return C.film_grain(fr, 0.012, rng)


def scene_broll(T, sc):
    clip, ct = sc["clip"], sc.get("clip_t", 0.0)
    rd = broll_reader(sc["name"], clip, ct, sc.get("speed", 1.0), sc.get("reel_cx", 0.5) if REEL else sc.get("cx", 0.5))
    src = rd.get(int(round((T - sc["t0"]) * 30)))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = 1.03 + 0.06 * prog
    M = np.array([[z, 0, (1 - z) * PW / 2], [0, z, (1 - z) * PH / 2]], np.float32)
    fr = cv2.warpAffine(src, M, (PW, PH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255.0
    fr = grade.grade(fr, grain=0.0, rng=None, face=(0.5, 0.45, 0.6, 0.6), clarity=0.04, face_lift=0.0, tint=0.3)
    return C.film_grain(fr, 0.012, np.random.default_rng(int(T * 30)))


def screen_frame(T):
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - TL.SCREEN_T0) * SFPS)), 0), N_SCREEN)
    return screen_reader.get(idx)


def scene_phone(T, sc):
    screen = screen_frame(T)
    cam = phonescene.cam_at(T, TL.CAMERA)
    enter = ease_out((T - sc["t0"]) / 0.8)
    g = ps.geometry(cam, extra=(0.0, (1 - enter) * 0.25 * PH))
    sway = 3.0 * math.sin(2 * math.pi * T / 7.0)
    fr = ps.render(screen, g, opacity=min(1.0, enter * 1.6), sway=sway)
    g["sway"] = sway
    return C.film_grain(fr, 0.006, np.random.default_rng(int(T * 30))), g


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
    if T > c[1] + 0.45 and T < nxt:
        return None
    return best


def cap_hide(T):
    """Captions step aside while the logo sting (wide) or a full-frame 3D header is on screen."""
    k = 0.0
    s0 = getattr(TL, "STING_T0", -99.0)
    if not REEL:
        k = max(k, ease_out((T - s0 + 0.1) / 0.25) * (1 - ease_io((T - (s0 + 2.75)) / 0.25)))
    for h in getattr(TL, "HEADERS_3D", []):
        k = max(k, ease_out((T - h[0] + 0.1) / 0.2) * (1 - ease_io((T - (h[1] + 0.15)) / 0.3)))
    return 1.0 - k


def draw_captions(fr, T, y_cap):
    hide = cap_hide(T)
    if hide <= 0.01:
        return
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
    prev = CD.CHUNKS[i - 1][2].split() if i > 0 and c[0] - CD.CHUNKS[i - 1][1] < 1.2 else []
    fin = clamp01((T - c[0] + 0.02) / 0.14)
    fout = 1.0 - clamp01((T - (c[1] + 0.30)) / 0.16)
    nxt = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
    if nxt - c[0] < 0.6:
        fout = 1.0
    x, _, mw, size = L["cap"]
    img = S.caption_block(prev, words, act, age, size, mw, align="center" if REEL else "left")
    blend(fr, img, x, y_cap + (1 - ease_out(fin)) * 10, fin * fout * hide)


def draw_ctas(fr, T, u=None):
    x, y, s = L["cta"]
    ctas, now = (TL.REEL_CTAS, u) if (CUTS and u is not None and hasattr(TL, "REEL_CTAS")) else (TL.CTAS, T)
    for cta in ctas:
        t0, what = cta[0], cta[1]
        t = now - t0
        if t < 0 or t > 9:
            continue
        if what == "engage":
            C.cta_engage(fr, t, x, y - (88 * s if not REEL else 0), grid=not REEL, scale=s)
            continue
        fn = {"subscribe": C.cta_subscribe, "like": C.cta_like, "share": C.cta_share, "comment": C.cta_comment}[what]
        fn(fr, t, x, y, scale=s)


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
            C.spotlight(pic, r, a, radius=20, dim=0.55)
            C.draw_frame_box(pic, r, T - t0, a, radius=18)
            if label:
                C.draw_callout(pic, r, label, T - t0, a, size=26 if not REEL else 30, min_x=30, max_x=PW - 30)
    for (tt, u, v) in TL.TAPS:
        if tt - 0.3 <= T <= tt + 0.95:
            x, y = ps.to_out(geo, u, v)
            C.draw_tap(pic, x, y + geo.get("sway", 0), T - tt)


def draw_overlays(fr, T, sc, u=None):
    kind = sc["kind"]
    if kind == "title":
        return
    t_end = TITLE.span()[1]
    k_in = ease_out((T - t_end) / 0.6)                          # sidebar elements slide in after the title
    bx, by, bs = L["bug"]
    s0 = getattr(TL, "STING_T0", -99.0)
    a = k_in
    if s0 <= T < s0 + 2.9:
        a = 0.0 if T < s0 + 2.75 else 1.0
    S.draw_bug(fr, bx, by, a, size=bs)
    tx, ty, tw, tsize = L["topic"]
    step_on = [st for st in TL.STEPS if st[0] <= T < st[1] and kind == "phone"]
    if REEL:
        y_cap = 1330
        if step_on:
            t0, t1, n, label = step_on[0]
            fa = ease_out((T - t0) / 0.35) * (1 - ease_io((T - (t1 - 0.25)) / 0.25))
            S.draw_step(fr, L["step"][0], L["step"][1], n, TL.N_STEPS, label, fa, size=L["step"][2], width=L["step"][3])
            y_cap = 1470
        else:
            S.draw_topic(fr, tx, ty, TL.TOPIC_KICKER, TL.TOPIC_SHORT, k_in, width=tw, size=tsize, t=T)
            y_cap = 1450
        draw_captions(fr, T, y_cap)
    else:
        yb = S.draw_topic(fr, tx, ty, TL.TOPIC_KICKER, TL.TOPIC, k_in, width=tw, size=tsize, t=T)
        S.draw_rule(fr, tx, yb + 26, 120 * k_in, k_in)
        draw_captions(fr, T, L["cap"][1])
        if step_on:
            t0, t1, n, label = step_on[0]
            fa = ease_out((T - t0) / 0.35) * (1 - ease_io((T - (t1 - 0.25)) / 0.25))
            S.draw_step(fr, L["step"][0], L["step"][1], n, TL.N_STEPS, label, fa, size=L["step"][2], width=L["step"][3])
    draw_ctas(fr, T, u)
    sx, sy, ss, sname = L["sting"]
    import aurora as A
    A.draw_sting(fr, T - s0, sx, sy, size=ss, bug=(bx, by, bs), name=sname)


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
            fr = {"push": S.push, "scan": S.scan, "prism": S.prism}[tk](fr, p)
    if CUTS and u is not None:
        for (us, a, b) in CUTS[1:]:
            p = (u - us) / 0.30
            if -1 < p < 1:
                fr = S.push(fr, p)
    return fr


def render_frame(T, u=None):
    sc = scene_at(T)
    if sc["kind"] == "title":
        base, _ = face_crop(T, W, H, 1.0, 0.5, 0.42)
        fr = TITLE.background(base, T)
        TITLE.draw(fr, T)
        fr = transitions(np.ascontiguousarray(fr), T, u)
    else:
        fr = BACK_FULL.copy()
        pic = transitions(picture(T, sc), T, u)
        t_end = TITLE.span()[1]
        k = ease_out((T - t_end) / 0.5)                         # the card settles into place after the title
        if k < 1:
            sc_ = lerp(1.06, 1.0, k)
            M = np.array([[sc_, 0, (1 - sc_) * PW / 2], [0, sc_, (1 - sc_) * PH / 2]], np.float32)
            pic = cv2.warpAffine(pic, M, (PW, PH), borderMode=cv2.BORDER_REFLECT)
        CARD.compose(fr, np.clip(pic, 0, 1))
    fr = np.ascontiguousarray(np.clip(fr, 0, 1), dtype=np.float32)
    draw_overlays(fr, T, sc, u)
    for (t0, t1, hd) in HEADERS:
        if t0 - 0.05 <= T < t1 + 0.4:
            k = ease_out((T - t0) / 0.3) * (1 - ease_io((T - t1) / 0.36))
            fr *= 1 - 0.66 * k
            hd.draw(fr, T - t0)
    now = u if (CUTS and u is not None) else T
    fade = 1 - clamp01((now - NARR) / (TAIL - 0.04))
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
