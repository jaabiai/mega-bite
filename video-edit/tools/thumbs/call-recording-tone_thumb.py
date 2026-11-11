"""Blog / YouTube thumbnail for call-recording-tone, Studio palette (midnight, teal / cyan, REC red).

usage: call-recording-tone_thumb.py FACE_T OUT.jpg [FACE_CX] [FRAME_DIR]
  (grab the face frame first: ffmpeg -ss FACE_T -i Main.mp4 -frames:v 1 FRAME_DIR/f_FACE_T.png)
"""
import sys, numpy as np, cv2
import os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(ROOT, "projects", "call-recording-tone"))
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import text3d as T3
import studio as S

D = sys.argv[4] if len(sys.argv) > 4 else "./"   # folder holding f_<t>.png frames grabbed from the face-cam
F = os.path.join(ROOT, "assets", "fonts") + "/"
ARCH = F + "ArchivoBlack-Regular.ttf"
MAN8, MAN7 = F + "Manrope-800.ttf", F + "Manrope-700.ttf"
ML = F + "AnekMalayalam-800.ttf"
W, H = 1280, 720
FACE_T = float(sys.argv[1]) if len(sys.argv) > 1 else 16.2
FACE_CX = float(sys.argv[3]) if len(sys.argv) > 3 else 0.55
OUT = sys.argv[2] if len(sys.argv) > 2 else "thumb.jpg"


def ramp(n, stops):
    xs = np.linspace(0, 1, max(int(n), 1))
    return np.stack([np.interp(xs, [p for p, _ in stops], [c[k] for _, c in stops]) for k in range(3)], -1)


def face_layer(path, cx_frac, width, zoom=1.0, cy_top=0.0):
    src = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    sh, sw = src.shape[:2]
    ch = sh / zoom
    cw = ch * width / H
    xa = int(np.clip(cx_frac * sw - cw / 2, 0, sw - cw))
    ya = int(np.clip(cy_top * sh, 0, sh - ch))
    crop = cv2.resize(src[ya:ya + int(ch), xa:xa + int(cw)], (width, H), interpolation=cv2.INTER_AREA)
    crop = np.clip((crop - 0.5) * 1.10 + 0.50, 0, 1)
    # tame the blown-out window behind the presenter so it sits in the dark set
    lum = crop.mean(-1, keepdims=True)
    hot = np.clip((lum - 0.80) / 0.2, 0, 1)
    crop = crop * (1 - 0.55 * hot) + np.array([0.10, 0.22, 0.30], np.float32) * 0.55 * hot
    return crop


def place_face(fr, face, x0, fade=230):
    w = face.shape[1]
    a = (np.clip(np.arange(w, dtype=np.float32) / fade, 0, 1) ** 1.5)[None, :, None]
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    a = a * (1 - 0.30 * np.clip((yy - 0.78) / 0.22, 0, 1))
    region = fr[:, x0:x0 + w]
    region[:] = region * (1 - a) + face[:, :region.shape[1]] * a


def text3d(fr, lines, cx, cy, bw, bh, yaw=-14, pitch=6):
    size = T3.fit_size(lines, ARCH, bw, bh)
    blk = T3.Block(lines, ARCH, size, S.SIDE, depth=0.24, layers=26)
    lay = blk.render(W, H, yaw=yaw, pitch=pitch, scale=1.0, cx=cx, cy=cy, sweep=0.35)
    T3.shadow_and_glow(fr, lay, shadow=0.6, glow=0.40, offset=(0, 12))
    T3.composite(fr, lay)


def shadowed(img, draw_fn, blur=7, alpha=0.85, dy=4):
    m = Image.new("L", img.size, 0)
    draw_fn(ImageDraw.Draw(m), 255)
    img.paste(Image.new("RGB", img.size, (0, 0, 0)), (0, dy), m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha)))


def text(img, xy, txt, font, fill=(255, 255, 255), stops=None, anchor="la"):
    shadowed(img, lambda d, v: d.text(xy, txt, font=font, fill=v, anchor=anchor))
    if stops is None:
        ImageDraw.Draw(img).text(xy, txt, font=font, fill=fill, anchor=anchor)
        return
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).text(xy, txt, font=font, fill=255, anchor=anchor)
    bb = m.getbbox()
    col = np.zeros((img.size[1], img.size[0], 3), np.uint8)
    col[:, bb[0]:bb[2]] = ramp(bb[2] - bb[0], stops)[None].astype(np.uint8)
    img.paste(Image.fromarray(col), (0, 0), m)


def chip(img, x, y, label, fg, bg, dot=None, size=24):
    f = ImageFont.truetype(MAN8, size)
    pad = size * 0.75
    dw = size * 0.95 if dot else 0
    w, h = int(f.getlength(label) + 2 * pad + dw), int(size * 1.75)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
    if dot:
        r = size * 0.27
        cx, cy = x + pad + r, y + h / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dot)
    d.text((x + pad + dw, y + h / 2 + 1), label, font=f, fill=fg, anchor="lm")
    return x + w


