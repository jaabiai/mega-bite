#!/usr/bin/env python3
"""Original illustrations for the Equal AI blog post (V Create) - no video frames, no app artwork.

usage: equal_ai.py OUT_DIR
writes hero.jpg, how-it-works.jpg, settings.jpg (1280x720 each)

Palette follows the video's "Mist" look: green-black ground, bone type, one blood-red accent, moss green for "allowed".
Malayalam is set in Anek Malayalam with complex shaping (Raqm), English in Big Shoulders / Albert Sans / JetBrains Mono.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
F = os.path.join(ROOT, "assets", "fonts")
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
W, H = 1280, 720

INK = (11, 16, 13)
INK2 = (22, 31, 26)
CARD = (28, 38, 32)
LINE = (58, 74, 64)
BONE = (236, 231, 218)
FOG = (168, 180, 170)
RED = (214, 58, 44)
MOSS = (120, 176, 120)


def _f(name, size, ml=False):
    return ImageFont.truetype(os.path.join(F, name), int(size),
                              layout_engine=ImageFont.Layout.RAQM if ml else ImageFont.Layout.BASIC)


ML = lambda s: _f("AnekMalayalam-800.ttf", s, True)
DISP = lambda s: _f("BigShouldersDisplay-900.ttf", s)
TXT = lambda s: _f("AlbertSans-700.ttf", s)
TXT6 = lambda s: _f("AlbertSans-600.ttf", s)
MONO = lambda s: _f("JetBrainsMono-700.ttf", s)


def ground():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = np.clip(1 - np.hypot((xx / W - 0.72) * 1.1, yy / H - 0.45) / 0.9, 0, 1) ** 1.6
    a = np.array(INK, np.float32)[None, None]
    b = np.array((30, 46, 38), np.float32)[None, None]
    img = a * (1 - g[..., None]) + b * g[..., None]
    noise = np.random.default_rng(3).normal(0, 2.2, (H, W, 1))
    return Image.fromarray(np.clip(img + noise, 0, 255).astype(np.uint8))


def rr(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def spaced(d, xy, s, font, fill, track=0.18):
    x, y = xy
    for c in s:
        d.text((x, y), c, font=font, fill=fill)
        x += font.getlength(c) + track * font.size


def mark(d, x, y):
    spaced(d, (x, y), "V CREATE", MONO(18), FOG, 0.3)


def phone(img, x, y, w, h):
    """A plain phone outline with an incoming call from an unknown number and the assistant's question."""
    d = ImageDraw.Draw(img)
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((x + 10, y + 24, x + w + 10, y + h + 24), radius=48, fill=160)
    img.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(img)
    rr(d, (x, y, x + w, y + h), 46, fill=(40, 46, 44), outline=(90, 100, 94), width=3)
    rr(d, (x + 12, y + 12, x + w - 12, y + h - 12), 36, fill=(16, 22, 19))
    rr(d, (x + w / 2 - 46, y + 26, x + w / 2 + 46, y + 50), 12, fill=(6, 8, 7))
    cx = x + w / 2
    d.text((cx, y + 98), "INCOMING CALL", font=MONO(15), fill=FOG, anchor="mm")
    d.ellipse((cx - 44, y + 126, cx + 44, y + 214), fill=CARD, outline=LINE, width=2)
    d.text((cx, y + 170), "?", font=DISP(56), fill=BONE, anchor="mm")
    d.text((cx, y + 246), "Unknown caller", font=TXT(26), fill=BONE, anchor="mm")
    d.text((cx, y + 280), "+91 9XXXX XXXXX", font=MONO(17), fill=FOG, anchor="mm")
    # the assistant answers first
    by = y + 322
    rr(d, (x + 30, by, x + w - 30, by + 120), 18, fill=(34, 48, 40), outline=(70, 96, 80), width=2)
    rr(d, (x + 44, by + 14, x + 118, by + 40), 10, fill=RED)
    d.text((x + 81, by + 27), "AI", font=MONO(16), fill=BONE, anchor="mm")
    d.text((x + 46, by + 52), "ആരാണ്? എന്തിനാണ്", font=ML(24), fill=BONE)
    d.text((x + 46, by + 82), "വിളിക്കുന്നത്?", font=ML(24), fill=BONE)
    # answer buttons
    for bx, col in ((cx - 70, RED), (cx + 70, MOSS)):
        d.ellipse((bx - 32, y + h - 112, bx + 32, y + h - 48), fill=col)
    d.text((cx - 70, y + h - 80), "✕", font=_f("JetBrainsMono-700.ttf", 26), fill=BONE, anchor="mm")
    d.line((cx + 56, y + h - 80, cx + 66, y + h - 70, cx + 86, y + h - 92), fill=INK, width=5)


