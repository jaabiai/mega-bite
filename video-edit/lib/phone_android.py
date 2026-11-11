"""Procedurally drawn Android phone (own design): slim even bezels, flat aluminium rails, a punch-hole front camera in
the top-left corner of the display, volume rocker + power key on the right.  Same interface as phone.build().

Geometry is expressed in screen pixels of the recording (screen_w x screen_h) and scaled to the requested height.
"""
import numpy as np
from PIL import Image, ImageDraw


def _rr(d, box, r, **kw):
    d.rounded_rectangle(box, radius=r, **kw)


def build(screen_h, screen_w_over_h=720 / 1608, rail=((150, 154, 162), (64, 67, 74)), hole=(0.085, 0.0185, 0.024)):
    """Return (frame_rgba, screen_mask_L, (screen_x, screen_y, screen_w, screen_h)) at the given screen height.
    hole = (centre x / screen width, centre y / screen height, radius / screen width) of the punch-hole camera."""
    ss = 2
    sh = int(round(screen_h))
    sw = int(round(screen_h * screen_w_over_h))
    u = sh / 1608.0                                   # design unit: 1 px of a 1608 px tall display
    bez, band, pad = 15 * u, 8 * u, 20 * u
    r_scr = 52 * u
    W = int(round(sw + 2 * (bez + band + pad)))
    H = int(round(sh + 2 * (bez + band + pad)))
    S = lambda v: int(round(v * ss))
    body = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    ox0, oy0, ox1, oy1 = pad, pad, W - pad, H - pad
    R_out = r_scr + bez + band

    # keys on the right rail (behind the body)
    key = (88, 91, 98, 255)
    kw = 5 * u
    _rr(d, (S(ox1 - 3), S(oy0 + 300 * u), S(ox1 + kw), S(oy0 + 470 * u)), S(kw), fill=key)     # volume rocker
    _rr(d, (S(ox1 - 3), S(oy0 + 560 * u), S(ox1 + kw), S(oy0 + 650 * u)), S(kw), fill=key)     # power

    # aluminium rail with a vertical brushed gradient
    yy, xx = np.mgrid[0:H * ss, 0:W * ss].astype(np.float32)
    t = np.clip(xx / (W * ss) * 0.35 + yy / (H * ss) * 0.65, 0, 1)
    c0, c1 = np.array(rail[0], np.float32), np.array(rail[1], np.float32)
    g = np.zeros((H * ss, W * ss, 4), np.uint8)
    g[..., :3] = (c0 * (1 - t[..., None]) + c1 * t[..., None]).astype(np.uint8)
    g[..., 3] = 255
    m = Image.new("L", (W * ss, H * ss), 0)
    _rr(ImageDraw.Draw(m), (S(ox0), S(oy0), S(ox1), S(oy1)), S(R_out), fill=255)
    body.paste(Image.fromarray(g, "RGBA"), (0, 0), m)
    rim = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    _rr(ImageDraw.Draw(rim), (S(ox0), S(oy0), S(ox1), S(oy1)), S(R_out), outline=(255, 255, 255, 110), width=max(2, S(1.6 * u)))
    ra = np.array(rim)
    ra[..., 3] = (ra[..., 3] * np.clip(1.2 - t * 1.5, 0, 1)).astype(np.uint8)
    body = Image.alpha_composite(body, Image.fromarray(ra, "RGBA"))

    # black glass front, then the display hole
    d = ImageDraw.Draw(body)
    bx0, by0, bx1, by1 = ox0 + band, oy0 + band, ox1 - band, oy1 - band
    _rr(d, (S(bx0), S(by0), S(bx1), S(by1)), S(R_out - band), fill=(6, 6, 8, 255))
    sx0, sy0 = bx0 + bez, by0 + bez
    sx1, sy1 = sx0 + sw, sy0 + sh
    holeL = Image.new("L", (W * ss, H * ss), 255)
    _rr(ImageDraw.Draw(holeL), (S(sx0), S(sy0), S(sx1), S(sy1)), S(r_scr), fill=0)
    a = np.array(body.getchannel("A"), np.float32) * (np.array(holeL, np.float32) / 255.0)
    body.putalpha(Image.fromarray(a.astype(np.uint8), "L"))

    # punch-hole camera: drawn on top of the display, top-left
    hx, hy, hr = sx0 + hole[0] * sw, sy0 + hole[1] * sh, hole[2] * sw
    d = ImageDraw.Draw(body)
    d.ellipse((S(hx - hr), S(hy - hr), S(hx + hr), S(hy + hr)), fill=(4, 4, 6, 255))
    d.ellipse((S(hx - hr * 0.45), S(hy - hr * 0.45), S(hx + hr * 0.45), S(hy + hr * 0.45)), fill=(22, 26, 38, 255))
    d.ellipse((S(hx - hr * 0.30), S(hy - hr * 0.62), S(hx - hr * 0.05), S(hy - hr * 0.37)), fill=(120, 140, 170, 200))

    frame = body.resize((W, H), Image.LANCZOS)
    smask = Image.new("L", (W * ss, H * ss), 0)
    _rr(ImageDraw.Draw(smask), (S(sx0), S(sy0), S(sx1), S(sy1)), S(r_scr), fill=255)
    smask = smask.resize((W, H), Image.LANCZOS)
    return frame, smask, (int(round(sx0)), int(round(sy0)), sw, sh)
