"""Audio-derived features used ONLY to drive visuals (beat pulses). The audio itself is never modified or re-encoded."""
import os, subprocess
import numpy as np


def compute(source_mp4, out_npz, fps=30):
    import scipy.signal as sg
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", source_mp4, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    b, a = sg.butter(4, [40, 200], btype="band", fs=16000)
    lo = sg.filtfilt(b, a, x)
    hop = 80                                              # 5 ms
    n = len(lo) // hop
    env = np.sqrt((lo[:n * hop].reshape(n, hop) ** 2).mean(1))
    env = sg.savgol_filter(env, 9, 2)
    d = np.maximum(0, np.diff(env, prepend=env[0]))
    d = d / (np.percentile(d, 97) + 1e-9)
    nf = int(len(x) / 16000 * fps) + 3
    k = np.zeros(nf, np.float32)
    for i in range(nf):
        s, e = int(i / fps * 200), int((i + 1) / fps * 200)
        k[i] = d[s:max(e, s + 1)].max() if s < len(d) else 0
    k = np.clip(k, 0, 1)
    out = np.zeros_like(k)
    acc = 0.0
    for i in range(nf):
        acc = max(k[i], acc * 0.80)
        out[i] = acc
    np.savez(out_npz, kick=out, duration=len(x) / 16000.0)
    return out


class Audio:
    def __init__(self, npz, fps=30):
        z = np.load(npz)
        self.kick_arr = z["kick"]
        self.duration = float(z["duration"])
        self.fps = fps

    def kick(self, t):
        i = int(min(max(t * self.fps, 0), len(self.kick_arr) - 1))
        return float(self.kick_arr[i])
