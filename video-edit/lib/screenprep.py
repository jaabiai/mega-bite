"""Clean-up of the iPhone screen recording (1320x2868 RGB frames, time S in recording seconds).

* blurs every e-mail address / account name (ours and other people's)
* removes the screen-recording indicators (red dot in the island, orange status icon)
* removes the floating AssistiveTouch bubble
Rect coordinates are normalised (u0, v0, u1, v1) over the screen.
"""
import cv2
import numpy as np

SW, SH = 1320, 2868

# (S_start, S_end, (u0, v0, u1, v1))
BLUR_RECTS = [
    # account sheet sliding up / settled: header + every account row
    (21.95, 22.55, (0.00, 0.20, 1.00, 1.00)),
    (22.55, 29.45, (0.03, 0.255, 0.97, 0.845)),
    # "Manage your Google Account" pop-over: e-mail line, tail of the e-mail behind it, account rows under it
    (28.25, 36.95, (0.10, 0.228, 0.56, 0.290)),
    (28.25, 36.95, (0.56, 0.285, 0.80, 0.345)),
    (28.25, 36.60, (0.02, 0.372, 0.98, 0.900)),
    (36.40, 36.95, (0.02, 0.150, 0.98, 0.900)),
    # Google Account page header (name + e-mail + avatar) and the flick-scroll that removes it
    (36.60, 37.95, (0.06, 0.135, 0.70, 0.300)),
    (37.95, 38.50, (0.00, 0.000, 1.00, 0.360)),
    # passkey page: e-mail chip
    (73.55, 88.00, (0.03, 0.498, 0.70, 0.560)),
    (73.50, 73.90, (0.03, 0.405, 0.70, 0.470)),     # chip position during the page's first frames
]

R = None          # per-project rules module (BLUR_RECTS, DOT, ORANGE, ASSIST, BUBBLE_CAL, BLUR_SIGMA)


def configure(rules):
    """rules: module with BLUR_RECTS [(s0, s1, (u0, v0, u1, v1))], BLUR_SIGMA, DOT / ORANGE / ASSIST (x, y, r) or None,
    BUBBLE_CAL dict(t_light, t_dark, centre_in_crop, rim, lower_valid)."""
    global R
    R = rules


def _blur_rect(img, rect, soft=True):
    u0, v0, u1, v1 = rect
    x0, y0, x1, y1 = (int(max(0, u0) * SW), int(max(0, v0) * SH), int(min(1, u1) * SW), int(min(1, v1) * SH))
    if x1 <= x0 or y1 <= y0:
        return
    sigma = R.BLUR_SIGMA
    pad = 3 * sigma
    xa, ya, xb, yb = max(0, x0 - pad), max(0, y0 - pad), min(SW, x1 + pad), min(SH, y1 + pad)
    roi = img[ya:yb, xa:xb]
    # blur twice: second pass is on a much smaller image for speed and extra strength
    small = cv2.resize(roi, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / 4.0 * 1.6)
    blur = cv2.resize(small, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_CUBIC)
    m = np.zeros(roi.shape[:2], np.float32)
    m[y0 - ya:y1 - ya, x0 - xa:x1 - xa] = 1.0
    if soft:
        m = cv2.GaussianBlur(m, (0, 0), 6)
    img[ya:yb, xa:xb] = (roi * (1 - m[..., None]) + blur * m[..., None]).astype(np.uint8)


_masks = {}
_island = {}