def hero():
    img = ground()
    d = ImageDraw.Draw(img)
    spaced(d, (72, 120), "EQUAL AI  ·  AI CALL ASSISTANT", MONO(20), RED, 0.22)
    d.text((70, 168), "സ്പാം കോളുകൾ", font=ML(84), fill=BONE)
    d.text((70, 272), "ഇനി AI എടുക്കും", font=ML(84), fill=RED)
    d.text((72, 398), "ആരാണ്, എന്തിനാണ് വിളിക്കുന്നത് എന്ന് AI", font=ML(28), fill=FOG)
    d.text((72, 436), "ചോദിച്ചറിയും; ആവശ്യമുള്ള കോൾ മാത്രം", font=ML(28), fill=FOG)
    d.text((72, 474), "നിങ്ങൾക്ക് കൈമാറും.", font=ML(28), fill=FOG)
    for i, t in enumerate(("iPhone", "Android", "മലയാളം ഗൈഡ്")):
        fnt = ML(24) if i == 2 else TXT(24)
        w = fnt.getlength(t) + 40
        x0 = 72 + sum(fnt_w for fnt_w in ([TXT(24).getlength("iPhone") + 52, TXT(24).getlength("Android") + 52][:i]))
        rr(d, (x0, 546, x0 + w, 592), 23, outline=LINE, width=2)
        d.text((x0 + w / 2, 569), t, font=fnt, fill=BONE, anchor="mm")
    mark(d, 72, 650)
    phone(img, 840, 70, 330, 600)
    return img


def arrow(d, x0, y0, x1, y1, col, w=4):
    d.line((x0, y0, x1, y1), fill=col, width=w)
    v = np.array([x1 - x0, y1 - y0], np.float32)
    v /= np.linalg.norm(v) + 1e-6
    n = np.array([-v[1], v[0]])
    p = np.array([x1, y1])
    a, b = p - v * 16 + n * 9, p - v * 16 - n * 9
    d.polygon([tuple(p), tuple(a), tuple(b)], fill=col)


def how():
    img = ground()
    d = ImageDraw.Draw(img)
    spaced(d, (64, 56), "HOW IT WORKS", MONO(20), RED, 0.25)
    d.text((62, 88), "Equal AI പ്രവർത്തിക്കുന്നത് ഇങ്ങനെ", font=ML(46), fill=BONE)
    # 1 call comes in
    boxes = [(64, 230, 344, 520), (410, 230, 778, 520)]
    rr(d, boxes[0], 22, fill=CARD, outline=LINE, width=2)
    rr(d, boxes[1], 22, fill=CARD, outline=(110, 70, 62), width=2)
    d.text((88, 254), "01", font=MONO(20), fill=RED)
    d.text((88, 290), "കോൾ വരുന്നു", font=ML(34), fill=BONE)
    d.text((88, 344), "സ്പാം, പ്രൊമോഷൻ,", font=ML(24), fill=FOG)
    d.text((88, 378), "അറിയാത്ത നമ്പർ...", font=ML(24), fill=FOG)
    spaced(d, (88, 470), "UNKNOWN NUMBER", MONO(16), FOG, 0.12)
    d.text((434, 254), "02", font=MONO(20), fill=RED)
    d.text((434, 292), "AI കോൾ എടുക്കുന്നു", font=ML(30), fill=BONE)
    d.text((434, 344), "ആരാണ്, എന്തിനാണ് എന്ന്", font=ML(24), fill=FOG)
    d.text((434, 378), "വിളിക്കുന്നയാളുടെ ഭാഷയിൽ", font=ML(24), fill=FOG)
    d.text((434, 412), "ചോദിച്ചറിയുന്നു", font=ML(24), fill=FOG)
    spaced(d, (434, 470), "MALAYALAM · HINDI · ENGLISH", MONO(16), FOG, 0.08)
    arrow(d, 352, 375, 400, 375, BONE)
    # 3 outcomes
    rr(d, (840, 200, 1216, 360), 22, fill=(30, 46, 34), outline=MOSS, width=2)
    rr(d, (840, 392, 1216, 552), 22, fill=(46, 28, 26), outline=RED, width=2)
    d.text((864, 222), "ആവശ്യമുള്ള കോൾ", font=ML(30), fill=BONE)
    d.text((864, 268), "നിങ്ങൾക്ക് കൈമാറും", font=ML(26), fill=MOSS)
    spaced(d, (864, 318), "FORWARDED TO YOU", MONO(15), FOG, 0.12)
    d.text((864, 414), "സ്പാം / പ്രൊമോഷൻ", font=ML(30), fill=BONE)
    d.text((864, 462), "റിജക്ട് അല്ലെങ്കിൽ സൈലന്റ്", font=ML(23), fill=(240, 120, 104))
    spaced(d, (864, 510), "REJECTED · SILENCED", MONO(15), FOG, 0.12)
    arrow(d, 786, 340, 832, 296, MOSS)
    arrow(d, 786, 410, 832, 456, RED)
    d.text((64, 600), "ഓരോ കോളിന്റെയും ചുരുക്കവും ട്രാൻസ്ക്രിപ്റ്റും ആപ്പിൽ കാണാം.", font=ML(26), fill=FOG)
    mark(d, 64, 664)
    return img


