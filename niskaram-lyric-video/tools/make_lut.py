#!/usr/bin/env python3
"""Generate the cinematic grade as a 3D LUT (.cube): soft S-curve, lifted blacks,
emerald-teal shadows, warm gold highlights, slightly restrained saturation."""
import numpy as np, pathlib, os, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work')); WORK.mkdir(parents=True, exist_ok=True)
N = 33

def smoothstep(x): return x * x * (3 - 2 * x)

def grade(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # contrast: blend toward a smoothstep S-curve
    out = np.stack([r, g, b], -1)
    out = out * 0.55 + smoothstep(np.clip(out, 0, 1)) * 0.45
    # lift blacks / roll off whites
    out = 0.010 + out * 0.988
    out = np.where(out > 0.94, 0.94 + (out - 0.94) * 0.8, out)
    luma = (0.2126 * out[..., 0] + 0.7152 * out[..., 1] + 0.0722 * out[..., 2])[..., None]
    sh = np.clip(1 - luma * 1.6, 0, 1) ** 2
    hi = np.clip((luma - 0.35) / 0.65, 0, 1) ** 1.6
    out = out + sh * np.array([-0.022, 0.006, 0.026]) + hi * np.array([0.034, 0.014, -0.032])
    # saturation
    luma = (0.2126 * out[..., 0] + 0.7152 * out[..., 1] + 0.0722 * out[..., 2])[..., None]
    out = luma + (out - luma) * 0.98
    return np.clip(out, 0, 1)

def main():
    ax = np.linspace(0, 1, N)
    # .cube order: red varies fastest
    bb, gg, rr = np.meshgrid(ax, ax, ax, indexing='ij')
    grid = np.stack([rr, gg, bb], -1).reshape(-1, 3)
    res = grade(grid)
    path = WORK / 'cinema.cube'
    with open(path, 'w') as f:
        f.write('TITLE "Miraya cinematic"\nLUT_3D_SIZE %d\n' % N)
        for r, g, b in res: f.write(f'{r:.6f} {g:.6f} {b:.6f}\n')
    print('wrote', path)

if __name__ == '__main__':
    main()
