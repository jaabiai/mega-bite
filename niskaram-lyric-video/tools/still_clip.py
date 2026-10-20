#!/usr/bin/env python3
"""Turn a still image (public-domain painting, museum open-access scan, historic photograph) into a camera-move clip.

The film and the reels use *footage*; where no free-licence footage exists for a line (prayer, sujood, mosque interior, Quran)
a still gets a slow push / pan so it sits in the edit like any other shot.  The result is written as a normal mp4 into
$WORK/src (film) or $WORK/vsrc (reels), so make_shots.py / reels.py treat it like a stock clip.

  python3 tools/still_clip.py stills/spec_film.json [--only 900001,900002]

spec: a list of {id, image, w, h, dur, fps, cam: {a: [cx, cy, zw], b: [cx, cy, zw]}, tone?: {sat, contrast, bright, warm}, out?}
  cx, cy  centre of the camera window in image coordinates (0..1)
  zw      width of the window as a fraction of the image width (smaller = closer); the height follows from w:h
"""
import json, os, pathlib, subprocess, sys
import numpy as np
from PIL import Image, ImageEnhance

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work'))
MAX_SIDE = 7000

def smooth(p):
    return p * p * (3 - 2 * p)

def load(path, tone):
    im = Image.open(path)
    im.draft('RGB', (MAX_SIDE, MAX_SIDE))
    im = im.convert('RGB')
    if max(im.size) > MAX_SIDE:
        k = MAX_SIDE / max(im.size); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    if tone:
        if 'sat' in tone: im = ImageEnhance.Color(im).enhance(tone['sat'])
        if 'contrast' in tone: im = ImageEnhance.Contrast(im).enhance(tone['contrast'])
        if 'bright' in tone: im = ImageEnhance.Brightness(im).enhance(tone['bright'])
        if tone.get('warm'):
            a = np.asarray(im).astype(np.float32); k = tone['warm']
            a[..., 0] *= 1 + 0.10 * k; a[..., 2] *= 1 - 0.14 * k
            im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return im

def box(im, cam, p, aspect, ease=True):
    """Camera window (x0, y0, x1, y1) in image pixels at progress p; aspect = out_h / out_w."""
    q = smooth(p) if ease else p
    cx = cam['a'][0] + (cam['b'][0] - cam['a'][0]) * q
    cy = cam['a'][1] + (cam['b'][1] - cam['a'][1]) * q
    zw = cam['a'][2] + (cam['b'][2] - cam['a'][2]) * q
    w = zw * im.width; h = w * aspect
    if h > im.height: h = im.height; w = h / aspect
    x0 = min(max(cx * im.width - w / 2, 0), im.width - w); y0 = min(max(cy * im.height - h / 2, 0), im.height - h)
    return (x0, y0, x0 + w, y0 + h)

def render(item):
    out = pathlib.Path(item.get('out') or (WORK / ('vsrc' if item['h'] > item['w'] else 'src') / f"{item['id']}.mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H, fps, dur = item['w'], item['h'], item.get('fps', 24), item['dur']
    img = pathlib.Path(item['image'])
    im = load(img if img.is_absolute() else WORK / 'stills' / img, item.get('tone'))
    n = round(dur * fps)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-an',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', str(out)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        b = box(im, item['cam'], i / max(1, n - 1), H / W)
        pr.stdin.write(im.resize((W, H), Image.LANCZOS, box=b).tobytes())
    pr.stdin.close(); pr.wait()
    print('wrote', out, f'{out.stat().st_size / 1e6:.1f} MB', flush=True)

if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    only = {int(x) for x in sys.argv[sys.argv.index('--only') + 1].split(',')} if '--only' in sys.argv else None
    for it in spec:
        if only is None or it['id'] in only:
            render(it)
