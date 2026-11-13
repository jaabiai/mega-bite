#!/usr/bin/env python3
"""Showcase renderer (V Create product films).

Graded 4K face-cam reframed by a virtual camera (TL.CAM_WIDE / TL.CAM_REEL), a 2.39:1 letterbox in 16:9 or a 4:5
window in 9:16, an opening 3D title, tracked feature callouts (tracks.json from tools/track_points.py), chapter labels and
titles in the bars, cinema subtitles in the bars, product cards and prompts.  The edit is a cut list of source ranges
(TL.WIDE_CUTS / TL.REEL_CUTS); every timeline time is a SOURCE time.

usage: render_showcase.py --project NAME --format wide|reel --face Main.mp4 --out out.mp4 [--start S --end E]
       render_showcase.py ... --frames u1,u2,... --out-dir DIR          (stills at OUTPUT times)
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
import timeline as TL, captions_data as CD
import grade_cine as G, showcase as S, cine as C, aurora as A
from gfx import ease_io, ease_out, clamp01, lerp

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--format", choices=["wide", "reel"], default="wide")
ap.add_argument("--face", required=True)
ap.add_argument("--out", default=None)
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float, default=None)
ap.add_argument("--frames", default=None)
ap.add_argument("--out-dir", default=None)
ap.add_argument("--crf", type=int, default=16)
ap.add_argument("--preset", default="slow")
args = ap.parse_args()

REEL = args.format == "reel"
W, H = (1080, 1920) if REEL else (1920, 1080)
FPS = TL.FPS
SW, SH = 2880, 1620                     # decode size: 0.75 x 4K keeps every punch-in above output resolution

# ---- edit: output time u -> source time T ---------------------------------------------------------------------
PAD = (0.06, 0.10) if REEL else (0.0, 0.0)
CUTS, _u = [], 0.0
for a, b in (TL.REEL_CUTS if REEL else TL.WIDE_CUTS):
    a, b = max(a - PAD[0], 0.0), min(b + PAD[1], TL.SRC_END)
    CUTS.append((_u, a, b))
    _u += b - a
OUT_TOTAL = _u
END_U = args.end if args.end is not None else OUT_TOTAL


def u_to_T(u):
    for us, a, b in CUTS:
        if u < us + (b - a):
            return a + (u - us)
    return CUTS[-1][2] - 1e-3


# ---- layout ---------------------------------------------------------------------------------------------------
if REEL:
    # 9:16 layout built around the Reels / Shorts safe zone: the platform UI covers the top ~220 px, the bottom ~420 px
    # and a button column on the right (x > ~940 from y ~1000).  Text lives only inside x 48..940, y 236..1500.
    BAR = 0
    PX, PY, PW, PH = 40, 484, 1000, 880                          # picture card (rounded, shadowed)
    SAFE_L, SAFE_R = 48, 940
    SAFE_CX = (SAFE_L + SAFE_R) / 2
    ROW1_Y, PANEL_Y = 240, 318                                   # logo + chapter row, panel / big-title row
    SUB_Y = 1432                                                 # subtitle block centre (between card and bottom zone)
    REEL_ZOOM = getattr(TL, "REEL_ZOOM", 1.12)                   # the card is wider than 4:5: punch in to keep the phone big
else:
    BAR = S.bar_h(W, H)
    PX, PY, PW, PH = 0, BAR, W, H - 2 * BAR
TITLE_END = TL.TITLE_END
TITLE = S.title3d(W, H, TL.TITLE_BEATS_REEL if REEL else TL.TITLE_BEATS, box=(0.76, 0.32) if REEL else (0.80, 0.56))
GRADE_PIC = G.Grader(PW, PH, getattr(TL, "GRADE", {}))
GRADE_FULL = G.Grader(W, H, getattr(TL, "GRADE", {}))


# ---- source reader --------------------------------------------------------------------------------------------
class SeekReader:
    def __init__(self, path, w, h, fps, vf, jump=75):
        self.path, self.w, self.h, self.fps, self.vf, self.jump = path, w, h, fps, vf, jump
        self.proc, self.pos, self.cur = None, -10 ** 9, None
        self.size = w * h * 3

    def _start(self, idx):
        self.close()
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{idx / self.fps:.4f}", "-i", self.path, "-vf", self.vf, "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-"]
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


reader = SeekReader(args.face, SW, SH, 30.0, f"scale={SW}:{SH}:flags=lanczos")

_ft = os.path.join(_project_dir(), "face_track.json")
FT = json.load(open(_ft)) if os.path.exists(_ft) else None
_tr = os.path.join(_project_dir(), "tracks.json")
TRACKS = json.load(open(_tr))["points"] if os.path.exists(_tr) else {}


def face_at(T):
    if FT is None:
        return 0.62, 0.30
    return float(np.interp(T, FT["t"], FT["x"])), float(np.interp(T, FT["t"], FT["y"]))


def track_at(name, T):
    d = TRACKS.get(name)
    if not d:
        return None
    k = (T - d["t0"]) * 30.0
    xy = d["xy"]
    if k < 0 or k > len(xy) - 1:
        return None
    i = int(k)
    j = min(i + 1, len(xy) - 1)
    f = k - i
    return xy[i][0] * (1 - f) + xy[j][0] * f, xy[i][1] * (1 - f) + xy[j][1] * f


# ---- virtual camera -------------------------------------------------------------------------------------------
CAM = TL.CAM_REEL if REEL else TL.CAM_WIDE


def cam_at(T):
    i = 0
    for k, r in enumerate(CAM):
        if r[0] <= T:
            i = k
    r0 = CAM[i]
    if i + 1 < len(CAM) and not (len(CAM[i + 1]) > 4 and CAM[i + 1][4] == "cut") and T >= r0[0]:
        r1 = CAM[i + 1]
        k = clamp01((T - r0[0]) / max(r1[0] - r0[0], 1e-3))
        return lerp(r0[1], r1[1], k), lerp(r0[2], r1[2], k), lerp(r0[3], r1[3], k)
    return r0[1], r0[2], r0[3]


def window(cx, cy, z, aspect, by_height):
    if by_height:
        wh = SH / z
        ww = wh * aspect
    else:
        ww = SW / z
        wh = ww / aspect
    ww, wh = min(ww, SW), min(wh, SH)
    x0 = float(np.clip(cx * SW - ww / 2, 0, SW - ww))
    y0 = float(np.clip(cy * SH - wh / 2, 0, SH - wh))
    return x0, y0, ww, wh


def crop_resize(src, win, ow, oh):
    x0, y0, ww, wh = win
    xi, yi = int(math.floor(x0)), int(math.floor(y0))
    xe, ye = min(int(math.ceil(x0 + ww)) + 1, SW), min(int(math.ceil(y0 + wh)) + 1, SH)
    crop = src[yi:ye, xi:xe]
    sx, sy = ow / ww, oh / wh
    nw, nh = max(int(round((xe - xi) * sx)), 1), max(int(round((ye - yi) * sy)), 1)
    small = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA if sx < 1 else cv2.INTER_CUBIC)
    ax, ay = nw / (xe - xi), nh / (ye - yi)
    M = np.float32([[1, 0, -(x0 - xi) * ax], [0, 1, -(y0 - yi) * ay]])
    out = cv2.warpAffine(small, M, (ow, oh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out.astype(np.float32) * (1.0 / 255)


def to_pic(win, x, y, ow, oh, ox, oy):
    """Source-normalised point -> output pixels for a window rendered at (ox, oy, ow, oh)."""
    x0, y0, ww, wh = win
    return ox + (x * SW - x0) / ww * ow, oy + (y * SH - y0) / wh * oh


def graded(src, win, ow, oh, grader, T, n):
    pic = crop_resize(src, win, ow, oh)
    fx, fy = face_at(T)
    x0, y0, ww, wh = win
    face = ((fx * SW - x0) / ww, (fy * SH - y0) / wh, 0.085 * SW / ww, 0.17 * SH / wh)
    grader.rng = np.random.default_rng(n)
    return grader(pic, face=face)


# ---- captions -------------------------------------------------------------------------------------------------
def _seg_of(T):
    for us, a, b in CUTS:
        if a <= T <= b:
            return a, b
    return None


def active_chunk(T):
    best = None
    seg = _seg_of(T)
    for i, c in enumerate(CD.CHUNKS):
        if seg is not None and c[0] > seg[1] - PAD[1] - 0.02:
            continue                                   # starts after this kept range: never flash it in the padding
        nxt = CD.CHUNKS[i + 1][0] if i + 1 < len(CD.CHUNKS) else 1e9
        if c[0] - 0.05 <= T < min(c[1] + 0.35, nxt - 0.02):
            best = i
    return best


def draw_subs(fr, T, cy, size, max_w, alpha=1.0, cx=None):
    i = active_chunk(T)
    if i is None or alpha <= 0.01:
        return
    c = CD.CHUNKS[i]
    wt = CD.word_times(c)
    words = [w for w, _, _ in wt]
    act, age = -1, 0.0
    for k, (_, ws, we) in enumerate(wt):
        if T >= ws:
            act, age = k, T - ws
    fin = clamp01((T - c[0] + 0.05) / 0.12)
    img = S.subtitle(words, act, age, size, max_w)
    S.paste(fr, img, (W / 2 if cx is None else cx) - img.width / 2, cy - img.height / 2, fin * alpha)


# ---- chapters / header ----------------------------------------------------------------------------------------
CH = TL.CHAPTERS


def chapter_at(T):
    idx = None
    for i, c in enumerate(CH):
        if c[0] <= T:
            idx = i
    return idx


def draw_top(fr, T, a_ui):
    """Logo bug, chapter header (or the big chapter title), prompts."""
    s0 = TL.STING_T0
    sting_on = s0 <= T < s0 + 2.9
    bug_a = a_ui * (0.0 if (sting_on and T < s0 + 2.75) else 1.0)
    if REEL:
        bx, by, bs = SAFE_L, ROW1_Y, 48
    else:
        bx, by, bs = 40, BAR // 2 - 22, 44
    S.draw_bug(fr, bx, by, bug_a, size=bs)
    ci = chapter_at(T)
    if ci is None:
        return
    t_ch, name, card = CH[ci]
    nxt = CH[ci + 1][0] if ci + 1 < len(CH) else TL.SRC_END
    prog = clamp01((T - t_ch) / max(nxt - t_ch, 0.1))
    bt = 0.0
    if card:
        if REEL:
            bt = S.bar_title(fr, T - t_ch, ci + 1, card, SAFE_CX, PANEL_Y + 74, size=40, dur=2.6)
        else:
            bt = S.bar_title(fr, T - t_ch, ci + 1, card, W / 2, BAR / 2 - 4, size=50, dur=2.6)
    ha = a_ui * (1 - (bt if (card and T - t_ch < 2.6) else 0.0)) * ease_out(clamp01((T - t_ch) / 0.4 if not card else 1.0))
    if card and T - t_ch < 2.6:
        ha = a_ui * (ease_out(clamp01((T - t_ch - 2.3) / 0.3)))
    if REEL:
        S.draw_header(fr, 0, ROW1_Y + 10, ci + 1, len(CH), name, alpha=ha, size=22, right=SAFE_R - 8, progress=prog, width=1)
    else:
        S.draw_header(fr, 0, BAR // 2 - 16, ci + 1, len(CH), name, alpha=ha, size=24, right=W - 48, progress=prog, width=1)


def draw_ctas(fr, T, a_ui):
    ctas = list(TL.CTAS)
    if REEL:
        ctas = [(t, "subscribe") for t, _ in getattr(TL, "REEL_CTAS_SRC", [])]
    for t0, what in ctas:
        t = T - t0
        if t < 0 or t > 4.0:
            continue
        if REEL:
            x, y, s = SAFE_L, PANEL_Y + 82, 0.70
        else:
            x, y, s = W / 2 - 205, BAR / 2 - 31, 0.80
        if what == "subscribe":
            C.cta_subscribe(fr, t, x, y, dur=3.6, scale=s)
        elif what == "like":
            C.cta_like(fr, t, x + 70, y, dur=2.0, scale=s)
        elif what == "share":
            C.cta_share(fr, t, x + 70, y, dur=2.4, scale=s)


# ---- in-picture graphics --------------------------------------------------------------------------------------
def panel_active(T):
    """Reel: the top area shows a product panel instead of the chapter header."""
    for (a, b) in (TL.INFO_CARD, TL.LIP_DIAGRAM, TL.PRICE[:2], (199.61, 203.7)):
        if a - 0.1 <= T < b + 0.1:
            return True
    return False


def draw_graphics(fr, T, win):
    def P(x, y):
        return to_pic(win, x, y, PW, PH, PX, PY)

    # tracked callouts
    sz = 26 if REEL else 30
    for (t0, t1, name, idx, label, sub, side, dist) in TL.CALLOUTS:
        if not (t0 <= T < t1 + 0.05):
            continue
        p = track_at(name, T)
        if p is None:
            continue
        ax, ay = P(*p)
        if label is None:                      # ring + leader to a diagram: dist holds the target in output pixels
            if REEL:
                continue
            tx, ty = dist[0]
            S.pin_line(fr, T - t0, ax, ay, tx, ty, dur=t1 - t0)
            continue
        dd = (dist[0] * (0.75 if REEL else 1.0), dist[1] * (0.75 if REEL else 1.0))
        S.callout(fr, T - t0, ax, ay, idx, label, sub, side=side, dist=dd, size=sz, dur=t1 - t0, clip=(PY, PY + PH),
                  xmax=(SAFE_R if REEL else None))
    for (t0, t1, name) in getattr(TL, "HEAT_WAVES", []):
        if t0 <= T < t1:
            p = track_at(name, T)
            if p is not None:
                ax, ay = P(*p)
                S.heat_waves(fr, T - t0, ax, ay, t1 - t0, scale=0.8 if REEL else 1.0)

    if REEL:
        a, b = TL.INFO_CARD
        S.info_rows(fr, T - a, SAFE_L + 4, PANEL_Y + 6, [("5 COLOURS", "plus a transparent version"),
                                                         ("iPHONE 13+", "and newer models")], b - a, size=26)
        a, b = TL.LIP_DIAGRAM
        S.lip_diagram(fr, T - a, SAFE_L, PANEL_Y - 4, b - a, w=340, size=20)
        a, b, mrp, price, note = TL.PRICE
        S.price_card(fr, T - a, SAFE_L + 4, PANEL_Y + 6, mrp, price, note=note, size=0.62, dur=b - a)
        S.chip(fr, T - 199.61, SAFE_L, PANEL_Y + 8, "Link in the description", 4.1, size=26)
        return

    a, b = TL.NOT_SPONSORED
    S.chip(fr, T - a, 72, PY + 36, "Not sponsored  ·  my own experience", b - a, size=24)
    a, b, nm, sub = TL.NAME_TAG
    S.name_tag(fr, T - a, 72, PY + 40, nm, sub, b - a, size=40)
    a, b = TL.INFO_CARD
    S.info_rows(fr, T - a, 80, PY + 70, [("5 COLOURS", "plus a transparent version"), ("iPHONE 13+", "and newer models"),
                                         ("LINK", "in the description")], b - a, size=40)
    a, b = TL.LENS_CARD
    S.lens_card(fr, T - a, 80, PY + 70, b - a, size=28, align="left")
    a, b = TL.LIP_DIAGRAM
    S.lip_diagram(fr, T - a, 72, PY + 36, b - a, w=520, align="left", size=26)
    a, b, mrp, price, note = TL.PRICE
    S.price_card(fr, T - a, 90, PY + 80, mrp, price, note=note, size=1.0, dur=b - a)
    a, b, title, items, foot = TL.SUMMARY
    S.spec_list(fr, T - a, items, 80, PY + 56, size=30, dur=b - a, title=title, extra_h=40, extra_w=150)
    if a <= T < b:
        k = ease_out(clamp01((T - a - 2.4) / 0.5)) * (1 - ease_io(clamp01((T - (b - 0.35)) / 0.35)))
        if k > 0:
            fi, _ = S._txt_rgba(foot.upper(), S.font("label6", 22), S.EMBER_HI, tracking=2)
            S.paste(fr, fi, 80, PY + 56 + 30 * 0.8 + 12 + int(30 * 1.55) * len(items) + 14, k)


# ---- frame ----------------------------------------------------------------------------------------------------
def render(u):
    T = u_to_T(u)
    n = int(round(T * 30))
    src = reader.get(n)
    cx, cy, z = cam_at(T)
    fr = np.zeros((H, W, 3), np.float32)
    t_open = T - TITLE_END                                  # > 0 once the title hands over to the film
    if t_open < 0.55:
        full_win = window(cx, cy, z, W / H, REEL)
        full = graded(src, full_win, W, H, GRADE_FULL, T, n)
        if T < TITLE_END:
            fr = TITLE.background(full, T)
            TITLE.draw(fr, T)
            fr = np.ascontiguousarray(fr)
        else:
            fr = full.copy()
        p = (T - TITLE_END) / 0.22
        if -1 < p < 1:
            fr = C.flash(np.ascontiguousarray(fr), p)
        if t_open >= 0:
            k = ease_io(clamp01(t_open / 0.55))
            if REEL:
                win = window(cx, cy, z * REEL_ZOOM, PW / PH, True)
                lay = layout_reel(src, win, T, n)
                fr = fr * (1 - k) + lay * k
            else:
                S.letterbox(fr, int(round(BAR * k)))
        return finish(fr, u, T, max(0.0, clamp01(t_open / 0.55)) if t_open >= 0 else 0.0,
                      window(cx, cy, z * (REEL_ZOOM if REEL else 1.0), PW / PH, REEL))
    win = window(cx, cy, z * (REEL_ZOOM if REEL else 1.0), PW / PH, REEL)
    if REEL:
        fr = layout_reel(src, win, T, n)
    else:
        fr[PY:PY + PH] = graded(src, win, PW, PH, GRADE_PIC, T, n)
    return finish(fr, u, T, 1.0, win)


_CARD = {}


def _card_masks():
    """Anti-aliased rounded-card alpha, its drop shadow and a thin warm rim (cached)."""
    if not _CARD:
        r, ss = 34, 3
        m = np.zeros((PH * ss, PW * ss), np.uint8)
        cv2.rectangle(m, (r * ss, 0), ((PW - r) * ss, PH * ss), 255, -1)
        cv2.rectangle(m, (0, r * ss), (PW * ss, (PH - r) * ss), 255, -1)
        for cx_, cy_ in ((r, r), (PW - r, r), (r, PH - r), (PW - r, PH - r)):
            cv2.circle(m, (cx_ * ss, cy_ * ss), r * ss, 255, -1, lineType=cv2.LINE_AA)
        alpha = cv2.resize(m, (PW, PH), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        shadow = np.zeros((H, W), np.float32)
        shadow[PY + 18:PY + PH + 18, PX:PX + PW] = alpha
        shadow = cv2.GaussianBlur(shadow, (0, 0), 26)
        er = cv2.erode(alpha, np.ones((3, 3), np.uint8))
        _CARD.update(alpha=alpha[..., None], shadow=shadow[..., None], rim=np.clip(alpha - er, 0, 1)[..., None])
    return _CARD


def layout_reel(src, win, T, n):
    fr = np.zeros((H, W, 3), np.float32)
    cx, cy, z = cam_at(T)
    bgw = window(cx, cy, z * 0.92, W / H, True)
    bg = crop_resize(src, bgw, W // 6, H // 6)
    bg = cv2.GaussianBlur(bg, (0, 0), 7)
    bg = cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR)
    g = bg.mean(-1, keepdims=True)
    fr[:] = (bg * 0.45 + g * 0.55) * 0.30 + np.array(S.INK, np.float32) / 255 * 0.45
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    fr *= 1 - 0.35 * np.clip((yy - 0.78) / 0.22, 0, 1)             # calmer bottom zone under the platform caption
    M = _card_masks()
    fr *= 1 - 0.55 * M["shadow"]
    pic = graded(src, win, PW, PH, GRADE_PIC, T, n)
    sub = fr[PY:PY + PH, PX:PX + PW]
    sub[:] = sub * (1 - M["alpha"]) + pic * M["alpha"]
    sub[:] = sub * (1 - 0.8 * M["rim"]) + np.array((150, 112, 88), np.float32) / 255 * 0.8 * M["rim"]
    return fr


def finish(fr, u, T, a_ui, win):
    fr = np.ascontiguousarray(fr, dtype=np.float32)
    if a_ui > 0:
        draw_graphics(fr, T, win)
        if not REEL:
            S.letterbox(fr, int(round(BAR * a_ui)))
        draw_top(fr, T, a_ui)
        draw_ctas(fr, T, a_ui)
        sub_a = clamp01((a_ui - 0.85) / 0.15)           # subtitles wait until the bars / panels are in place
        if REEL:
            draw_subs(fr, T, SUB_Y, 40, SAFE_R - SAFE_L - 20, sub_a, cx=SAFE_CX)
        else:
            draw_subs(fr, T, H - BAR / 2, 38, 1640, sub_a)
        s0 = TL.STING_T0
        if s0 <= T < s0 + 3.0:
            if REEL:
                A.draw_sting(fr, T - s0, SAFE_CX, PY + PH / 2, size=180, bug=(SAFE_L, ROW1_Y, 48), name=True)
            else:
                A.draw_sting(fr, T - s0, 400, PY + PH / 2, size=210, bug=(40, BAR // 2 - 22, 44), name=True)
    fade = clamp01((OUT_TOTAL - u) / 0.6)
    return np.clip(fr * fade, 0, 1)


def main():
    if args.frames:
        os.makedirs(args.out_dir, exist_ok=True)
        for t in [float(x) for x in args.frames.split(",")]:
            t0 = time.time()
            fr = render(t)
            cv2.imwrite(os.path.join(args.out_dir, f"{'r' if REEL else 'w'}_{t:07.2f}.png"),
                        cv2.cvtColor((fr * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
            print(f"u={t:7.2f} T={u_to_T(t):7.2f}  {time.time() - t0:5.2f}s", flush=True)
        return
    n0, n1 = int(round(args.start * FPS)), int(round(END_U * FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-pix_fmt", "yuv420p",
                            "-profile:v", "high", "-tune", "film", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    t_start = time.time()
    for k in range(n0, n1):
        u = k / FPS
        enc.stdin.write((render(u) * 255 + 0.5).astype(np.uint8).tobytes())
        if (k - n0) % 60 == 0:
            el = time.time() - t_start
            done = k - n0 + 1
            print(f"u={u:7.2f}  {done}/{n1 - n0}  elapsed {el:6.0f}s  eta {el / done * (n1 - n0 - done):6.0f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    reader.close()
    print("done", args.out, flush=True)


if __name__ == "__main__":
    main()
