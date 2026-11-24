#!/usr/bin/env python3
"""V Create "Mist" compositor (16:9 YouTube or 9:16 Short) for projects whose timeline sets STYLE = "mist".

A moody thriller-film look (lib/grade_moody.py: green, misty, desaturated, skin kept warm) with film-title type
(lib/mist.py: Big Shoulders Display, Albert Sans, JetBrains Mono; bone white + one blood-red accent).

* Talking head: full-bleed graded shot; a green-black shade on the free side (left in 16:9, top in 9:16) carries the
  chapter rail (number + name + a red line that fills over the chapter), chapter slates, notes, prompts and the
  word-by-word subtitles.  The opening 3D title sits in that free column: the presenter's face is never covered,
  dimmed or blurred.
* App demos (16:9): split frame - the iPhone on a dark misty stage on the left, the presenter in a tall panel on the
  right; steps and subtitles in the stage's left column.  9:16: the iPhone floats over the softened shot, below the
  top band.
* B-roll from Mixkit; every scene change is a film-burn dissolve; the Short's joins are hidden by alternating the
  framing (wide / close) so they read as camera cuts, with no dip and no whoosh.

usage:
  render_mist.py --project NAME --format wide|reel --face main.mp4 --screen screen_clean.mp4 --broll-dir DIR --out x.mp4
  render_mist.py ... --frames 1.5,20,40 --out-dir stills/
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
import mist as MS, phonescene, pop, timeline as TL, captions_data as CD
from grade_moody import MoodyGrader
from gfx import ease_io, ease_out, clamp01, lerp, blend

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--format", choices=["wide", "reel"], default="wide")
ap.add_argument("--face", required=True)
ap.add_argument("--screen", required=True)
ap.add_argument("--broll-dir", required=True)
ap.add_argument("--out", default=None)
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float, default=None)
ap.add_argument("--frames", default=None)
ap.add_argument("--out-dir", default=None)
ap.add_argument("--crf", type=int, default=16)
ap.add_argument("--preset", default="medium")
args = ap.parse_args()

REEL = args.format == "reel"
W, H = (1080, 1920) if REEL else (1920, 1080)
FPS = TL.FPS
TAIL = 0.35
CUTS = SEGS = None
if REEL and getattr(TL, "REEL_CUTS", None):
    PRE, POST = TL.REEL_PAD
    CUTS, SEGS, u = [], [], 0.0
    for a, b in TL.REEL_CUTS:
        SEGS.append((a, b))
        a2, b2 = max(a - PRE, 0.0), min(b + POST, TL.NARR_END)
        CUTS.append((u, a2, b2))
        u += b2 - a2
    REEL_NARR = u
NARR = REEL_NARR if CUTS else TL.NARR_END
TOTAL = NARR + TAIL
END_T = args.end if args.end is not None else TOTAL

# ---- layout ---------------------------------------------------------------------------------------------------
PANEL_X = 1240                                       # 16:9 split: presenter panel from here to the right edge
if REEL:
    L = dict(bug=(986, 300, 80), rail=(64, 236), chap=(64, 282, 64), key=(64, 290), step=(64, 290),
             cap=(64, 446, 940, 50, 3, "top"), cap_phone=(64, 446, 940, 48, 3, "top"), cta=[(64, 372)],
             phone_hb=0.50, phone_anchor=(0.5, 0.665), x_min=24, tag_x=(30, W - 30))
else:
    L = dict(bug=(1826, 86, 84), rail=(64, 58), chap=(64, 112, 60), key=(64, 300), step=(64, 300),
             cap=(64, 1000, 680, 46, 2, "bottom"), cap_phone=(56, 1000, 430, 38, 3, "bottom"),
             cta=[(64, 560), (64, 650)], phone_hb=0.86, phone_anchor=(0.43, 0.5), x_min=520, tag_x=(500, PANEL_X - 12))
SHADE = MS.side_shade(W, H, REEL)
TITLE_SHADE = MS.side_shade(W, H, REEL, strength=0.80)
STAGE_SHADE = SHADE * 0.5 + 0.5
LOGO = os.path.join(HERE, "assets", "logo", getattr(TL, "LOGO", "vcreate.png"))

# ---- readers --------------------------------------------------------------------------------------------------
FW, FH = 2880, 1620
face_reader = pop.SeekReader(args.face, FW, FH, 30.0, f"scale={FW}:{FH}:flags=lanczos", jump=60)
SW_, SH_ = TL.SCREEN_SIZE
SFPS = float(TL.SCREEN_FPS)
screen_reader = pop.SeekReader(args.screen, SW_, SH_, SFPS, "null", jump=int(4 * SFPS))
N_SCREEN = int(round((TL.SCREEN_END - TL.SCREEN_T0) * SFPS)) - 1
_broll = {}


def broll_reader(sc):
    name = sc["name"]
    if name not in _broll:
        sp = sc.get("speed", 1.0)
        cx = sc.get("reel_cx", 0.5) if REEL else sc.get("cx", 0.5)
        spf = f"setpts=PTS/{sp}," if sp != 1.0 else ""
        vf = (f"{spf}scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos:in_color_matrix=bt709,"
              f"crop={W}:{H}:(iw-{W})*{cx}:(ih-{H})/2,fps=30")
        _broll[name] = pop.SeekReader(os.path.join(args.broll_dir, f"{sc['clip']}.mp4"), W, H, 30.0, vf, t_off=sc.get("clip_t", 0.0), jump=60)
    return _broll[name]


GM = TL.GRADE_MOODY
GR = MoodyGrader(W, H, GM)
REEL_TOP = 640
if REEL:
    GR_REEL = MoodyGrader(W, H - REEL_TOP, GM)
    _f = np.clip(np.arange(H - REEL_TOP, dtype=np.float32) / 170.0, 0, 1)
    REEL_FEATHER = (_f * _f * (3 - 2 * _f))[:, None, None]
    _p = np.clip((np.arange(H, dtype=np.float32) - 640.0) / 150.0, 0, 1)
    PHONE_FADE = (_p * _p * (3 - 2 * _p))[:, None, None]
_SMALL = dict(GM, base=dict(GM.get("base", {}), grain=0.0, vignette=0.0, halation=0.0, bloom=0.0))
GR_SMALL = MoodyGrader(W // 4, H // 4, _SMALL)
PW = W - PANEL_X
GR_PANEL = None if REEL else MoodyGrader(PW, H, dict(GM, base=dict(GM.get("base", {}), vignette=0.40)))
GR_BROLL = MoodyGrader(W, H, dict(GM, base=dict(GM.get("base", {}), face_lift=0.0, **getattr(TL, "BROLL_GRADE", {}))))

ps = phonescene.PhoneScene(1, None, W, H, layout="wide", hb_frac=L["phone_hb"], anchor=L["phone_anchor"], x_min=L["x_min"],
                           titanium=((120, 128, 122), (40, 46, 42)), bg=np.zeros((10, 10, 3), np.float32), src=(SW_, SH_))
if REEL:
    TITLE = MS.MistTitle(W, H, TL.TITLE_BEATS_REEL, 0.5, 0.245, (0.86, 0.135))
else:
    TITLE = MS.MistTitle(W, H, TL.TITLE_BEATS, 0.19, 0.46, (0.30, 0.36))

# ---- face -----------------------------------------------------------------------------------------------------
_ft_path = os.path.join(_project_dir(), "face_track.json")
_FT = json.load(open(_ft_path)) if os.path.exists(_ft_path) else None


def face_at(T):
    if _FT is None:
        return TL.FACE_ANCHOR["fx"], TL.FACE_ANCHOR["fy"]
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


_SEG_IDX = [0]                                       # reel: index of the current Short segment (framing alternates)


def face_shot(T, sc):
    z0, z1 = sc.get("zoom", (1.0, 1.04))
    prog = clamp01((T - sc["t0"]) / max(sc["t1"] - sc["t0"], 0.1))
    z = lerp(z0, z1, ease_io(prog))
    if REEL:
        z *= 1.0 if _SEG_IDX[0] % 2 == 0 else 1.13      # wide / close on alternate Short segments
        hh = H - REEL_TOP
        pic, (fx, fy) = face_crop(T, W, hh, max(z, 1.0), 0.5, 0.40)     # zoom >= 1: the shot always fills its area
        pic = np.clip(GR_REEL(pic, face=(fx, fy - 0.02, 0.30, 0.22), center=(fx, 0.45)), 0, 1)
        small, _ = face_crop(T, W // 4, H // 4, 1.0, 0.5, 0.50)
        bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 6), (W, H), interpolation=cv2.INTER_CUBIC)
        bg = GR_SMALL(cv2.resize(bg, (W // 4, H // 4)), grain_on=False)
        bg = cv2.resize(bg, (W, H), interpolation=cv2.INTER_CUBIC) * 0.30
        out = bg.copy()
        out[REEL_TOP:] = bg[REEL_TOP:] * (1 - REEL_FEATHER) + pic * REEL_FEATHER
        return out
    fr, (fx, fy) = face_crop(T, W, H, z, sc.get("tx", 0.58), 0.44)
    return np.clip(GR(fr, face=(fx, fy - 0.02, 0.20, 0.30), center=(fx, 0.5)), 0, 1)


def blurred_bg(T, dark=0.36):
    """Soft, dark misty backdrop for phone segments: the shot at 1/4 size, graded, blurred and pushed down."""
    fr, (fx, fy) = face_crop(T, W // 4, H // 4, 1.15, 0.5, 0.45)
    g = GR_SMALL(fr, face=(fx, fy, 0.3, 0.3), center=(0.5, 0.5), grain_on=False)
    g = cv2.GaussianBlur(g, (0, 0), 7)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
    return np.clip(g * dark, 0, 1)


_BGV = None


def _bg_vignette():
    global _BGV
    if _BGV is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx = 0.5 if REEL else (L["phone_anchor"][0])
        d = np.hypot((xx / W - cx) * 1.2, yy / H - 0.55)
        _BGV = (1 - 0.60 * np.clip(d / 0.8, 0, 1) ** 1.6)[..., None].astype(np.float32)
    return _BGV


# ---- phone ----------------------------------------------------------------------------------------------------
def screen_frame(T):
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - TL.SCREEN_T0) * SFPS)), 0), N_SCREEN)
    return screen_reader.get(idx)


def phone_layer(T, sc, shade=None):
    fr = blurred_bg(T) * _bg_vignette()
    if shade is not None:
        fr *= shade
    screen = screen_frame(T)
    cam = phonescene.cam_at(T, TL.CAMERA_REEL if REEL and hasattr(TL, "CAMERA_REEL") else TL.CAMERA)
    enter = ease_out(clamp01((T - sc["t0"]) / 0.7))
    g = ps.geometry(cam, extra=(0.0, (1 - enter) * 0.14 * H))
    g["sway"] = 2.0 * math.sin(2 * math.pi * T / 7.0)
    lay = ps.layer(screen, g, sway=g["sway"])
    if REEL:                                   # keep the top band clear: the zoomed phone fades out under it
        lay = lay * PHONE_FADE
    a = lay[..., 3]
    small = cv2.resize(a, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    sh = cv2.GaussianBlur(small, (0, 0), 7)
    sh = cv2.resize(sh, (W, H), interpolation=cv2.INTER_LINEAR)
    sh = np.roll(sh, 26, axis=0)[..., None] * 0.78
    fr = fr * (1 - sh)
    fr = fr * (1 - a[..., None]) + lay[..., :3]
    return fr, g


def panel(T, sc):
    """The presenter in the tall right-hand panel of the 16:9 split frame (slow push-in)."""
    prog = clamp01((T - sc["t0"]) / max(sc["t1"] - sc["t0"], 0.1))
    z = lerp(1.00, 1.05, ease_io(prog))
    pic, (fx, fy) = face_crop(T, PW, H, z, 0.5, 0.40)
    return np.clip(GR_PANEL(pic, face=(fx, fy - 0.02, 0.30, 0.22), center=(fx, 0.45)), 0, 1)


def to_out(g, u, v):
    x, y = ps.to_out(g, u, v)
    return x, y + g["sway"]


def phone_marks(fr, T, g):
    stage = fr if REEL else fr[:, :PANEL_X]
    for h in TL.HIGHLIGHTS:
        t0, t1, (u0, v0, u1, v1) = h[:3]
        lab = h[3] if len(h) > 3 else ""
        if t0 - 0.25 <= T <= t1 + 0.3:
            a = ease_out((T - (t0 - 0.25)) / 0.3) * (1 - ease_io((T - t1) / 0.3))
            x0, y0 = to_out(g, u0, v0)
            x1, y1 = to_out(g, u1, v1)
            r = (x0, y0, x1, y1)
            MS.spotlight(stage, r, a, radius=20, dim=0.55)
            MS.brackets(stage, r, T - t0, a)
            # (labels stay in the timeline as notes: the step line says it, and a tag would cover the app's own UI)
    for (tt, u, v) in TL.TAPS:
        if tt - 0.15 <= T <= tt + 0.95:
            x, y = to_out(g, u, v)
            MS.tap(stage, x, y, T - tt)


# ---- B-roll ---------------------------------------------------------------------------------------------------
def broll_shot(T, sc):
    rd = broll_reader(sc)
    src = rd.get(int(round((T - sc["t0"]) * 30)))
    prog = clamp01((T - sc["t0"]) / (sc["t1"] - sc["t0"]))
    z = 1.02 + 0.05 * prog
    M = np.array([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * H / 2]], np.float32)
    fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255.0
    return np.clip(GR_BROLL(fr, face=(0.5, 0.45, 0.5, 0.5), center=(0.5, 0.5)), 0, 1)


# ---- scene picture --------------------------------------------------------------------------------------------
def scene_at(T):
    for sc in TL.SCENES:
        if sc["t0"] <= T < sc["t1"]:
            return sc
    return TL.SCENES[-1]


def picture(T, sc):
    """-> (frame with phone marks, phone geometry or None).  16:9 phone scenes come back as the full split frame."""
    k = sc["kind"]
    k_t = title_on(T)
    sh = SHADE if k_t <= 0.001 else SHADE * (1 - k_t) + TITLE_SHADE * k_t
    if k in ("face", "title"):
        return face_shot(T, sc if k == "face" else dict(sc, zoom=sc.get("zoom", (1.0, 1.0)))) * sh, None
    if k == "broll":
        return broll_shot(T, sc) * sh, None
    fr, g = phone_layer(T, sc, shade=sh if REEL else STAGE_SHADE)
    phone_marks(fr, T, g)
    if not REEL:
        fr[:, PANEL_X:] = panel(T, sc)
        fr[:, PANEL_X:PANEL_X + 2] = fr[:, PANEL_X:PANEL_X + 2] * 0.45 + MS.BONEF * 0.55        # hairline
        fr[60:150, PANEL_X:PANEL_X + 4] = MS.REDF                                                # red tick
    return fr, g


def seg_bounds(T):
    """Short: the padded kept segment that contains T (None in the 16:9 edit)."""
    if not SEGS:
        return None
    for a, b in SEGS:
        a2, b2 = max(a - TL.REEL_PAD[0], 0.0), min(b + TL.REEL_PAD[1], TL.NARR_END)
        if a2 - 1e-6 <= T < b2 + 1e-6:
            return a2, b2
    return None


def scene_for(T):
    """Short: a scene change that falls just after a join (or just before one) is moved onto the join itself, so the
    join is one clean camera cut - no half dissolve, no one-frame flash of the other framing."""
    sc = scene_at(T)
    sb = seg_bounds(T)
    if sb is None:
        return sc
    a2, b2 = sb
    for t in TL.MIXES:
        if a2 < t <= a2 + 0.4 and T < t:
            return scene_at(t)
        if b2 - 0.4 <= t < b2 and T >= t:
            return scene_at(t - 1e-3)
    return sc


def mix_ok(t, T):
    """A dissolve at scene change t is drawn only if it lies wholly inside the kept segment (Short) - never across a join."""
    sb = seg_bounds(T)
    return sb is None or (sb[0] <= t - MIX / 2 and t + MIX / 2 <= sb[1])


def prev_scene(sc):
    i = TL.SCENES.index(sc)
    return TL.SCENES[i - 1] if i > 0 else None


# ---- overlays -------------------------------------------------------------------------------------------------
def seg_of(T):
    if not SEGS:
        return None
    best = None
    for (a, b) in SEGS:
        if a - TL.REEL_PAD[0] - 1e-6 <= T < b + TL.REEL_PAD[1] + 1e-6:
            best = (a, b)
    return best


def active_chunk(T):
    seg = seg_of(T)
    best = None
    for i, c in enumerate(CD.CHUNKS):
        if seg and not (seg[0] - 0.15 <= c[0] < seg[1] - 0.08):
            continue
        if c[0] - 0.02 <= T:
            best = i
    if best is None:
        return None
    c = CD.CHUNKS[best]
    nxt = CD.CHUNKS[best + 1][0] if best + 1 < len(CD.CHUNKS) else 1e9
    if T > c[1] + 0.45 and T < nxt:
        return None
    return best


def title_on(T):
    t_end = TITLE.span()[1]
    return 1 - ease_out((T - t_end) / 0.3)


KEYW = {w.lower() for w in getattr(TL, "KEY_WORDS", [])}


def _key_idx(words):
    out = set()
    clean = ["".join(c for c in w if c.isalnum()).lower() for w in words]
    for i, w in enumerate(clean):
        if w in KEYW:
            out.add(i)
    for i in range(len(words) - 1):
        if clean[i] + " " + clean[i + 1] in KEYW:
            out |= {i, i + 1}
    return out


def draw_captions(fr, T, spec):
    hide = 1.0 if not REEL else 1.0 - title_on(T)
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
    fin = clamp01((T - c[0] + 0.02) / 0.14)
    fout = 1.0 - clamp01((T - (c[1] + 0.30)) / 0.16)
    nxt = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
    if nxt - c[0] < 0.6:
        fout = 1.0
    x, y, mw, size, lines, align = spec
    img = MS.caption_img(words, act, age, _key_idx(words), size, mw, lines_max=lines)
    p = img.pad
    rise = (1 - ease_out(fin)) * 12
    yy = (y - (img.height - 2 * p) if align == "bottom" else y) + rise
    blend(fr, img, x - p, yy - p, fin * fout * hide)


def chapter_now(T):
    cur = None
    for ch in TL.CHAPTERS:
        if ch[0] <= T:
            cur = ch
    return cur


def slate_t0(t0):
    """When a chapter slate starts: the chapter's first word, or in the Short the first kept moment of the chapter."""
    if not SEGS:
        return t0
    for a, b in SEGS:
        a2, b2 = a - TL.REEL_PAD[0], b + TL.REEL_PAD[1]
        if b2 > t0:
            return max(t0, a2)
    return t0