def _paint_island(img, box):
    """Repaint the black Dynamic Island pill (anti-aliased) – used where a blur rectangle reaches over it."""
    x0, y0, x1, y1 = box
    if box not in _island:
        k = 4
        m = np.zeros(((y1 - y0 + 8) * k, (x1 - x0 + 8) * k), np.uint8)
        cv2.rectangle(m, (4 * k + (y1 - y0) // 2 * k, 4 * k), (4 * k + (x1 - x0) * k - (y1 - y0) // 2 * k, 4 * k + (y1 - y0) * k), 255, -1)
        r = (y1 - y0) * k // 2
        cv2.circle(m, (4 * k + r, 4 * k + r), r, 255, -1)
        cv2.circle(m, (4 * k + (x1 - x0) * k - r, 4 * k + r), r, 255, -1)
        _island[box] = cv2.resize(m, (x1 - x0 + 8, y1 - y0 + 8), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255.0
    a = _island[box]
    roi = img[y0 - 4:y1 + 4, x0 - 4:x1 + 4]
    img[y0 - 4:y1 + 4, x0 - 4:x1 + 4] = (roi * (1 - a)).astype(np.uint8)


def _circle_mask(shape, cx, cy, r):
    m = np.zeros(shape[:2], np.uint8)
    cv2.circle(m, (cx, cy), r, 255, -1)
    return m


_CAL = {}


def calibrate_bubble_multi(sdr_path):
    """Fit the AssistiveTouch bubble per radius and channel from several frames on different flat backgrounds
    (R.BUBBLE_CAL['times']): obs = m * bg + b with m = 1 - alpha and b = alpha * colour (least squares over the frames)."""
    import subprocess
    cal = R.BUBBLE_CAL
    cx, cy, _ = R.ASSIST
    n = 300
    x0, y0 = max(0, min(cx - 150, SW - n)), max(0, min(cy - 150, SH - n))

    def grab(t):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", sdr_path, "-frames:v", "1",
                              "-vf", f"crop={n}:{n}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8).reshape(n, n, 3).astype(np.float32)

    frames = [grab(t) for t in cal["times"]]
    yy, xx = np.mgrid[0:n, 0:n]
    cxm, cym = cal["centre_in_crop"]
    r = np.hypot(xx - cxm, yy - cym)
    r_in, r_out = cal.get("ring", (105, 135))
    ring = (r > r_in) & (r < r_out)
    bgs = np.array([np.median(f[ring], axis=0) for f in frames])                    # (F, 3)
    nb = 140
    m_prof, b_prof = np.ones((nb, 3), np.float32), np.zeros((nb, 3), np.float32)
    for k in range(nb):
        sel = (r >= k) & (r < k + 1)
        if sel.sum() < 6:
            continue
        obs = np.array([np.median(f[sel], axis=0) for f in frames])                 # (F, 3)
        for c in range(3):
            A = np.stack([bgs[:, c], np.ones(len(frames))], axis=1)
            sol, *_ = np.linalg.lstsq(A, obs[:, c], rcond=None)
            m_prof[k, c], b_prof[k, c] = sol
    m_prof = np.clip(m_prof, 0.25, 1.0)
    for c in range(3):                                                                # light smoothing along r
        m_prof[:, c] = np.convolve(np.pad(m_prof[:, c], 2, mode="edge"), np.ones(3) / 3, mode="same")[2:-2]
        b_prof[:, c] = np.convolve(np.pad(b_prof[:, c], 2, mode="edge"), np.ones(3) / 3, mode="same")[2:-2]
    rim = cal["rim"]
    m_prof[rim:] = 1.0
    b_prof[rim:] = 0.0
    ar = np.arange(nb, dtype=np.float32)
    oma = np.stack([np.interp(r, ar, m_prof[:, c]) for c in range(3)], axis=-1).astype(np.float32)
    aC = np.stack([np.interp(r, ar, b_prof[:, c]) for c in range(3)], axis=-1).astype(np.float32)
    _CAL.update(oma=oma, aC=aC, box=(x0, y0, n), centre=(cxm, cym))


def calibrate_bubble(sdr_path, bg_light=None, bg_dark=None):
    """Estimate the AssistiveTouch bubble's per-pixel alpha / colour from two frames where it sits on flat backgrounds.
    obs = (1-a)*bg + a*C  ->  (1-a) = (obs_L - obs_D) / (bg_L - bg_D)."""
    import subprocess
    cal = R.BUBBLE_CAL
    t_light, t_dark = cal["t_light"], cal["t_dark"]
    cx, cy, _ = R.ASSIST
    n = 300
    x0, y0 = max(0, min(cx - 150, SW - n)), max(0, min(cy - 150, SH - n))      # box stays inside the frame

    def grab(t):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", sdr_path, "-frames:v", "1",
                              "-vf", f"crop={n}:{n}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8).reshape(n, n, 3).astype(np.float32)

    L, D = grab(t_light), grab(t_dark)
    yy, xx = np.mgrid[0:n, 0:n]
    cxm, cym = cal["centre_in_crop"]                                      # bubble centre (measured on the flat light frame)
    r = np.hypot(xx - cxm, yy - cym)
    r_in, r_out = cal.get("ring", (130, 146))                             # flat background ring around the bubble
    ring = (r > r_in) & (r < r_out)
    bgL = np.median(L[ring], axis=0) if bg_light is None else np.array(bg_light, np.float32)
    bgD = np.median(D[ring & (yy < cal["lower_valid"] + 5)], axis=0) if bg_dark is None else np.array(bg_dark, np.float32)
    raw = (L - D) / (bgL - bgD)[None, None, :]                       # per-channel (1-a) estimate
    valid = (yy < cal["lower_valid"]) & (r < cal.get("valid_r", 135))              # lower rim of the dark frame sits on another background
    # radial profiles (median over angle), per channel
    nb = 140
    oma_prof = np.ones((nb, 3), np.float32)
    for k in range(nb):
        sel = valid & (r >= k) & (r < k + 1)
        if sel.sum() >= 6:
            oma_prof[k] = np.median(raw[sel], axis=0)
    oma_prof = np.clip(oma_prof, 0.25, 1.0)
    # smooth the profile a little and force 1.0 beyond the rim
    for c in range(3):
        oma_prof[:, c] = np.convolve(np.pad(oma_prof[:, c], 2, mode="edge"), np.ones(3) / 3, mode="same")[2:-2]
    rim = cal["rim"]
    oma_prof[rim:] = 1.0
    ar = np.arange(nb, dtype=np.float32)
    one_minus_a = np.stack([np.interp(r, ar, oma_prof[:, c]) for c in range(3)], axis=-1).astype(np.float32)
    aC = (L - one_minus_a * bgL[None, None, :]).astype(np.float32)
    # a*C is also radially symmetric: take it from the profile of the light frame
    ac_prof = np.zeros((nb, 3), np.float32)
    for k in range(nb):
        sel = (r >= k) & (r < k + 1) & (yy < 280)
        if sel.sum() >= 6:
            ac_prof[k] = np.median(aC[sel], axis=0)
    ac_prof[rim:] = 0.0
    aC = np.stack([np.interp(r, ar, ac_prof[:, c]) for c in range(3)], axis=-1).astype(np.float32)
    _CAL.update(oma=one_minus_a, aC=aC, box=(x0, y0, n), centre=(cxm, cym))


def _erase_bubble(img):
    if not _CAL:
        raise RuntimeError("call screenprep.calibrate_bubble(sdr_path) first")
    x0, y0, n = _CAL["box"]
    roi = img[y0:y0 + n, x0:x0 + n].astype(np.float32)
    out = (roi - _CAL["aC"]) / _CAL["oma"]
    img[y0:y0 + n, x0:x0 + n] = np.clip(out, 0, 255).astype(np.uint8)


def _remove_indicators(img, band, disc=28):
    """Find the red / orange recording indicators wherever they currently sit inside `band` (x0, y0, x1, y1) and paint them out
    together with the black disc they sit in."""
    x0, y0, x1, y1 = band
    roi = img[y0:y1, x0:x1]
    r, g, b = (roi[..., k].astype(np.int16) for k in range(3))
    m = (((r - b) > 90) & (r > 150)).astype(np.uint8)
    if not m.any():
        return
    n, _, stats, cen = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((5, 5), np.uint8)))
    mask = np.zeros(m.shape, np.uint8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 20:
            cv2.circle(mask, (int(round(cen[i][0])), int(round(cen[i][1]))), disc, 255, -1)
    img[y0:y1, x0:x1] = cv2.inpaint(np.ascontiguousarray(roi), mask, 6, cv2.INPAINT_TELEA)


# ---- AssistiveTouch bubble, second method: rebuild the background instead of un-mixing the bubble -------------------------
_BG = {}


def _bubble_geom(spec, centre):
    key = ("geom", round(centre[0], 1), round(centre[1], 1))
    if key not in _BG:
        cx, cy = centre
        r, f = spec["radius"], spec.get("feather", 4)
        pad = r + f + 28
        x0, y0, x1, y1 = max(int(cx - pad), 0), max(int(cy - pad), 0), min(int(cx + pad), SW), min(int(cy + pad), SH)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(xx - cx, yy - cy)
        _BG[key] = dict(box=(x0, y0, x1, y1), d=d, xx=xx, yy=yy, m=np.clip((r + f - d) / f, 0, 1)[..., None])
    return _BG[key]


def erase_bubble(img, S):
    """Mode by recording time (spec['modes'] = [(s0, s1, mode)]): 'flat' wallpaper -> fill with the colour around it,
    'inpaint' -> generic fill (transitions), 'patch' -> redraw the known header / search-field edge of the Recents page."""
    spec = R.BUBBLE
    hit = next((e for e in spec["modes"] if e[0] <= S < e[1]), None)       # (s0, s1, mode) or (s0, s1, mode, (cx, cy))
    if hit is None:
        return
    mode = hit[2]
    g = _bubble_geom(spec, hit[3] if len(hit) > 3 else spec["centre"])
    x0, y0, x1, y1 = g["box"]
    roi = img[y0:y1, x0:x1]
    d, m = g["d"], g["m"]
    r, f = spec["radius"], spec.get("feather", 4)
    ring = (d > r + f + 4) & (d < r + f + 24)
    if mode == "flat":
        px = roi[ring].astype(np.float32)
        if px.std(0).max() <= 2.5:
            col = np.median(px, axis=0)
            img[y0:y1, x0:x1] = (roi * (1 - m) + col[None, None, :] * m + 0.5).astype(np.uint8)
            return
        mode = "inpaint"                                  # not flat after all
    if mode == "inpaint":
        mask = (d <= r + f / 2).astype(np.uint8) * 255
        img[y0:y1, x0:x1] = cv2.inpaint(np.ascontiguousarray(roi), mask, 7, cv2.INPAINT_TELEA)
        return
    pa = spec["patch"]                                   # header colour, search-field colour and the field's outline
    hx, hy = pa["header_px"]; fx, fy = pa["fill_px"]
    base = np.median(img[hy:hy + 6, hx:hx + 20].reshape(-1, 3), axis=0).astype(np.float32)
    fill = np.median(img[fy:fy + 6, fx:fx + 20].reshape(-1, 3), axis=0).astype(np.float32)
    px0, py0, px1, py1 = pa["pill"]
    rad = (py1 - py0) / 2
    qx = np.maximum(np.abs(g["xx"] - (px0 + px1) / 2) - ((px1 - px0) / 2 - rad), 0)      # stadium (pill) distance field
    sdf = np.hypot(qx, g["yy"] - (py0 + py1) / 2) - rad
    cov = np.clip(0.5 - sdf, 0, 1)[..., None]
    patch = base[None, None, :] * (1 - cov) + fill[None, None, :] * cov
    if "line_y" in pa:                                   # hairline under the navigation bar
        ly = pa["line_y"]
        lc = np.median(img[ly, hx:hx + 20].reshape(-1, 3), axis=0).astype(np.float32)
        patch[(g["yy"] == ly)] = lc
    img[y0:y1, x0:x1] = (roi * (1 - m) + patch * m + 0.5).astype(np.uint8)


def prepare(img, S):
    """img: HxWx3 uint8 RGB (modified & returned); S = recording time of the frame in seconds."""
    if getattr(R, "ASSIST", None) and not getattr(R, "BUBBLE", None):
        _erase_bubble(img)                               # linear overlay model: undo it on the untouched pixels, before any blur
    for s0, s1, rect in R.BLUR_RECTS:
        if s0 <= S <= s1:
            _blur_rect(img, rect)
    for s0, s1, (ix0, iy0, ix1, iy1) in getattr(R, "ISLAND_FIX", []):      # blurs must not smear the Dynamic Island
        if s0 <= S <= s1:
            _paint_island(img, (ix0, iy0, ix1, iy1))
    dot = getattr(R, "DOT", None)
    if dot:                                              # island dot -> pure black
        cv2.circle(img, (dot[0], dot[1]), dot[2], (0, 0, 0), -1)
    orange = getattr(R, "ORANGE", None)
    if orange:                                           # orange recording glyph -> small inpaint
        cx, cy, r = orange
        pad = r + 30
        x0, y0, x1, y1 = cx - pad, cy - pad, cx + pad, cy + pad
        roi = np.ascontiguousarray(img[y0:y1, x0:x1])
        if orange not in _masks:
            _masks[orange] = _circle_mask(roi.shape, pad, pad, r)
        img[y0:y1, x0:x1] = cv2.inpaint(roi, _masks[orange], 6, cv2.INPAINT_TELEA)
    band = getattr(R, "INDICATOR_BAND", None)
    if band:                                             # moving indicators: detect by colour instead of fixed positions
        _remove_indicators(img, band)
    if getattr(R, "BUBBLE", None):
        erase_bubble(img, S)
    return img
