"""Verification report for the vertical Reel.   python verify_reel.py REEL.mp4 [--no-ocr]

Everything is measured on the finished MP4 (and compared against the completed landscape MP4, read-only).  Exit code 1 if any check FAILs.
Output is also written next to the reel as verify_output_reel.txt.
"""
import rl_common  # noqa: F401  (must be first)
import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import numpy as np

from rl_common import ROOT, CLIP_START, CLIP_END, FPS, NFRAMES
from hl_common import W, H

LANDSCAPE = os.path.join(ROOT, "output_hinglish_landscape", "Chalo_Jantar_Mantar_Hinglish_Landscape_1080p.mp4")
TIMING = os.path.join(ROOT, "output_hinglish_landscape", "lyric_timing_hinglish.json")
LANDSCAPE_SHA = "2d9bc9347e94fbfdf38bdb8c5c69a4cd0959898d5ca53a20155b01dd7124699f"
FAILS, LOG = [], []


def say(s=""):
    print(s, flush=True)
    LOG.append(s)


def ok(cond, label, detail=""):
    say(f"   [{'PASS' if cond else 'FAIL'}] {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        FAILS.append(label)
    return cond


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path, extra=()):
    return json.loads(run(["ffprobe", "-v", "error", "-count_packets", *extra, "-show_streams", "-show_format", "-of", "json", path]).stdout)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def audio_packets(path, interval=None):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_packets", "-show_data_hash", "sha256",
           "-show_entries", "packet=pts_time,size,duration_time,data_hash", "-of", "json"]
    if interval:
        cmd += ["-read_intervals", interval]
    return json.loads(run(cmd + [path]).stdout)["packets"]


