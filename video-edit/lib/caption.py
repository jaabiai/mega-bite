"""Left-aligned, word-highlight captions drawn as RGBA overlays."""
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from brand import FONTS, font_path, hex2rgb


@lru_cache(maxsize=64)
def _font(name, size):
    return ImageFont.truetype(font_path(FONTS[name]), int(round(size)))


def layout(words, font, max_w, space):
    """Greedy wrap -> list of lines, each a list of (index, word, width). `space` is the full gap between words."""
    lines, cur, w = [], [], 0.0
    for i, word in enumerate(words):
        ww = font.getlength(word)
        add = ww if not cur else space + ww
        if cur and w + add > max_w:
            lines.append(cur)
            cur, w = [], 0.0
            add = ww
        cur.append((i, word, ww))
        w += add
    if cur:
        lines.append(cur)
    return lines


def draw_caption(canvas, words, active, pal, S=1.0, x=110, y=540, max_w=780, size=64,
                 anchor="center", pop=1.0, opacity=1.0, upcoming=0.55, shadow=True):
    """Draw onto `canvas` (RGBA PIL image) in place. Coordinates are 1080p-space, scaled by S.

    active: index of the word being spoken (None = no highlight, -1 = none spoken yet).
    pop: 1.0 -> 1.12 scale on the active word (animation parameter).
    """
    f = _font("caption", size * S)
    space = f.getlength(" ") + 0.30 * size * S      # room for the highlight pill's padding
    lines = layout(words, f, max_w * S, space)
    line_h = size * S * 1.34
    block_h = line_h * len(lines)
    top = y * S - (block_h / 2 if anchor == "center" else block_h if anchor == "bottom" else 0)
    accent = hex2rgb(pal["accent"]) + (255,)
    on_acc = hex2rgb(pal["on_accent"]) + (255,)
    white = hex2rgb(pal["text"])

    W, H = canvas.size
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pills = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shad = Image.new("L", (W, H), 0)
    gd, pd, td, sd = (ImageDraw.Draw(im) for im in (glow, pills, text, shad))

    for li, line in enumerate(lines):
        cx = x * S
        cy = top + li * line_h
        for idx, word, ww in line:
            is_act = (active is not None and idx == active)
            font = f
            tx, ty = cx, cy
            if is_act:
                pad_x, pad_y = 0.17 * size * S, 0.06 * size * S
                scale = pop
                bw = (ww + 2 * pad_x) * scale
                bh = (size * S * 1.18 + 2 * pad_y) * scale
                ccx = cx + ww / 2
                ccy = cy + size * S * 0.66
                box = (ccx - bw / 2, ccy - bh / 2, ccx + bw / 2, ccy + bh / 2)
                rad = 0.26 * size * S * scale
                gd.rounded_rectangle(box, radius=rad, fill=accent[:3] + (200,))
                pd.rounded_rectangle(box, radius=rad, fill=accent)
                font = _font("caption_active", size * S * scale)
                tw = font.getlength(word)
                tx = ccx - tw / 2
                ty = ccy - size * S * scale * 0.66
                td.text((tx, ty), word, font=font, fill=on_acc)
            else:
                a = 255 if (active is None or idx < active) else int(255 * upcoming)
                if active == -1:
                    a = int(255 * upcoming)
                td.text((tx, ty), word, font=font, fill=white + (a,))
                sd.text((tx, ty), word, font=font, fill=a)
            cx += ww + space

    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if shadow:
        sh = shad.filter(ImageFilter.GaussianBlur(7 * S))
        sa = (np.array(sh, np.float32) * 0.75).astype(np.uint8)
        sl = np.zeros((H, W, 4), np.uint8)
        sl[..., 3] = sa
        sl = Image.fromarray(sl, "RGBA")
        off = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        off.paste(sl, (0, int(3 * S)))
        out = Image.alpha_composite(out, off)
    if active is not None and active >= 0:
        gb = glow.filter(ImageFilter.GaussianBlur(14 * S))
        ga = np.array(gb)
        ga[..., 3] = (ga[..., 3] * 0.55).astype(np.uint8)
        out = Image.alpha_composite(out, Image.fromarray(ga, "RGBA"))
    out = Image.alpha_composite(out, pills)
    out = Image.alpha_composite(out, text)
    if opacity < 1.0:
        a = np.array(out)
        a[..., 3] = (a[..., 3] * opacity).astype(np.uint8)
        out = Image.fromarray(a, "RGBA")
    canvas.alpha_composite(out)
    return canvas
