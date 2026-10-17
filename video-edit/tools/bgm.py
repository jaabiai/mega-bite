"""Background-music bed + voice-ducked mix.

  bed:  tracks are decoded, loudness-matched, placed on a timeline with equal-power crossfades and fades.
  mix:  voice (untouched level) + bed, where the bed is sidechain-ducked by the voice, then a ceiling limiter.

Music source: Mixkit "Stock Music Free License" (commercial use incl. YouTube / social video allowed, no attribution needed).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

SR = 48000


def decode(path, start=0.0):
    """-> float32 array (n, 2) at 48 kHz"""
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", path, "-ar", str(SR), "-ac", "2", "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def lufs_of(x):
    """integrated loudness (LUFS) of a float32 stereo array"""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"]
    err = subprocess.run(cmd, input=x.astype(np.float32).tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def eq_power(n, rising):
    t = np.linspace(0, np.pi / 2, n, dtype=np.float32)
    return np.sin(t) if rising else np.cos(t)


def make_bed(sections, total, track_dir, out_wav, fade_in=1.5, fade_out=3.0, target_lufs=-20.0):
    """sections: [dict(track=id, t0=seconds on the timeline, skip=seconds into the track)], each runs until the next one starts (+crossfade).
    each section dict may carry xf (crossfade seconds going INTO it)."""
    n = int(total * SR)
    bed = np.zeros((n, 2), np.float32)
    for k, sec in enumerate(sections):
        x = decode(os.path.join(track_dir, f"{sec['track']}.mp3"), sec.get("skip", 0.0))
        x *= 10 ** ((target_lufs - lufs_of(x[: SR * 90])) / 20)              # every track on the same loudness
        xf = sec.get("xf", 4.0) if k > 0 else 0.0
        t0 = sec["t0"] - xf / 2                                              # the new track starts under the previous one's tail
        end = (sections[k + 1]["t0"] + sections[k + 1].get("xf", 4.0) / 2) if k + 1 < len(sections) else total
        a, b = max(int(t0 * SR), 0), min(int(end * SR), n)
        seg = x[: b - a].copy()
        if len(seg) < b - a:
            raise ValueError(f"track {sec['track']} is too short for its section ({len(seg)/SR:.1f}s < {(b-a)/SR:.1f}s)")
        if k == 0:
            fi = int(fade_in * SR)
            seg[:fi] *= eq_power(fi, True)[:, None]
        else:
            fi = int(xf * SR)
            seg[:fi] *= eq_power(fi, True)[:, None]
        if k + 1 < len(sections):
            fo = int(sections[k + 1].get("xf", 4.0) * SR)
            seg[-fo:] *= eq_power(fo, False)[:, None]
        bed[a:b] += seg
    fo = int(fade_out * SR)
    bed[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None] ** 1.5       # smooth tail
    tmp = out_wav + ".f32"
    open(tmp, "wb").write(bed.tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", tmp, "-c:a", "pcm_f32le", out_wav], check=True)
    os.remove(tmp)
    return out_wav


def speech_rms_db(path):
    """average level (dBFS RMS, 20 ms frames) of the voice while it is speaking"""
    x = decode(path)[:, 0].astype(np.float64)
    w = int(0.02 * SR)
    n = len(x) // w
    f = 20 * np.log10(np.sqrt((x[: n * w].reshape(n, w) ** 2).mean(1)) + 1e-9)
    return float(f[f > -30].mean())


def mix(voice, bed, out, voice_lufs, under_db=13.0, duck_db=6.0, ratio=2.0, attack=30, release=600, ceiling=0.841, total=None):
    """voice + ducked bed.
    under_db: loudness of the bed below the voice while the voice is silent;  duck_db: extra reduction while the voice speaks
    (the sidechain threshold is derived from the voice's own speech level, so it works for any voice loudness)."""
    music_lufs = -20.0                                         # bed was normalised to this in make_bed
    gain = (voice_lufs - under_db) - music_lufs
    thr_db = speech_rms_db(voice) - duck_db * ratio / (ratio - 1)      # reduction = (level - thr) * (1 - 1/ratio) = duck_db
    thr = 10 ** (thr_db / 20)
    fc = (f"[1:a]volume={gain:.2f}dB[m0];"
          f"[0:a]asplit=2[v][sc];"
          f"[m0][sc]sidechaincompress=threshold={thr:.5f}:ratio={ratio}:attack={attack}:release={release}:makeup=1[md];"
          f"[v][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit={ceiling}:attack=5:release=60:level=disabled:latency=1[o]")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", bed, "-filter_complex", fc, "-map", "[o]", "-c:a", "pcm_s16le", "-ar", str(SR)]
    if total:
        cmd += ["-t", f"{total:.3f}"]
    subprocess.run(cmd + [out], check=True)
    return out


if __name__ == "__main__":
    print(__doc__)
