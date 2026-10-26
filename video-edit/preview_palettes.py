"""Render palette preview strips (face scene | screen-recording scene) for owner approval.

usage: python preview_palettes.py <face_frame.png> <screen_frame.png> <out_dir>
"""
import sys, os
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import brand, phone, scene, caption, grade, logo_placeholder
from brand import PALETTES, hex2rgb

face_png, screen_png, out_dir = sys.argv[1:4]
os.makedirs(out_dir, exist_ok=True)
PW, PH = 1280, 720
S = PH / 1080.0


def blur_box(arr, x0, y0, x1, y1, sigma=22):
    roi = arr[y0:y1, x0:x1]
    arr[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (0, 0), sigma)
    return arr


def face_panel(pal):
    im = cv2.cvtColor(cv2.imread(face_png), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    g = grade.grade(im, grain=0.008)
    z, fx, fx_t = 1.22, 0.54, 0.65              # zoom, face centre in source, where we want it
    x0 = fx - fx_t / z
    x0 = min(max(x0, 0.0), 1 - 1 / z)
    y0 = 0.02
    h0, w0 = g.shape[:2]
    crop = g[int(y0 * h0):int((y0 + 1 / z) * h0), int(x0 * w0):int((x0 + 1 / z) * w0)]
    g = cv2.resize(crop, (PW, PH), interpolation=cv2.INTER_AREA)
    # left scrim in the palette's dark colour (also keeps captions readable on the bright sky)
    xs = np.linspace(0, 1, PW, dtype=np.float32)[None, :, None]
    a = np.clip(1.0 - xs / 0.50, 0, 1) ** 1.5 * 0.80
    dark = np.array(hex2rgb(pal["bg0"]), np.float32) / 255
    g = g * (1 - a) + dark[None, None, :] * a
    img = Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    caption.draw_caption(img, ["Lock", "your", "Google", "search", "history"], 3, pal, S=S, x=96, y=500, max_w=470, size=70)
    logo_placeholder.draw_bug(img, pal, S=S)
    return img.convert("RGB")


def phone_panel(pal):
    bg = scene.background(PW, PH, pal, glow_center=(0.74, 0.5)).convert("RGBA")
    scr = cv2.cvtColor(cv2.imread(screen_png), cv2.COLOR_BGR2RGB)
    scr = blur_box(scr.copy(), 190, 1470, 775, 1555)
    hs = int(PH * 0.90)
    frame, smask, (sx, sy, sw, sh) = phone.build(hs)
    scr_r = cv2.resize(scr, (sw, sh), interpolation=cv2.INTER_AREA)
    grp = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    grp.paste(Image.fromarray(scr_r).convert("RGBA"), (sx, sy))
    a = np.array(grp)
    a[..., 3] = (np.array(smask, np.float32)).astype(np.uint8)
    grp = Image.fromarray(a, "RGBA")
    grp.alpha_composite(phone.glass_gloss(*frame.size))
    grp.alpha_composite(frame)
    cx, cy = int(PW * 0.74), PH // 2
    px, py = cx - frame.size[0] // 2, cy - frame.size[1] // 2
    sh_layer = scene.drop_shadow(bg.size, grp.getchannel("A"), blur=28 * S * 1.5, offset=(px, py + int(26 * S)), opacity=0.6) if False else None
    # shadow (offset handled by pasting mask at position)
    m = Image.new("L", bg.size, 0)
    m.paste(grp.getchannel("A"), (px, py + int(22 * S)))
    from PIL import ImageFilter
    m = m.filter(ImageFilter.GaussianBlur(26 * S * 1.4))
    sh_a = (np.array(m, np.float32) * 0.65).astype(np.uint8)
    shl = np.zeros((PH, PW, 4), np.uint8); shl[..., 3] = sh_a
    bg.alpha_composite(Image.fromarray(shl, "RGBA"))
    bg.alpha_composite(grp, (px, py))
    caption.draw_caption(bg, ["Require", "extra", "verification"], 1, pal, S=S, x=96, y=500, max_w=560, size=70)
    logo_placeholder.draw_bug(bg, pal, S=S)
    return bg.convert("RGB")


def swatches(pal, w, h=70):
    img = Image.new("RGB", (w, h), hex2rgb(pal["bg0"]))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(brand.font_path(brand.FONTS["label"]), 22)
    x = 24
    for key in ("accent", "accent2", "bg0", "bg1", "text"):
        d.rounded_rectangle((x, 14, x + 42, 56), radius=10, fill=hex2rgb(pal[key]), outline=(255, 255, 255), width=1)
        d.text((x + 52, 20), f"{key} {pal[key]}", font=f, fill=(235, 235, 235))
        x += 52 + int(f.getlength(f"{key} {pal[key]}")) + 26
    return img


for name, pal in PALETTES.items():
    a, b = face_panel(pal), phone_panel(pal)
    sheet = Image.new("RGB", (PW * 2, PH + 70))
    sheet.paste(a, (0, 0)); sheet.paste(b, (PW, 0))
    sheet.paste(swatches(pal, PW * 2), (0, PH))
    path = os.path.join(out_dir, f"palette_{name}.png")
    sheet.save(path)
    print(path)
