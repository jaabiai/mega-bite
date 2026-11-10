"""Extruded 3D text without a 3D engine.

A block of lines is drawn once (front face with a bevel, side colour layer).  Each frame the block is posed in space
(yaw / pitch / roll, scale, position) and rendered as a stack of perspective-warped copies from the back of the extrusion
to the front face, so the sides appear and turn correctly as the block rotates.

    blk = Block([("YOUR OWN", WHITE, 0.62), ("AI ASSISTANT", AURORA, 1.0)], font_path, size=300)
    rgb, a, (x0, y0) = blk.render(W, H, yaw=-18, pitch=6, scale=1.0, cx=W / 2, cy=H / 2, sweep=0.4)
    composite(frame, rgb, a, x0, y0)

`rgb` is premultiplied float32, `a` float32 alpha, both cropped to the block's bounding box at (x0, y0).
"""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont


def _ramp(n, stops):
    xs = np.linspace(0, 1, max(int(n), 1), dtype=np.float32)
    pos = [p for p, _ in stops]
    return np.stack([np.interp(xs, pos, [c[k] for _, c in stops]) for k in range(3)], -1) / 255.0


def _rot(yaw, pitch, roll):
    y, p, r = (math.radians(v) for v in (yaw, pitch, roll))
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]], np.float32)
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]], np.float32)
    Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]], np.float32)
    return Rz @ Rx @ Ry


class Block:
    def __init__(self, lines, font_path, size, side, depth=0.22, layers=26, line_gap=0.94, tracking=0.0):
        """lines: [(text, face_stops, rel_size)] - face_stops is ("v" | "h", [(pos, rgb), ...]).
        side: horizontal colour stops of the extrusion.  depth: extrusion depth as a fraction of `size`."""
        self.layers = layers
        self.depth = depth * size
        metrics = []
        for txt, _, rel in lines:
            ft = ImageFont.truetype(font_path, int(round(size * rel)))
            l, t, r, b = ft.getbbox(txt)
            tr = tracking * size * rel
            wd = sum(ft.getlength(c) for c in txt) + tr * max(len(txt) - 1, 0)
            metrics.append((ft, wd, t, b, tr))
        pad = int(size * 0.16)
        w = int(max(m[1] for m in metrics)) + 2 * pad
        heights = [m[3] - m[2] for m in metrics]
        gaps = [int(size * lines[i][2] * (line_gap - 0.74)) for i in range(len(lines) - 1)]
        h = int(sum(heights) + sum(gaps)) + 2 * pad
        mask = Image.new("L", (w, h), 0)
        face = np.zeros((h, w, 3), np.float32)
        y = pad
        for i, ((txt, (mode, stops), rel), (ft, wd, t, b, tr)) in enumerate(zip(lines, metrics)):
            lm = Image.new("L", (w, h), 0)
            d = ImageDraw.Draw(lm)
            x = (w - wd) / 2
            for c in txt:
                d.text((x, y - t), c, font=ft, fill=255)
                x += ft.getlength(c) + tr
            mask = Image.fromarray(np.maximum(np.asarray(mask), np.asarray(lm)))
            x0, x1 = int((w - wd) / 2), int((w + wd) / 2)
            if mode == "h":
                col = np.zeros((1, w, 3), np.float32)
                col[0, x0:x1] = _ramp(x1 - x0, stops)
                col[0, :x0], col[0, x1:] = col[0, x0], col[0, x1 - 1]
                band = np.repeat(col, b - t + 8, axis=0)
            else:
                band = np.repeat(_ramp(b - t + 8, stops)[:, None, :], w, axis=1)
            lmf = (np.asarray(lm, np.float32) / 255.0)[..., None]
            yy0 = max(y - 4, 0)
            region = face[yy0:yy0 + band.shape[0]]
            region[:] = region * (1 - lmf[yy0:yy0 + band.shape[0]]) + band[:region.shape[0]] * lmf[yy0:yy0 + band.shape[0]]
            y += (b - t) + (gaps[i] if i < len(gaps) else 0)
        m = np.asarray(mask, np.float32) / 255.0
        # bevel: light from the top-left picks out the upper edges, the lower edges fall into shade
        soft = cv2.GaussianBlur(m, (0, 0), max(size * 0.012, 1.2))
        gx = cv2.Sobel(soft, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(soft, cv2.CV_32F, 0, 1, ksize=3)
        lit = np.clip((gx * 0.45 + gy * 0.9) * 3.2, -1, 1)[..., None]
        face = face + np.clip(lit, 0, 1) * 0.55 * (1 - face) - np.clip(-lit, 0, 1) * 0.38 * face
        self.w, self.h = w, h
        self.mask = m
        self.face = np.dstack([np.clip(face, 0, 1) * m[..., None], m]).astype(np.float32)        # premultiplied RGBA
        side_rgb = np.repeat(_ramp(w, side)[None, :, :], h, axis=0)
        self.side = (np.dstack([side_rgb * m[..., None], m]) * 255).astype(np.uint8)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self._diag = (xx + yy * 0.55) / (w + h * 0.55)

    def _homography(self, z, R, s, cx, cy, f):
        w, h = self.w, self.h
        pts = np.array([[-w / 2, -h / 2, z], [w / 2, -h / 2, z], [w / 2, h / 2, z], [-w / 2, h / 2, z]], np.float32) * s
        p = pts @ R.T
        d = f / (f + p[:, 2])
        dst = np.stack([cx + p[:, 0] * d, cy + p[:, 1] * d], 1).astype(np.float32)
        src = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
        return cv2.getPerspectiveTransform(src, dst), dst

    def render(self, W, H, yaw=0.0, pitch=0.0, roll=0.0, scale=1.0, cx=None, cy=None, focal=None, sweep=None, alpha=1.0):
        """Returns (rgb_premultiplied, alpha, (x0, y0)) cropped to the block's bounding box, or None when off-screen.
        sweep: 0..1 position of a specular band crossing the front face (None = no band)."""
        if alpha <= 0 or scale <= 0:
            return None
        cx = W / 2 if cx is None else cx
        cy = H / 2 if cy is None else cy
        f = focal or 1.6 * max(W, H)
        R = _rot(yaw, pitch, roll)
        zs = [self.depth * k / self.layers for k in range(self.layers, -1, -1)]
        homs, pts = [], []
        for z in zs:
            Hm, dst = self._homography(z, R, scale, cx, cy, f)
            homs.append(Hm)
            pts.append(dst)
        allp = np.concatenate(pts)
        x0, y0 = int(max(math.floor(allp[:, 0].min()) - 2, 0)), int(max(math.floor(allp[:, 1].min()) - 2, 0))
        x1, y1 = int(min(math.ceil(allp[:, 0].max()) + 2, W)), int(min(math.ceil(allp[:, 1].max()) + 2, H))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return None
        Tm = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64)
        size = (x1 - x0, y1 - y0)
        rgb = np.zeros((size[1], size[0], 3), np.float32)
        a = np.zeros((size[1], size[0], 1), np.float32)
        n = self.layers
        for k, Hm in enumerate(homs[:-1]):                       # back of the extrusion -> just behind the face
            depth_k = 1 - k / n                                   # 1 = far, 0 = near
            shade = 0.26 + 0.52 * (1 - depth_k) ** 0.9
            if k >= n - 2:
                shade *= 0.62                                     # dark seam right behind the face
            lay = cv2.warpPerspective(self.side, Tm @ Hm, size, flags=cv2.INTER_LINEAR).astype(np.float32) / 255.0
            la = lay[..., 3:4]
            rgb = rgb * (1 - la) + lay[..., :3] * shade
            a = a * (1 - la) + la
        face = self.face
        if sweep is not None:
            band = np.exp(-((self._diag - (sweep * 1.5 - 0.25)) / 0.07) ** 2)[..., None] * self.mask[..., None]
            face = face.copy()
            face[..., :3] = np.clip(face[..., :3] + band * 0.55, 0, 1)
        lay = cv2.warpPerspective(face, Tm @ homs[-1], size, flags=cv2.INTER_LINEAR)
        la = lay[..., 3:4]
        rgb = rgb * (1 - la) + lay[..., :3]
        a = a * (1 - la) + la
        return rgb * alpha, a[..., 0] * alpha, (x0, y0)


