"""Assemble the edited voice track (48 kHz, 24-bit mono) from the EDL.

* speech 'cores' come straight from the recording, sample-accurate
* pauses (pads) are clean room tone, so breaths / mouth noise / fillers between phrases disappear
* cuts inside continuous speech (splices) get a short equal-power crossfade
"""
import json
import numpy as np
import wave

S = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/work/'
SR = 48000
FPS = 30.0
SPF = int(SR / FPS)       # 1600 samples per video frame

src = np.load(S + 'audio/mono48.npy').astype(np.float64)
edl = json.load(open(S + 'edl_s.json'))
pieces = edl['pieces']
total_frames = edl['total_frames']

# ------------------------------------------------------------------ room tone bed
def frame_db(a, n=SR // 10):
    return np.array([20 * np.log10(np.sqrt(np.mean(a[i:i + n] ** 2)) + 1e-9) for i in range(0, len(a) - n, n)])

db100 = frame_db(src)
win = 25                                    # 2.5 s of 100 ms frames
best, best_i = 1e9, 0
for i in range(0, len(db100) - win):
    seg = db100[i:i + win]
    score = seg.max() * 1.0 + seg.mean() * 0.5
    if score < best:
        best, best_i = score, i
bed_start = best_i * (SR // 10)
bed = src[bed_start:bed_start + 25 * (SR // 10)].copy()
print(f"room tone bed: {bed_start / SR:.2f}-{(bed_start + len(bed)) / SR:.2f}s  max {db100[best_i:best_i + win].max():.1f} dB  mean {db100[best_i:best_i + win].mean():.1f} dB")
bed -= bed.mean()


def tone(n, k):
    """n samples of room tone, starting at a different offset for every pad."""
    off = (k * 7919) % max(len(bed) - n - 1, 1)
    out = bed[off:off + n].copy()
    f = min(int(0.01 * SR), n // 2)
    if f > 0:                               # gentle edges so the pad never clicks
        r = np.sin(np.linspace(0, np.pi / 2, f)) ** 2
        out[:f] *= r
        out[-f:] *= r[::-1]
    return out


def ramp(n):
    return np.sin(np.linspace(0, np.pi / 2, n)) ** 2          # 0 -> 1, equal-power partner is sqrt(1-r^2)


out = np.zeros(total_frames * SPF)
STG_A, STG_N = 719 * SPF, 84 * SPF               # welcome stinger gap
h = STG_N // 2
out[STG_A:STG_A + h] = tone(h, 999)
out[STG_A + h:STG_A + STG_N] = tone(STG_N - h, 1000)
FADE_IN = int(0.008 * SR)
FADE_OUT = int(0.035 * SR)
for k, p in enumerate(pieces):
    sa, sb = p['a'] * SPF, p['b'] * SPF
    L = sb - sa
    cs = int(round(p['on'] * SR)) - sa
    ce = int(round(p['off'] * SR)) - sa
    cs, ce = max(cs, 0), min(ce, L)
    e = np.zeros(L)
    e[cs:ce] = 1.0
    if p['lead_pad'] and cs > 0:
        n = min(FADE_IN, ce - cs)
        e[cs:cs + n] = ramp(n)
    elif p['lead_pad']:
        pass
    if p['tail_pad'] and ce < L:
        n = min(FADE_OUT, ce - cs)
        e[ce - n:ce] *= ramp(n)[::-1]
    speech = src[sa:sb] * e
    pad = np.zeros(L)
    h_end = min(cs + FADE_IN, L)                 # head pad (+ the part under the fade-in)
    if h_end > 0:
        pad[:h_end] = tone(h_end, 2 * k)
    t_beg = max(ce - FADE_OUT, 0)                # tail pad (+ the part under the fade-out)
    if L - t_beg > 0:
        pad[t_beg:] += tone(L - t_beg, 2 * k + 1) if t_beg >= h_end else 0
    pad *= np.sqrt(np.clip(1 - e ** 2, 0, 1))
    oa = p['out_a'] * SPF
    out[oa:oa + L] = speech + pad

# ------------------------------------------------------------------ "Welcome to Mega Byte" (optional; cut from an earlier Megabyte video)
import os
WELCOME = S + 'audio/welcome_clip.npy'           # mono, 48 kHz, float, already trimmed (first word starts at index ~0)
WELCOME_AT = 0.52                                # seconds after the stinger start (logo hit)
if os.path.exists(WELCOME):
    wc = np.load(WELCOME).astype(np.float64)
    i0 = STG_A + int(WELCOME_AT * SR)
    n = min(len(wc), STG_A + STG_N - i0 - int(0.05 * SR))
    wc = wc[:n].copy()
    f = int(0.012 * SR)
    wc[:f] *= np.linspace(0, 1, f) ** 2
    wc[-f:] *= np.linspace(1, 0, f) ** 2
    # blend with the room tone so the clip sits on the same noise floor
    out[i0:i0 + n] = out[i0:i0 + n] * 0.0 + wc + tone(n, 1001) * 0.0
    print(f"welcome clip inserted at out {i0 / SR:.3f}s, {n / SR:.2f}s long")
else:
    print('no welcome clip yet -> stinger gap is room tone')

# ------------------------------------------------------------------ splice crossfades (cut inside speech)
H = int(0.006 * SR)           # +-6 ms around the cut
for p, q in zip(pieces, pieces[1:]):
    if q['seg'] != p['seg']:
        continue
    T = q['out_a'] * SPF
    prev = src[p['b'] * SPF - H: p['b'] * SPF + H]
    nxt = src[q['a'] * SPF - H: q['a'] * SPF + H]
    r = np.sin(np.linspace(0, np.pi / 2, 2 * H))
    out[T - H:T + H] = prev * r[::-1] + nxt * r
    print(f"splice crossfade at out {T / SR:.3f}s")

peak = np.abs(out).max()
print(f"assembled: {len(out) / SR:.2f}s  peak {20 * np.log10(peak):.1f} dBFS")

# click detector: largest sample-to-sample jump relative to local RMS around every piece boundary
d = np.abs(np.diff(out))
worst = []
for p in pieces:
    for t in (p['out_a'] * SPF, p['out_b'] * SPF):
        a, b = max(t - 120, 1), min(t + 120, len(d) - 1)
        loc = np.sqrt(np.mean(out[max(t - 2400, 0):t + 2400] ** 2)) + 1e-9
        worst.append((d[a:b].max() / loc, t / SR))
worst.sort(reverse=True)
print("largest boundary jumps (x local RMS):", [(round(w, 2), round(t, 2)) for w, t in worst[:5]])

pcm = np.clip(out, -1, 1)
pcm = (pcm * (2 ** 23 - 1)).astype(np.int32)
b = np.empty((len(pcm), 3), np.uint8)
b[:, 0] = pcm & 255
b[:, 1] = (pcm >> 8) & 255
b[:, 2] = (pcm >> 16) & 255
with wave.open(S + 'audio/voice_edit.wav', 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(3)
    w.setframerate(SR)
    w.writeframes(b.tobytes())
np.save(S + 'audio/voice_edit.npy', out.astype(np.float32))
print('wrote audio/voice_edit.wav')
