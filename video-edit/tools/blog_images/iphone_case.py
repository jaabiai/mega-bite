#!/usr/bin/env python3
"""Original illustrations for the iPhone case review blog post (no video frames).

usage: iphone_case.py OUT_DIR
writes hero.jpg (1280x720), features.jpg (1280x1000), camera-lip.jpg (1280x620), price.jpg (1280x640)

The case is drawn as a flat vector illustration in the product's colours (sage-grey shell, ember accents): a raised
camera island with three lenses, MagSafe ring, dotted heat vents, button covers on the sides, thicker corners.
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
def case_back(h=1100):
    """Back view of the case (portrait), RGBA, height h.  Returns (img, anchors) with anchors in image px."""
    ss = 2
    W0, H0 = 560, 1140                       # design units
    k = h / H0
    S = lambda v: v * k * ss
    W, H = int(W0 * k), int(H0 * k)
    im = Image.new("RGBA", (W * ss + 4 * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox = 2 * ss
    P = lambda x, y: (ox + S(x), S(y))
    # side button covers (behind the shell): right edge = phone's left side seen from the back
    for (y0, y1) in ((250, 312), (360, 450), (480, 570)):
        d.rounded_rectangle([*P(W0 - 14, y0), *P(W0 + 1, y1)], radius=S(6), fill=SAGE_D)
    for (y0, y1) in ((360, 500), (760, 830)):
        d.rounded_rectangle([*P(-1, y0), *P(14, y1)], radius=S(6), fill=SAGE_D)
    # shell with a vertical gradient
    shell = Image.new("L", im.size, 0)
    ImageDraw.Draw(shell).rounded_rectangle([*P(6, 0), *P(W0 - 6, H0)], radius=S(92), fill=255)
    grad = np.zeros((im.size[1], im.size[0], 4), np.uint8)
    t = np.linspace(0, 1, im.size[1])[:, None]
    for c in range(3):
        grad[..., c] = (SAGE_L[c] * (1 - t) * 0.35 + SAGE[c] * (1 - t) * 0.65 + SAGE_D[c] * t).astype(np.uint8)
    grad[..., 3] = 255
    im.paste(Image.fromarray(grad, "RGBA"), (0, 0), shell)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([*P(6, 0), *P(W0 - 6, H0)], radius=S(92), outline=(84, 96, 90), width=int(S(5)))
    d.rounded_rectangle([*P(22, 16), *P(W0 - 22, H0 - 16)], radius=S(78), outline=(176, 190, 181), width=int(S(3)))
    # thicker corners (drop protection)
    for cx, cy, a0 in ((6, 0, 180), (W0 - 6, 0, 270), (6, H0, 90), (W0 - 6, H0, 0)):
        bx = (cx - 4 if cx < W0 / 2 else cx - 180 + 4)
        by = (cy - 4 if cy < H0 / 2 else cy - 180 + 4)
        d.arc([*P(bx, by), *P(bx + 184, by + 184)], start=a0, end=a0 + 90, fill=(74, 86, 80), width=int(S(10)))
    # camera island (raised plate)
    isl = [*P(44, 40), *P(404, 400)]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([isl[0] + S(6), isl[1] + S(10), isl[2] + S(6), isl[3] + S(10)], radius=S(70), fill=(0, 0, 0, 120))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(S(8))))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(isl, radius=S(70), fill=(168, 181, 172), outline=(92, 104, 98), width=int(S(5)))
    d.rounded_rectangle([isl[0] + S(16), isl[1] + S(16), isl[2] - S(16), isl[3] - S(16)], radius=S(56),
                        outline=(204, 214, 207), width=int(S(3)))
    # X pattern
    d.line([*P(230, 120), *P(300, 210)], fill=(222, 230, 225), width=int(S(9)))
    d.line([*P(300, 280), *P(230, 350)], fill=(222, 230, 225), width=int(S(9)))
    # dotted vent triangle in the island
    for i in range(9):
        for j in range(9):
            if i + j < 9:
                x = 250 + i * 14 + (j % 2) * 7
                y = 360 - j * 13
                d.ellipse([*P(x - 3.2, y - 3.2), *P(x + 3.2, y + 3.2)], fill=(74, 84, 80))
    # lenses
    for (lx, ly, r) in ((136, 130, 66), (136, 300, 66), (262, 216, 66)):
        d.ellipse([*P(lx - r - 10, ly - r - 10), *P(lx + r + 10, ly + r + 10)], fill=(196, 202, 206), outline=(120, 126, 132), width=int(S(3)))
        d.ellipse([*P(lx - r, ly - r), *P(lx + r, ly + r)], fill=(24, 27, 32))
        d.ellipse([*P(lx - r * 0.55, ly - r * 0.55), *P(lx + r * 0.55, ly + r * 0.55)], fill=(10, 12, 16), outline=(60, 70, 90), width=int(S(2)))
        d.ellipse([*P(lx - r * 0.38, ly - r * 0.52), *P(lx - r * 0.08, ly - r * 0.22)], fill=(150, 170, 205))
    d.ellipse([*P(342, 92), *P(384, 134)], fill=(236, 232, 214), outline=(140, 140, 130), width=int(S(2)))       # flash
    d.ellipse([*P(357, 172), *P(369, 184)], fill=(40, 44, 48))                                                    # mic
    d.ellipse([*P(336, 300), *P(382, 346)], fill=(20, 22, 26), outline=(110, 116, 122), width=int(S(2)))       # LiDAR
    # ember accents
    d.rounded_rectangle([*P(36, 150), *P(48, 250)], radius=S(5), fill=EMBER)
    d.rounded_rectangle([*P(400, 200), *P(412, 300)], radius=S(5), fill=EMBER)
    d.line([*P(430, 600), *P(500, 690)], fill=EMBER, width=int(S(11)))
    # dotted vent bottom right of the shell
    for i in range(7):
        for j in range(5):
            x = 430 + i * 14 + (j % 2) * 7
            y = 720 + j * 14
            d.ellipse([*P(x - 3.2, y - 3.2), *P(x + 3.2, y + 3.2)], fill=(84, 96, 90))
    # MagSafe ring
    cx, cy, r = 280, 760, 190
    d.ellipse([*P(cx - r, cy - r), *P(cx + r, cy + r)], outline=(96, 108, 102), width=int(S(16)))
    d.ellipse([*P(cx - r + 30, cy - r + 30), *P(cx + r - 30, cy + r - 30)], outline=(160, 172, 165), width=int(S(4)))
    d.rounded_rectangle([*P(cx - 16, cy + r + 20), *P(cx + 16, cy + r + 66)], radius=S(8), fill=(110, 122, 116))
    im = im.resize((W + 4, H), Image.LANCZOS)
    anchors = {
        "action": ((W0 + 1) * k + 2, 281 * k), "buttons": ((W0 + 1) * k + 2, 465 * k),
        "lip": (44 * k + 2, 380 * k), "lens": (262 * k + 2, 216 * k), "magsafe": ((cx - r) * k + 2, cy * k),
        "vent": (480 * k + 2, 748 * k), "corner": (40 * k + 2, (H0 - 40) * k), "island": (230 * k + 2, 40 * k),
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
    img = backdrop(W, H, glows=((0.74, 0.45, 0.50, EMBER, 0.26), (0.10, 0.90, 0.5, SAGE, 0.10)))
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
    img = backdrop(W, H, glows=((0.5, 0.45, 0.45, EMBER, 0.14), (0.5, 1.0, 0.6, SAGE, 0.10)))
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
        ("action", (930, 250), 2, "Action button", "Covered, not left open", "left"),
        ("corner", (380, 860), 3, "Drop protection", "Built to take a fall", "right"),
        ("lip", (380, 360), 4, "Raised camera lip", "Lens stays off the table", "right"),
        ("magsafe", (380, 620), 5, "MagSafe", "Supported", "right"),
        ("buttons", (930, 440), 6, "Button grip", "Good grip on every button", "left"),
        ("vent", (930, 760), 7, "Heat vents", "Let warm air escape", "left"),
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
    dl.rounded_rectangle([S(140), S(bot - slab), S(1140), S(bot)], radius=S(26), fill=SAGE + (255,), outline=(208, 220, 212, 255), width=S(3))
    dl.rounded_rectangle([S(160), S(bot - slab + 12), S(1120), S(bot - 10)], radius=S(18), outline=(120, 134, 126, 255), width=S(2))
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
