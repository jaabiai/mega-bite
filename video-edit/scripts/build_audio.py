#!/usr/bin/env python3
"""Sound design for the video - everything is synthesised here, so there is no third-party
audio and nothing that can trigger a copyright / Content-ID claim.

* SFX: a small set of soft UI sounds (whoosh, pop, click, bell, chime, shimmer, thud ...)
  placed on the timeline from the same timeline the overlay uses.  Rules: every sound is
  quiet, whooshes come in 3 different variants, and a whoosh is skipped when another one
  happened less than 3 s earlier (no "whoosh-whoosh-whoosh" fatigue).
* Music: a soft A-minor tech/ambient bed (pad + bass + pluck arpeggio + light kick/hat).
* Mix: narration (cleaned) -> music is ducked under the voice (side-chain) -> SFX on top ->
  loudness-normalised to -14 LUFS / -1.5 dBTP (YouTube reference level).

Usage: build_audio.py OUT.wav
"""
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_timeline  # noqa: E402
from common import MAIN, WORK, sh  # noqa: E402
from compose import VOICE_CHAIN  # noqa: E402
from edl import EDL  # noqa: E402

SR = 48000
AUD = os.path.join(WORK, "audio")
os.makedirs(AUD, exist_ok=True)


# ------------------------------------------------------------------ helpers
def write_wav(path, x):
    x = np.atleast_2d(x)
    if x.shape[0] == 1:
        x = np.vstack([x, x])
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        d = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64) / 32768
        return d.reshape(-1, w.getnchannels()).T


def t_axis(n):
    return np.arange(n) / SR


def exp_env(n, tau):
    return np.exp(-t_axis(n) / tau)


def fade(x, a=.005, b=.02):
    n = len(x)
    ia, ib = int(a * SR), int(b * SR)
    x = x.copy()
    if ia:
        x[:ia] *= np.linspace(0, 1, ia)
    if ib:
        x[-ib:] *= np.linspace(1, 0, ib)
    return x