def struck_bubble(img, x, y, txt, size=27):
    f = ImageFont.truetype(MAN7, size)
    tw = f.getlength(txt)
    ic = size * 1.5
    w, h = int(tw + ic + size * 1.6), int(size * 2.2)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x, y, x + w, y + h], radius=h * 0.32, fill=S.PANEL + (240,), outline=S.LINE + (255,), width=2)
    # speaker icon
    sx, sy = x + size * 0.7, y + h / 2
    d.polygon([(sx, sy - size * 0.22), (sx + size * 0.28, sy - size * 0.22), (sx + size * 0.62, sy - size * 0.5),
               (sx + size * 0.62, sy + size * 0.5), (sx + size * 0.28, sy + size * 0.22), (sx, sy + size * 0.22)], fill=S.MUTE + (255,))
    for k, rr in enumerate((0.42, 0.72)):
        d.arc([sx + size * 0.62 - size * rr, sy - size * rr, sx + size * 0.62 + size * rr, sy + size * rr], -45, 45,
              fill=S.MUTE + (255,), width=max(2, int(size * 0.09)))
    tx = x + ic + size * 0.8
    d.text((tx, y + h / 2), txt, font=f, fill=(196, 206, 220, 255), anchor="lm")
    d.line([(tx - 6, y + h / 2 + 2), (tx + tw + 6, y + h / 2 + 2)], fill=S.REC + (255,), width=max(4, int(size * 0.16)))
    sh = lay.split()[3].filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.6))
    img.paste(Image.new("RGB", img.size, (0, 0, 0)), (0, 10), sh)
    img.paste(lay, (0, 0), lay)
    # red "no" badge on the corner
    r = size * 0.78
    cx, cy = x + w - r * 0.35, y - r * 0.15
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=S.REC, outline=(255, 255, 255), width=3)
    k = r * 0.42
    d.line([(cx - k, cy - k), (cx + k, cy + k)], fill=(255, 255, 255), width=int(r * 0.26))
    d.line([(cx - k, cy + k), (cx + k, cy - k)], fill=(255, 255, 255), width=int(r * 0.26))
    return y + h


def toggle_card(img, x, y, size=24):
    f = ImageFont.truetype(MAN7, size)
    label = "Play audio tone"
    sw_w, sw_h = size * 2.3, size * 1.3
    w, h = int(f.getlength(label) + sw_w + size * 2.2), int(size * 2.6)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x, y, x + w, y + h], radius=h * 0.3, fill=(246, 249, 252, 255))
    d.text((x + size * 0.8, y + h / 2), label, font=f, fill=(20, 28, 40, 255), anchor="lm")
    tx = x + w - size * 0.8 - sw_w
    ty = y + (h - sw_h) / 2
    d.rounded_rectangle([tx, ty, tx + sw_w, ty + sw_h], radius=sw_h / 2, fill=(14, 170, 150, 255))
    r = sw_h * 0.36
    cx, cy = tx + sw_w - sw_h / 2, ty + sw_h / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
    glow = lay.split()[3].filter(ImageFilter.GaussianBlur(16))
    gcol = Image.new("RGB", img.size, S.TEAL)
    img.paste(gcol, (0, 0), glow.point(lambda v: int(v * 0.55)))
    img.paste(lay, (0, 0), lay)


def logo(img, x, y, s=62):
    lg = Image.open(os.path.join(ROOT, "assets", "logo", "vcreate.png")).convert("RGBA")
    lg.thumbnail((s, s))
    img.paste(lg, (x, y), lg)


cv2.imwrite(D + "face_src.png", cv2.imread(D + f"f_{FACE_T}.png"))
fr = S.backdrop(W, H).astype(np.float32)
place_face(fr, face_layer(D + "face_src.png", FACE_CX, 660, zoom=1.0, cy_top=0.0), 620)
text3d(fr, [("NO MORE", S.FACE_WHITE, 0.56), ("ANNOUNCEMENT", S.FACE_TEAL, 1.0)], 340, 200, 610, 250, yaw=-13)
img = Image.fromarray((np.clip(fr, 0, 1) * 255).astype(np.uint8))
xe = chip(img, 58, 44, "REC", (255, 255, 255), (150, 28, 34), dot=(255, 255, 255), size=22)
chip(img, xe + 12, 44, "ANDROID", (6, 18, 24), S.TEAL, size=22)
struck_bubble(img, 58, 322, "“This call is now being recorded”", size=27)
text(img, (58, 420), "അനൗൺസ്‌മെന്റ് ഇല്ലാതെ", ImageFont.truetype(ML, 50))
text(img, (58, 498), "കോൾ റെക്കോർഡ് ചെയ്യാം", ImageFont.truetype(ML, 54), stops=[(0, S.TEAL), (1, S.CYAN)])
toggle_card(img, 58, 612, size=24)
logo(img, 1196, 30, 58)
img.save(OUT, quality=93)
print("wrote", OUT)
