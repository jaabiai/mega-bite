#!/usr/bin/env python3
"""Final audio mix: cleaned voice + ducked music bed + timeline-synced SFX -> mix.wav (48 kHz stereo).

usage: mix_audio.py --voice voice_clean.wav --music track.mp3 --sfx-dir dir --out mix.wav
"""
import argparse, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import timeline as TL

ap = argparse.ArgumentParser()
ap.add_argument("--voice", required=True)
ap.add_argument("--music", required=True)
ap.add_argument("--sfx-dir", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--music-lufs", type=float, default=-27.0, help="loudness of the music bed on its own")
args = ap.parse_args()
SR = 48000
TOTAL = TL.TOTAL


def decode(path, af=None, ch=2):
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", af] if af else []) + ["-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, ch).copy()


def lufs(x):
    cmd = ["ffmpeg", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"]
    out = subprocess.run(cmd, input=x.astype(np.float32).tobytes(), capture_output=True).stderr.decode()
    return float(out.split("Integrated loudness:")[-1].split("I:")[1].split("LUFS")[0])


N = int(round(TOTAL * SR))
voice = decode(args.voice)
mix_v = np.zeros((N, 2), np.float32)
mix_v[: min(N, len(voice))] = voice[:N]

# ---- music bed ---------------------------------------------------------------------------------------
music = decode(args.music, "highpass=f=110,lowpass=f=14000,equalizer=f=1800:t=q:w=0.8:g=-3.5,equalizer=f=3500:t=q:w=1.0:g=-1.5")
if len(music) < N:                                    # loop with a 2 s cross-fade if the track is short
    reps = int(np.ceil(N / len(music))) + 1
    xf = 2 * SR
    out = music
    for _ in range(reps):
        a, b = out[:-xf], music
        fade = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
        out = np.concatenate([a, out[-xf:] * (1 - fade) + b[:xf] * fade, b[xf:]])
        if len(out) >= N:
            break
    music = out
music = music[:N]
music *= 10 ** ((args.music_lufs - lufs(music)) / 20)

# envelope of the voice -> ducking curve
mono = mix_v.mean(axis=1)
win = int(0.06 * SR)
sq = np.convolve(mono ** 2, np.ones(win) / win, mode="same")
env_db = 10 * np.log10(sq + 1e-10)
speech = np.clip((env_db - (-46.0)) / 10.0, 0, 1)                     # 0 silence .. 1 speech
# one-pole attack/release smoothing (block-wise, vectorised via scipy-free loop on 10 ms hops)
hop = int(0.01 * SR)
sp_h = speech[::hop].copy()
att, rel = np.exp(-1 / (0.05 / 0.01)), np.exp(-1 / (0.50 / 0.01))
y = np.zeros_like(sp_h)
for i in range(1, len(sp_h)):
    c = att if sp_h[i] > y[i - 1] else rel
    y[i] = c * y[i - 1] + (1 - c) * sp_h[i]
duck_db = np.interp(np.arange(N), np.arange(len(y)) * hop, -4.5 * y)    # up to -4.5 dB while talking
t = np.arange(N) / SR
swell = np.interp(t, [TL.NARR_END - 1.2, TL.NARR_END + 0.6], [0.0, 8.0])   # music comes up for the end card
fade_in = np.clip(t / 1.4, 0, 1) ** 2
fade_out = np.clip((TOTAL - t) / 3.0, 0, 1) ** 1.5
gain = 10 ** ((duck_db + swell) / 20) * fade_in * fade_out
music *= gain[:, None].astype(np.float32)

# ---- SFX ---------------------------------------------------------------------------------------------
sfx_cache = {}


def sfx(name):
    if name not in sfx_cache:
        x = decode(os.path.join(args.sfx_dir, f"sfx_{name}.mp3"))
        x /= max(np.abs(x).max(), 1e-6)                 # peak-normalise, gains below are relative to 0 dBFS
        sfx_cache[name] = x
    return sfx_cache[name]


events = []          # (time, name, gain_dB)
events.append((0.55, "3124", -15))
events.append((17.50, "3005", -13))                # logo sting pops in
events.append((19.45, "1489", -16))                # ...and flies into the corner
for (tt, kind) in TL.TRANSITIONS:
    if kind == "wipe":
        events.append((tt - 0.42, "1492", -9))
    else:
        events.append((tt - 0.22, "1489", -13))
for (tt, u, v) in TL.TAPS:
    events.append((tt, "1109", -13))
for (t0, t1, n, label) in TL.STEPS[1:]:
    events.append((t0, "3005", -17))
events += [(14.38, "2856", -8), (14.52, "2852", -15),            # padlock closes
           (21.05, "2354", -10), (21.18, "933", -13),            # subscribe click + bell
           (23.95, "2354", -10),                                 # share
           (78.40, "2852", -13)]                                 # Save -> locked
sfx_bus = np.zeros((N, 2), np.float32)
for tt, name, gdb in events:
    x = sfx(name) * 10 ** (gdb / 20)
    i0 = int(round(tt * SR))
    i1 = min(N, i0 + len(x))
    if i0 < 0 or i0 >= N:
        continue
    sfx_bus[i0:i1] += x[: i1 - i0]

mix = mix_v + music + sfx_bus
peak = np.abs(mix).max()
print(f"peak before limiter {20 * np.log10(peak + 1e-9):.2f} dBFS")
# gentle safety limiter: soft knee above 0.85
thr = 0.85
over = np.abs(mix) > thr
mix[over] = np.sign(mix[over]) * (thr + (1 - thr) * np.tanh((np.abs(mix[over]) - thr) / (1 - thr)))
print(f"mix loudness {lufs(mix):.1f} LUFS")
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s24le", args.out], stdin=subprocess.PIPE)
p.communicate(mix.astype(np.float32).tobytes())
print("wrote", args.out)
