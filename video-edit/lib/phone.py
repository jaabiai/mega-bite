"""Procedurally drawn smartphone frame (own design, iPhone-Pro-Max proportions) + screen mask.

Geometry is expressed in *screen pixels* of a 1320x2868 recording and scaled by k.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SCREEN_W, SCREEN_H = 1320, 2868
SCREEN_R = 172      # display corner radius
BEZEL = 24          # black glass border
BAND = 16           # metal band visible from the front
PAD = 26            # room for side buttons


def _rr(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def build(screen_h, titanium=((92, 94, 99), (36, 37, 41))):
    """Return (frame_rgba, screen_mask_L, (screen_x, screen_y, screen_w, screen_h)) at the given screen height."""
    k = screen_h / SCREEN_H
    ss = 2  # supersample
    sw, sh = round(SCREEN_W * k), round(SCREEN_H * k)
    pad = round(PAD * k)
    bz, bd, rr_ = BEZEL * k, BAND * k, SCREEN_R * k
    W = sw + 2 * (bz + bd) + 2 * pad
    H = sh + 2 * (bz + bd) + 2 * pad
    W, H = int(round(W)), int(round(H))
    S = lambda v: int(round(v * ss))

    body = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    ox0, oy0 = pad, pad
    ox1, oy1 = W - pad, H - pad
    R_out = rr_ + bz + bd

    # side buttons (behind the body)
    btn = (70, 72, 77, 255)
    def pill(x0, y0, x1, y1, col=btn):
        _rr(d, (S(x0), S(y0), S(x1), S(y1)), S(min(x1 - x0, y1 - y0) / 2.2), fill=col)
    bw = 9 * k
    top = oy0
    pill(ox0 - bw, top + 330 * k, ox0 + 4, top + 430 * k)                 # action
    pill(ox0 - bw, top + 560 * k, ox0 + 4, top + 800 * k)                 # vol up
    pill(ox0 - bw, top + 840 * k, ox0 + 4, top + 1080 * k)                # vol down
    pill(ox1 - 4, top + 700 * k, ox1 + bw, top + 1010 * k)                # power
    pill(ox1 - 4, top + 1500 * k, ox1 + bw * 0.8, top + 1680 * k, (52, 53, 57, 255))  # camera control

    # titanium body with diagonal gradient
    grad = Image.new("RGBA", (W * ss, H * ss))
    gp = np.zeros((H * ss, W * ss, 4), np.uint8)
    yy, xx = np.mgrid[0:H * ss, 0:W * ss].astype(np.float32)
    t = np.clip((xx / (W * ss) * 0.55 + yy / (H * ss) * 0.45), 0, 1)
    c0, c1 = np.array(titanium[0], np.float32), np.array(titanium[1], np.float32)
    col = c0[None, None, :] * (1 - t[..., None]) + c1[None, None, :] * t[..., None]
    gp[..., :3] = col.astype(np.uint8)
    gp[..., 3] = 255
    grad = Image.fromarray(gp, "RGBA")
    mask = Image.new("L", (W * ss, H * ss), 0)
    _rr(ImageDraw.Draw(mask), (S(ox0), S(oy0), S(ox1), S(oy1)), S(R_out), fill=255)
    body.paste(grad, (0, 0), mask)

    # specular rim: thin bright line along the outer edge, fading from top-left
    rim = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    _rr(rd, (S(ox0), S(oy0), S(ox1), S(oy1)), S(R_out), outline=(255, 255, 255, 120), width=max(2, S(2.2 * k)))
    fade = np.clip(1.15 - t * 1.6, 0.0, 1.0)
    ra = np.array(rim)
    ra[..., 3] = (ra[..., 3] * fade).astype(np.uint8)
    body = Image.alpha_composite(body, Image.fromarray(ra, "RGBA"))

    # inner dark line between band and bezel, then the black glass bezel
    d = ImageDraw.Draw(body)
    bx0, by0, bx1, by1 = ox0 + bd, oy0 + bd, ox1 - bd, oy1 - bd
    _rr(d, (S(bx0), S(by0), S(bx1), S(by1)), S(R_out - bd), fill=(8, 8, 10, 255))
    # screen hole
    sx0, sy0, sx1, sy1 = bx0 + bz, by0 + bz, bx1 - bz, by1 - bz
    hole = Image.new("L", (W * ss, H * ss), 255)
    _rr(ImageDraw.Draw(hole), (S(sx0), S(sy0), S(sx1), S(sy1)), S(rr_), fill=0)
    alpha = np.array(body.getchannel("A"), np.float32) * (np.array(hole, np.float32) / 255.0)
    body.putalpha(Image.fromarray(alpha.astype(np.uint8), "L"))

    frame = body.resize((W, H), Image.LANCZOS)
    smask = Image.new("L", (W * ss, H * ss), 0)
    _rr(ImageDraw.Draw(smask), (S(sx0), S(sy0), S(sx1), S(sy1)), S(rr_), fill=255)
    smask = smask.resize((W, H), Image.LANCZOS)
    return frame, smask, (int(round(sx0)), int(round(sy0)), sw, sh)


def glass_gloss(w, h, strength=0.07):
    """Faint diagonal reflection over the screen (RGBA)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = (xx / w + yy / h)
    band = np.exp(-((d - 0.55) / 0.10) ** 2) * 0.7 + np.exp(-((d - 0.30) / 0.22) ** 2) * 0.3
    a = (band * strength * 255).astype(np.uint8)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = 255
    out[..., 3] = a
    return Image.fromarray(out, "RGBA")