def settings():
    img = ground()
    d = ImageDraw.Draw(img)
    spaced(d, (64, 52), "KEY SETTINGS", MONO(20), RED, 0.25)
    d.text((62, 84), "ആപ്പിലെ പ്രധാന സെറ്റിംഗുകൾ", font=ML(46), fill=BONE)
    cards = [
        ("Your Instructions", "AI എന്ത് പറയണം", ["Busy · Everyday calls · Business", "വോയ്‌സ് നോട്ടായോ മെസേജായോ", "പുതിയ നിർദേശം നൽകാം"]),
        ("Your Call Preferences", "ഏതൊക്കെ കോളുകൾ", ["All calls", "All calls except...", "Only unknown numbers"]),
        ("Voice & Language", "ഭാഷയും ശബ്ദവും", ["3 ഭാഷകൾ വരെ, ഒരു Primary ഭാഷ", "വിളിക്കുന്നയാളുടെ ഭാഷയിൽ മറുപടി", "ഇഷ്ടമുള്ള AI ശബ്ദം"]),
        ("Silent Mode", "പ്രൊമോഷൻ കോളുകൾ മ്യൂട്ട്", ["ലോൺ · ക്രെഡിറ്റ് കാർഡ്", "ജോലി ഓഫർ · റിയൽ എസ്റ്റേറ്റ്", "Muted Contacts"]),
    ]
    for i, (name, ml, rows) in enumerate(cards):
        cx, cy = 64 + (i % 2) * 586, 188 + (i // 2) * 248
        rr(d, (cx, cy, cx + 562, cy + 224), 20, fill=CARD, outline=LINE, width=2)
        d.text((cx + 24, cy + 20), f"0{i + 1}", font=MONO(18), fill=RED)
        d.text((cx + 70, cy + 14), name, font=DISP(36), fill=BONE)
        d.text((cx + 24, cy + 64), ml, font=ML(26), fill=FOG)
        for k, r in enumerate(rows):
            yy = cy + 112 + k * 34
            d.ellipse((cx + 26, yy + 10, cx + 34, yy + 18), fill=MOSS if i < 3 else RED)
            has_ml = any("ഀ" <= ch <= "ൿ" for ch in r)
            d.text((cx + 48, yy), r, font=ML(22) if has_ml else TXT6(22), fill=BONE)
    mark(d, 64, 676)
    return img


if __name__ == "__main__":
    for name, fn in (("hero.jpg", hero), ("how-it-works.jpg", how), ("settings.jpg", settings)):
        fn().convert("RGB").save(os.path.join(OUT, name), quality=88, optimize=True, progressive=True)
        print("wrote", os.path.join(OUT, name))