SLATES = [(slate_t0(t0), n, title) for t0, t1, n, title in TL.CHAPTERS]


def slate_on(T):
    for t0, n, title in SLATES:
        if t0 - 0.05 <= T <= t0 + TL.CHAPTER_SLATE + 0.4:
            return True
    return False


def draw_chapter(fr, T, sc):
    x, y, size = L["chap"]
    if sc["kind"] == "phone" and not REEL:
        x, size = L["step"][0], 50
    for t0, n, title in SLATES:
        MS.chapter(fr, T - t0, TL.CHAPTER_SLATE, n, title, x, y, size=size)


def draw_rail(fr, T, sc):
    """Persistent chapter rail: 'CH 03  SET IT UP' in mono + a hairline that fills red over the chapter."""
    ch = chapter_now(T)
    if ch is None:
        return
    t0, t1, n, title = ch
    a = ease_out((T - TITLE.span()[1] - 0.2) / 0.5) * (1 - title_on(T))
    if slate_on(T):
        st = next(s0 for s0, nn, _ in SLATES if nn == n)
        a *= 0.0 if T - st < TL.CHAPTER_SLATE else ease_out((T - st - TL.CHAPTER_SLATE) / 0.4)
    if a <= 0.01:
        return
    x, y = L["rail"]
    lab = MS.label(f"CH {n:02d}", "mono", 18 if not REEL else 22, MS.RED, tracking=0.2)
    MS.put(fr, lab, x, y, a)
    nm = MS.label(title.upper(), "mono", 18 if not REEL else 22, MS.FOG, tracking=0.16)
    MS.put(fr, nm, x + lab.width - 2 * lab.pad + 18, y, a)
    wl = 260 if not REEL else 360
    yy = int(y + (34 if not REEL else 40))
    prog = clamp01((T - t0) / max(t1 - t0, 0.1))
    fr[yy:yy + 2, x:x + wl] = fr[yy:yy + 2, x:x + wl] * (1 - 0.35 * a) + MS.BONEF * 0.35 * a
    xf = int(x + wl * prog)
    if xf > x:
        fr[yy - 1:yy + 3, x:xf] = fr[yy - 1:yy + 3, x:xf] * (1 - a) + MS.REDF * a