def fit_size(lines, font_path, max_w, max_h, line_gap=0.94, tracking=0.0, probe=200):
    """Font size at which the block (without padding) fills max_w x max_h."""
    wmax, htot = 0.0, 0.0
    for i, (txt, _, rel) in enumerate(lines):
        ft = ImageFont.truetype(font_path, int(probe * rel))
        l, t, r, b = ft.getbbox(txt)
        wmax = max(wmax, sum(ft.getlength(c) for c in txt) + tracking * probe * rel * max(len(txt) - 1, 0))
        htot += (b - t) + (probe * rel * (line_gap - 0.74) if i < len(lines) - 1 else 0)
    return probe * min(max_w / wmax, max_h / htot)


def composite(fr, layer, opacity=1.0):
    """Blend a render() result onto a float32 RGB frame in place."""
    if layer is None:
        return
    rgb, a, (x0, y0) = layer
    h, w = a.shape
    reg = fr[y0:y0 + h, x0:x0 + w]
    reg[:] = reg * (1 - a[..., None] * opacity) + rgb * opacity


def shadow_and_glow(fr, layer, shadow=0.55, glow=0.5, offset=(0, 26), tint=(1.0, 0.55, 0.75)):
    """Soft drop shadow under the block and a coloured bloom around it (call before composite)."""
    if layer is None:
        return
    rgb, a, (x0, y0) = layer
    H, W = fr.shape[:2]
    q = 6
    full = np.zeros((H, W), np.float32)
    full[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
    small = cv2.resize(full, (W // q, H // q), interpolation=cv2.INTER_AREA)
    if shadow > 0:
        sh = cv2.GaussianBlur(small, (0, 0), 5.0)
        M = np.array([[1, 0, offset[0] / q], [0, 1, offset[1] / q]], np.float32)
        sh = cv2.warpAffine(sh, M, (W // q, H // q))
        fr *= 1 - cv2.resize(sh, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * shadow
    if glow > 0:
        gl = cv2.GaussianBlur(small, (0, 0), 9.0)
        gl = cv2.resize(gl, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * glow
        fr[:] = 1 - (1 - fr) * (1 - np.clip(gl, 0, 1) * np.array(tint, np.float32))
