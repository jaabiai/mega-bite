#!/usr/bin/env python3
"""MEGABYTE / V Create "Pop" compositor (16:9 YouTube or 9:16 reel) for projects whose timeline sets STYLE = "pop".

Light neo-brutalist explainer: warm dotted paper, the face-cam in an ink-bordered card with a hard shadow, karaoke
captions on a white speech card under it (never on the presenter), stickers for the topic / channel / prompts.  Phone
segments put the whole iPhone on the paper with a hard ink shadow; a magnifier loupe on an ink line blows up the
control being talked about, a step checklist ticks along (16:9) or a step sticker sits on top (9:16), and the face
stays in a round sticker.  Explainer graphics replace B-roll.  The topic opens with extruded outlined 3D blocks.
Cuts are covered by a diagonal yellow paper wipe.  The 9:16 version follows the Reels / Shorts safe zone.

usage:
  render_pop.py --project NAME --format wide|reel --face main.mp4 --screen screen_clean.mp4 --out x.mp4 [--start --end]
  render_pop.py ... --frames 1.5,20,40 --out-dir stills/
"""
import argparse, json, math, os, subprocess, sys, time
import numpy as np
import cv2
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))


def _project_dir():
    for i, a in enumerate(sys.argv):
        if a == "--project" and i + 1 < len(sys.argv):
            return os.path.join(HERE, "projects", sys.argv[i + 1])
    sys.exit("--project NAME is required (a folder under projects/)")


sys.path.insert(0, _project_dir())
import pop, phonescene, timeline as TL, captions_data as CD
from grade_cine import Grader
from gfx import ease_io, ease_out, ease_back, clamp01, lerp, blend

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--format", choices=["wide", "reel"], default="wide")
ap.add_argument("--face", required=True)
ap.add_argument("--screen", required=True)
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
TAIL = 0.30
CUTS = None
SEGS = None
if REEL:
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
    L = dict(card=(40, 236, 1000, 1030), cap_face=(540, 1296, 930, 46), cap_phone=(540, 1318, 930, 44),
             cap_explain=(540, 1300, 930, 44), bug=(1000, 272, 64), topic=(64, 300), cta=[(64, 300)],
             notes=(64, 300), phone_hb=0.49, phone_anchor=(0.5, 0.425), loupe=(872, 600, 160), pip=None,
             side=(48, 1010, 74), step=(48, 282))
else:
    L = dict(card=(60, 56, 1280, 720), cap_face=(700, 810, 1200, 48), cap_phone=(1492, 792, 730, 42),
             cap_explain=(1010, 884, 1240, 46), bug=(1400, 60, 84), topic=(1400, 236), cta=[(1400, 640), (1400, 758)],
             notes=(1400, 470), phone_hb=0.86, phone_anchor=(0.415, 0.5), loupe=(1490, 352, 212), pip=(232, 892, 128),
             side=(1128, 250, 98), step=(70, 300))
CX, CY, CW, CH = L["card"]
CARD = pop.HardCard(CX, CY, CW, CH, r=30, border=6, shadow=14)
PAPER = pop.Paper(W, H)
LOGO = os.path.join(HERE, "assets", "logo", getattr(TL, "LOGO", "logo.png"))

# ---- readers --------------------------------------------------------------------------------------------------
FW, FH = 2560, 1440
face_reader = pop.SeekReader(args.face, FW, FH, 30.0, f"scale={FW}:{FH}:flags=lanczos", jump=60)
SW_, SH_ = TL.SCREEN_SIZE
SFPS = float(TL.SCREEN_FPS)
screen_reader = pop.SeekReader(args.screen, SW_, SH_, SFPS, "null", jump=int(4 * SFPS))
N_SCREEN = int(round((TL.SCREEN_END - TL.SCREEN_T0) * SFPS)) - 1

GR_CARD = Grader(CW, CH, TL.GRADE)
PIP_R = L["pip"][2] if L["pip"] else 120
GR_PIP = Grader(2 * PIP_R, 2 * PIP_R, dict(TL.GRADE, vignette=0.0))
PIP = pop.Bubble(PIP_R)
TCARD = (390, 220)
GR_TCARD = Grader(*TCARD, TL.GRADE)

ps = phonescene.PhoneScene(1, None, W, H, layout="wide", hb_frac=L["phone_hb"], anchor=L["phone_anchor"], x_min=0,
                           titanium=((86, 86, 92), (30, 30, 34)), bg=np.zeros((10, 10, 3), np.float32), src=(SW_, SH_))