def draw_steps(fr, T):
    if slate_on(T):
        return
    x, y = L["step"]
    started = [st for st in TL.STEPS if st[0] <= T]
    if not started:
        return
    t0, t1, n, label = started[-1]                # only the latest step: a new step replaces the previous one outright
    if not (t0 <= T <= t1 + 0.4):
        return
    a = clamp01((T - t0) / 0.2) * (1 - ease_io((T - t1) / 0.35))
    size = 34 if not REEL else 40
    kick = MS.label(f"STEP {n:02d}", "mono", 20 if not REEL else 24, MS.RED, tracking=0.22)
    MS.reveal(fr, kick, x, y, clamp01((T - t0) / 0.35), a)
    lines = MS.wrap(label, "text8", size, 420 if not REEL else 900)
    for k, ln in enumerate(lines[:2]):
        img = MS.label(ln, "text8", size, MS.BONE)
        MS.reveal(fr, img, x, y + (32 if not REEL else 38) + k * size * 1.18, clamp01((T - t0 - 0.06 - 0.05 * k) / 0.4), a)


def draw_keys(fr, T, sc):
    for t0, t1, text in getattr(TL, "KEY_POINTS", []):
        if t0 <= T <= t1 + 0.4:
            if REEL and (slate_on(T) or any(st[0] <= T <= st[1] + 0.4 for st in TL.STEPS)):
                continue
            x, y = L["key"]
            MS.key_line(fr, T - t0, t1 - t0, text, x, y, size=46 if not REEL else 48, max_w=600 if not REEL else 940)


