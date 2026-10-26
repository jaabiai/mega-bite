"""Left-aligned, word-highlight captions drawn as small RGBA overlays (only the caption bbox is rasterised)."""
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from brand import FONTS, font_path, hex2rgb


@lru_cache(maxsize=128)
def font(name, size):
    return ImageFont.truetype(font_path(FONTS[name]), int(round(size)))


def layout(words, f, max_w, space):
    lines, cur, w = [], [], 0.0
    for i, word in enumerate(words):
        ww = f.getlength(word)
        add = ww if not cur else space + ww
        if cur and w + add > max_w:
            lines.append(cur)
            cur, w, add = [], 0.0, ww
        cur.append((i, word, ww))
        w += add
    if cur:
        lines.append(cur)
    return lines


def render_caption(words, active, pal, S=1.0, max_w=620, size=64, pop=1.0, opacity=1.0, upcoming=0.50):
    """Return (RGBA PIL image, (ox, oy)) where (ox, oy) is the offset of the image relative to the block's
    top-left corner at (0, 0) in caption space.  The caller pastes it at (x + ox, y_top + oy).
    Also returns block height so callers can centre/bottom-anchor it: -> (img, ox, oy, block_h)."""
    f = font("caption", size * S)
    space = f.getlength(" ") + 0.30 * size * S
    lines = layout(words, f, max_w * S, space)
    line_h = size * S * 1.34
    block_h = line_h * len(lines)
    pad = 46 * S
    W = int(max_w * S + 2 * pad + 40 * S)
    H = int(block_h + 2 * pad)
    accent = hex2rgb(pal["accent"])
    on_acc = hex2rgb(pal["on_accent"]) + (255,)
    white = hex2rgb(pal["text"])

    text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shad = Image.new("L", (W, H), 0)
    td, sd = ImageDraw.Draw(text), ImageDraw.Draw(shad)
    pill_box = None
    for li, line in enumerate(lines):
        cx, cy = pad, pad + li * line_h
        for idx, word, ww in line:
            is_act = active is not None and idx == active
            if is_act:
                px, py = 0.17 * size * S, 0.06 * size * S
                bw = (ww + 2 * px) * pop
                bh = (size * S * 1.18 + 2 * py) * pop
                ccx, ccy = cx + ww / 2, cy + size * S * 0.66
                box = (ccx - bw / 2, ccy - bh / 2, ccx + bw / 2, ccy + bh / 2)
                rad = 0.26 * size * S * pop
                pill_box = (box, rad)
                fa = font("caption_active", size * S * pop)
                tw = fa.getlength(word)
                td.text((ccx - tw / 2, ccy - size * S * pop * 0.66), word, font=fa, fill=on_acc)
            else:
                spoken = active is None or idx < active
                a = 255 if spoken else int(255 * upcoming)
                td.text((cx, cy), word, font=f, fill=white + (a,))
                sd.text((cx, cy), word, font=f, fill=a)
            cx += ww + space

    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pills = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if pill_box is not None:
        ss = 3
        m = Image.new("L", (W * ss, H * ss), 0)
        ImageDraw.Draw(m).rounded_rectangle([c * ss for c in pill_box[0]], radius=pill_box[1] * ss, fill=255)
        m = m.resize((W, H), Image.LANCZOS)
        solid = Image.new("RGBA", (W, H), accent + (255,))
        pills = Image.composite(solid, pills, m)
        glow = Image.composite(Image.new("RGBA", (W, H), accent + (210,)), glow, m)
    sh = np.array(shad.filter(ImageFilter.GaussianBlur(7 * S)), np.float32) * 0.80
    sl = np.zeros((H, W, 4), np.uint8)
    sl[..., 3] = sh.astype(np.uint8)
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_layer.paste(Image.fromarray(sl, "RGBA"), (0, int(3 * S)))
    out = Image.alpha_composite(out, shadow_layer)
    if active is not None and active >= 0:
        ga = np.array(glow.filter(ImageFilter.GaussianBlur(14 * S)))
        ga[..., 3] = (ga[..., 3] * 0.50).astype(np.uint8)
        out = Image.alpha_composite(out, Image.fromarray(ga, "RGBA"))
    out = Image.alpha_composite(out, pills)
    out = Image.alpha_composite(out, text)
    if opacity < 1.0:
        a = np.array(out)
        a[..., 3] = (a[..., 3] * opacity).astype(np.uint8)
        out = Image.fromarray(a, "RGBA")
    return out, -pad, -pad, block_h


def draw_caption(canvas, words, active, pal, S=1.0, x=96, y=500, anchor="center", slide=0.0, **kw):
    """Convenience wrapper: render and alpha-composite onto `canvas` (RGBA PIL) at 1080p-space (x, y)."""
    img, ox, oy, block_h = render_caption(words, active, pal, S=S, **kw)
    top = y * S - (block_h / 2 if anchor == "center" else block_h if anchor == "bottom" else 0) + slide * S
    canvas.alpha_composite(img, (int(x * S + ox), int(top + oy)))
    return block_h
