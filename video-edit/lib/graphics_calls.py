"""Explainer graphics for the "hide WhatsApp calls from the call log" video: a Recents list that loses its WhatsApp rows
once Face ID is required, and the "Face ID unlocks WhatsApp" diagram.  All drawn procedurally (no third-party artwork)."""
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw
from brand import hex2rgb
from caption import font
from gfx import *
from graphics import lock_icon, check_icon, tint

WA_GREEN = (37, 211, 102)                    # generic "messenger green" used for the WhatsApp markers
GREY = (150, 163, 154)

ROWS = [
    ("Alex", "phone", "9:14 AM", False),
    ("Priya", "WhatsApp Audio", "9:04 AM", True),
    ("Office", "phone (2)", "8:37 AM", False),
    ("Sam", "WhatsApp Video", "8:11 AM", True),
    ("Maya", "phone", "7:41 AM", False),
    ("Dad", "WhatsApp Audio", "Yesterday", True),
]


# ---------------------------------------------------------------------------------------------- icons
def face_id_icon(size, rgb, width=None):
    """Face ID glyph: four corner brackets, eyes, nose, smile."""
    s = int(size)
    w = width or max(2.0, s * 0.05)

    def fn(d, ss):
        K = s * ss
        lw = int(w * ss)
        m = 0.07 * K
        d.rounded_rectangle([m, m, K - m, K - m], radius=0.24 * K, outline=255, width=lw)
        g0, g1 = 0.34 * K, 0.66 * K                                      # gaps in the middle of every side
        d.rectangle([g0, 0, g1, m + lw + 2], fill=0)
        d.rectangle([g0, K - m - lw - 2, g1, K], fill=0)
        d.rectangle([0, g0, m + lw + 2, g1], fill=0)
        d.rectangle([K - m - lw - 2, g0, K, g1], fill=0)
        for ex in (0.36, 0.64):                                          # eyes
            d.line([ex * K, 0.34 * K, ex * K, 0.45 * K], fill=255, width=lw)
            for ey in (0.34, 0.45):
                d.ellipse([ex * K - lw / 2, ey * K - lw / 2, ex * K + lw / 2, ey * K + lw / 2], fill=255)
        d.line([0.50 * K, 0.38 * K, 0.50 * K, 0.55 * K, 0.45 * K, 0.58 * K], fill=255, width=lw, joint="curve")   # nose
        d.arc([0.33 * K, 0.50 * K, 0.67 * K, 0.76 * K], 25, 155, fill=255, width=lw)                              # smile
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def handset_bubble(size, bg_rgb, fg=(255, 255, 255)):
    """Round 'messenger' badge: coloured disc, white ring-bubble with a phone handset (generic, not the trademarked glyph)."""
    s = int(size)

    def disc(d, ss):
        d.ellipse([0, 0, s * ss - 1, s * ss - 1], fill=255)

    def glyph(d, ss):
        K = s * ss
        lw = int(0.075 * K)
        d.arc([0.20 * K, 0.18 * K, 0.80 * K, 0.78 * K], 112, 450, fill=255, width=lw)              # bubble ring
        d.polygon([(0.24 * K, 0.80 * K), (0.22 * K, 0.60 * K), (0.38 * K, 0.74 * K)], fill=255)        # tail
        d.arc([0.34 * K, 0.30 * K, 0.78 * K, 0.74 * K], 150, 240, fill=255, width=int(0.10 * K))        # handset body
        d.ellipse([0.35 * K, 0.53 * K, 0.43 * K, 0.61 * K], fill=255)
        d.ellipse([0.51 * K, 0.67 * K, 0.59 * K, 0.75 * K], fill=255)
    img = with_mask((s, s), bg_rgb, aa_shape((s, s), disc))
    return Image.alpha_composite(img, with_mask((s, s), fg, aa_shape((s, s), glyph)))


def phone_glyph(size, rgb):
    s = int(size)

    def fn(d, ss):
        K = s * ss
        d.arc([0.12 * K, 0.12 * K, 0.88 * K, 0.88 * K], 100, 200, fill=255, width=int(0.17 * K))
        d.ellipse([0.14 * K, 0.58 * K, 0.34 * K, 0.78 * K], fill=255)
        d.ellipse([0.58 * K, 0.14 * K, 0.78 * K, 0.34 * K], fill=255)
    return with_mask((s, s), rgb, aa_shape((s, s), fn))


