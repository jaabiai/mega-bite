"""Independent audio-sync diagnostic.
For every line start, measure vocal-onset strength (spectral flux, 300-4000 Hz) in [-0.15,+0.30] s and
report its percentile rank against random times in the same song.  Random placement -> ~50th percentile;
starts aligned with vocal onsets -> high.  Also reports the per-line time of the strongest onset near the start."""
import os
import sys, json, numpy as np, soundfile as sf, scipy.signal as sg
T = os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")

def flux(x, sr=16000, lo=300, hi=4000, hop=0.01):
    f, t, S = sg.stft(x, sr, nperseg=512, noverlap=512 - int(sr * hop))
    m = (f >= lo) & (f <= hi)
    M = np.log1p(np.abs(S[m]) * 30)
    d = np.maximum(0, np.diff(M, axis=1)).sum(0)
    d = np.concatenate([[0], d])
    return d / (np.median(d) + 1e-9), hop

def main(timing, shift=0.0):
    x, sr = sf.read(T + "work/audio16k.wav", dtype="float32")
    d, hop = flux(x)
    lines = json.load(open(timing, encoding="utf-8"))["lines"]
    def score(t):
        a, b = int((t - 0.15) / hop), int((t + 0.30) / hop)
        return d[max(0, a):b].max()
    sc = np.array([score(l["start"] + shift) for l in lines])
    rng = np.random.RandomState(0)
    rnd = np.array([score(t) for t in rng.uniform(5, 262, 4000)])
    pct = np.array([(rnd < s).mean() for s in sc])
    return lines, sc, pct, rnd

if __name__ == "__main__":
    lines, sc, pct, rnd = main(sys.argv[1])
    print(f"mean percentile of line starts vs random times: {pct.mean()*100:.1f}  (random=50)")
    print(f"share of starts above random median: {(pct>0.5).mean()*100:.0f}%   above 80th pct: {(pct>0.8).mean()*100:.0f}%")
    for sh in (-0.8, -0.4, 0.4, 0.8):
        _, s2, p2, _ = main(sys.argv[1], sh)
        print(f"  control: all starts shifted by {sh:+.1f}s -> mean percentile {p2.mean()*100:.1f}")
