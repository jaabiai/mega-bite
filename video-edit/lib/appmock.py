"""Illustrated (generic, unbranded) phone app screens at the 1320x2868 screen-recording resolution.

Used when the real app blocks screen recording: the project's screens.py composes these building blocks per time so the
phone scene can zoom, spotlight and tap on them exactly like on a recording.  No official logos or artwork.
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SW, SH = 1320, 2868
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "fonts", "PlusJakartaSans-VF.ttf")

BG = (244, 244, 247)
CARD = (255, 255, 255)
INK = (22, 22, 26)
SUB = (112, 114, 122)
LINE = (226, 226, 232)
PRIMARY = (28, 28, 32)
ACCENT = (150, 112, 48)
OK = (34, 150, 86)
KEY = (252, 252, 254)
KB = (209, 211, 217)

_F = {}


def f(size, w=600):
    key = (int(size), w)
    if key not in _F:
        ft = ImageFont.truetype(FONT, int(size))
        ft.set_variation_by_axes([w])
        _F[key] = ft
    return _F[key]


def canvas(bg=BG):
    return Image.new("RGB", (SW, SH), bg)


def status_bar(img, clock="9:41", dark=False):
    d = ImageDraw.Draw(img)
    col = (255, 255, 255) if dark else INK
    d.text((150, 98), clock, font=f(52, 650), fill=col, anchor="lm")
    x = 1010
    for i, h in enumerate((16, 24, 32, 40)):                                  # signal
        d.rounded_rectangle([x + i * 20, 118 - h, x + i * 20 + 12, 118], radius=3, fill=col)
    d.rounded_rectangle([1110, 80, 1190, 118], radius=11, outline=col, width=4)  # battery
    d.rounded_rectangle([1117, 87, 1170, 111], radius=6, fill=col)
    d.rounded_rectangle([1194, 92, 1200, 106], radius=2, fill=col)
    d.rounded_rectangle([472, 42, 848, 152], radius=55, fill=(0, 0, 0))       # island


def nav(img, title, back=True, y=250):
    d = ImageDraw.Draw(img)
    if back:
        d.line([(110, y - 34), (76, y), (110, y + 34)], fill=INK, width=9, joint="curve")
    d.text((SW / 2, y), title, font=f(54, 700), fill=INK, anchor="mm")


def big_title(img, txt, y, size=88, sub=None):
    d = ImageDraw.Draw(img)
    d.text((80, y), txt, font=f(size, 800), fill=INK, anchor="ls")
    if sub:
        yy = y + 30
        for line in sub.split("\n"):
            d.text((80, yy + 46), line, font=f(46, 500), fill=SUB, anchor="ls")
            yy += 64


def card(img, box, r=44, fill=CARD, outline=None, width=0):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def row(img, y, label, sub=None, icon=(150, 112, 48), h=170, chevron=True, x0=60, x1=SW - 60, hot=False):
    d = ImageDraw.Draw(img)
    if hot:
        d.rounded_rectangle([x0, y, x1, y + h], radius=40, fill=(238, 232, 220))
    d.ellipse([x0 + 40, y + h / 2 - 46, x0 + 132, y + h / 2 + 46], fill=icon)
    if sub:
        d.text((x0 + 170, y + h / 2 - 22), label, font=f(50, 650), fill=INK, anchor="lm")
        d.text((x0 + 170, y + h / 2 + 34), sub, font=f(40, 500), fill=SUB, anchor="lm")
    else:
        d.text((x0 + 170, y + h / 2), label, font=f(50, 650), fill=INK, anchor="lm")
    if chevron:
        cx, cy = x1 - 70, y + h / 2
        d.line([(cx - 14, cy - 24), (cx + 10, cy), (cx - 14, cy + 24)], fill=SUB, width=7, joint="curve")


def tile(img, box, label, icon=(150, 112, 48), hot=False):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=44, fill=(238, 232, 220) if hot else CARD, outline=ACCENT if hot else None, width=6 if hot else 0)
    cx = (x0 + x1) / 2
    d.rounded_rectangle([cx - 62, y0 + 56, cx + 62, y0 + 180], radius=34, fill=icon)
    lines = label.split("\n")
    for i, ln in enumerate(lines):
        d.text((cx, y0 + 250 + i * 58), ln, font=f(44, 650), fill=INK, anchor="mm")


def field(img, y, label, value="", placeholder="", focused=False, caret=False, h=170, x0=80, x1=SW - 80):
    d = ImageDraw.Draw(img)
    d.text((x0, y - 30), label, font=f(42, 600), fill=SUB, anchor="ls")
    d.rounded_rectangle([x0, y, x1, y + h], radius=34, fill=CARD, outline=PRIMARY if focused else LINE, width=6 if focused else 4)
    txt = value if value else placeholder
    col = INK if value else (170, 172, 180)
    d.text((x0 + 44, y + h / 2), txt, font=f(52, 600 if value else 500), fill=col, anchor="lm")
    if caret:
        cx = x0 + 44 + (f(52, 600).getlength(value) if value else 0) + 6
        d.rectangle([cx, y + h / 2 - 40, cx + 5, y + h / 2 + 40], fill=ACCENT)


def button(img, y, label, kind="primary", pressed=False, h=160, x0=80, x1=SW - 80, enabled=True):
    d = ImageDraw.Draw(img)
    if kind == "primary":
        fill = (60, 60, 66) if pressed else PRIMARY
        if not enabled:
            fill = (190, 190, 196)
        d.rounded_rectangle([x0, y, x1, y + h], radius=h / 2, fill=fill)
        d.text(((x0 + x1) / 2, y + h / 2), label, font=f(52, 700), fill=(255, 255, 255), anchor="mm")
    else:
        d.rounded_rectangle([x0, y, x1, y + h], radius=h / 2, fill=(236, 236, 240) if pressed else CARD, outline=PRIMARY, width=5)
        d.text(((x0 + x1) / 2, y + h / 2), label, font=f(52, 700), fill=INK, anchor="mm")


def otp(img, y, digits, n=6, active=None, masked=False):
    d = ImageDraw.Draw(img)
    gap, w = 30, (SW - 160 - 5 * 30) / 6
    for i in range(n):
        x0 = 80 + i * (w + gap)
        on = active is not None and i == active
        d.rounded_rectangle([x0, y, x0 + w, y + 200], radius=30, fill=CARD, outline=PRIMARY if on else LINE, width=6 if on else 4)
        if i < len(digits):
            ch = "•" if masked else digits[i]
            d.text((x0 + w / 2, y + 100), ch, font=f(84, 700), fill=INK, anchor="mm")


def keyboard(img, kind="alpha", pressed=None):
    """Simple system keyboard at the bottom (alpha or numeric)."""
    d = ImageDraw.Draw(img)
    top = 1880
    d.rectangle([0, top, SW, SH], fill=KB)
    if kind == "num":
        keys = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["", "0", "del"]]
        kw, kh, gx, gy = (SW - 4 * 24) / 3, 186, 24, 22
        for r, rowk in enumerate(keys):
            for c, k in enumerate(rowk):
                x0 = 24 + c * (kw + gx)
                y0 = top + 30 + r * (kh + gy)
                if not k:
                    continue
                fill = (180, 182, 190) if pressed == k else KEY
                d.rounded_rectangle([x0, y0, x0 + kw, y0 + kh], radius=22, fill=fill)
                d.text((x0 + kw / 2, y0 + kh / 2), k, font=f(76, 500), fill=INK, anchor="mm")
        return
    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    kw, kh = 112, 166
    for r, letters in enumerate(rows):
        n = len(letters)
        total = n * kw + (n - 1) * 16
        x = (SW - total) / 2
        y0 = top + 40 + r * (kh + 32)
        for k in letters:
            fill = (180, 182, 190) if pressed == k else KEY
            d.rounded_rectangle([x, y0, x + kw, y0 + kh], radius=18, fill=fill)
            d.text((x + kw / 2, y0 + kh / 2), k, font=f(64, 500), fill=INK, anchor="mm")
            x += kw + 16
    y0 = top + 40 + 3 * (kh + 32)
    d.rounded_rectangle([40, y0, 280, y0 + kh], radius=18, fill=(172, 175, 184))
    d.text((160, y0 + kh / 2), "123", font=f(50, 500), fill=INK, anchor="mm")
    d.rounded_rectangle([300, y0, 1020, y0 + kh], radius=18, fill=KEY)
    d.text((660, y0 + kh / 2), "space", font=f(50, 500), fill=INK, anchor="mm")
    d.rounded_rectangle([1040, y0, 1280, y0 + kh], radius=18, fill=(172, 175, 184))
    d.text((1160, y0 + kh / 2), "@", font=f(56, 500), fill=INK, anchor="mm")


def check(img, cx, cy, r, prog=1.0, col=OK):
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    if prog > 0:
        pts = [(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.32), (cx + r * 0.46, cy - r * 0.30)]
        if prog < 1:
            k = prog * 2
            if k <= 1:
                pts = [pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * k, pts[0][1] + (pts[1][1] - pts[0][1]) * k)]
            else:
                k -= 1
                pts = [pts[0], pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * k, pts[1][1] + (pts[2][1] - pts[1][1]) * k)]
        d.line(pts, fill=(255, 255, 255), width=int(r * 0.16), joint="curve")


def face_scan(img, cx, cy, t, done=False):
    """Face outline inside an oval guide with a sweeping scan line (or a success ring)."""
    d = ImageDraw.Draw(img)
    rx, ry = 330, 420
    d.ellipse([cx - rx - 26, cy - ry - 26, cx + rx + 26, cy + ry + 26], outline=OK if done else ACCENT, width=14)
    # head + shoulders silhouette
    d.ellipse([cx - 150, cy - 260, cx + 150, cy + 80], fill=(214, 216, 222))
    d.pieslice([cx - 290, cy + 120, cx + 290, cy + 640], 180, 360, fill=(214, 216, 222))
    if not done:
        k = 0.5 - 0.5 * math.cos(t * 2 * math.pi / 1.4)
        y = cy - ry + 40 + k * (2 * ry - 80)
        d.rectangle([cx - rx + 30, y - 4, cx + rx - 30, y + 4], fill=ACCENT)
    else:
        check(img, cx + rx - 40, cy + ry - 60, 90)


def banner(img, title, body, y=40, app="A"):
    """Notification banner sliding over the top of the screen."""
    d = ImageDraw.Draw(img)
    x0, x1 = 40, SW - 40
    d.rounded_rectangle([x0, y, x1, y + 290], radius=60, fill=(250, 250, 252), outline=(220, 220, 226), width=3)
    d.rounded_rectangle([x0 + 40, y + 50, x0 + 150, y + 160], radius=28, fill=ACCENT)
    d.text((x0 + 95, y + 105), app, font=f(60, 800), fill=(255, 255, 255), anchor="mm")
    d.text((x0 + 190, y + 80), title, font=f(46, 700), fill=INK, anchor="lm")
    d.text((x1 - 60, y + 80), "now", font=f(38, 500), fill=SUB, anchor="rm")
    yy = y + 150
    for line in body.split("\n"):
        d.text((x0 + 190, yy), line, font=f(42, 500), fill=INK, anchor="lm")
        yy += 58


def to_array(img):
    return np.asarray(img, np.uint8)