def app_tile(size, pal):
    """Stylised green messenger tile (rounded square) used in the unlock diagram."""
    s = int(size)
    tile = rrect((s, s), (0, 0, s - 1, s - 1), s * 0.225, (30, 190, 92), 1.0)
    # soft top-left light
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    k = np.clip(1.0 - (xx + yy) / (1.5 * s), 0, 1)[..., None]
    a = np.asarray(tile, np.float32)
    a[..., :3] = np.clip(a[..., :3] + k * 38, 0, 255)
    tile = Image.fromarray(a.astype(np.uint8), "RGBA")
    tile.alpha_composite(_glyph_only(int(s * 0.74)), (int(s * 0.13), int(s * 0.13)))
    return tile


def _glyph_only(s):
    def glyph(d, ss):
        K = s * ss
        lw = int(0.075 * K)
        d.arc([0.12 * K, 0.10 * K, 0.88 * K, 0.86 * K], 112, 450, fill=255, width=lw)
        d.polygon([(0.17 * K, 0.90 * K), (0.14 * K, 0.66 * K), (0.34 * K, 0.82 * K)], fill=255)
        d.arc([0.30 * K, 0.26 * K, 0.84 * K, 0.80 * K], 150, 240, fill=255, width=int(0.11 * K))
        d.ellipse([0.31 * K, 0.58 * K, 0.41 * K, 0.68 * K], fill=255)
        d.ellipse([0.50 * K, 0.74 * K, 0.60 * K, 0.84 * K], fill=255)
    return with_mask((s, s), (255, 255, 255), aa_shape((s, s), glyph))


def _text(img, xy, txt, f, fill):
    ImageDraw.Draw(img).text(xy, txt, font=f, fill=fill)


# ---------------------------------------------------------------------------------------------- Recents list
def _card(w, h, r):
    base = rrect((w, h), (0, 0, w - 1, h - 1), r, (18, 24, 20), 0.90, outline=(255, 255, 255, 34), width=2)
    return base


def _row_layer(w, h, name, sub, when, wa, S, hot=0.0, acc=(198, 244, 50)):
    """One Recents row (RGBA). `hot` 0..1 pulses a green outline on WhatsApp rows."""
    img = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    av = int(h * 0.64)
    ax, ay = int(h * 0.20), int((h - av) / 2)
    avatar = rrect((av, av), (0, 0, av - 1, av - 1), av / 2, (40, 118, 76) if wa else (62, 74, 66), 1.0)
    img.alpha_composite(avatar, (ax, ay))
    fi = font("title", av * 0.46)
    _text(img, (ax + (av - fi.getlength(name[0])) / 2, ay + av * 0.17), name[0], fi, (255, 255, 255, 255))
    tx = ax + av + h * 0.20
    fn_, fs, ft = font("label", h * 0.30), font("body", h * 0.235), font("body", h * 0.23)
    _text(img, (tx, h * 0.14), name, fn_, (255, 255, 255, 255))
    sx = tx
    if wa:
        b = handset_bubble(int(h * 0.26), WA_GREEN)
        img.alpha_composite(b, (int(tx), int(h * 0.55)))
        sx = tx + h * 0.26 + h * 0.07
    else:
        pg = phone_glyph(int(h * 0.22), GREY)
        img.alpha_composite(pg, (int(tx), int(h * 0.56)))
        sx = tx + h * 0.22 + h * 0.07
    _text(img, (sx, h * 0.54), sub, fs, GREY + (255,))
    tw = ft.getlength(when)
    _text(img, (w - tw - h * 0.55, h * 0.36), when, ft, GREY + (255,))
    info = aa_shape((int(h * 0.30), int(h * 0.30)), lambda d, ss: d.ellipse([0, 0, h * 0.30 * ss - 1, h * 0.30 * ss - 1], outline=255, width=int(2.2 * ss)))
    img.alpha_composite(with_mask(info.size, GREY, info), (int(w - h * 0.42), int(h * 0.35)))
    fi2 = font("title", h * 0.20)
    _text(img, (w - h * 0.42 + (h * 0.30 - fi2.getlength("i")) / 2, h * 0.355), "i", fi2, GREY + (255,))
    if hot > 0:
        o = rrect((int(w), int(h)), (3, 3, w - 4, h - 4), h * 0.24, WA_GREEN, 0.0, outline=WA_GREEN + (int(235 * hot),), width=3 * S)
        img.alpha_composite(o)
        tint = rrect((int(w), int(h)), (3, 3, w - 4, h - 4), h * 0.24, WA_GREEN, 0.10 * hot)
        img = Image.alpha_composite(tint, img)
    return img