LOUPE = pop.Loupe(L["loupe"][2])

TITLE = pop.PopTitle(W, H, TL.TITLE_BEATS_REEL if REEL else TL.TITLE_BEATS, box=(0.84, 0.34) if REEL else (0.66, 0.46))
HEADERS = [(h[0], h[1], pop.PopTitle(W, H, [(0.0, h[1] - h[0], h[2], {"kicker": h[3], "cy": 0.47 if REEL else 0.50,
                                                                      "box": (0.84, 0.26) if REEL else (0.70, 0.42)})]))
           for h in TL.HEADERS]

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


def graded_face(T, w, h, zoom, grader, ty=0.42):
    fr, (fx, fy) = face_crop(T, w, h, zoom, 0.5, ty)
    return np.clip(grader(fr, face=(fx, fy - 0.02, 0.26, 0.34), center=(fx, 0.5)), 0, 1)


def draw_pip(fr, T, alpha=1.0):
    if not L["pip"] or alpha <= 0.01:
        return
    x, y, r = L["pip"]
    pic = graded_face(T, 2 * r, 2 * r, 1.9, GR_PIP, ty=0.48)
    PIP.draw(fr, x, y, pic, scale=pop.pop_in(alpha * 0.32, 0.32) if alpha < 1 else 1.0, alpha=min(alpha * 3, 1))