def draw_bug(fr, T):
    x, y, s = L["bug"]
    k = ease_out((T - TITLE.span()[1] - 0.2) / 0.5)
    if k <= 0.01:
        return
    img = MS.logo_bug(s, LOGO)
    blend(fr, img, x - img.width / 2, y - img.height / 2, k * 0.92)


def draw_ctas(fr, T):
    slots = L["cta"]
    ctas = TL.REEL_CTAS if REEL and hasattr(TL, "REEL_CTAS") else TL.CTAS
    busy = [-1e9] * len(slots)
    for t0, what in sorted(ctas):
        k = 0
        while k < len(slots) - 1 and busy[k] > t0:
            k += 1
        busy[k] = t0 + 3.7
        t = T - t0
        if -0.1 <= t <= 3.7:
            x, y = slots[k]
            MS.cta(fr, what, t, x, y, scale=1.0 if not REEL else 1.05)


# ---- frame ----------------------------------------------------------------------------------------------------
MIX = 0.6


def base_frame(T, sc):
    fr, g = picture(T, sc)
    i = TL.SCENES.index(sc)
    if sc["t0"] in TL.MIXES and T - sc["t0"] < MIX / 2 and mix_ok(sc["t0"], T):
        pv = prev_scene(sc)
        if pv is not None:
            fa, _ = picture(T, pv)
            p = (T - sc["t0"] + MIX / 2) / MIX
            fr = MS.burn_mix(fa, fr, p)
            g = g if p > 0.5 else None
    nxt = TL.SCENES[i + 1] if i + 1 < len(TL.SCENES) else None
    if nxt is not None and nxt["t0"] in TL.MIXES and nxt["t0"] - T < MIX / 2 and mix_ok(nxt["t0"], T):
        fb, _ = picture(T, nxt)
        p = (T - nxt["t0"] + MIX / 2) / MIX
        fr = MS.burn_mix(fr, fb, p)
        g = g if p < 0.5 else None
    return np.ascontiguousarray(fr, dtype=np.float32), g


def render_frame(T, u=None):
    sc = scene_for(T)
    fr, g = base_frame(T, sc)
    ph = sc["kind"] == "phone"
    if T < TITLE.span()[1] + 0.45:
        TITLE.draw(fr, T)
    draw_bug(fr, T)
    draw_rail(fr, T, sc)
    draw_chapter(fr, T, sc)
    if ph:
        draw_steps(fr, T)
    else:
        draw_keys(fr, T, sc)
    draw_ctas(fr, T)
    draw_captions(fr, T, L["cap_phone"] if ph else L["cap"])
    now = u if (CUTS and u is not None) else T
    fade_in = clamp01(now / 0.5)
    fade = (1 - clamp01((now - NARR) / (TAIL - 0.04))) * (0.3 + 0.7 * fade_in)
    return np.clip(fr * fade, 0, 1)


def u_to_T(u):
    for k, (us, a, b) in enumerate(CUTS):
        if u < us + (b - a):
            _SEG_IDX[0] = k
            return a + (u - us)
    _SEG_IDX[0] = len(CUTS) - 1
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