def render_call_log(t, S, pal, bg_img, lay=None):
    """t seconds since scene start (about 4.7 s).  Mixed Recents list -> Face ID scan -> WhatsApp rows vanish."""
    lay = lay or {}
    fr = np.asarray(bg_img.convert("RGB"), np.float32).copy() / 255.0
    acc = hex2rgb(pal["accent"])
    dark = hex2rgb(pal["on_accent"])
    cx, top = lay.get("cx", 1290) * S, lay.get("top", 190) * S
    cw, row_h, head_h = lay.get("card_w", 640) * S, lay.get("row_h", 92) * S, lay.get("head_h", 112) * S
    n_rows = lay.get("rows", 6)
    rows = ROWS[:n_rows]
    # ---- timing
    p_in = ease_out(t / 0.55)
    t_scan0, t_scan1 = lay.get("t_scan", (1.55, 2.85))
    t_gone = lay.get("t_gone", 3.05)                       # WhatsApp rows start to leave
    k_gone = ease_io((t - t_gone) / 0.65)                  # 0 -> 1
    pulse = (0.5 + 0.5 * math.sin(t * 7.0)) if (0.55 < t < t_gone) else 0.0
    # ---- geometry: rows collapse when they vanish
    heights = [row_h * (1 - k_gone) if wa else row_h for (_, _, _, wa) in rows]
    pad_b = 18 * S
    full_h = head_h + row_h * len(rows) + pad_b
    cur_h = head_h + sum(heights) + pad_b
    x0 = cx - cw / 2
    y_off = (1 - p_in) * 70 * S
    card = _card(int(cw), int(cur_h), 36 * S)            # the card shrinks as the WhatsApp rows leave
    d = ImageDraw.Draw(card)
    f_title = font("title", 46 * S)
    d.text((34 * S, 26 * S), "Recents", font=f_title, fill=(255, 255, 255, 255))
    seg_w, seg_h = 218 * S, 46 * S
    seg = rrect((int(seg_w), int(seg_h)), (0, 0, seg_w - 1, seg_h - 1), seg_h / 2, (255, 255, 255), 0.10)
    sd = ImageDraw.Draw(seg)
    fs = font("label", 24 * S)
    sd.rounded_rectangle([4 * S, 4 * S, seg_w / 2, seg_h - 4 * S], radius=seg_h / 2 - 4 * S, fill=(255, 255, 255, 40))
    sd.text((28 * S, 6 * S), "All", font=fs, fill=(255, 255, 255, 255))
    sd.text((seg_w / 2 + 14 * S, 6 * S), "Missed", font=fs, fill=GREY + (255,))
    card.alpha_composite(seg, (int(cw - seg_w - 30 * S), int(34 * S)))
    y = head_h
    for (name, sub, when, wa), h_ in zip(rows, heights):
        if h_ <= 2 * S:
            continue
        lay_row = _row_layer(cw - 12 * S, row_h, name, sub, when, wa, S, hot=pulse if wa else 0.0)
        a = (1 - k_gone) if wa else 1.0
        stag = ease_out((t - 0.12 - 0.06 * rows.index((name, sub, when, wa))) / 0.35)
        if wa and k_gone > 0:
            lay_row = lay_row.crop((0, 0, lay_row.width, max(1, int(h_))))
        _paste_alpha(card, lay_row, int(6 * S), int(y), a * stag)
        y += h_
    # hairlines
    yy_ = head_h
    for h_ in heights[:-1]:
        yy_ += h_
        if h_ > 2 * S:
            ImageDraw.Draw(card).line([(int(110 * S), int(yy_)), (int(cw - 30 * S), int(yy_))], fill=(255, 255, 255, 22), width=max(1, int(S)))
    gl = glow_of(card, 26 * S, 0.8)
    blend_glow(fr, gl, x0, top + y_off, 0.22 * p_in)
    blend(fr, card, x0, top + y_off, p_in)
    # ---- Face ID scan badge
    if t_scan0 - 0.25 < t < t_gone + 0.5:
        appear = ease_back((t - (t_scan0 - 0.25)) / 0.4)
        leave = ease_io((t - (t_gone - 0.05)) / 0.4)
        a = clamp01(appear) * (1 - leave)
        sz = lay.get("badge", 210) * S
        bx, by = cx, top + head_h + row_h * 1.55 + y_off
        disc = rrect((int(sz), int(sz)), (0, 0, sz - 1, sz - 1), sz / 2, (10, 14, 12), 0.94, outline=acc + (255,), width=3.5 * S)
        scanning = t < t_scan1
        if scanning:
            fid = face_id_icon(sz * 0.52, acc, width=sz * 0.027)
            disc.alpha_composite(fid, (int((sz - fid.width) / 2), int((sz - fid.height) / 2)))
            k = (t - t_scan0) / (t_scan1 - t_scan0)                         # sweeping scan line
            ys = sz * (0.27 + 0.46 * (0.5 - 0.5 * math.cos(k * math.pi * 2.0)))
            line = rrect((int(sz * 0.56), int(5 * S)), (0, 0, sz * 0.56 - 1, 5 * S - 1), 2.5 * S, acc, 0.95)
            lg = glow_of(line, 7 * S, 1.6)
            disc.alpha_composite(lg, (int(sz * 0.22 - lg.pad), int(ys - lg.pad)))
            disc.alpha_composite(line, (int(sz * 0.22), int(ys)))
        else:
            ck = check_icon(sz * 0.40, acc, 7 * S)
            disc.alpha_composite(ck, (int((sz - ck.width) / 2), int((sz - ck.height) / 2)))
        g2 = glow_of(disc, 20 * S, 1.2)
        blend_glow(fr, g2, bx - sz / 2, by - sz / 2, 0.55 * a)
        blend(fr, disc, bx - sz / 2, by - sz / 2, a)
    # ---- result pill
    if t > t_gone + 0.45:
        a = ease_out((t - (t_gone + 0.45)) / 0.35)
        pf = font("title", lay.get("pill_size", 30) * S)
        txt = "WHATSAPP CALLS HIDDEN"
        pw, ph = int(pf.getlength(txt) + 96 * S), int(64 * S)
        pill = rrect((pw, ph), (0, 0, pw - 1, ph - 1), ph / 2, acc, 1.0)
        dd = ImageDraw.Draw(pill)
        ck = check_icon(30 * S, dark, 5 * S)
        pill.alpha_composite(ck, (int(22 * S), int(ph / 2 - ck.height / 2)))
        dd.text((62 * S, ph / 2 - pf.size * 0.62), txt, font=pf, fill=dark + (255,))
        blend(fr, pill, cx - pw / 2, top + full_h + 34 * S + (1 - a) * 20 * S, a)
    return fr