def fft_filter(x, lo=None, hi=None):
    """Smooth band limiting in the frequency domain."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def reverb(x, rt=1.4, wet=.25, seed=3):
    rng = np.random.default_rng(seed)
    n = int(rt * SR)
    ir = rng.standard_normal(n) * np.exp(-t_axis(n) * 6.9 / rt)
    ir = fft_filter(ir, hi=5500)
    ir[:int(.012 * SR)] *= np.linspace(0, 1, int(.012 * SR))
    L = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)
    y /= max(np.abs(y).max(), 1e-9) / max(np.abs(x).max(), 1e-9)
    out = np.zeros(L)
    out[:len(x)] += x * (1 - wet)
    out += y * wet
    return out


def peak(x, db):
    return x * (10 ** (db / 20) / max(np.abs(x).max(), 1e-9))


# ------------------------------------------------------------------ SFX
def whoosh(dur=.6, f0=500, f1=3600, width=1.6, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.standard_normal(n)
    N, hop = 2048, 512
    win = np.hanning(N)
    out = np.zeros(n + N)
    freqs = np.fft.rfftfreq(N, 1 / SR)
    for i in range(0, n, hop):
        fr = np.zeros(N)
        seg = x[i:i + N]
        fr[:len(seg)] = seg
        fc = f0 * (f1 / f0) ** (i / n)
        mask = np.exp(-.5 * (np.log2(np.maximum(freqs, 1) / fc) / (width / 2)) ** 2)
        out[i:i + N] += np.fft.irfft(np.fft.rfft(fr * win) * mask) * win
    out = out[:n]
    k = np.arange(n) / n
    out *= np.sin(np.pi * k ** .8) ** 2
    return peak(fade(out, .01, .05), -16)


def pop(f=720, dur=.16):
    n = int(dur * SR)
    t = t_axis(n)
    fr = f * (1 + .16 * np.exp(-t / .02))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * exp_env(n, .035) + .3 * np.sin(4 * np.pi * np.cumsum(fr) / SR) * exp_env(n, .02)
    return peak(fade(x, .002, .03), -18)


def click():
    n = int(.06 * SR)
    rng = np.random.default_rng(5)
    nz = fft_filter(rng.standard_normal(n), lo=2500) * exp_env(n, .004)
    tn = np.sin(2 * np.pi * 1900 * t_axis(n)) * exp_env(n, .012)
    return peak(fade(nz * .8 + tn * .5, .0005, .01), -19)


def tick():
    n = int(.07 * SR)
    return peak(fade(np.sin(2 * np.pi * 1650 * t_axis(n)) * exp_env(n, .016), .001, .02), -24)


def bell(f=1318.5, dur=1.5, level=-19):
    n = int(dur * SR)
    t = t_axis(n)
    x = np.zeros(n)
    for ratio, amp, tau in ((1, 1.0, .7), (2.0, .45, .45), (2.76, .3, .3), (5.4, .15, .12)):
        x += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / tau)
    x += .35 * np.sin(2 * np.pi * f * t + 2.2 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t / .08)) * np.exp(-t / .5)
    return peak(fade(x, .002, .15), level)


def chime2():
    a, b = bell(1318.5, 1.2, -20), bell(1975.5, 1.4, -20)
    out = np.zeros(int(1.7 * SR))
    out[:len(a)] += a
    out[int(.17 * SR):int(.17 * SR) + len(b)] += b
    return out


def soft_chime():
    n = int(1.6 * SR)
    t = t_axis(n)
    x = (np.sin(2 * np.pi * 880 * t) + .5 * np.sin(2 * np.pi * 1320 * t) + .2 * np.sin(2 * np.pi * 1760 * t)) * np.exp(-t / .55)
    x *= np.minimum(1, t / .06)
    return peak(fade(x, .002, .2), -21)


def shimmer(dur=1.0, seed=4):
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    t = t_axis(n)
    nz = fft_filter(rng.standard_normal(n), lo=4500, hi=14000)
    trem = .55 + .45 * np.sin(2 * np.pi * 17 * t + rng.uniform(0, 6))
    env = np.sin(np.pi * np.arange(n) / n) ** 1.5
    sp = sum(np.sin(2 * np.pi * f * t) * np.exp(-((t - c) ** 2) / .003) for f, c in
             ((2637, .15), (3135, .28), (3520, .41), (4186, .55), (3951, .66)) if c < dur)
    return peak(fade(nz * trem * env * .6 + sp * .25, .02, .1), -21)


def thud():
    n = int(.7 * SR)
    t = t_axis(n)
    fr = 38 + 85 * np.exp(-t / .07)
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / .18)
    rng = np.random.default_rng(2)
    x += fft_filter(rng.standard_normal(n), hi=380) * np.exp(-t / .05) * .8
    return peak(fade(x, .001, .1), -14)


def swell():
    n = int(1.0 * SR)
    rng = np.random.default_rng(6)
    t = t_axis(n)
    nz = fft_filter(rng.standard_normal(n), lo=120, hi=2200)
    env = (t / 1.0) ** 2 * np.exp(-((t - .85) ** 2) / .02) + .25 * np.exp(-((t - .85) ** 2) / .08)
    low = np.sin(2 * np.pi * 62 * t) * np.exp(-np.maximum(t - .85, 0) / .12) * np.minimum(1, t / .5)
    return peak(fade(nz * env + low * .6, .01, .12), -17)


SFX = {
    "whoosh_a": lambda: whoosh(.62, 420, 3400, 1.7, 1),
    "whoosh_b": lambda: whoosh(.55, 3000, 500, 1.7, 2),
    "whoosh_c": lambda: whoosh(.7, 250, 2200, 2.0, 3),
    "pop": pop, "pop_hi": lambda: pop(980, .14), "click": click, "tick": tick,
    "bell": bell, "chime2": chime2, "soft_chime": soft_chime, "shimmer": shimmer, "thud": thud, "swell": swell,
}


# ------------------------------------------------------------------ event list from the timeline
def events(tl):
    ev = []                                           # (time, sfx, gain_db)
    ev.append((0.12, "shimmer", -4))                  # logo reveal
    last_whoosh, k = -99, 0
    blocks = tl["blocks"]
    for i, b in enumerate(blocks):
        if b["start"] - last_whoosh >= 3:
            ev.append((b["start"], ["whoosh_a", "whoosh_c", "whoosh_b"][k % 3], 0))
            last_whoosh, k = b["start"], k + 1
        nxt = blocks[i + 1]["start"] if i + 1 < len(blocks) else 1e9
        if nxt - b["end"] > 3 and b["end"] - last_whoosh >= 3:
            ev.append((b["end"] + .02, "whoosh_b", -5))
            last_whoosh = b["end"]
        for s in b["subs"][1:]:
            ev.append((s["start"] + .05, "tick", 0))
    for c in tl["cta"]:
        if c["type"] == "subscribe":
            ev += [(c["start"] + .08, "pop", 0), (c["start"] + c["clickAt"], "click", 0), (c["start"] + c["clickAt"] + .22, "bell", 0)]
        else:
            ev.append((c["start"] + .1, "pop", 0))
            for i in range(len(c["items"])):
                ev.append((c["start"] + c["hitAt"] + i * .16, "pop_hi", 0 if i == 0 else -6))
    for t in tl["toasts"]:
        ev.append((t["start"] + .15, "chime2", 0))
    for t in tl["titles"]:
        if "chipStagger" in t:
            ev += [(x, "tick", 4) for x in t["chipStagger"]]
            ev.append((t["activeFrom"], "soft_chime", -3))
    # picture-specific sounds (times derived from the screen-recording mapping in the EDL)
    ev += [(15.0, "click", 0),            # tap Messages
           (26.2, "shimmer", -1),         # first reveal
           (45.0, "click", 0),            # long-press
           (63.8, "thud", 0),             # Slam effect lands
           (64.9, "swell", 0),            # Loud effect
           (74.3, "soft_chime", 0),       # Gentle effect
           (77.9, "shimmer", -2),         # Invisible ink selected
           (90.4, "click", 0),            # tap send
           (98.5, "shimmer", -1)]         # final reveal
    e = EDL["end_card"]["start"]
    ev += [(e + .15, "chime2", -2), (e + 1.9, "bell", 0), (e + 2.35, "pop_hi", 0), (e + 2.8, "pop_hi", 0)]
    ev = sorted(ev)
    # de-cluster: a tick is dropped when a "real" sound happens within 0.5 s of it
    keep = [e for e in ev if e[1] != "tick" or not any(o is not e and o[1] != "tick" and abs(o[0] - e[0]) < .5 for o in ev)]
    return keep


def sfx_track(total, ev):
    cache = {k: f() for k, f in SFX.items()}
    out = np.zeros((2, int(total * SR) + 2 * SR))
    rng = np.random.default_rng(11)
    for t, name, g in ev:
        x = cache[name] * 10 ** (g / 20)
        i = int(t * SR)
        pan = rng.uniform(-.25, .25)
        out[0, i:i + len(x)] += x * (1 - max(pan, 0))
        out[1, i:i + len(x)] += x * (1 + min(pan, 0))
    return out[:, :int(total * SR)]


# ------------------------------------------------------------------ music
def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def additive(f, dur, harm=10, bright=1.0, detune=0.0):
    n = int(dur * SR)
    t = t_axis(n)
    x = np.zeros(n)
    for h in range(1, harm + 1):
        if f * h > 6500:
            break
        x += np.sin(2 * np.pi * f * h * (1 + detune) * t) / h ** bright
    return x


def music(total, bpm=96):
    beat = 60 / bpm
    bar = 4 * beat
    nbars = int(np.ceil(total / bar)) + 1
    out = np.zeros(int((nbars * bar + 4) * SR))
    chords = [  # Am F C G
        dict(pad=[57, 60, 64, 69], bass=45), dict(pad=[53, 57, 60, 65], bass=41),
        dict(pad=[55, 60, 64, 67], bass=48), dict(pad=[55, 59, 62, 67], bass=43)]

    def put(x, t, g=1.0):
        i = int(t * SR)
        out[i:i + len(x)] += x[:max(0, len(out) - i)] * g

    rng = np.random.default_rng(21)
    kick_n = int(.4 * SR)
    kt = t_axis(kick_n)
    kick = np.sin(2 * np.pi * np.cumsum(46 + 90 * np.exp(-kt / .035)) / SR) * np.exp(-kt / .11)
    hat_n = int(.06 * SR)
    hat = fft_filter(rng.standard_normal(hat_n), lo=7000) * exp_env(hat_n, .012)
    for b in range(nbars):
        c = chords[b % 4]
        t0 = b * bar
        # pad (slow attack / release, two detuned layers)
        pad_len = bar + .8
        pad = np.zeros(int(pad_len * SR))
        for m in c["pad"]:
            pad += additive(midi(m), pad_len, 9, 1.2) + additive(midi(m), pad_len, 9, 1.2, .004)
        env = np.minimum(1, t_axis(len(pad)) / .6) * np.minimum(1, (pad_len - t_axis(len(pad))) / .8)
        put(peak(pad * env, -22) if b > 0 else peak(pad * env, -22), t0)
        if b >= 1:
            bass = additive(midi(c["bass"]), beat * 1.9, 3, 1.6)
            put(peak(fade(bass * exp_env(len(bass), 1.3), .01, .08), -23), t0)
            put(peak(fade(bass * exp_env(len(bass), 1.3), .01, .08), -26), t0 + 2 * beat)
        if b >= 2:
            order = [0, 2, 1, 3, 2, 1, 3, 2]
            for j, idx in enumerate(order):
                note = c["pad"][idx] + 12
                p = additive(midi(note), .5, 5, 1.1) * exp_env(int(.5 * SR), .16)
                put(peak(fade(p, .002, .1), -31 if j % 2 == 0 else -34), t0 + j * beat / 2 + .005 * rng.standard_normal())
        if b >= 4 and b < nbars - 3:
            put(peak(kick, -25), t0)
            put(peak(kick, -27), t0 + 2 * beat)
            for j in range(4):
                put(peak(hat, -37), t0 + (j + .5) * beat)
    out = reverb(out, rt=1.9, wet=.32)
    out = out[:int(total * SR)]
    # master fade in / out
    out *= np.minimum(1, t_axis(len(out)) / 2.5)
    out *= np.clip((total - t_axis(len(out))) / 3.5, 0, 1)
    return out


# ------------------------------------------------------------------ mix
def main(out_path):
    tl = build_timeline.build()
    total = tl["duration"]
    spoken = EDL["main_duration"]
    voice = os.path.join(AUD, "voice.wav")
    sh(f'ffmpeg -v error -y -i "{MAIN}" -vn -af "{VOICE_CHAIN},apad=whole_dur={total}" -t {total} -ar {SR} -ac 2 "{voice}"')

    mus = music(total)
    # a little more music once the voice has finished (end card)
    gain = np.where(t_axis(len(mus)) > EDL["end_card"]["start"], 10 ** (5 / 20), 1.0)
    gain = np.convolve(gain, np.ones(int(.8 * SR)) / int(.8 * SR), mode="same")
    mus = mus * gain
    write_wav(os.path.join(AUD, "music.wav"), mus)
    ev = events(tl)
    sfx = sfx_track(total, ev)
    write_wav(os.path.join(AUD, "sfx.wav"), sfx)
    json.dump([[round(t, 2), n, g] for t, n, g in ev], open(os.path.join(AUD, "sfx_events.json"), "w"))
    print(f"{len(ev)} sfx events, music {len(mus) / SR:.1f}s")

    # duck the music under the voice, sum, then normalise to YouTube loudness (two-pass)
    pre = os.path.join(AUD, "premix.wav")
    sh(f'ffmpeg -v error -y -i "{voice}" -i "{AUD}/music.wav" -i "{AUD}/sfx.wav" -filter_complex '
       f'"[0:a]asplit=2[v][sc];[1:a]volume=1dB[m];[m][sc]sidechaincompress=threshold=0.015:ratio=9:attack=15:release=450:makeup=1[md];'
       f'[v][md]amix=inputs=2:normalize=0:duration=longest[vm];[vm][2:a]amix=inputs=2:normalize=0:duration=longest[o]" '
       f'-map "[o]" -ar {SR} -ac 2 "{pre}"')
    def lufs(path):
        o = subprocess.run(f'ffmpeg -hide_banner -nostats -i "{path}" -af ebur128=peak=true -f null -', shell=True,
                           capture_output=True, text=True).stderr
        tail = o[o.rindex("Summary:"):]
        return (float(re.search(r"I:\s+(-?[\d.]+)\s+LUFS", tail).group(1)),
                float(re.search(r"Peak:\s+(-?[\d.]+)\s+dBFS", tail).group(1)))

    cur, gain = lufs(pre)[0], 0.0
    first = cur
    for _ in range(4):                                         # gain -> limiter -> measure, until on target
        gain += -14.0 - cur
        sh(f'ffmpeg -v error -y -i "{pre}" -af "volume={gain:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=disabled" '
           f'-ar {SR} -ac 2 "{out_path}"')
        cur, tp = lufs(out_path)
        if abs(cur + 14.0) < .25:
            break
    j = {"input_i": f"{first:.2f}"}
    print("wrote", out_path, "| measured before norm:", j["input_i"], "LUFS")


if __name__ == "__main__":
    main(sys.argv[1])
