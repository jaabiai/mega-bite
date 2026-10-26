"""Stand-in channel mark used ONLY until the real MEGA BYTE logo file is supplied."""
from PIL import Image, ImageDraw
from brand import hex2rgb, FONTS, font_path
from PIL import ImageFont


def draw_bug(canvas, pal, S=1.0, left=64, top=48, label="MEGA BYTE"):
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(font_path(FONTS["title"]), int(34 * S))
    fm = ImageFont.truetype(font_path(FONTS["title"]), int(24 * S))
    tw = f.getlength(label)
    d_ = 64 * S
    gap = 14 * S
    total = d_ + gap + tw
    x0 = left * S
    y0 = top * S
    acc = hex2rgb(pal["accent"])
    d.ellipse((x0, y0, x0 + d_, y0 + d_), fill=acc)
    mw = fm.getlength("MB")
    d.text((x0 + d_ / 2 - mw / 2, y0 + d_ / 2 - 17 * S), "MB", font=fm, fill=hex2rgb(pal["on_accent"]))
    d.text((x0 + d_ + gap, y0 + d_ / 2 - 24 * S), label, font=f, fill=(255, 255, 255, 235))
    return canvas