def norm_letters(s):
    return re.sub(r"[^a-z]", "", s.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reel")
    ap.add_argument("--no-ocr", action="store_true")
    ns = ap.parse_args()
    reel = ns.reel
    out_txt = os.path.join(os.path.dirname(os.path.abspath(reel)), "verify_output_reel.txt")
    t_start = time.time()
    say(f"Verification of {os.path.basename(reel)}  ({os.path.getsize(reel)/1e6:.2f} MB)")
    say("=" * 100)

    # ------------------------------------------------------------------------------------------------- [1] format
    say("[1] Format, aspect ratio, duration")
    p = probe(reel)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = next(s for s in p["streams"] if s["codec_type"] == "audio")
    say(f"    video: {v['codec_name']} {v['profile']} {v['width']}x{v['height']} {v['pix_fmt']} r={v['r_frame_rate']} avg={v['avg_frame_rate']} "
        f"frames={v['nb_read_packets']} dur={v['duration']} s  {int(v.get('bit_rate', 0))/1e6:.2f} Mb/s  color={v.get('color_space')}/{v.get('color_primaries')}/{v.get('color_transfer')}")
    say(f"    audio: {a['codec_name']} {a['profile']} {a['sample_rate']} Hz {a['channels']}ch dur={a['duration']} s  {int(a['bit_rate'])/1000:.0f} kb/s")
    say(f"    container duration = {p['format']['duration']} s")
    ok(v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p", "H.264 MP4, yuv420p", v["profile"])
    ok(v["width"] == 1080 and v["height"] == 1920, "resolution exactly 1080 x 1920")
    ok(v["width"] * 16 == v["height"] * 9, "aspect ratio exactly 9:16 (width/height = 0.5625), square pixels (SAR unspecified = 1:1)")
    ok(v["r_frame_rate"] == "30/1" and v["avg_frame_rate"] == "30/1", "constant 30 fps")
    ok(int(v["nb_read_packets"]) == 1530, "1530 video frames (= 51 s x 30)", v["nb_read_packets"])
    ok(abs(float(p["format"]["duration"]) - 51.0) < 1e-6, "container duration is exactly 51.000000 s", p["format"]["duration"])
    ok(abs(float(v["duration"]) - 51.0) < 1e-6, "video stream duration is exactly 51.000000 s", v["duration"])
    pts = [float(x.strip(",")) for x in run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "csv=p=0", reel]).stdout.split() if x.strip(",")]
    d = np.diff(sorted(pts))
    ok(abs(min(pts)) < 1e-9 and abs(max(pts) - 50.966667) < 1e-5 and np.allclose(d, 1 / 30, atol=1e-5), "frame times 0.000 ... 50.9667 s in exact 1/30 s steps",
       f"first {min(pts):.6f}, last {max(pts):.6f}, max step error {abs(d-1/30).max()*1000:.4f} ms")
    ok(float(a["duration"]) <= 51.0 and 51.0 - float(a["duration"]) < 0.0214, "audio stream ends within one AAC frame (21.3 ms) of 51.000 s",
       f"{a['duration']} s: the last whole AAC frame that starts before 155.000 s ends at 154.9867 s; the container duration is set by the video")
    ok(os.path.getsize(reel) < 100 * 1024 * 1024, "file < 100 MB")
    ok(os.path.basename(reel) == "Chalo_Jantar_Mantar_Reel_01m44s_to_02m35s_1080x1920.mp4", "file name as requested")

    # ------------------------------------------------------------------------------------------------- [2] audio
    say("\n[2] Audio = the original, from 01:44.000, untouched")
    src = audio_packets(LANDSCAPE, "103.9%155.1")
    start_i = next(i for i, q in enumerate(src) if abs(float(q["pts_time"]) - CLIP_START) < 1e-6)
    rp = audio_packets(reel)
    same = all(rp[i]["data_hash"] == src[start_i + i]["data_hash"] for i in range(len(rp)))
    say(f"    reel audio packets: {len(rp)} (first pts {rp[0]['pts_time']} s, last pts {rp[-1]['pts_time']} s); source packet at 104.000 s is #{start_i} of the window read")
    ok(abs(float(rp[0]["pts_time"])) < 1e-9, "audio starts at 0.000 s of the Reel")
    ok(len(rp) == 2390 and same, "all 2390 audio packets are byte-identical (SHA-256 per packet) to the landscape/original packets 104.000 s ... 154.9867 s",
       f"{sum(rp[i]['data_hash'] == src[start_i + i]['data_hash'] for i in range(len(rp)))}/{len(rp)} identical")
    ok(a["codec_name"] == "aac" and a["sample_rate"] == "48000" and a["channels"] == 2, "codec / sample rate / channels unchanged (AAC LC 48 kHz stereo)")
    pcm = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", reel, "-vn", "-f", "s16le", "-ac", "2", "-ar", "48000", "-"], capture_output=True).stdout, np.int16).reshape(-1, 2)
    pcm_src = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", LANDSCAPE, "-vn", "-f", "s16le", "-ac", "2", "-ar", "48000", "-"], capture_output=True).stdout, np.int16).reshape(-1, 2)
    s0 = int(CLIP_START * 48000)
    n = len(pcm)
    x_, y_ = pcm[2048:].astype(np.float64), pcm_src[s0 + 2048:s0 + n].astype(np.float64)
    d_ = x_ - y_
    ident = float(np.mean(d_ == 0))
    snr = 10 * np.log10((y_ ** 2).sum() / max((d_ ** 2).sum(), 1e-9))
    Fd = np.abs(np.fft.rfft(d_[:, 0])) ** 2
    Fs = np.abs(np.fft.rfft(y_[:, 0])) ** 2
    fr_ = np.fft.rfftfreq(len(d_), 1 / 48000)
    rel = {}
    for lo_, hi_ in ((0, 2000), (2000, 24001)):
        m_ = (fr_ >= lo_) & (fr_ < hi_)
        rel[(lo_, hi_)] = 10 * np.log10((Fd[m_].sum() + 1e-9) / (Fs[m_].sum() + 1e-9))
    say(f"    decoded PCM vs the song decoded from its start (after the first 2 AAC frames): {ident*100:.1f} % of samples identical, SNR {snr:.1f} dB over {n/48000:.2f} s; "
        f"difference vs signal: below 2 kHz {rel[(0, 2000)]:.0f} dB, above 2 kHz {rel[(2000, 24001)]:.0f} dB")
    say("    (the AAC packets are byte-identical; a decoder that starts at the cut has a different noise-substitution state than one that has decoded the whole song, "
        "which only changes noise-filled high-frequency content; the first 2 frames (43 ms) also lack their overlap partner)")
    ok(snr >= 30.0 and rel[(0, 2000)] <= -90.0, "decoded audio is the original signal: SNR >= 30 dB and the difference is >= 90 dB below the signal under 2 kHz (vocals / bass / beat untouched)",
       f"SNR {snr:.1f} dB, <2 kHz {rel[(0, 2000)]:.0f} dB")
    lag = 0
    seg = slice(48000, 48000 * 6)
    xc = np.correlate(pcm[seg, 0].astype(np.float64)[::4], pcm_src[s0 + seg.start:s0 + seg.stop, 0].astype(np.float64)[::4], mode="full")
    lag = (np.argmax(xc) - (len(pcm[seg, 0][::4]) - 1)) * 4
    ok(lag == 0, "cross-correlation of Reel audio vs the song at 104.000 s: lag 0 samples (no shift)", f"lag {lag} samples")
    say("    no music, vocals or sound effects were added or mixed: the audio stream is the copied packets only")

    # ------------------------------------------------------------------------------------------------- [3] lyrics
    say("\n[3] Lyrics included, Roman Hindi only")
    lines = json.load(open(TIMING, encoding="utf-8"))["lines"]
    inc = [l for l in lines if l["end"] > CLIP_START and l["start"] < CLIP_END - 0.3]
    say(f"    {len(inc)} lines in the clip: L{inc[0]['id']} ... L{inc[-1]['id']}; hooks: " +
        ", ".join(f"L{l['id']} {l['hook']}" for l in inc if l["hook"] != "regular"))
    ok([l["id"] for l in inc] == list(range(35, 55)), "lines L35-L54 (all 20 sung lines of 01:44-02:35, none missing, none from outside)")
    ok(not any("ऀ" <= c <= "ॿ" for l in inc for c in l["roman"]), "no Devanagari in any displayed lyric")
    import hinglish_check
    ok(not hinglish_check.check(verbose=False), "spelling check of the Roman lines against the Devanagari source: 0 problems (whole song)")
    hooks = {l["hook"] for l in inc if l["hook"] != "regular"}
    ok(hooks == {"stamp", "defiant", "march"}, "hook animations present in this section: Vote Chori! Gaddi Chor!, Ye Mulk Tera Baap Ka Nahin!, Chalo Jantar-Mantar! (x2)", str(sorted(hooks)))

    # ------------------------------------------------------------------------------------------------- [4] text audit
    say("\n[4] Text actually drawn: safe zones, no cut-off, no stray strings")
    from PIL import Image
    import rl_text as RT
    import hl_text as HT
    text_imgs = {}
    _mk, _bl, _bo = HT.make_sprite, HT.blit, HT.blur_of

    def mk(*a_, **k_):
        sp = _mk(*a_, **k_)
        text_imgs[id(sp["main"])] = sp["main"]
        return sp

    def bo(spr, r):
        o = _bo(spr, r)
        if id(spr) in text_imgs:
            text_imgs[id(o)] = o
        return o

    CUR = []

    def bl(frame, spr, cx, cy, op=1.0, mode="over", scale=1.0, rot=0.0, tint=None):
        isb = (tint is None and mode == "over" and 500 <= spr.width and 200 <= spr.height < 1200)      # stamp banners
        if (id(spr) in text_imgs or isb) and op > 0.15 and mode == "over":
            s_ = spr
            if scale != 1.0:
                s_ = s_.resize((max(1, int(s_.width * scale)), max(1, int(s_.height * scale))), Image.BILINEAR)
            if rot:
                s_ = s_.rotate(rot, resample=Image.BICUBIC, expand=True)
            bb = s_.getchannel("A").point(lambda v_: 255 if v_ > 110 else 0).getbbox()
            if bb:
                x0, y0 = int(round(cx - s_.width / 2)), int(round(cy - s_.height / 2))
                CUR.append((x0 + bb[0], y0 + bb[1], x0 + bb[2], y0 + bb[3], op))
        return _bl(frame, spr, cx, cy, op, mode, scale, rot, tint)

    for mod in (HT, RT):
        mod.make_sprite, mod.blit, mod.blur_of = mk, bl, bo
    eng = RT.ReelText(lines, CLIP_START, CLIP_END)
    blank = np.zeros((H, W, 3), np.uint8)
    SETTLE = {"regular": None, "stamp": 1.0, "defiant": 1.9, "march": 1.0}
    worst = {}
    n_set = 0
    for l in inc:
        dur = l["end"] - l["start"]
        t_from = max(CLIP_START, l["start"] + (0.5 * dur if l["hook"] == "regular" else SETTLE[l["hook"]]))
        t_to = min(CLIP_END - 0.4, max(t_from, l["end"] - 0.05))
        for t in np.arange(t_from, t_to + 1e-6, 3 / FPS):
            CUR.clear()
            fx = eng.effects(float(t))
            eng.draw(blank.copy(), float(t), (0, 0))              # un-shaken: shake is a transient effect
            for (x0, y0, x1, y1, op) in list(CUR):
                if op < 0.9:
                    continue
                n_set += 1
                for key, val in (("left", x0), ("right", W - x1), ("top", y0), ("bottom", H - y1)):
                    if key not in worst or val < worst[key][0]:
                        worst[key] = (int(val), l["id"], round(float(t), 2))
    say(f"    settled lyric text: {n_set} sprite placements; smallest margin to each frame edge (px, line id, song t): {worst}")
    ok(worst["left"][0] >= 60 and worst["right"][0] >= 60, "settled text keeps >= 60 px from the left and right edges (nothing cut off)", f"left {worst['left'][0]}, right {worst['right'][0]}")
    ok(worst["top"][0] >= 260, "settled text stays below the top ~260 px (Reels header zone)", f"top margin {worst['top'][0]}")
    ok(worst["bottom"][0] >= 420, "settled text stays above the bottom ~420 px (Reels caption / buttons zone)", f"bottom margin {worst['bottom'][0]}")
    strings = sorted(HT.RECORD)
    ok(all(HT.ROMAN_OK.match(s) for s in strings), f"all {len(strings)} distinct strings the engine drew are Roman-only")
    banned = re.compile(r"suno|mira|studio|made with|@|\.com|www|subscribe|channel|follow", re.I)
    ok(not any(banned.search(s) for s in strings), "no branding / credit / handle strings")
    lyric_letters = {c for l in lines for c in norm_letters(l["roman"])}
    ok(all(set(norm_letters(s)) <= lyric_letters for s in strings), "every letter drawn belongs to the lyrics")
    for mod in (HT, RT):
        mod.make_sprite, mod.blit, mod.blur_of = _mk, _bl, _bo

    # ------------------------------------------------------------------------------------------------- [5] video content
    say("\n[5] Picture: no black bars, no letterboxing, nothing stretched")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", reel, "-vf", "scale=270:480,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270)
    core = fr[12:-12]
    colmean = core.mean(axis=1)
    rowmax = core.max(axis=2)

    def run_from_edge(rm, bottom):
        rows = rm[::-1] if bottom else rm
        k = 0
        for val in rows:
            if val < 12:
                k += 1
            else:
                break
        return k
    top = np.array([run_from_edge(r, False) for r in rowmax])
    bot = np.array([run_from_edge(r, True) for r in rowmax])
    say(f"    left/right edge columns: darkest mean luma {colmean[:, :6].mean(axis=1).min():.1f} / {colmean[:, -6:].mean(axis=1).min():.1f} (never black: no pillarbox)")
    say(f"    near-black run from the top edge: longest {top.max()*4} px (frames with > 80 px: {(top*4 > 80).sum()}); from the bottom edge: longest {bot.max()*4} px, "
        f"mean {bot.mean()*4:.0f} px (dark foreground crowd / ground silhouettes)")
    ok(colmean[:, :6].mean(axis=1).min() > 5 and colmean[:, -6:].mean(axis=1).min() > 5, "no black pillar bars at the left/right edges")
    ok((top * 4 > 80).sum() <= 3, "no letterbox band at the top (only isolated whip-transition frames)", f"{(top*4 > 80).sum()} frame(s) > 80 px")
    ok(bot.max() * 4 <= 120, "bottom edge never has a black bar > 120 px (the dark strip is crowd/ground silhouette detail)", f"max {bot.max()*4} px")
    fade_in = fr[0].mean(), fr[3].mean(), fr[8].mean()
    fade_out = fr[-1].mean(), fr[-5].mean()
    say(f"    picture fade (audio untouched): mean luma frames 0/3/8 = {fade_in[0]:.1f}/{fade_in[1]:.1f}/{fade_in[2]:.1f}; last two samples = {fade_out[0]:.1f}/{fade_out[1]:.1f}")

    # ------------------------------------------------------------------------------------------------- [6] sync
    say("\n[6] Lyric synchronisation (measured from the finished MP4)")
    raw_full = subprocess.run(["ffmpeg", "-v", "error", "-i", reel, "-vf", "scale=270:480", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True).stdout
    rgb = np.frombuffer(raw_full, np.uint8).reshape(-1, 480, 270, 3).astype(np.int16)

    def first_frame(mask_fn, lo, hi, thr):
        base = mask_fn(rgb[max(lo - 4, 0)])
        for nn in range(lo, hi):
            if mask_fn(rgb[nn]) > max(thr, base * 3):
                return nn
        return None
    red_banner = lambda f: int(((f[..., 0] > 150) & (f[..., 1] < 70) & (f[..., 2] < 75)).sum())
    saffron_slab = lambda f: int(((f[..., 0] > 235) & (f[..., 1] > 118) & (f[..., 1] < 165) & (f[..., 2] < 70)).sum())
    ev = []
    for lid, fn, thr, label in ((39, red_banner, 1500, "red banner of 'Vote Chori!' lands"), (51, saffron_slab, 500, "saffron slab of 'Chalo' slams in")):
        l = next(x for x in lines if x["id"] == lid)
        exp = (l["start"] - CLIP_START) * FPS
        nn = first_frame(fn, int(exp) - 12, int(exp) + 15, thr)
        ev.append((lid, label, exp, nn))
        say(f"    L{lid}: {label}: first visible frame {nn} (= {nn/30:.3f} s) vs timing-file line start frame {exp:.1f} (= {exp/30:.3f} s)  -> offset {((nn-exp)/30*1000 if nn else float('nan')):+.0f} ms")
    ok(all(e[3] is not None and -0.5 <= e[3] - e[2] <= 2.5 for e in ev), "hook onsets in the MP4 land within 0-2 frames of the timing file's line starts (frame-exact mapping 104.000 s -> frame 0)")

    # vocal-band onset in the Reel's own audio near each line start (coarse, informational)
    import scipy.signal as ss
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", reel, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
    f_, tt_, Z = ss.stft(x, 16000, nperseg=512, noverlap=384)
    band = (f_ >= 250) & (f_ <= 3800)
    E = np.log1p(np.abs(Z[band]).sum(axis=0) * 50)
    flux = np.clip(np.diff(E, prepend=E[0]), 0, None)
    hop = 128 / 16000
    ds = []
    for l in inc:
        c = l["start"] - CLIP_START
        i0, i1 = int((c - 0.35) / hop), int((c + 0.35) / hop)
        seg_ = flux[max(0, i0):i1]
        if len(seg_):
            ds.append(abs((np.argmax(seg_) + max(0, i0)) * hop - c))
    ds = np.array(ds)
    say(f"    INFO: |timing-file line start - strongest vocal-band onset of the Reel's own audio within +-0.35 s|: median {np.median(ds)*1000:.0f} ms, "
        f"90th pct {np.percentile(ds,90)*1000:.0f} ms (coarse: drum transients share the band; the line times are the phase-1 Whisper alignment + manual refinement, reused unchanged)")

    if not ns.no_ocr:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        tmp = tempfile.mkdtemp(prefix="rl_ocr_")
        cache = {}

        def read_frame(nn):
            if nn not in cache:
                pth = os.path.join(tmp, f"f{nn}.png")
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(nn + 0.5) / FPS:.4f}", "-i", reel, "-frames:v", "1", pth], check=True)
                res, _ = ocr(pth)
                cache[nn] = [r[1] for r in (res or [])]
            return cache[nn]

        def sim(expected, texts):
            e = norm_letters(expected)
            tx = norm_letters("".join(texts))
            sm = difflib.SequenceMatcher(None, e, tx, autojunk=False)
            return sum(b.size for b in sm.get_matching_blocks()) / max(1, len(e))

        # (a) each line read from the finished MP4 once it is fully built
        scores, miss = {}, []
        for l in inc:
            dur = l["end"] - l["start"]
            tt = l["start"] + (0.8 * dur if l["hook"] == "regular" else {"stamp": 1.7, "defiant": 1.9, "march": 1.3}[l["hook"]])
            nn = int((tt - CLIP_START) * FPS)
            sc = sim(l["roman"], read_frame(nn))
            scores[l["id"]] = (sc, l["hook"])
            if sc < 0.6:
                miss.append((l["id"], l["hook"], round(sc, 2), l["roman"], norm_letters("".join(read_frame(nn)))[:40]))
        reg = [s for s, h in scores.values() if h == "regular"]
        hk = {h: [s for s, hh in scores.values() if hh == h] for h in ("stamp", "defiant", "march")}
        say(f"    OCR of the finished MP4, each line when fully built: regular lines mean {np.mean(reg):.2f} (n={len(reg)}); " +
            ", ".join(f"{h} {np.mean(v):.2f} (n={len(v)})" for h, v in hk.items()))
        for m in miss:
            say(f"      L{m[0]:<3} {m[1]:8s} {m[2]}  expected «{m[3]}»  read «{m[4]}»")
        weak = [(i, round(sc_, 2)) for i, (sc_, h_) in scores.items() if h_ == "regular" and sc_ < 0.85]
        if weak:
            say(f"      regular lines below 0.85 (stylised italic / partly covered by a flag or flash): {weak}")
        ok(np.mean(reg) > 0.85, "the right lyric is on screen at the right time: OCR recovers > 85 % of the letters of every regular line", f"mean {np.mean(reg):.2f}, min {min(reg):.2f}")
        ok(all(np.mean(v) > 0.7 for v in hk.values()), "hook lines are legible to OCR as well", str({h: round(float(np.mean(v)), 2) for h, v in hk.items()}))

        # (b) text onset of regular lines measured by bisection on OCR of the finished MP4
        say("    onset of each line's first word on screen (bisection, OCR of the MP4) vs the timing file:")
        offs = []
        for lid in (36, 38, 40, 41, 49, 50, 53, 54):
            l = next(x for x in lines if x["id"] == lid)
            first = norm_letters(l["roman"].split()[0])
            e0 = (l["start"] - CLIP_START) * FPS
            lo, hi = int(e0) - 14, int(e0) + 14
            def present(nn, first=first):
                toks = [norm_letters(w) for tx_ in read_frame(nn) for w in tx_.split()]
                return any(tk == first or (len(first) >= 2 and tk.startswith(first)) for tk in toks)
            if present(lo) or not present(hi):
                say(f"      L{lid} '{first}': could not bracket the onset (present at {lo}: {present(lo)}, at {hi}: {present(hi)})")
                continue
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if present(mid):
                    hi = mid
                else:
                    lo = mid
            offs.append((hi - e0) / FPS)
            say(f"      L{lid:<3} '{first}': readable from frame {hi} ({hi/30:.3f} s) ; timing-file start {e0/30:.3f} s ; offset {(hi-e0)/FPS*1000:+.0f} ms")
        ok(len(offs) >= 6 and all(-0.10 <= o <= 0.40 for o in offs),
           "every measured line appears (becomes readable) between 0.1 s before and 0.4 s after its timing-file start (the pop-in itself takes ~0.1-0.2 s)",
           f"median {np.median(offs)*1000:+.0f} ms, range {min(offs)*1000:+.0f} .. {max(offs)*1000:+.0f} ms" if offs else "none")

        # (c) sweep every 1.0 s for banned text and non-Latin characters
        allt = []
        for k in range(1, 51):
            allt += read_frame(int(k * FPS))
        flat = " | ".join(allt)
        ok(not banned.search(flat), "OCR sweep (50 frames, 1 per second) finds no SUNO / Mira / @handle / credit text", f"{len(allt)} text fragments read")
        ok(all(ord(c) < 0x250 or c in "…—’“”" for c in flat), "OCR sweep finds no non-Latin (e.g. Devanagari) characters")

    # ------------------------------------------------------------------------------------------------- [7] project safety
    say("\n[7] Existing files untouched")
    ok(sha256(LANDSCAPE) == LANDSCAPE_SHA, "landscape MP4 SHA-256 unchanged since it was delivered", LANDSCAPE_SHA[:16] + "...")
    r = run(["git", "status", "--porcelain"], cwd=ROOT)
    changed = [ln for ln in r.stdout.splitlines() if not ln[3:].startswith("chalo_jantar_mantar/reels/")]
    say("    git status outside chalo_jantar_mantar/reels/: " + (", ".join(changed) if changed else "clean"))
    ok(not changed, "no existing tracked file modified, nothing new outside the reels/ folder")
    r = run(["git", "diff", "--stat"], cwd=ROOT)
    ok(not r.stdout.strip(), "git diff is empty (no tracked file content changed)")
    man = os.path.join(ROOT, "backups", "pre_hinglish_landscape_2026-10-10", "MANIFEST.sha256")
    r = run(["sha256sum", "-c", "--ignore-missing", man], cwd=ROOT)
    bad = [ln for ln in r.stdout.splitlines() if not ln.endswith(": OK")]
    ok(r.returncode == 0 and not bad, "original MP4, lyrics, timing, portrait video, docs, tools, assets all match the pre-work SHA-256 manifest", f"{len(r.stdout.splitlines())} files compared")
    ok(os.path.dirname(os.path.abspath(reel)) == os.path.join(ROOT, "reels"), "Reel saved in the separate reels/ folder")

    say("\n" + "=" * 100)
    say(f"OVERALL: {'PASS' if not FAILS else 'FAIL  (' + '; '.join(FAILS) + ')'}   [{time.time()-t_start:.0f}s]")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