def tilted_card(fr, pic, cx, cy, rot, border=6, shadow=12, alpha=1.0):
    h, w = pic.shape[:2]
    img = np.zeros((h + 2 * border, w + 2 * border, 4), np.uint8)
    img[..., :3] = pop.INK
    img[..., 3] = 255
    img[border:border + h, border:border + w, :3] = (np.clip(pic, 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(img, "RGBA").rotate(rot, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", im.size, pop.INK + (0,))
    sh.putalpha(im.split()[3])
    blend(fr, sh, cx - im.width / 2 + shadow, cy - im.height / 2 + shadow, alpha)
    blend(fr, im, cx - im.width / 2, cy - im.height / 2, alpha)


# ---- scenes ---------------------------------------------------------------------------------------------------
def scene_at(T):
    for sc in TL.SCENES:
        if sc["t0"] <= T < sc["t1"]:
            return sc
    return TL.SCENES[-1]


def screen_frame(T):
    S_t = TL.screen_time(T)
    idx = min(max(int(round((S_t - TL.SCREEN_T0) * SFPS)), 0), N_SCREEN)
    return screen_reader.get(idx)


def phone_geo(T, sc):
    cam = phonescene.cam_at(T, TL.CAMERA)
    enter = ease_back(clamp01((T - sc["t0"]) / 0.55), 1.4)
    g = ps.geometry(cam, extra=(0.0, (1 - enter) * 0.35 * H))
    g["sway"] = 2.5 * math.sin(2 * math.pi * T / 6.0)
    return g


def to_out(g, u, v):
    x, y = ps.to_out(g, u, v)
    return x, y + g["sway"]


def draw_phone(fr, T, sc):
    screen = screen_frame(T)
    g = phone_geo(T, sc)
    lay = ps.layer(screen, g, sway=g["sway"])
    a = lay[..., 3:4]
    off = 16
    sh = np.zeros_like(a)
    sh[off:, off:] = a[:-off, :-off]
    fr[:] = fr * (1 - sh) + pop.INKF * sh
    fr[:] = fr * (1 - a) + lay[..., :3]
    return screen, g


# ---- captions -------------------------------------------------------------------------------------------------
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


def cap_hide(T):
    k = 0.0
    t_end = TITLE.span()[1]
    k = max(k, 1 - ease_out((T - t_end) / 0.25))
    for (t0, t1, _) in HEADERS:
        k = max(k, ease_out((T - t0 + 0.12) / 0.2) * (1 - ease_io((T - t1) / 0.25)))
    return 1.0 - k


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
    fin = clamp01((T - c[0] + 0.02) / 0.12)
    fout = 1.0 - clamp01((T - (c[1] + 0.30)) / 0.15)
    nxt = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
    if nxt - c[0] < 0.6:
        fout = 1.0
    cx, y, mw, size = spec
    img = pop.caption_card(words, act, age, size, mw)
    s = lerp(0.92, 1.0, ease_back(clamp01((T - c[0] + 0.02) / 0.2), 2.0))
    if abs(s - 1) > 1e-3:
        img = img.resize((max(int(img.width * s), 1), max(int(img.height * s), 1)), Image.BICUBIC)
    blend(fr, img, cx - img.width / 2, y + (1 - ease_out(fin)) * 12, fin * fout * hide)


# ---- stickers -------------------------------------------------------------------------------------------------
def draw_bug(fr, T, a=1.0):
    x, y, s = L["bug"]
    k = pop.pop_in(T - TITLE.span()[1] - 0.25)
    img = pop.logo_bug(s, LOGO)
    if REEL:
        pop.place(fr, img, x, y, scale=k, alpha=a * min(k * 2, 1))
        return
    pop.place(fr, img, x + img.width / 2, y + img.height / 2, scale=k, alpha=a * min(k * 2, 1))
    name = pop.sticker(TL.CHANNEL, size=26, fill=pop.PAPER, fg=pop.INK, kind="mono", pad=(4, 2), border=0, shadow=0, tracking=0.08)
    pop.place(fr, name, x + img.width + 14, y + img.height / 2 - 2, alpha=a * clamp01((T - TITLE.span()[1] - 0.45) / 0.2), anchor="l")


def cta_busy(T, slot=0):
    ctas = TL.REEL_CTAS if REEL else TL.CTAS
    return any(0 <= T - t0 <= 3.5 for t0, _ in ctas)


def draw_topic(fr, T, a=1.0):
    x, y = L["topic"]
    t1 = TITLE.span()[1]
    s1, a1 = pop.life(T, t1 + 0.35, 1e9)
    s2, a2 = pop.life(T, t1 + 0.50, 1e9)
    kick = pop.sticker(TL.TOPIC_KICKER, size=22 if REEL else 24, fill=pop.INK, fg=pop.YELLOW, kind="mono", pad=(16, 8), radius=8,
                       border=0, shadow=0, tracking=0.06)
    ttl = pop.sticker(TL.TOPIC, size=40 if REEL else 46, fill=pop.YELLOW, kind="display", pad=(20, 8), radius=14, border=5, shadow=8)
    if REEL:
        pop.place(fr, kick, x, y - 34, scale=s1, alpha=a * a1, anchor="l", rot=0)
        pop.place(fr, ttl, x - 4, y + 22, scale=s2, alpha=a * a2, anchor="l", rot=-2.0)
    else:
        pop.place(fr, kick, x, y, scale=s1, alpha=a * a1, anchor="l")
        pop.place(fr, ttl, x - 2, y + 74, scale=s2, alpha=a * a2, anchor="l", rot=-2.5)


def draw_ctas(fr, T):
    ctas = TL.REEL_CTAS if REEL else TL.CTAS
    slots = L["cta"]
    busy_until = [-1e9] * len(slots)
    for t0, what in sorted(ctas):
        k = 0
        while k < len(slots) - 1 and busy_until[k] > t0:
            k += 1
        busy_until[k] = t0 + 3.5
        t = T - t0
        if -0.1 <= t <= 3.6:
            x, y = slots[k]
            pop.cta(fr, what, t, x, y, scale=0.86 if REEL else 0.92)


def draw_face_notes(fr, T):
    x, y = L["notes"]
    if REEL:
        for i, (t0, t1, txt, col) in enumerate(TL.FACE_NOTES):
            s, a = pop.life(T, t0, min(t1, TL.TIP_STAMP[0] - 0.05))
            img = pop.sticker(txt, size=40, fill=col, kind="display", pad=(18, 6), radius=12, border=5, shadow=7)
            pop.place(fr, img, x + i * 250, y, scale=s, alpha=a, rot=(-4, 3, -2)[i % 3], anchor="l")
        t0, t1, txt = TL.TIP_STAMP
        s, a = pop.life(T, t0, t1)
        img = pop.sticker(txt, size=44, fill=pop.PINK, fg=pop.WHITE, kind="display", pad=(22, 8), radius=14, border=5, shadow=8)
        pop.place(fr, img, x, y, scale=s, alpha=a, rot=-3, anchor="l")
        return
    for i, (t0, t1, txt, col) in enumerate(TL.FACE_NOTES):
        s, a = pop.life(T, t0, t1)
        img = pop.sticker(txt, size=46, fill=col, kind="display", pad=(20, 6), radius=14, border=5, shadow=8)
        pop.place(fr, img, x + (i % 2) * 40, y + i * 92, scale=s, alpha=a, rot=(-4, 3, -2)[i % 3], anchor="l")
    t0, t1, txt = TL.TIP_STAMP
    s, a = pop.life(T, t0, t1)
    img = pop.sticker(txt, size=44, fill=pop.PINK, fg=pop.WHITE, kind="display", pad=(22, 8), radius=14, border=5, shadow=8)
    pop.place(fr, img, x - 6, y + 3 * 92 + 10, scale=s, alpha=a, rot=-5, anchor="l")


def draw_side_notes(fr, T):
    x, y, dy = L["side"]
    for t0, t1, txt, col, row in TL.SIDE_NOTES:
        s, a = pop.life(T, t0, t1)
        if a <= 0:
            continue
        icon = None
        if txt.endswith("✓"):
            txt, icon = txt[:-1].strip(), pop.ic_check
        img = pop.sticker(txt, size=34 if REEL else 40, fill=col, kind="display", pad=(18, 6), radius=12, border=5, shadow=7,
                          icon=icon)
        pop.place(fr, img, x + (row % 2) * 26, y + row * dy, scale=s, alpha=a, rot=(-2.5, 2.0, -1.5, 2.5)[row % 4], anchor="l")


def draw_checklist(fr, T, sc):
    if REEL:
        on = [st for st in TL.STEPS if st[0] <= T < st[1]]
        if not on:
            return
        t0, t1, n, label = on[0]
        s, a = pop.life(T, t0, t1 - 0.05, 0.3, 0.18)
        badge = pop.sticker(f"STEP {n}", size=30, fill=pop.PINK, fg=pop.WHITE, kind="mono", pad=(16, 8), radius=10, border=4, shadow=6,
                            tracking=0.04)
        lab = pop.sticker(label, size=38, fill=pop.YELLOW, kind="text", pad=(18, 6), radius=12, border=5, shadow=7)
        x, y = L["step"]
        pop.place(fr, badge, x, y, scale=s, alpha=a, anchor="l", rot=-3)
        pop.place(fr, lab, x + badge.width + 8, y + 4, scale=s, alpha=a, anchor="l", rot=1.5)
        return
    x, y = L["step"]
    t_in = sc["t0"]
    head = pop.sticker("HOW TO", size=26, fill=pop.INK, fg=pop.YELLOW, kind="mono", pad=(16, 8), radius=8, border=0, shadow=0, tracking=0.08)
    s, a = pop.life(T, t_in + 0.15, 1e9)
    pop.place(fr, head, x, y - 70, scale=s, alpha=a, anchor="l")
    for i, (t0, t1, n, label) in enumerate(TL.STEPS):
        s, a = pop.life(T, t_in + 0.25 + 0.07 * i, 1e9)
        if a <= 0:
            continue
        active = t0 <= T < t1
        done = T >= t1
        fill = pop.YELLOW if active else pop.WHITE
        num_fill = pop.PINK if active else (pop.MINT if done else pop.WHITE)
        num = pop.sticker(str(n), size=30, fill=num_fill, fg=pop.WHITE if (active or done) else pop.INK, kind="display",
                          pad=(14, 2), radius=26, border=4, shadow=5, min_w=52)
        lab = pop.sticker(label, size=30, fill=fill, fg=pop.INK if (active or not done) else (60, 58, 62), kind="text",
                          pad=(16, 6), radius=12, border=4, shadow=5 if active else 3)
        yy = y + i * 86
        dim = 1.0 if (active or done) else 0.55
        bump = 1 + 0.08 * math.exp(-((T - t0 - 0.12) / 0.10) ** 2)
        pop.place(fr, num, x, yy, scale=s * bump, alpha=a, anchor="l")
        pop.place(fr, lab, x + 74, yy, scale=s, alpha=a * dim, anchor="l", rot=-1.2 if active else 0)
        if done:
            k = ease_out((T - t1) / 0.25)
            img = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
            pop.ic_check(ImageDraw.Draw(img), 6, 30, 52, pop.INK)
            pop.place(fr, img, x + 74 + lab.width + 18, yy, scale=k, alpha=a * k)


def draw_phone_marks(fr, T, screen, g):
    # thumbnail tags + marker rings
    for t0, t1, (u, v), txt, col in TL.THUMB_TAGS:
        s, a = pop.life(T, t0, t1)
        if a <= 0:
            continue
        x, y = to_out(g, u, v)
        img = pop.sticker(txt, size=26 if REEL else 28, fill=col, kind="display", pad=(12, 2), radius=10, border=4, shadow=5)
        pop.place(fr, img, x, y, scale=s, alpha=a, rot=(-5 if int(t0 * 10) % 2 else 4))
    for t0, t1, (u0, v0, u1, v1) in TL.RINGS:
        if t0 <= T <= t1 + 0.25:
            x0, y0 = to_out(g, u0, v0)
            x1, y1 = to_out(g, u1, v1)
            pop.marker_ring(fr, (x0, y0, x1, y1), T - t0, 1 - ease_io((T - t1) / 0.25), seed=int(t0))
    # loupes
    lx, ly, lr = L["loupe"]
    for t0, t1, (u, v), hw, label in TL.LOUPES:
        if not (t0 <= T <= t1 + 0.22):
            continue
        sc_, al = pop.life(T, t0, t1, 0.36, 0.2)
        side = 2 * hw * SW_
        x0, y0 = int(u * SW_ - side / 2), int(v * SH_ - side / 2)
        crop = np.zeros((int(side), int(side), 3), np.uint8) + 240
        sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x0 + int(side), SW_), min(y0 + int(side), SH_)
        crop[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = screen[sy0:sy1, sx0:sx1]
        content = cv2.resize(crop, (2 * lr, 2 * lr), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        tx, ty = to_out(g, u, v)
        rr = hw * SW_ * g["s"]
        k_line = ease_out((T - t0) / 0.3) * (1 - ease_io((T - t1) / 0.2))
        dx, dy = lx - tx, ly - ty
        dist = math.hypot(dx, dy) + 1e-6
        p0 = (tx + dx / dist * rr, ty + dy / dist * rr)
        p1 = (lx - dx / dist * lr * sc_, ly - dy / dist * lr * sc_)
        pop.ink_line(fr, p0, p1, 5, k_line)
        pop.ring(fr, tx, ty, rr, 5, k_line)
        LOUPE.draw(fr, lx, ly, content, scale=sc_, alpha=al)
        lab = pop.sticker(label, size=34 if REEL else 40, fill=pop.YELLOW, kind="display", pad=(20, 6), radius=12, border=5, shadow=7)
        s2, a2 = pop.life(T, t0 + 0.12, t1, 0.3, 0.2)
        pop.place(fr, lab, lx, ly + lr + (34 if REEL else 42), scale=s2, alpha=a2, rot=-2)
    for (tt, u, v) in TL.TAPS:
        if tt - 0.2 <= T <= tt + 0.9:
            x, y = to_out(g, u, v)
            pop.tap(fr, x, y, T - tt)


# ---- explainer ------------------------------------------------------------------------------------------------
_TILES = []


def _tiles():
    if _TILES:
        return _TILES
    rng = np.random.default_rng(7)
    pals = [((255, 196, 120), (255, 120, 90), (90, 60, 70)), ((170, 230, 200), (60, 170, 120), (40, 80, 60)),
            ((255, 225, 150), (255, 160, 60), (120, 70, 40)), ((235, 205, 255), (180, 120, 230), (70, 40, 90)),
            ((255, 210, 220), (255, 110, 150), (90, 40, 60)), ((210, 240, 170), (120, 190, 80), (50, 90, 40)),
            ((255, 236, 180), (240, 190, 90), (110, 80, 50)), ((225, 225, 225), (160, 150, 140), (60, 55, 50))]
    for i, (sky, mid, low) in enumerate(pals):
        n, k = 200, 3
        im = Image.new("RGB", (n * k, n * k), sky)
        d = ImageDraw.Draw(im)
        for yy in range(n * k):
            f = yy / (n * k)
            c = tuple(int(sky[j] * (1 - f * 0.5) + mid[j] * f * 0.5) for j in range(3))
            d.line([(0, yy), (n * k, yy)], fill=c)
        sx = rng.uniform(0.2, 0.8) * n * k
        d.ellipse([sx - 28 * k, 40 * k, sx + 28 * k, 96 * k], fill=(255, 250, 235))
        pts = [(0, n * k)] + [(x * n * k / 6, (0.55 + 0.15 * rng.uniform(-1, 1)) * n * k) for x in range(7)] + [(n * k, n * k)]
        d.polygon(pts, fill=mid)
        pts = [(0, n * k)] + [(x * n * k / 5, (0.75 + 0.1 * rng.uniform(-1, 1)) * n * k) for x in range(6)] + [(n * k, n * k)]
        d.polygon(pts, fill=low)
        if i % 3 == 1:                                                   # a person silhouette on some tiles
            px = rng.uniform(0.3, 0.7) * n * k
            d.ellipse([px - 18 * k, 92 * k, px + 18 * k, 128 * k], fill=(40, 36, 44))
            d.rounded_rectangle([px - 32 * k, 126 * k, px + 32 * k, 210 * k], radius=24 * k, fill=(40, 36, 44))
        im = im.resize((n, n), Image.LANCZOS)
        b, sh = 5, 7
        out = Image.new("RGBA", (n + 2 * b + sh, n + 2 * b + sh), (0, 0, 0, 0))
        dd = ImageDraw.Draw(out)
        dd.rounded_rectangle([sh, sh, n + 2 * b + sh - 1, n + 2 * b + sh - 1], radius=18, fill=pop.INK + (255,))
        dd.rounded_rectangle([0, 0, n + 2 * b - 1, n + 2 * b - 1], radius=18, fill=pop.INK + (255,))
        m = Image.new("L", (n, n), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, n - 1, n - 1], radius=13, fill=255)
        out.paste(im, (b, b), m)
        _TILES.append(out)
    return _TILES


def _mini_frame(w, h, icon, col, label):
    """Portrait 9:16 screen outline with an icon and a ratio tag (PIL RGBA)."""
    b, sh = 5, 8
    img = Image.new("RGBA", (w + 2 * b + sh, h + 2 * b + sh + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([sh, sh, w + 2 * b + sh - 1, h + 2 * b + sh - 1], radius=26, fill=pop.INK + (255,))
    d.rounded_rectangle([0, 0, w + 2 * b - 1, h + 2 * b - 1], radius=26, fill=pop.INK + (255,))
    d.rounded_rectangle([b, b, w + b - 1, h + b - 1], radius=21, fill=tuple(col) + (255,))
    k = 3
    ic = Image.new("RGBA", (120 * k, 120 * k), (0, 0, 0, 0))
    icon(ImageDraw.Draw(ic), 14 * k, 60 * k, 82 * k, pop.INK)
    ic = ic.resize((120, 120), Image.LANCZOS)
    img.alpha_composite(ic, (int(b + w / 2 - 60 + 6), int(b + h / 2 - 60)))
    tag = pop.sticker(label, size=26, fill=pop.WHITE, kind="mono", pad=(12, 4), radius=8, border=4, shadow=4)
    img.alpha_composite(tag, (int((w + 2 * b) / 2 - tag.width / 2), int(h + 2 * b - tag.height / 2)))
    return img


_MINI = {}


def draw_explain(fr, T, sc):
    E = TL.EXPLAIN
    icons = {"chat": pop.ic_chat, "play": pop.ic_play, "star": pop.ic_star}
    t_tiles, t_q, t_hard, t_out = E["tiles_t"], E["question_t"], E["hard_t"], E["out_t"]
    # header
    head_txt = "WHERE DOES IT GO?" if T < t_tiles else "WHICH ONE FITS?"
    t_head = sc["t0"] + 0.15 if T < t_tiles else t_q - 0.25
    s, a = pop.life(T, t_head, (t_tiles - 0.15) if T < t_tiles else t_out)
    head = pop.sticker(head_txt, size=52 if REEL else 58, fill=pop.INK, fg=pop.YELLOW, kind="display", pad=(26, 8), radius=14,
                       border=0, shadow=0)
    hy = 330 if REEL else 120
    pop.place(fr, head, W / 2, hy, scale=s, alpha=a, rot=-1.5)
    # phase A: where the picture will be used
    k_out = ease_io((T - (t_tiles - 0.35)) / 0.35)
    for i, (t0, label, ic, col) in enumerate(E["uses"]):
        s, a = pop.life(T, t0, t_tiles - 0.1, 0.34, 0.25)
        if a <= 0:
            continue
        key = (label, REEL)
        if key not in _MINI:
            _MINI[key] = _mini_frame(196 if REEL else 170, int((196 if REEL else 170) * 16 / 9), icons[ic], col,
                                     "9:16" if i < 2 else "?:?")
        mf = _MINI[key]
        st = pop.sticker(label, size=36 if REEL else 40, fill=col, kind="text", pad=(18, 6), radius=12, border=5, shadow=7,
                         icon=icons[ic])
        if REEL:
            cx, cy = W / 2 + (i - 1) * 330, 730
            pop.place(fr, mf, cx, cy, scale=s, alpha=a, rot=(-4, 2, 5)[i])
            pop.place(fr, st, cx, cy + mf.height / 2 + 40 - (i % 2) * 0, scale=s, alpha=a, rot=(-3, 2, -2)[i])
        else:
            cx, cy = W / 2 + (i - 1) * 470, 520
            pop.place(fr, mf, cx, cy - 20, scale=s, alpha=a, rot=(-4, 2, 5)[i])
            pop.place(fr, st, cx, cy + mf.height / 2 + 26, scale=s, alpha=a, rot=(-3, 2, -2)[i])
    # phase B / C: square tiles that hide the real shape
    if T >= t_tiles - 0.05:
        tiles = _tiles()
        cols = 3 if REEL else 4
        size = 230 if REEL else 200
        gap = 40 if REEL else 46
        x0 = W / 2 - (cols * size + (cols - 1) * gap) / 2 + size / 2
        y0 = (690 if REEL else 360)
        shake = 0.0
        for i, tile in enumerate(tiles[: (6 if REEL else 8)]):
            r, c = divmod(i, cols)
            s, a = pop.life(T, t_tiles + 0.06 * i, t_out, 0.34, 0.2)
            if a <= 0:
                continue
            if T > t_hard:
                shake = 5 * math.sin((T - t_hard) * 38 + i) * math.exp(-(T - t_hard) * 2.2)
            cx = x0 + c * (size + gap) + shake
            cy = y0 + r * (size + gap)
            pop.place(fr, tile, cx, cy, scale=s * size / 214, alpha=a, rot=(-3, 2, -1, 3, 1, -2, 3, -3)[i])
            sq, aq = pop.life(T, t_q + 0.08 * i, t_out, 0.3, 0.2)
            q = pop.sticker("?", size=44, fill=pop.WHITE, kind="display", pad=(16, 0), radius=24, border=4, shadow=5)
            pulse = 1 + 0.06 * math.sin((T - t_q) * 6 + i)
            pop.place(fr, q, cx + size * 0.30, cy - size * 0.30, scale=sq * pulse, alpha=aq)
            tag = pop.sticker("1:1", size=24, fill=pop.YELLOW, kind="mono", pad=(10, 2), radius=8, border=4, shadow=4)
            pop.place(fr, tag, cx - size * 0.30, cy + size * 0.36, scale=s, alpha=a)
        s, a = pop.life(T, t_hard, t_out, 0.3, 0.2)
        stamp = pop.sticker("HARD TO TELL!", size=78 if REEL else 92, fill=pop.PINK, fg=pop.WHITE, kind="display", pad=(30, 8),
                            radius=18, border=6, shadow=10)
        rows = 2
        pop.place(fr, stamp, W / 2, y0 + (rows - 1) * (size + gap) / 2, scale=s, alpha=a, rot=-7)


# ---- frame ----------------------------------------------------------------------------------------------------
def draw_face_scene(fr, T, sc):
    z0, z1 = sc.get("zoom", (1.0, 1.05))
    prog = clamp01((T - sc["t0"]) / max(sc["t1"] - sc["t0"], 0.1))
    z = lerp(z0, z1, ease_io(prog))
    pic = graded_face(T, CW, CH, z, GR_CARD, ty=0.40 if REEL else 0.42)
    k = ease_back(clamp01((T - sc["t0"] + 0.05) / 0.5), 1.3)
    dy = int((1 - k) * 60)
    CARD.compose(fr, pic, 0, dy)
    busy = cta_busy(T)
    notes_on = any(t0 <= T <= t1 + 0.3 for t0, t1, *_ in TL.FACE_NOTES) or (TL.TIP_STAMP[0] <= T <= TL.TIP_STAMP[1] + 0.3)
    topic_a = 1.0
    if REEL:
        topic_a = 0.0 if (busy or notes_on) else 1.0
    draw_bug(fr, T)
    draw_topic(fr, T, topic_a)
    draw_face_notes(fr, T)
    draw_ctas(fr, T)
    draw_captions(fr, T, L["cap_face"])


def draw_phone_scene(fr, T, sc):
    screen, g = draw_phone(fr, T, sc)
    draw_phone_marks(fr, T, screen, g)
    draw_side_notes(fr, T)
    if sc["name"] == "steps":
        draw_checklist(fr, T, sc)
    elif not REEL:
        x, y = L["step"]
        s, a = pop.life(T, sc["t0"] + 0.2, sc["t1"])
        head = pop.sticker("THE PROBLEM", size=30, fill=pop.INK, fg=pop.YELLOW, kind="mono", pad=(18, 8), radius=8, border=0,
                           shadow=0, tracking=0.06)
        pop.place(fr, head, x, y - 70, scale=s, alpha=a, anchor="l")
        sq = pop.sticker("Photos shows squares", size=34, fill=pop.WHITE, kind="text", pad=(16, 6), radius=12, border=4, shadow=5)
        s2, a2 = pop.life(T, sc["t0"] + 0.45, sc["t1"])
        pop.place(fr, sq, x, y + 10, scale=s2, alpha=a2, anchor="l", rot=-1.5)
    draw_pip(fr, T, clamp01((T - sc["t0"] - 0.3) / 0.35))
    if not REEL:
        bx, by, bs = L["bug"]
        pop.place(fr, pop.logo_bug(64, LOGO), W - 70, 70)
    else:
        bx, by, bs = L["bug"]
        pop.place(fr, pop.logo_bug(bs, LOGO), bx, by)
    draw_captions(fr, T, L["cap_phone"])


def draw_explain_scene(fr, T, sc):
    draw_explain(fr, T, sc)
    draw_pip(fr, T, clamp01((T - sc["t0"] - 0.3) / 0.35))
    if REEL:
        bx, by, bs = L["bug"]
        pop.place(fr, pop.logo_bug(bs, LOGO), bx, by)
    else:
        pop.place(fr, pop.logo_bug(64, LOGO), W - 70, 70)
    draw_captions(fr, T, L["cap_explain"])


def render_frame(T, u=None):
    sc = scene_at(T)
    fr = PAPER.at(T)
    kind = sc["kind"]
    if kind == "title":
        fr = TITLE.background(fr, T).astype(np.float32)
        TITLE.draw(fr, T)
        if not REEL:
            pic = graded_face(T, *TCARD, 1.15, GR_TCARD, ty=0.45)
            k = pop.pop_in(T - 0.35, 0.4)
            if k > 0.01:
                tilted_card(fr, pic, W - 70 - TCARD[0] / 2, H - 60 - TCARD[1] / 2, 4.0, alpha=min(1, k * 2))
                rec = pop.sticker("● LIVE TIP", size=22, fill=pop.PINK, fg=pop.WHITE, kind="mono", pad=(12, 4), radius=8, border=4,
                                  shadow=4)
                pop.place(fr, rec, W - 70 - TCARD[0] + 40, H - 60 - TCARD[1] - 6, scale=k, rot=4)
    elif kind == "header":
        for (t0, t1, hd) in HEADERS:
            if t0 - 0.3 <= T < t1 + 0.3:
                fr = hd.background(fr, T).astype(np.float32)
                hd.draw(fr, T - t0)
    elif kind == "face":
        draw_face_scene(fr, T, sc)
    elif kind == "phone":
        draw_phone_scene(fr, T, sc)
    elif kind == "explain":
        draw_explain_scene(fr, T, sc)
    fr = np.ascontiguousarray(np.clip(fr, 0, 1), dtype=np.float32)
    # transitions
    if not REEL:
        for tw in TL.WIPES:
            p = (T - tw) / 0.42
            if -1 < p < 1:
                fr = pop.paper_wipe(fr, p)
        for tp in TL.POPS:
            fr = pop.pop_zoom(fr, (T - tp) / 0.35)
    else:
        for tw in TL.WIPES:
            if seg_of(tw) and seg_of(tw)[0] + 0.3 < tw:            # a wipe that falls inside a kept reel segment
                p = (T - tw) / 0.42
                if -1 < p < 1:
                    fr = pop.paper_wipe(fr, p, angle=0.18)
        for tp in TL.POPS:
            fr = pop.pop_zoom(fr, (T - tp) / 0.35)
        if u is not None:
            for (us, a, b) in CUTS[1:]:
                fr = pop.pop_zoom(fr, (u - us) / 0.35)
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
