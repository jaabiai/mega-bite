#!/usr/bin/env python3
"""V Create "Signal" compositor (16:9 YouTube or 9:16 reel) for projects whose timeline sets STYLE = "signal".

Cinematic keynote look: the shot runs full-bleed with a film grade (lib/grade_cine.py, TL.GRADE) and a cut-to-cut
framing (wide / close, TL.SCENES zoom); a graphite shade on the free side (left in 16:9, top in 9:16) carries the tip
counter (a numbered ring that fills from the first to the last word of each tip, TL.TIPS), the step line (TL.STEPS),
key points (TL.KEY_POINTS) and karaoke captions with key words in lime serif italic (TL.KEY_WORDS).  Each tip opens
with a full-frame numeral card.  Phone segments float the iPhone over a blurred, darkened copy of the shot, with camera
moves (TL.CAMERA), a spotlight + lime frame (TL.HIGHLIGHTS) and taps; B-roll (TL.SCENES kind "broll") comes from
Mixkit.  Scene changes are lens-blur crossfades (TL.MIXES).  Nothing is drawn on the presenter's face or body.

usage:
  render_signal.py --project NAME --format wide|reel --face main.mp4 --screen screen_clean.mp4 --broll-dir DIR --out x.mp4
  render_signal.py ... --frames 1.5,20,40 --out-dir stills/
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
import signalkit as SG, phonescene, pop, timeline as TL, captions_data as CD
from grade_cine import Grader
from gfx import ease_io, ease_out, ease_back, clamp01, lerp, blend

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
if REEL:
    L = dict(bug=(986, 300, 82), tip=(118, 318, 50), step=(64, 396), key=None, cap=(64, 480, 930, 50),
             cap_phone=(64, 500, 930, 46), cta=[(64, 318)], phone_hb=0.47, phone_anchor=(0.5, 0.66), pip=None, x_min=24)
else:
    L = dict(bug=(1818, 92, 92), tip=(150, 150, 54), step=(96, 262), key=(96, 300), cap=(70, 820, 760, 48),
             cap_phone=(70, 820, 700, 46), cta=[(96, 650), (96, 740)], phone_hb=0.90, phone_anchor=(0.66, 0.5),
             pip=(1556, 806, 300, 169), x_min=880)
SHADE = SG.side_shade(W, H, REEL)
SHADE_PHONE = SG.side_shade(W, H, REEL, strength=0.45)
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


GR = Grader(W, H, TL.GRADE)
REEL_TOP = 640
GR_REEL = Grader(W, H - REEL_TOP, TL.GRADE) if REEL else None
if REEL:
    _f = np.clip(np.arange(H - REEL_TOP, dtype=np.float32) / 170.0, 0, 1)
    REEL_FEATHER = (_f * _f * (3 - 2 * _f))[:, None, None]
GR_SMALL = Grader(W // 4, H // 4, dict(TL.GRADE, grain=0.0, vignette=0.0, halation=0.0, bloom=0.0))
PIP = L["pip"]
GR_PIP = Grader(PIP[2], PIP[3], dict(TL.GRADE, vignette=0.1)) if PIP else None
GR_BROLL = Grader(W, H, dict(TL.GRADE, face_lift=0.0, **getattr(TL, "BROLL_GRADE", {})))

ps = phonescene.PhoneScene(1, None, W, H, layout="wide", hb_frac=L["phone_hb"], anchor=L["phone_anchor"], x_min=L["x_min"],
                           titanium=((132, 136, 140), (48, 50, 54)), bg=np.zeros((10, 10, 3), np.float32), src=(SW_, SH_))
TITLE = SG.SignalTitle(W, H, TL.TITLE_BEATS_REEL if REEL else TL.TITLE_BEATS, box=(0.86, 0.22) if REEL else (0.74, 0.34))

# ---- face -----------------------------------------------------------------------------------------------------
_ft_path = os.path.join(_project_dir(), "face_track.json")
_FT = json.load(open(_ft_path)) if os.path.exists(_ft_path) else None


def face_at(T):
    if _FT is None:
        return TL.FACE_ANCHOR["fx"], TL.FACE_ANCHOR["fy"]
    return float(np.interp(T, _FT["t"], _FT["x"])), float(np.interp(T, _FT["t"], _FT["y"]))


def face_crop(T, w, h, zoom=1.0, tx=0.5, ty=0.42, fx_bias=0.0):
    src = face_reader.get(int(round(T * 30)))
    fx, fy = face_at(T)
    fx += fx_bias
    s_ = max(w / FW, h / FH) * zoom
    x0 = min(max(fx * FW * s_ - tx * w, 0.0), FW * s_ - w)
    y0 = min(max(fy * FH * s_ - ty * h, 0.0), FH * s_ - h)
    M = np.array([[s_, 0, -x0], [0, s_, -y0]], np.float32)
    interp = cv2.INTER_AREA if s_ < 0.8 else (cv2.INTER_LINEAR if s_ < 1.0 else cv2.INTER_CUBIC)
    fr = cv2.warpAffine(src, M, (w, h), flags=interp).astype(np.float32) / 255.0
    return fr, ((fx * FW * s_ - x0) / w, (fy * FH * s_ - y0) / h)


def face_shot(T, sc):
    """Full-frame graded face. 16:9 keeps the source framing (face right of centre); 9:16 centres the face low."""
    z0, z1 = sc.get("zoom", (1.0, 1.04))
    prog = clamp01((T - sc["t0"]) / max(sc["t1"] - sc["t0"], 0.1))
    z = lerp(z0, z1, ease_io(prog))
    if REEL:
        # the presenter sits in the lower 66 % of the frame; above him a soft, dark extension of the same shot keeps the
        # top clear for the tip counter, steps and captions
        top = REEL_TOP
        hh = H - top
        pic, (fx, fy) = face_crop(T, W, hh, z * 0.9, 0.5, 0.40)
        pic = np.clip(GR_REEL(pic, face=(fx, fy - 0.02, 0.30, 0.22), center=(fx, 0.45)), 0, 1)
        small, _ = face_crop(T, W // 4, H // 4, 1.0, 0.5, 0.50)
        bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 6), (W, H), interpolation=cv2.INTER_CUBIC) * 0.30
        out = bg.copy()
        m = REEL_FEATHER
        out[top:] = bg[top:] * (1 - m) + pic * m
        return out
    else:
        fr, (fx, fy) = face_crop(T, W, H, z, sc.get("tx", 0.60), 0.44)
    return np.clip(GR(fr, face=(fx, fy - 0.02, 0.20 if not REEL else 0.30, 0.30 if not REEL else 0.18), center=(fx, 0.5)), 0, 1)


def blurred_bg(T):
    """Soft, dark backdrop for phone segments: the shot at 1/4 size, graded, blurred and pushed down."""
    fr, (fx, fy) = face_crop(T, W // 4, H // 4, 1.15, 0.5, 0.45)
    g = GR_SMALL(fr, face=(fx, fy, 0.3, 0.3), center=(0.5, 0.5), grain_on=False)
    g = cv2.GaussianBlur(g, (0, 0), 7)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return np.clip(g * 0.42, 0, 1)


_BGV = None


def _bg_vignette():
    global _BGV
    if _BGV is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot((xx / W - 0.62 if not REEL else xx / W - 0.5) * 1.2, yy / H - 0.55)
        _BGV = (1 - 0.55 * np.clip(d / 0.8, 0, 1) ** 1.6)[..., None].astype(np.float32)
    return _BGV


# ---- phone ----------------------------------------------------------------------------------------------------
def screen_frame(T):
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - TL.SCREEN_T0) * SFPS)), 0), N_SCREEN)
    return screen_reader.get(idx)


def phone_shot(T, sc):
    fr = blurred_bg(T) * _bg_vignette()
    screen = screen_frame(T)
    cam = phonescene.cam_at(T, TL.CAMERA_REEL if REEL and hasattr(TL, "CAMERA_REEL") else TL.CAMERA)
    enter = ease_out(clamp01((T - sc["t0"]) / 0.7))
    g = ps.geometry(cam, extra=(0.0, (1 - enter) * 0.18 * H))
    g["sway"] = 2.0 * math.sin(2 * math.pi * T / 7.0)
    lay = ps.layer(screen, g, sway=g["sway"])
    a = lay[..., 3]
    small = cv2.resize(a, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    sh = cv2.GaussianBlur(small, (0, 0), 7)
    sh = cv2.resize(sh, (W, H), interpolation=cv2.INTER_LINEAR)
    sh = np.roll(sh, 26, axis=0)[..., None] * 0.75
    fr = fr * (1 - sh)
    fr = fr * (1 - a[..., None]) + lay[..., :3]
    return fr, g


def to_out(g, u, v):
    x, y = ps.to_out(g, u, v)
    return x, y + g["sway"]


def phone_marks(fr, T, g):
    for h in TL.HIGHLIGHTS:
        t0, t1, (u0, v0, u1, v1) = h[:3]
        lab = h[3] if len(h) > 3 else ""
        if t0 - 0.25 <= T <= t1 + 0.3:
            a = ease_out((T - (t0 - 0.25)) / 0.3) * (1 - ease_io((T - t1) / 0.3))
            x0, y0 = to_out(g, u0, v0)
            x1, y1 = to_out(g, u1, v1)
            r = (x0, y0, x1, y1)
            SG.spotlight(fr, r, a, radius=20, dim=0.55)
            SG.frame_box(fr, r, T - t0, a)
            if lab:
                SG.callout(fr, r, lab, T - t0, a, side="right" if not REEL else "left", size=30 if not REEL else 34,
                           max_x=W - 40)
    for (tt, u, v) in TL.TAPS:
        if tt - 0.15 <= T <= tt + 0.95:
            x, y = to_out(g, u, v)
            SG.tap(fr, x, y, T - tt)


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
    """-> (frame, phone geometry or None)"""
    k = sc["kind"]
    if k == "face" or k == "title":
        return face_shot(T, sc if k == "face" else dict(sc, zoom=(1.0, 1.0))), None
    if k == "broll":
        return broll_shot(T, sc), None
    fr, g = phone_shot(T, sc)
    return fr, g


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


def card_on(T):
    """Strength (0..1) of a tip card on screen."""
    k = 0.0
    for t0, t1, n, title, sub in TL.TIPS:
        cd = getattr(TL, "TIP_CARD", 2.2)
        if t0 - 0.1 <= T <= t0 + cd + 0.4:
            k = max(k, ease_out((T - t0 + 0.1) / 0.3) * (1 - ease_io((T - t0 - cd) / 0.35)))
    return k


def cap_hide(T):
    t_end = TITLE.span()[1]
    k = 1 - ease_out((T - t_end) / 0.3)
    return 1.0 - max(k, card_on(T))


KEYW = {w.lower() for w in getattr(TL, "KEY_WORDS", [])}


def _key_idx(words):
    out = set()
    for i, w in enumerate(words):
        clean = "".join(c for c in w if c.isalnum() or c in "-'").lower()
        if clean in KEYW:
            out.add(i)
    # two-word keys ("assistive touch")
    for i in range(len(words) - 1):
        pair = ("".join(c for c in words[i] if c.isalnum()) + " " + "".join(c for c in words[i + 1] if c.isalnum())).lower()
        if pair in KEYW:
            out |= {i, i + 1}
    return out


def draw_captions(fr, T, spec):
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
    fin = clamp01((T - c[0] + 0.02) / 0.14)
    fout = 1.0 - clamp01((T - (c[1] + 0.30)) / 0.16)
    nxt = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
    if nxt - c[0] < 0.6:
        fout = 1.0
    x, y, mw, size = spec
    img = SG.caption_img(words, act, age, _key_idx(words), size, mw, lines_max=2 if not REEL else 3)
    p = img.pad
    yy = y + (1 - ease_out(fin)) * 14
    if not REEL:
        yy = y + (2 * size * 1.3 - (img.height - 2 * p)) + (1 - ease_out(fin)) * 14     # bottom-aligned block
    blend(fr, img, x - p + 26, yy - p, fin * fout * hide)


def draw_tip(fr, T):
    cx, cy, r = L["tip"]
    for t0, t1, n, title, sub in TL.TIPS:
        cd = getattr(TL, "TIP_CARD", 2.2)
        if not (t0 <= T <= t1 + 1.0):
            continue
        tin = T - (t0 + cd * 0.75)
        if tin < 0:
            continue
        prog = clamp01((T - t0) / (t1 - t0))
        SG.tip_counter(fr, cx, cy, n, prog, title, tin, None if T <= t1 else T - t1, r=r, title_size=34 if not REEL else 38,
                       reel=REEL)


def draw_tip_card(fr, T):
    for t0, t1, n, title, sub in TL.TIPS:
        cd = getattr(TL, "TIP_CARD", 2.2)
        if t0 - 0.1 <= T <= t0 + cd + 0.4:
            SG.tip_card(fr, T - t0, cd, n, title, sub, reel=REEL)


def draw_steps(fr, T, sc):
    x, y = L["step"]
    started = [st for st in TL.STEPS if st[0] <= T]
    if not started:
        return
    for st in started[-1:]:                     # only the latest step: a new step replaces the previous one outright
        t0, t1, n, label = st
        if not (t0 <= T <= t1 + 0.4):
            continue
        a = clamp01((T - t0) / 0.2) * (1 - ease_io((T - t1) / 0.35))
        kick = SG.label(f"STEP {n:02d}", "mono", 20 if not REEL else 24, SG.LIME, tracking=0.2)
        img = SG.label(label, "semi", 32 if not REEL else 36, SG.WHITE)
        SG.reveal(fr, kick, x, y, clamp01((T - t0) / 0.35), a)
        SG.reveal(fr, img, x, y + (32 if not REEL else 36), clamp01((T - t0 - 0.06) / 0.4), a)


def draw_keys(fr, T):
    if L["key"] is None:
        return
    x, y = L["key"]
    for t0, t1, text in getattr(TL, "KEY_POINTS", []):
        if t0 <= T <= t1 + 0.4:
            SG.key_point(fr, T - t0, t1 - t0, text, x, y, size=64 if not REEL else 66)


def draw_bug(fr, T):
    x, y, s = L["bug"]
    k = ease_out((T - TITLE.span()[1] - 0.2) / 0.5)
    if k <= 0.01:
        return
    img = SG.logo_bug(s, LOGO)
    blend(fr, img, x - img.width / 2, y - img.height / 2, k)


def draw_ctas(fr, T):
    slots = L["cta"]
    ctas = TL.REEL_CTAS if REEL and hasattr(TL, "REEL_CTAS") else TL.CTAS
    busy = [-1e9] * len(slots)
    for t0, what in sorted(ctas):
        k = 0
        while k < len(slots) - 1 and busy[k] > t0:
            k += 1
        busy[k] = t0 + 3.8
        t = T - t0
        if -0.1 <= t <= 3.8:
            x, y = slots[k]
            SG.cta(fr, what, t, x, y, scale=1.0 if not REEL else 1.05)


def draw_pip(fr, T, sc):
    if not PIP or sc["kind"] != "phone":
        return
    x, y, w, h = PIP
    a = ease_out((T - sc["t0"] - 0.3) / 0.4) * (1 - ease_io((T - sc["t1"] + 0.3) / 0.3))
    if a <= 0.01:
        return
    pic, (fx, fy) = face_crop(T, w, h, 1.7, 0.5, 0.45)
    pic = np.clip(GR_PIP(pic, face=(fx, fy, 0.3, 0.4), center=(0.5, 0.5), grain_on=False), 0, 1)
    k = 3
    from PIL import Image, ImageDraw
    m = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=18 * k, fill=255)
    m = np.asarray(m.resize((w, h), Image.LANCZOS), np.float32)[..., None] / 255 * a
    reg = fr[y:y + h, x:x + w]
    sh = cv2.GaussianBlur(np.pad(m[..., 0], 20), (0, 0), 10)
    fr[y - 20 + 10:y + h + 20 + 10, x - 20:x + w + 20] *= (1 - 0.5 * sh[..., None])
    reg[:] = reg * (1 - m) + pic * m
    edge = cv2.morphologyEx((m[..., 0] > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)[..., None]
    reg[:] = reg * (1 - edge * 0.8 * a) + SG.LIMEF * edge * 0.8 * a


# ---- frame ----------------------------------------------------------------------------------------------------
MIX = 0.5


def base_frame(T, sc):
    fr, g = picture(T, sc)
    for tb in getattr(TL, "MIXES", []):
        if sc["t0"] == tb and T - tb < MIX / 2:
            pv = prev_scene(sc)
            if pv is not None:
                fa, _ = picture(T, pv)
                p = (T - tb + MIX / 2) / MIX
                fr = SG.blur_mix(fa, fr, p)
                g = g if p > 0.5 else None
        nxt = TL.SCENES[TL.SCENES.index(sc) + 1] if TL.SCENES.index(sc) + 1 < len(TL.SCENES) else None
        if nxt is not None and nxt["t0"] == tb and tb - T < MIX / 2:
            fb, _ = picture(T, nxt)
            p = (T - tb + MIX / 2) / MIX
            fr = SG.blur_mix(fr, fb, p)
            g = g if p < 0.5 else None
    return np.ascontiguousarray(fr, dtype=np.float32), g


def render_frame(T, u=None):
    sc = scene_at(T)
    fr, g = base_frame(T, sc)
    t_end = TITLE.span()[1]
    if T < t_end + 0.4:                                        # opening title over the darkened, softened shot
        k = 1 - ease_io((T - t_end) / 0.4)
        small = cv2.resize(fr, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        soft = cv2.resize(cv2.GaussianBlur(small, (0, 0), 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        fr = fr * (1 - k) + soft * 0.38 * k
        TITLE.draw(fr, T)
    if g is not None:
        phone_marks(fr, T, g)
    fr *= SHADE_PHONE if sc["kind"] == "phone" else SHADE
    ck = card_on(T)
    if ck > 0.001:
        fr *= 1 - 0.62 * ck
        draw_tip_card(fr, T)
    draw_pip(fr, T, sc)
    draw_bug(fr, T)
    draw_tip(fr, T)
    if sc["kind"] == "phone":
        draw_steps(fr, T, sc)
    draw_keys(fr, T)
    draw_ctas(fr, T)
    draw_captions(fr, T, L["cap_phone"] if sc["kind"] == "phone" else L["cap"])
    now = u if (CUTS and u is not None) else T
    fade_in = clamp01(now / 0.5)
    fade = (1 - clamp01((now - NARR) / (TAIL - 0.04))) * (0.3 + 0.7 * fade_in)
    if CUTS and u is not None:
        for (us, a, b) in CUTS[1:]:
            p = (u - us) / 0.22
            if -1 < p < 1:
                fr *= 1 - 0.35 * (1 - abs(p))                 # quick dip on reel joins
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
