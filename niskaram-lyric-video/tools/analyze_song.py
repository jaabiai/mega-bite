#!/usr/bin/env python3
"""Find musical onsets in the song (numpy only) -> $WORK/onsets.json (seconds, song time).
Used to land cut/transition midpoints on musical accents."""
import json, os, pathlib, subprocess
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work')); WORK.mkdir(parents=True, exist_ok=True)

def main():
    sr, hop, n = 22050, 256, 2048
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(ROOT / 'inputs' / 'song.mp3'), '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    win = np.hanning(n)
    frames = 1 + (len(x) - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * win, axis=1))
    edges = np.unique(np.geomspace(2, n // 2, 41).astype(int))
    B = np.stack([S[:, a:b].sum(1) for a, b in zip(edges[:-1], edges[1:])], 1)
    L = np.log1p(10 * B)
    flux = np.r_[0, np.maximum(0, np.diff(L, axis=0)).sum(1)]
    fps = sr / hop
    local = np.convolve(flux, np.ones(int(fps)) / int(fps), 'same')
    thr = local * 1.3 + flux.std() * 0.25
    peaks = [i for i in range(2, len(flux) - 2) if flux[i] > thr[i] and flux[i] >= flux[i - 1] and flux[i] > flux[i + 1] and flux[i] >= flux[i - 2] and flux[i] >= flux[i + 2]]
    onsets, last = [], -1.0
    for i in peaks:
        t = i / fps
        if t - last >= 0.18:
            onsets.append([round(t, 3), round(float(flux[i]), 3)]); last = t
        elif onsets and flux[i] > onsets[-1][1]:
            onsets[-1] = [round(t, 3), round(float(flux[i]), 3)]; last = t
    json.dump(onsets, open(WORK / 'onsets.json', 'w'))
    print(f'{len(onsets)} onsets -> {WORK / "onsets.json"}')

if __name__ == '__main__':
    main()
