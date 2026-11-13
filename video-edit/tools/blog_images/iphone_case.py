#!/usr/bin/env python3
"""Original illustrations for the iPhone case review blog post (no video frames).

usage: iphone_case.py OUT_DIR
writes hero.jpg (1280x720), features.jpg (1280x1000), camera-lip.jpg (1280x620), price.jpg (1280x640)

The case is drawn as a flat vector illustration of the actual design (charcoal shell, camera window showing the phone's
finish with three lenses and a white chevron, flash / LiDAR / triangle vent, ember strips, octagonal textured panel with a
MagSafe ring and oval, corner vents with ember stripes, bumper corners).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
F = os.path.join(ROOT, "assets", "fonts")
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)

INK = (12, 13, 16)
GLASS = (22, 24, 28)
PAPER = (243, 239, 232)
MUTE = (160, 160, 164)
EMBER = (255, 106, 43)
EMBER_HI = (255, 170, 110)
SAGE = (150, 166, 156)
SAGE_D = (104, 118, 110)
SAGE_L = (186, 199, 190)


def font(name, size):
    return ImageFont.truetype(os.path.join(F, name), int(size))


ML = lambda s: font("AnekMalayalam-800.ttf", s)
DISP = lambda s: font("Unbounded-800.ttf", s)
DISP6 = lambda s: font("Unbounded-600.ttf", s)
LAB = lambda s: font("BarlowCondensed-700.ttf", s)
LAB6 = lambda s: font("BarlowCondensed-600.ttf", s)
BODY = lambda s: font("Inter-600.ttf", s)


def backdrop(w, h, glows=((0.78, 0.40, 0.55, EMBER, 0.20), (0.18, 0.85, 0.50, SAGE, 0.10))):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    img = np.zeros((h, w, 3), np.float32) + np.array(INK, np.float32) / 255
    for gx, gy, gr, col, a in glows:
        d = np.hypot((u - gx) * w / h, v - gy) / gr
        img += (np.exp(-d * d * 2.2) * a)[..., None] * np.array(col, np.float32) / 255
    # faint dot grid
    grid = ((xx % 32 < 1.5) & (yy % 32 < 1.5)).astype(np.float32) * 0.035
    img += grid[..., None]
    vig = 1 - 0.35 * np.clip(np.hypot(u - 0.5, v - 0.5) / 0.75, 0, 1) ** 1.6
    img *= vig[..., None]
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def shadow(img, layer, dx=0, dy=24, blur=34, alpha=0.6):
    a = layer.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha))
    img.paste((0, 0, 0, 255), (dx, dy), a)


def text(img, xy, s, ft, fill=PAPER, anchor="la", shadow_a=0.7):
    if shadow_a:
        m = Image.new("L", img.size, 0)
        ImageDraw.Draw(m).text((xy[0], xy[1] + 3), s, font=ft, fill=255, anchor=anchor)
        img.paste((0, 0, 0, 255), (0, 0), m.filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(v * shadow_a)))
    ImageDraw.Draw(img).text(xy, s, font=ft, fill=fill, anchor=anchor)


def tracked(d, xy, s, ft, fill, tr):
    x, y = xy
    for c in s:
        d.text((x, y), c, font=ft, fill=fill)
        x += ft.getlength(c) + tr
    return x


# ---------------------------------------------------------------------------------------------- the case
CH = (78, 81, 87)          # charcoal shell
CH_D = (48, 50, 55)
CH_L = (122, 126, 133)
PANEL = (60, 63, 68)
CREAM = (233, 221, 198)    # the phone's own finish, seen through the camera window


def _dots(d, P, S, pts_fn, x0, y0, x1, y1, step, r, fill):
    y = y0
    row = 0
    while y <= y1:
        x = x0 + (step / 2 if row % 2 else 0)
        while x <= x1:
            if pts_fn(x, y):
                d.ellipse([*P(x - r, y - r), *P(x + r, y + r)], fill=fill)
            x += step
        y += step * 0.87
        row += 1


def _in_tri(a, b, c):
    def f(x, y):
        def sgn(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = sgn((x, y), a, b), sgn((x, y), b, c), sgn((x, y), c, a)
        neg = d1 < 0 or d2 < 0 or d3 < 0
        pos = d1 > 0 or d2 > 0 or d3 > 0
        return not (neg and pos)
    return f


def case_back(h=1100):
    """Back view of the case as sold (charcoal shell, camera window showing the phone's cream finish, three lenses,
    white chevron strips, flash / LiDAR / triangle vent, ember strips, octagonal textured panel with MagSafe ring and
    oval, corner vents with ember stripes, bumper corners).  RGBA at height h; returns (img, anchors)."""
    ss = 2
    W0, H0 = 560, 1140
    k = h / H0
    S = lambda v: v * k * ss
    W, H = int(W0 * k), int(H0 * k)
    pad = 6
    im = Image.new("RGBA", (W * ss + 2 * pad * ss, H * ss), (0, 0, 0, 0))
    ox = pad * ss
    P = lambda x, y: (ox + S(x), S(y))
    d = ImageDraw.Draw(im)
    # button covers (behind the shell): right edge = action + volume, left edge = power + camera control
    for (y0, y1) in ((236, 296), (330, 420), (446, 536)):
        d.rounded_rectangle([*P(W0 - 16, y0), *P(W0 + 3, y1)], radius=S(7), fill=CH_D)
    for (y0, y1) in ((330, 450), (610, 690)):
        d.rounded_rectangle([*P(-3, y0), *P(16, y1)], radius=S(7), fill=CH_D)
    # shell with a soft vertical gradient
    shell = Image.new("L", im.size, 0)
    ImageDraw.Draw(shell).rounded_rectangle([*P(6, 0), *P(W0 - 6, H0)], radius=S(98), fill=255)
    grad = np.zeros((im.size[1], im.size[0], 4), np.uint8)
    t = np.linspace(0, 1, im.size[1])[:, None]
    for c in range(3):
        grad[..., c] = (CH_L[c] * 0.25 * (1 - t) + CH[c] * (1 - 0.25 * (1 - t)) * (1 - 0.18 * t)).astype(np.uint8)
    grad[..., 3] = 255
    im.paste(Image.fromarray(grad, "RGBA"), (0, 0), shell)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([*P(6, 0), *P(W0 - 6, H0)], radius=S(98), outline=(36, 38, 42), width=int(S(5)))
    d.rounded_rectangle([*P(18, 12), *P(W0 - 18, H0 - 12)], radius=S(86), outline=(112, 116, 123), width=int(S(3)))
    d.rounded_rectangle([*P(30, 24), *P(W0 - 30, H0 - 24)], radius=S(74), outline=(58, 61, 66), width=int(S(2)))
    # bumper corners (air-cushion style)
    for (bx, by, a0) in ((6, 0, 180), (W0 - 6 - 196, 0, 270), (6, H0 - 196, 90), (W0 - 6 - 196, H0 - 196, 0)):
        d.arc([*P(bx, by), *P(bx + 196, by + 196)], start=a0 + 12, end=a0 + 78, fill=(140, 144, 151), width=int(S(4)))
    # camera island: raised plate with a lip
    isl = (40, 38, 520, 404)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([*P(isl[0] + 4, isl[1] + 12), *P(isl[2] + 4, isl[3] + 14)], radius=S(66), fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(S(9))))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([*P(*isl[:2]), *P(*isl[2:])], radius=S(66), fill=(96, 100, 107), outline=(34, 36, 40), width=int(S(6)))
    d.rounded_rectangle([*P(isl[0] + 14, isl[1] + 14), *P(isl[2] - 14, isl[3] - 14)], radius=S(54),
                        outline=(140, 145, 152), width=int(S(3)))
    # camera window (phone finish) bounded on the right by the white chevron
    win = [(70, 66), (300, 66), (356, 221), (300, 376), (70, 376)]
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).polygon([P(x, y) for x, y in win], fill=255)
    rr = Image.new("L", im.size, 0)
    ImageDraw.Draw(rr).rounded_rectangle([*P(70, 66), *P(420, 376)], radius=S(44), fill=255)
    m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(rr)))
    cream = np.zeros((im.size[1], im.size[0], 4), np.uint8)
    tt = np.linspace(0, 1, im.size[0])[None, :]
    for c in range(3):
        cream[..., c] = (CREAM[c] * (1.02 - 0.10 * tt)).clip(0, 255).astype(np.uint8)
    cream[..., 3] = 255
    im.paste(Image.fromarray(cream, "RGBA"), (0, 0), m)
    d = ImageDraw.Draw(im)
    for (lx, ly, r) in ((152, 138, 66), (152, 304, 66), (262, 221, 66)):
        d.ellipse([*P(lx - r - 7, ly - r - 7), *P(lx + r + 7, ly + r + 7)], fill=(30, 31, 34))
        d.ellipse([*P(lx - r, ly - r), *P(lx + r, ly + r)], fill=(14, 15, 18), outline=(70, 74, 82), width=int(S(2)))
        d.ellipse([*P(lx - r * 0.5, ly - r * 0.5), *P(lx + r * 0.5, ly + r * 0.5)], fill=(8, 9, 12), outline=(48, 58, 82), width=int(S(2)))
        d.ellipse([*P(lx - r * 0.34, ly - r * 0.46), *P(lx - r * 0.08, ly - r * 0.20)], fill=(120, 150, 205))
    d.line([*P(312, 82), *P(364, 204)], fill=(236, 236, 234), width=int(S(11)))
    d.line([*P(364, 238), *P(312, 360)], fill=(236, 236, 234), width=int(S(11)))
    # right side of the island: flash, mic, LiDAR, triangle vent
    d.ellipse([*P(414, 88), *P(470, 144)], fill=(40, 40, 42))
    d.ellipse([*P(422, 96), *P(462, 136)], fill=(236, 200, 70))
    d.rounded_rectangle([*P(430, 168), *P(452, 196)], radius=S(10), fill=(40, 42, 46))
    d.ellipse([*P(410, 286), *P(470, 346)], fill=(16, 17, 20), outline=(70, 74, 80), width=int(S(2)))
    tri = ((350, 376), (412, 376), (381, 316))
    _dots(d, P, S, _in_tri(*tri), 350, 318, 412, 374, 10, 2.8, (34, 36, 40))
    d.rounded_rectangle([*P(46, 170), *P(58, 262)], radius=S(5), fill=EMBER)
    d.rounded_rectangle([*P(502, 196), *P(514, 288)], radius=S(5), fill=EMBER)
    # octagonal textured panel
    oct_ = [(142, 452), (418, 452), (488, 522), (488, 1012), (418, 1082), (142, 1082), (72, 1012), (72, 522)]
    d.polygon([P(x, y) for x, y in oct_], fill=PANEL, outline=(40, 42, 46))
    tex = Image.new("L", im.size, 0)
    ImageDraw.Draw(tex).polygon([P(x, y) for x, y in oct_], fill=255)
    dots = Image.new("RGBA", im.size, (0, 0, 0, 0))
    _dots(ImageDraw.Draw(dots), P, S, lambda x, y: True, 72, 452, 488, 1082, 9, 1.7, (44, 46, 51, 255))
    im.paste(dots, (0, 0), Image.fromarray(np.minimum(np.asarray(tex), np.asarray(dots.split()[3]))))
    d = ImageDraw.Draw(im)
    for (x, y) in ((150, 474), (410, 474), (466, 530), (466, 1004), (410, 1060), (150, 1060), (94, 1004), (94, 530)):
        d.ellipse([*P(x - 7, y - 7), *P(x + 7, y + 7)], fill=(36, 38, 42), outline=(104, 108, 114), width=int(S(1.5)))
    # corner vents with ember stripes (top-right and bottom-left chamfers)
    _dots(d, P, S, _in_tri((436, 446), (512, 446), (512, 522)), 436, 446, 512, 522, 10, 2.8, (30, 32, 36))
    d.line([*P(410, 474), *P(470, 534)], fill=EMBER, width=int(S(10)))
    _dots(d, P, S, _in_tri((48, 1012), (48, 1090), (126, 1090)), 48, 1012, 126, 1090, 10, 2.8, (30, 32, 36))
    d.line([*P(92, 1000), *P(150, 1058)], fill=EMBER, width=int(S(10)))
    # MagSafe ring and the oval below it
    cx, cy, r = 280, 712, 168
    d.ellipse([*P(cx - r - 10, cy - r - 10), *P(cx + r + 10, cy + r + 10)], fill=(42, 44, 49))
    d.ellipse([*P(cx - r + 26, cy - r + 26), *P(cx + r - 26, cy + r - 26)], fill=(66, 69, 75), outline=(96, 100, 107), width=int(S(2)))
    d.arc([*P(cx - r - 4, cy - r - 4), *P(cx + r + 4, cy + r + 4)], start=200, end=320, fill=(120, 124, 131), width=int(S(3)))
    d.rounded_rectangle([*P(256, 924), *P(304, 1022)], radius=S(24), fill=(52, 54, 59), outline=(96, 100, 107), width=int(S(2)))
    im = im.resize((W + 2 * pad, H), Image.LANCZOS)
    A = lambda x, y: (x * k + pad, y * k)
    anchors = {
        "lens": A(152, 138), "lip": A(isl[0] + 3, 300), "action": A(W0 + 2, 266), "buttons": A(W0 + 2, 375),
        "magsafe": A(cx - r - 6, cy + 40), "grip": A(420, 860), "vent": A(488, 470), "corner": A(30, H0 - 40),
        "island": A(280, isl[1]),
    }
    return im, anchors


def rotate(img, deg):
    return img.rotate(deg, resample=Image.BICUBIC, expand=True)


def logo(img, x, y, s=60):
    lg = Image.open(os.path.join(ROOT, "assets", "logo", "vcreate.png")).convert("RGBA")
    lg.thumbnail((s, s))
    img.alpha_composite(lg, (int(x), int(y)))
    tracked(ImageDraw.Draw(img), (x + s + 14, y + s / 2 - 13), "V CREATE", LAB(26), PAPER, 4)


def chip(img, x, y, s, size=26, dot=EMBER):
    ft = LAB(size)
    w = int(ft.getlength(s.upper()) + 2.6 * size + len(s) * 1.6)
    h = int(size * 1.8)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=GLASS + (235,), outline=(84, 80, 76, 255), width=2)
    d.ellipse([x + size * 0.7 - 6, y + h / 2 - 6, x + size * 0.7 + 6, y + h / 2 + 6], fill=dot)
    tracked(d, (x + size * 1.3, y + h / 2 - size * 0.62), s.upper(), ft, PAPER, 1.6)
    return x + w


def callout(img, ax, ay, tx, ty, n, title, sub, align="left"):
    d = ImageDraw.Draw(img)
    ft, fs, fn = LAB(34), BODY(22), DISP6(26)
    w = max(ft.getlength(title.upper()) + 40, fs.getlength(sub)) + 96
    h = 92
    x0 = min(tx, img.width - 30 - w) if align == "left" else max(tx - w, 30)
    y0 = ty - h / 2
    ex = x0 if align == "left" else x0 + w
    d.line([(ax, ay), (ex, ty)], fill=EMBER, width=3)
    d.ellipse([ax - 13, ay - 13, ax + 13, ay + 13], outline=EMBER, width=4)
    d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=PAPER)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=10, fill=GLASS + (240,), outline=(78, 74, 70, 255), width=2)
    d.rectangle([x0, y0, x0 + 5, y0 + h], fill=EMBER)
    d.text((x0 + 22, y0 + 18), f"{n:02d}", font=fn, fill=EMBER)
    tracked(d, (x0 + 74, y0 + 12), title.upper(), ft, PAPER, 1.8)
    d.text((x0 + 74, y0 + 54), sub, font=fs, fill=(206, 202, 196))


# ---------------------------------------------------------------------------------------------- 1. hero
def hero():
    W, H = 1280, 720
    img = backdrop(W, H, glows=((0.74, 0.40, 0.48, (255, 150, 70), 0.34), (0.86, 0.08, 0.40, (255, 205, 120), 0.16),
                                (0.10, 0.90, 0.5, SAGE, 0.06)))
    case, _ = case_back(620)
    case = rotate(case, -14)
    shadow(img, Image.new("RGBA", img.size), 0, 0, 1, 0)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lay.alpha_composite(case, (W - case.width - 70, (H - case.height) // 2 + 10))
    shadow(img, lay, 18, 36, 40, 0.75)
    img.alpha_composite(lay)
    logo(img, 60, 48, 56)
    text(img, (60, 170), "iPhone-ന്", ML(64))
    text(img, (60, 252), "ഒരു കിടിലൻ കവർ", ML(74), fill=EMBER)
    d = ImageDraw.Draw(img)
    tracked(d, (64, 372), "HONEST REVIEW  ·  NOT SPONSORED", LAB(28), (210, 206, 200), 3)
    x = 60
    y = 430
    for s in ("Action button cover", "Raised camera lip", "MagSafe"):
        x = chip(img, x, y, s, 24) + 12
        if x > 640:
            x, y = 60, y + 58
    # price badge
    by = 560
    pw = DISP(52).getlength("₹520")
    d.rounded_rectangle([60, by, 60 + 48 + pw + 190, by + 92], radius=16, fill=EMBER)
    d.text((84, by + 48), "₹520", font=DISP(52), fill=INK, anchor="lm")
    d.text((84 + pw + 24, by + 30), "ONWARDS", font=LAB(28), fill=INK, anchor="lm")
    d.text((84 + pw + 24, by + 64), "MRP ₹1,999", font=BODY(22), fill=(70, 30, 10), anchor="lm")
    return img.convert("RGB")


# ---------------------------------------------------------------------------------------------- 2. features
def features():
    W, H = 1280, 1000
    img = backdrop(W, H, glows=((0.5, 0.42, 0.45, (255, 150, 70), 0.22), (0.5, 1.0, 0.6, (255, 205, 120), 0.08)))
    case, A = case_back(820)
    x0, y0 = (W - case.width) // 2, 120
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lay.alpha_composite(case, (x0, y0))
    shadow(img, lay, 10, 30, 36, 0.7)
    img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    tracked(d, (60, 40), "WHAT THIS CASE GETS RIGHT", LAB(34), EMBER, 4)
    P = lambda k: (x0 + A[k][0], y0 + A[k][1])
    items = [
        ("lens", (380, 150), 1, "Camera design", "Perfectly designed camera area", "right"),
        ("action", (930, 230), 2, "Action button", "Covered, not left open", "left"),
        ("corner", (380, 900), 3, "Drop protection", "Built to take a fall", "right"),
        ("lip", (380, 360), 4, "Raised camera lip", "Lens stays off the table", "right"),
        ("magsafe", (380, 650), 5, "MagSafe", "Supported", "right"),
        ("buttons", (930, 380), 6, "Button grip", "Good grip on every button", "left"),
        ("vent", (930, 540), 7, "Heat vents", "Let warm air escape", "left"),
        ("grip", (930, 800), 8, "Textured back", "Satisfying to hold", "left"),
    ]
    for key, (tx, ty), n, t1, t2, al in items:
        ax, ay = P(key)
        callout(img, ax, ay, tx, ty, n, t1, t2, align=al)
    return img.convert("RGB")


# ---------------------------------------------------------------------------------------------- 3. camera lip
def camera_lip():
    W, H = 1280, 620
    img = backdrop(W, H, glows=((0.3, 0.6, 0.5, EMBER, 0.12),))
    d = ImageDraw.Draw(img)
    tracked(d, (60, 44), "RAISED CAMERA LIP", LAB(38), EMBER, 4)
    text(img, (60, 92), "ലെൻസ് മേശയിൽ തട്ടില്ല", ML(44))
    ss = 2
    lay = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    S = lambda v: v * ss
    table_y = 470
    dl.rectangle([S(40), S(table_y), S(W - 40), S(table_y + 70)], fill=(52, 44, 38, 255))
    dl.line([S(40), S(table_y), S(W - 40), S(table_y)], fill=(170, 160, 148, 255), width=S(3))
    for k in range(40):
        x = 50 + k * 30
        dl.line([S(x), S(table_y + 10), S(x - 22), S(table_y + 60)], fill=(70, 60, 54, 255), width=S(2))
    lip_h, bump_h, slab = 70, 14, 78
    bot = table_y - lip_h
    dl.rounded_rectangle([S(140), S(bot - slab), S(1140), S(bot)], radius=S(26), fill=CH + (255,), outline=(150, 154, 161, 255), width=S(3))
    dl.rounded_rectangle([S(160), S(bot - slab + 12), S(1120), S(bot - 10)], radius=S(18), outline=(60, 63, 68, 255), width=S(2))
    cx0, cx1 = 230, 560
    dl.rectangle([S(cx0), S(bot), S(cx1), S(bot + bump_h)], fill=(58, 60, 64, 255))
    for k in range(3):
        lx = cx0 + 55 + k * 110
        dl.ellipse([S(lx - 40), S(bot + 2), S(lx + 40), S(bot + bump_h + 10)], fill=(20, 22, 26, 255), outline=(150, 160, 178, 255), width=S(2))
    for xa, xb in ((cx0 - 26, cx0 - 4), (cx1 + 4, cx1 + 26)):
        dl.rounded_rectangle([S(xa), S(bot), S(xb), S(bot + lip_h)], radius=S(5), fill=EMBER + (255,))
    gx = (cx0 + cx1) / 2
    ya, yb = bot + bump_h + 12, table_y - 3
    dl.line([S(gx), S(ya + 8), S(gx), S(yb - 8)], fill=PAPER + (255,), width=S(3))
    dl.polygon([(S(gx), S(ya)), (S(gx - 9), S(ya + 13)), (S(gx + 9), S(ya + 13))], fill=PAPER + (255,))
    dl.polygon([(S(gx), S(yb)), (S(gx - 9), S(yb - 13)), (S(gx + 9), S(yb - 13))], fill=PAPER + (255,))
    lay = lay.resize((W, H), Image.LANCZOS)
    shadow(img, lay, 0, 14, 18, 0.6)
    img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    d.line([(gx + 12, (ya + yb) / 2), (cx1 + 80, (ya + yb) / 2)], fill=PAPER, width=2)
    tracked(d, (cx1 + 92, (ya + yb) / 2 - 22), "GAP", LAB(40), PAPER, 3)
    d.line([(cx1 + 15, bot + lip_h / 2), (760, 250)], fill=EMBER, width=2)
    tracked(d, (770, 218), "RAISED BORDER TOUCHES FIRST", LAB(30), EMBER_HI, 2)
    d.text((770, 258), "the lenses never scrape the surface", font=BODY(24), fill=(214, 210, 204))
    tracked(d, (60, 560), "NO LENS PROTECTOR NEEDED  ·  NO SCRATCHES", LAB(28), (190, 186, 180), 3)
    d.text((1220, 566), "Brand spec: 1.5 mm raised camera lip", font=BODY(20), fill=(150, 146, 140), anchor="ra")
    return img.convert("RGB")


# ---------------------------------------------------------------------------------------------- 4. price
def price():
    W, H = 1280, 640
    img = backdrop(W, H, glows=((0.28, 0.45, 0.50, EMBER, 0.20), (0.85, 0.6, 0.5, SAGE, 0.10)))
    d = ImageDraw.Draw(img)
    tracked(d, (70, 60), "PRICE & MODELS", LAB(36), EMBER, 4)
    d.text((70, 150), "MRP", font=LAB(34), fill=MUTE)
    d.text((150, 136), "₹1,999", font=DISP6(56), fill=(200, 196, 190))
    w = DISP6(56).getlength("₹1,999")
    d.line([(146, 176), (154 + w, 170)], fill=EMBER, width=6)
    d.text((66, 220), "₹520", font=DISP(150), fill=EMBER)
    tracked(d, (74, 410), "ONWARDS  ·  PRICE VARIES BY PHONE MODEL", LAB(30), PAPER, 3)
    # right column: facts
    rows = [("iPhone 13+", "this style comes from iPhone 13 onwards"),
            ("5 colours", "plus a transparent version"),
            ("This listing", "iPhone 17 Pro  ·  iPhone 18 Pro")]
    y = 150
    for big, small in rows:
        d.rounded_rectangle([740, y, 1220, y + 112], radius=14, fill=GLASS + (230,), outline=(76, 72, 68, 255), width=2)
        d.rectangle([740, y, 745, y + 112], fill=EMBER)
        d.text((770, y + 18), big, font=DISP(34), fill=PAPER)
        d.text((770, y + 68), small, font=BODY(21), fill=(196, 192, 186))
        y += 132
    tracked(d, (74, 560), "CHECK THE CURRENT PRICE ON THE LISTING BEFORE YOU BUY", LAB6(24), (170, 166, 160), 2)
    logo(img, 1070, 556, 44)
    return img.convert("RGB")


if __name__ == "__main__":
    hero().save(os.path.join(OUT, "hero.jpg"), quality=92)
    features().save(os.path.join(OUT, "features.jpg"), quality=92)
    camera_lip().save(os.path.join(OUT, "camera-lip.jpg"), quality=92)
    price().save(os.path.join(OUT, "price.jpg"), quality=92)
    print("wrote", OUT)