def _paste_alpha(card, layer, x, y, opacity):
    if opacity <= 0:
        return
    if opacity < 1:
        a = np.asarray(layer, np.uint8).copy()
        a[..., 3] = (a[..., 3] * opacity).astype(np.uint8)
        layer = Image.fromarray(a, "RGBA")
    card.alpha_composite(layer, (x, y))


# ---------------------------------------------------------------------------------------------- Face ID unlocks WhatsApp
def render_face_unlock(t, S, pal, bg_img, lay=None):
    """t since scene start (about 5.7 s): locked app tile <- Face ID scan -> padlock opens."""
    lay = lay or {}
    fr = np.asarray(bg_img.convert("RGB"), np.float32).copy() / 255.0
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    cx, cy = lay.get("cx", 1290) * S, lay.get("cy", 480) * S
    vertical = lay.get("vertical", False)
    tile_s = lay.get("tile", 230) * S
    face_s = lay.get("face", 230) * S
    gap = lay.get("gap", 210) * S
    if vertical:
        fpos, tpos = (cx, cy - gap), (cx, cy + gap * 0.95)
    else:
        fpos, tpos = (cx - gap, cy), (cx + gap, cy)
    t_scan0, t_ok, t_open = 1.5, 3.1, 3.4
    p_f, p_t = ease_back(t / 0.5), ease_back((t - 0.15) / 0.5)
    # --- app tile with padlock
    tile = app_tile(tile_s, pal)
    unlocked = t >= t_open
    if not unlocked:
        tile_a = np.asarray(tile, np.float32)
        tile_a[..., :3] *= 0.62
        tile = Image.fromarray(tile_a.astype(np.uint8), "RGBA")
    scale = 1.0 + (0.07 * math.sin(min(max((t - t_open) / 0.5, 0), 1) * math.pi) if unlocked else 0.0)
    tl = tile if scale == 1.0 else tile.resize((int(tile.width * scale), int(tile.height * scale)), Image.LANCZOS)
    tx, ty = tpos[0] - tl.width / 2, tpos[1] - tl.height / 2
    glow = glow_of(tl, 24 * S, 1.0)
    blend_glow(fr, glow, tx, ty, (0.55 if unlocked else 0.12) * clamp01(p_t))
    blend(fr, tl, tx, ty, clamp01(p_t))
    lk_s = tile_s * 0.46
    open_amt = ease_back((t - t_open) / 0.4) if unlocked else 0.0
    lock = lock_icon(lk_s, (238, 242, 239), acc if unlocked else (238, 242, 239), open_amt=min(max(open_amt, 0), 1.2))
    ring_r = lk_s * 0.78
    bdg = rrect((int(ring_r * 2), int(ring_r * 2)), (0, 0, ring_r * 2 - 1, ring_r * 2 - 1), ring_r, (12, 17, 14), 0.96, outline=(acc if unlocked else (238, 242, 239)) + (255,), width=3 * S)
    bx, by = tx + tl.width - ring_r * 1.15, ty + tl.height - ring_r * 1.15
    blend(fr, bdg, bx, by, clamp01(p_t))
    blend(fr, lock, bx + ring_r - lock.width / 2, by + ring_r - lock.height / 2 + 2 * S, clamp01(p_t))
    # --- face id disc
    sz = face_s
    scanning = t_scan0 <= t < t_ok
    ok = t >= t_ok
    disc = rrect((int(sz), int(sz)), (0, 0, sz - 1, sz - 1), sz / 2, (10, 14, 12), 0.94,
                 outline=(acc if (scanning or ok) else (150, 163, 154)) + (255,), width=3.5 * S)
    if ok:
        ck = check_icon(sz * 0.44, acc, 8 * S)
        disc.alpha_composite(ck, (int((sz - ck.width) / 2), int((sz - ck.height) / 2)))
    else:
        fid = face_id_icon(sz * 0.52, acc if scanning else (210, 218, 213), width=sz * 0.028)
        disc.alpha_composite(fid, (int((sz - fid.width) / 2), int((sz - fid.height) / 2)))
        if scanning:
            k = (t - t_scan0) / (t_ok - t_scan0)
            ys = sz * (0.27 + 0.46 * (0.5 - 0.5 * math.cos(k * math.pi * 2.0)))
            line = rrect((int(sz * 0.56), int(5 * S)), (0, 0, sz * 0.56 - 1, 5 * S - 1), 2.5 * S, acc, 0.95)
            lg = glow_of(line, 7 * S, 1.6)
            disc.alpha_composite(lg, (int(sz * 0.22 - lg.pad), int(ys - lg.pad)))
            disc.alpha_composite(line, (int(sz * 0.22), int(ys)))
    g2 = glow_of(disc, 20 * S, 1.2)
    blend_glow(fr, g2, fpos[0] - sz / 2, fpos[1] - sz / 2, (0.6 if (scanning or ok) else 0.12) * clamp01(p_f))
    blend(fr, disc, fpos[0] - sz / 2, fpos[1] - sz / 2, clamp01(p_f))
    if ok and t < t_ok + 0.9:                                            # success pulse
        r = (t - t_ok) / 0.9
        rad = (sz / 2 + 90 * ease_out(r) * S)
        ring = Image.new("RGBA", (int(rad * 2 + 20), int(rad * 2 + 20)), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((10, 10, 10 + rad * 2, 10 + rad * 2), outline=acc + (int(220 * (1 - r)),), width=int(5 * S))
        blend(fr, ring, fpos[0] - ring.width / 2, fpos[1] - ring.height / 2)
    # --- connector between the two
    if t > 2.3:
        k = ease_io((t - 2.3) / 0.7)
        a0, a1 = np.array(fpos, np.float32), np.array(tpos, np.float32)
        u = (a1 - a0) / np.linalg.norm(a1 - a0)
        p0 = a0 + u * (sz / 2 + 24 * S)
        p1 = a1 - u * (tile_s / 2 + 28 * S)
        pe = p0 + (p1 - p0) * k
        lay_ = Image.new("RGBA", (int(fr.shape[1]), int(fr.shape[0])), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay_)
        col = acc + (235,)
        dl.line([tuple(p0), tuple(pe)], fill=col, width=int(6 * S))
        if k > 0.98:
            n = np.array([-u[1], u[0]])
            hd = 22 * S
            dl.polygon([tuple(p1 + u * 6 * S), tuple(p1 - u * hd + n * hd * 0.7), tuple(p1 - u * hd - n * hd * 0.7)], fill=col)
        blend(fr, lay_, 0, 0, 1.0)
    # --- result pill
    if t > t_open + 0.35:
        a = ease_out((t - (t_open + 0.35)) / 0.35)
        pf = font("title", lay.get("pill_size", 30) * S)
        txt = "FACE ID OR PASSCODE"
        pw, ph = int(pf.getlength(txt) + 96 * S), int(64 * S)
        pill = rrect((pw, ph), (0, 0, pw - 1, ph - 1), ph / 2, acc, 1.0)
        dd = ImageDraw.Draw(pill)
        dd.ellipse((26 * S, ph / 2 - 8 * S, 42 * S, ph / 2 + 8 * S), fill=dark + (255,))
        dd.text((58 * S, ph / 2 - pf.size * 0.62), txt, font=pf, fill=dark + (255,))
        py = (cy + gap * 0.95 + tile_s / 2 + 70 * S) if vertical else (cy + tile_s / 2 + 80 * S)
        blend(fr, pill, cx - pw / 2, py + (1 - a) * 20 * S, a)
    return fr


# ---------------------------------------------------------------------------------------------- 24 MP -> 48 MP
def _scene_image(w, h, pal):
    """A small procedural 'photo' (sky, sun with fine rays, hills, wires) – lots of fine detail, so pixelation is obvious."""
    acc, acc2 = [np.array(hex2rgb(pal[k]), np.float32) for k in ("accent", "accent2")]
    b0, b1 = [np.array(hex2rgb(pal[k]), np.float32) for k in ("bg0", "bg1")]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    sky = b1[None, None, :] * (1 - np.clip(v / 0.62, 0, 1)[..., None]) + acc2[None, None, :] * 0.85 * np.clip(v / 0.62, 0, 1)[..., None]
    sx, sy = 0.68, 0.50
    d = np.hypot((u - sx) * w, (v - sy) * w)
    ang = np.arctan2((v - sy), (u - sx))
    rays = 0.5 + 0.5 * np.sin(ang * 36.0)
    glow = np.exp(-(d / (0.34 * h)) ** 2)[..., None]
    sun = (d < 0.11 * h).astype(np.float32)[..., None]
    img = sky + acc[None, None, :] * (0.55 * glow * (0.55 + 0.45 * rays[..., None]))
    img = img * (1 - sun) + acc[None, None, :] * 1.05 * sun
    for k, (base, amp, fr, ph, tone) in enumerate(((0.66, 0.05, 1.3, 0.8, 0.30), (0.74, 0.06, 0.9, 2.1, 0.12))):
        ridge = base + amp * np.sin(2 * np.pi * u * fr + ph) + 0.012 * np.sin(2 * np.pi * u * 9.0 + k)
        m = (v > ridge)[..., None]
        img = np.where(m, (b0 * (1 - tone) + b1 * tone)[None, None, :] * np.ones_like(img), img)
    for xw in np.linspace(0.05, 0.95, 24):                                     # thin 'wires' / fine vertical detail
        wire = (np.abs(u - xw) < 0.0016) & (v > 0.05) & (v < 0.62)
        img = np.where(wire[..., None], img * 0.55, img)
    return np.clip(img, 0, 255).astype(np.uint8)


def render_megapixel(t, S, pal, bg_img, lay=None):
    """t since scene start (>= 6 s).  Pixelated photo sharpens as the counter runs 24 -> 48 MP; result pill at the end."""
    lay = lay or {}
    fr = np.asarray(bg_img.convert("RGB"), np.float32).copy() / 255.0
    acc, dark = hex2rgb(pal["accent"]), hex2rgb(pal["on_accent"])
    cx, top = lay.get("cx", 1290) * S, lay.get("top", 150) * S
    fw, fh = int(lay.get("frame_w", 560) * S), int(lay.get("frame_h", 420) * S)
    p_in = ease_out(t / 0.5)
    # --- breadcrumb chip
    f_c = font("label", lay.get("chip_size", 24) * S)
    chip_txt = "CAMERA  ›  FORMAT  ›  RESOLUTION"
    cw_, ch_ = int(f_c.getlength(chip_txt) + 56 * S), int(52 * S)
    chip = rrect((cw_, ch_), (0, 0, cw_ - 1, ch_ - 1), ch_ / 2, tint(pal, 0.5), 0.9, outline=acc + (150,), width=2 * S)
    ImageDraw.Draw(chip).text((28 * S, 10 * S), chip_txt, font=f_c, fill=(255, 255, 255, 235))
    blend(fr, chip, cx - cw_ / 2, top - 70 * S + (1 - p_in) * -30 * S, p_in)
    # --- pixelated photo
    base = _scene_image(max(fw // 2, 8), max(fh // 2, 8), pal)
    steps = [(0.0, 28), (1.0, 14), (1.45, 7), (1.9, 4), (2.35, 2), (2.8, 1)]
    px = 28
    for t0, p in steps:
        if t >= t0:
            px = p
    sm = cv2.resize(base, (max(base.shape[1] // px, 2), max(base.shape[0] // px, 2)), interpolation=cv2.INTER_AREA)
    pix = cv2.resize(sm, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST) if px > 1 else base
    pix = cv2.resize(pix, (fw, fh), interpolation=cv2.INTER_NEAREST if px > 1 else cv2.INTER_CUBIC)
    photo = Image.fromarray(pix, "RGB").convert("RGBA")
    mask = aa_shape((fw, fh), lambda dr, ss: dr.rounded_rectangle([0, 0, fw * ss - 1, fh * ss - 1], radius=26 * S * ss, fill=255))
    photo.putalpha(mask)
    border = rrect((fw, fh), (0, 0, fw - 1, fh - 1), 26 * S, acc, 0.0, outline=acc + (255 if t > 2.8 else 140,), width=3.5 * S)
    photo = Image.alpha_composite(photo, border)
    g = glow_of(photo, 28 * S, 1.0)
    blend_glow(fr, g, cx - fw / 2, top, (0.22 + (0.45 if t > 2.8 else 0.0)) * p_in)
    blend(fr, photo, cx - fw / 2, top + (1 - p_in) * 50 * S, p_in)
    # --- megapixel counter
    k = ease_io((t - 0.9) / 1.6)
    val = 24 + int(round(24 * k))
    done = val >= 48
    f_n = font("title", lay.get("num_size", 190) * S)
    f_u = font("title", lay.get("unit_size", 74) * S)
    num = str(val)
    nw, uw = f_n.getlength("48"), f_u.getlength(" MP")
    tx = cx - (nw + uw) / 2
    ty = top + fh + lay.get("num_gap", 24) * S
    layer = Image.new("RGBA", (int(nw + uw + 80 * S), int(f_n.size * 1.45)), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    col = (acc if done else (235, 238, 236)) + (255,)
    ld.text((40 * S, 0), num, font=f_n, fill=col)
    ld.text((40 * S + f_n.getlength(num) + 6 * S, f_n.size * 0.50), "MP", font=f_u, fill=col)
    pop = 1.0 + (0.10 * max(0.0, 1 - (t - 2.5) / 0.35) if done else 0.0)
    if pop != 1.0:
        layer = layer.resize((int(layer.width * pop), int(layer.height * pop)), Image.LANCZOS)
    if done:
        blend_glow(fr, glow_of(layer, 22 * S, 1.3), tx - 40 * S - (layer.width - (nw + uw + 80 * S)) / 2, ty, 0.55)
    blend(fr, layer, tx - 40 * S - (layer.width - (nw + uw + 80 * S)) / 2, ty - (layer.height - f_n.size * 1.45) / 2, p_in)
    # --- result pill
    if t > 3.0:
        a = ease_out((t - 3.0) / 0.35)
        pf = font("title", lay.get("pill_size", 30) * S)
        txt = "PERFECT 48 MP PHOTOS"
        pw, ph = int(pf.getlength(txt) + 100 * S), int(64 * S)
        pill = rrect((pw, ph), (0, 0, pw - 1, ph - 1), ph / 2, acc, 1.0)
        ck = check_icon(30 * S, dark, 5 * S)
        pill.alpha_composite(ck, (int(24 * S), int(ph / 2 - ck.height / 2)))
        ImageDraw.Draw(pill).text((66 * S, ph / 2 - pf.size * 0.62), txt, font=pf, fill=dark + (255,))
        blend(fr, pill, cx - pw / 2, ty + f_n.size * 1.12 + 14 * S + (1 - a) * 20 * S, a)
    return fr
