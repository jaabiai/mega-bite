"""Verification report for the Hinglish landscape lyric video (run AFTER the final MP4 exists).

  python verify_landscape.py FINAL.mp4 ORIGINAL.mp4 [--chunks DIR] [--no-ocr]

Every check prints PASS/FAIL/INFO; the process exit code is 1 if any check FAILs. Output is also written to
output_hinglish_landscape/verify_output_hinglish_landscape.txt (next to the final video).
"""
import glob, hashlib, json, os, re, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUTDIR = os.path.join(ROOT, "output_hinglish_landscape")
FAILS = []
LOG = []


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


def probe(path):
    r = run(["ffprobe", "-v", "error", "-count_packets", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(r.stdout)


def audio_md5(path):
    r = run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"])
    return r.stdout.strip().replace("MD5=", "")


def pcm_md5(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-f", "s16le", "-"], capture_output=True)
    return hashlib.md5(r.stdout).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm_letters(s):
    return re.sub(r"[^a-z]", "", s.lower())


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("final")
    ap.add_argument("original")
    ap.add_argument("--chunks", default=None)
    ap.add_argument("--no-ocr", action="store_true")
    ns = ap.parse_args()
    final, original, chunks, use_ocr = ns.final, ns.original, ns.chunks, not ns.no_ocr
    t_start = time.time()
    say(f"Verification of {os.path.basename(final)}  ({os.path.getsize(final)/1e6:.1f} MB)")
    say("=" * 100)

    # ------------------------------------------------------------------ [1] stream properties
    say("[1] Video format")
    pf, po = probe(final), probe(original)
    v = next(s for s in pf["streams"] if s["codec_type"] == "video")
    a = next(s for s in pf["streams"] if s["codec_type"] == "audio")
    ov = next(s for s in po["streams"] if s["codec_type"] == "video")
    oa = next(s for s in po["streams"] if s["codec_type"] == "audio")
    say(f"    video: {v['codec_name']} {v['profile']} {v['width']}x{v['height']} {v['pix_fmt']} SAR {v.get('sample_aspect_ratio')} DAR {v.get('display_aspect_ratio')} "
        f"r={v['r_frame_rate']} avg={v['avg_frame_rate']} frames={v.get('nb_read_packets')} dur={v['duration']}s bitrate={int(v.get('bit_rate', 0))/1e6:.2f} Mb/s")
    say(f"    audio: {a['codec_name']} {a['sample_rate']} Hz {a['channels']}ch dur={a['duration']}s")
    say(f"    original: video {ov['width']}x{ov['height']} {ov['r_frame_rate']} fps; audio {oa['codec_name']} {oa['sample_rate']} Hz {oa['channels']}ch dur={oa['duration']}s; "
        f"container {po['format']['duration']}s")
    ok(v["width"] == 1920 and v["height"] == 1080, "resolution is exactly 1920x1080")
    ok(abs(v["width"] / v["height"] - 16 / 9) < 1e-9 and v.get("sample_aspect_ratio") in ("1:1", None), "aspect ratio 16:9 with square pixels")
    ok(v["r_frame_rate"] == "30/1" and v["avg_frame_rate"] == "30/1", "constant 30 fps")
    ok(int(v["nb_read_packets"]) == round(float(oa["duration"]) * 30), "frame count == duration x 30", f"{v['nb_read_packets']} frames")
    ok(abs(float(pf["format"]["duration"]) - float(po["format"]["duration"])) < 0.02, "container duration equals original",
       f"{pf['format']['duration']} vs {po['format']['duration']}")
    ok(abs(float(v["duration"]) - float(a["duration"])) < 0.05, "video and audio streams have equal length")
    ok(os.path.getsize(final) < 100 * 1024 * 1024, "file < 100 MB (GitHub per-file limit)")
    ok(os.path.basename(final) == "Chalo_Jantar_Mantar_Hinglish_Landscape_1080p.mp4", "file name as requested")

    # ------------------------------------------------------------------ [2] audio
    say("\n[2] Audio unchanged")
    m_new, m_old = audio_md5(final), audio_md5(original)
    say(f"    audio-stream md5 final={m_new}  original={m_old}")
    ok(m_new == m_old, "audio stream is bit-identical to the original (stream copy)")
    p_new, p_old = pcm_md5(final), pcm_md5(original)
    ok(p_new == p_old, "decoded PCM identical", p_new)
    ok(a["codec_name"] == oa["codec_name"] and a["bit_rate"] == oa["bit_rate"], "same codec/bitrate", f"{a['codec_name']} {a['bit_rate']}")

    # ------------------------------------------------------------------ [3] lyric integrity & timing
    say("\n[3] Lyrics, order and timing")
    old = json.load(open(os.path.join(ROOT, "lyric_timing.json"), encoding="utf-8"))["lines"]
    new = json.load(open(os.path.join(OUTDIR, "lyric_timing_hinglish.json"), encoding="utf-8"))["lines"]
    ok(len(old) == len(new) == 95, "95 lyric lines in both timing files", f"{len(old)} / {len(new)}")
    ok(all(o["id"] == n["id"] and o["start"] == n["start"] and o["end"] == n["end"] and o["text"] == n["source_text"] for o, n in zip(old, new)),
       "ids, order, start/end times and Devanagari source text identical to the verified phase-1 timing file")
    raw = [l.strip() for l in open(os.path.join(ROOT, "lyrics.txt"), encoding="utf-8").read().split("\n")]
    body = raw[raw.index(next(l for l in raw if l.startswith("[")) ):]
    lyric_lines = [l for l in body if l and not l.startswith("[")]
    ok(lyric_lines == [o["text"] for o in old], "supplied lyrics.txt == timing source text (every line, in order, none added/dropped)", f"{len(lyric_lines)} lines")
    mono = all(new[i]["end"] > new[i]["start"] and (i == 0 or new[i]["start"] >= new[i - 1]["end"] - 1e-6) for i in range(len(new)))
    ok(mono and new[-1]["end"] <= 267.2, "timing monotonic, positive durations, inside the song")

    # ------------------------------------------------------------------ [4] hinglish
    say("\n[4] Roman Hindi")
    import hinglish_check
    probs = hinglish_check.check(verbose=False)
    ok(not probs, "word-by-word consonant-skeleton check Devanagari->Roman: 0 problems", f"{len(probs)} problems")
    alltext = "".join(l["roman"] for l in new) + open(os.path.join(OUTDIR, "lyrics_hinglish.txt"), encoding="utf-8").read() + \
        open(os.path.join(OUTDIR, "lyrics_hinglish.srt"), encoding="utf-8").read()
    ok(not any("ऀ" <= c <= "ॿ" for c in alltext), "no Devanagari characters in any Roman lyric output (txt/srt/json roman field)")
    ok(all(re.fullmatch(r"[A-Za-z …,!?\-]+", l["roman"]) for l in new), "every displayed lyric uses only Latin letters + , ! ? … -")

    # ------------------------------------------------------------------ [5] drawn-text audit + safe area
    say("\n[5] Text actually drawn by the compositor")
    import hl_sprites  # noqa: F401  (puts the project's tools/ on sys.path for art.py)
    import hl_text
    from PIL import Image
    from hl_common import W, H, FPS
    # instrument the compositor: remember every text sprite and record where each one is blitted (bbox of its visible glyph pixels)
    text_imgs = {}
    _mk, _bl, _bo = hl_text.make_sprite, hl_text.blit, hl_text.blur_of

    def mk(*a_, **k_):
        sp = _mk(*a_, **k_)
        text_imgs[id(sp["main"])] = sp["main"]
        return sp

    def bo(spr, r):
        out = _bo(spr, r)
        if id(spr) in text_imgs:
            text_imgs[id(out)] = out
        return out

    CUR = []

    def bl(frame, spr, cx, cy, op=1.0, mode="over", scale=1.0, rot=0.0, tint=None):
        if id(spr) in text_imgs and op > 0.15 and mode == "over":
            s_ = spr
            if scale != 1.0:
                s_ = s_.resize((max(1, int(s_.width * scale)), max(1, int(s_.height * scale))), Image.BILINEAR)
            if rot:
                s_ = s_.rotate(rot, resample=Image.BICUBIC, expand=True)
            bb = s_.getchannel("A").point(lambda v: 255 if v > 110 else 0).getbbox()
            if bb:
                x0, y0 = int(round(cx - s_.width / 2)), int(round(cy - s_.height / 2))
                CUR.append((x0 + bb[0], y0 + bb[1], x0 + bb[2], y0 + bb[3], op))
        return _bl(frame, spr, cx, cy, op, mode, scale, rot, tint)

    hl_text.make_sprite, hl_text.blit, hl_text.blur_of = mk, bl, bo
    eng = hl_text.TextEngine(new)
    blank = np.zeros((H, W, 3), np.uint8)

    def boxes_at(t):
        CUR.clear()
        fx = eng.effects(t)
        eng.draw(blank.copy(), t, fx["shake"])
        return list(CUR)

    # (a) settled state: once a line is fully built (regular: from 50 % of its sung span; hooks: after the build-up, >= 1.2 s) until it ends
    worst = {}
    n_set = 0
    for l in new:
        dur = l["end"] - l["start"]
        t_from = l["start"] + (max(1.2, 0.5 * dur) if l["hook"] != "regular" else 0.5 * dur)
        t_to = max(t_from, l["end"])
        for t in np.arange(t_from, t_to + 1e-6, 3 / FPS):
            for (x0, y0, x1, y1, op) in boxes_at(float(t)):
                if op < 0.9:
                    continue
                n_set += 1
                for key, val in (("left", x0), ("right", W - x1), ("top", y0), ("bottom", H - y1)):
                    if key not in worst or val < worst[key][0]:
                        worst[key] = (int(val), l["id"], round(float(t), 2))
    say(f"    settled lyric text: {n_set} sprite placements checked; smallest margin to the frame edge in px (value, line id, t): {worst}")
    ok(min(v[0] for v in worst.values()) >= 54, "all settled lyric text sits inside the 5 % action-safe area (margin >= 54 px)", str(worst))
    # (b) whole timeline, every 3rd frame: how often does a (mostly opaque) glyph box poke outside the frame while a hook animates in/out?
    out_frames, n_frames = [], 0
    for n in range(0, 8016, 3):
        t = n / FPS
        n_frames += 1
        if any(op >= 0.5 and (x0 < 0 or y0 < 0 or x1 > W or y1 > H) for (x0, y0, x1, y1, op) in boxes_at(t)):
            out_frames.append(round(t, 2))
    say(f"    all {n_frames} sampled frames: {len(out_frames)} show a text box crossing the frame edge (hook words sliding in/out): "
        + (", ".join(f"{x}s" for x in out_frames[:20]) + (" ..." if len(out_frames) > 20 else "") if out_frames else "none"))
    hl_text.make_sprite, hl_text.blit, hl_text.blur_of = _mk, _bl, _bo
    strings = sorted(hl_text.RECORD)
    banned = re.compile(r"suno|mira|studio|made with|@|\.com|www|subscribe|channel", re.I)
    ok(all(hl_text.ROMAN_OK.match(s) for s in strings), f"all {len(strings)} distinct strings drawn are Roman-only", "")
    ok(not any(banned.search(s) for s in strings), "no branding / credit strings among everything drawn")
    drawn_words = {norm_letters(w) for s in strings for w in re.split(r"[\s\-]+", s) if norm_letters(w)}
    lyric_words = {norm_letters(w) for l in new for w in re.split(r"[\s\-]+", l["roman"]) if norm_letters(w)} | {"chalo", "jantar", "mantar", "awaaz", "janta", "ki"}
    lyric_letters = {c for w in lyric_words for c in w}
    extra = sorted(w for w in drawn_words if (w not in lyric_words if len(w) > 1 else w not in lyric_letters))
    singles = sorted(w for w in drawn_words if len(w) == 1)
    ok(not extra, "every drawn word comes from the lyrics (or the song title); single letters are per-letter hook animations", f"extra: {extra}; {len(singles)} single-letter sprites")
    say("    distinct strings drawn: " + "; ".join(strings[:12]) + " ...")

    # background contains no text: it never uses ImageFont / text drawing / the original video
    bg_src = {f: open(os.path.join(HERE, f), encoding="utf-8").read() for f in ("hl_scenes.py", "hl_sprites.py", "hl_post.py", "hl_common.py")}
    leaks = [f for f, s in bg_src.items() if re.search(r"ImageFont|ImageDraw\.Draw\(.*\)\.text|\.text\(|VideoCapture|original\.mp4|\.mp4", s)]
    ok(not leaks, "background modules contain no text-drawing calls and never read the original video frames", f"{leaks}")

    # ------------------------------------------------------------------ [6] OCR on the final video
    if use_ocr:
        say("\n[6] OCR on decoded frames of the FINAL MP4 (independent check of what a viewer sees)")
        from rapidocr_onnxruntime import RapidOCR
        import tempfile
        from PIL import Image
        ocr = RapidOCR()
        tmp = tempfile.mkdtemp(prefix="hl_ocr_")

        def grab(t, name):
            p = os.path.join(tmp, name + ".png")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", final, "-frames:v", "1", p], check=True)
            return p

        def read(p):
            res, _ = ocr(p)
            return [r[1] for r in (res or [])]

        # (a) sweep every 2 s for banned strings / non-Latin text
        seen_all = []
        for k, t in enumerate(np.arange(1.0, 266.5, 2.0)):
            seen_all += read(grab(float(t), f"sw{k}"))
        flat = " | ".join(seen_all)
        ok(not banned.search(flat), f"OCR sweep of {len(np.arange(1.0, 266.5, 2.0))} frames found no SUNO / MIRA / studio / @handle / credit text", f"{len(seen_all)} text fragments read")
        ok(all(ord(c) < 0x250 or c in "…—’“”" for c in flat), "OCR sweep found no non-Latin (e.g. Devanagari) characters")
        # (b) per-line OCR: at the moment the line is fully formed
        miss, scores = [], {}
        for l in new:
            hook = l["hook"] != "regular"
            tt = l["start"] + (min(1.6, 0.7 * (l["end"] - l["start"])) if hook else 0.8 * (l["end"] - l["start"]))
            exp = norm_letters(l["roman"])
            txt = norm_letters("".join(read(grab(float(tt), f"l{l['id']}"))))
            # fraction of the expected letters found in order (longest common subsequence ratio via difflib)
            import difflib
            sm = difflib.SequenceMatcher(None, exp, txt, autojunk=False)
            score = sum(b.size for b in sm.get_matching_blocks()) / max(1, len(exp))
            scores[l["id"]] = (score, l["hook"])
            if score < 0.6:
                miss.append((l["id"], l["hook"], round(score, 2), l["roman"], txt[:40]))
        by_style = {}
        for i, (s, h) in scores.items():
            by_style.setdefault(h, []).append(s)
        say("    OCR letter-match per style (mean): " + ", ".join(f"{h}={np.mean(v):.2f} (n={len(v)})" for h, v in sorted(by_style.items())))
        say(f"    lines with OCR match < 0.6: {len(miss)} (stylised display fonts / animation in flight are expected to read poorly):")
        for m in miss:
            say(f"      L{m[0]:<3} {m[1]:8s} score {m[2]}  expected «{m[3]}»  read «{m[4]}»")
        regs = [s for s, h in scores.values() if h == "regular"]
        ok(np.mean(regs) > 0.8, "regular lyric lines are legible: OCR recovers > 80% of the Roman letters on average", f"mean {np.mean(regs):.2f}")
        ok(np.mean([s for s, _ in scores.values()]) > 0.7, "all lines (incl. hooks) OCR mean > 70%", f"mean {np.mean([s for s, _ in scores.values()]):.2f}")

    # ------------------------------------------------------------------ [7] sync sanity vs. audio
    say("\n[7] Lyric sync vs. the audio (signal-level sanity check of the phase-1 timing)")
    import scipy.signal as ss
    raw_pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", original, "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw_pcm, np.float32)
    f, tt_, Z = ss.stft(x, 16000, nperseg=512, noverlap=384)
    band = (f >= 250) & (f <= 3800)
    E = np.log1p(np.abs(Z[band]).sum(axis=0) * 50)
    flux = np.clip(np.diff(E, prepend=E[0]), 0, None)
    hop = 128 / 16000
    ds = []
    for l in new:
        i0 = int((l["start"] - 0.35) / hop); i1 = int((l["start"] + 0.35) / hop)
        seg = flux[max(0, i0):i1]
        ds.append(abs((np.argmax(seg) + max(0, i0)) * hop - l["start"]))
    ds = np.array(ds)
    say(f"    |line start - strongest vocal-band onset within +-0.35 s|: median {np.median(ds)*1000:.0f} ms, 90th pct {np.percentile(ds,90)*1000:.0f} ms, "
        f"{(ds<=0.15).mean()*100:.0f}% of lines within 150 ms")
    say("    (INFO only: drum/beat transients inside the same band make this a coarse, noisy check; the line times themselves come from the phase-1 Whisper "
        "forced alignment + manual spectrogram refinement, reused unchanged)")
    say("    note: word-by-word reveals inside a line are spread over the line's sung span in proportion to syllable counts (approximate, not word-level aligned).")

    # ------------------------------------------------------------------ [8] hooks
    say("\n[8] Special hook animations: where they appear in the song")
    names = {"wake": "Deshwasiyo Jaago!", "march": "Chalo Jantar-Mantar!", "stamp": "Vote Chori! Gaddi Chor!", "defiant": "Ye Mulk Tera Baap Ka Nahin!", "people": "Ye Janta Ka Hindustan Hai!"}
    for h, nm in names.items():
        rows = [l for l in new if l["hook"] == h]
        say(f"    {nm:32s} style '{h}': " + ", ".join(f"L{l['id']} {l['start']:.1f}-{l['end']:.1f}s" for l in rows))
    ok(all(any(l["hook"] == h for l in new) for h in names), "all five hook types are present at their own song positions")
    ok(len({tuple(sorted(l["id"] for l in new if l["hook"] == h)) for h in names}) == 5, "each hook has its own set of lines (never shown all together)")

    # ------------------------------------------------------------------ [9] encode fidelity
    if chunks:
        say("\n[9] Final encode vs. near-lossless render")
        r = run(["ffmpeg", "-v", "info", "-nostats", "-f", "concat", "-safe", "0", "-i", os.path.join(chunks, "concat.txt"), "-i", final,
                 "-filter_complex", "[0:v][1:v]psnr=stats_file=/dev/null", "-f", "null", "-"], )
        out = r.stderr + r.stdout
        mm = re.search(r"average:([\d.]+)", out)
        say("    " + (mm and f"PSNR (final vs near-lossless chunks) average {mm.group(1)} dB" or out[-300:]))
        ok(bool(mm) and float(mm.group(1)) > 38.0, "final encode keeps > 38 dB PSNR vs the near-lossless render")

    # ------------------------------------------------------------------ [10] originals untouched
    say("\n[10] Existing files untouched")
    man = os.path.join(ROOT, "backups", "pre_hinglish_landscape_2026-10-10", "MANIFEST.sha256")
    r = run(["sha256sum", "-c", "--ignore-missing", man], cwd=ROOT)
    bad = [l for l in r.stdout.splitlines() if not l.endswith(": OK")]
    say(f"    manifest check: {len(r.stdout.splitlines())} files compared, {len(bad)} differences")
    ok(r.returncode == 0 and not bad, "every pre-existing project file matches the snapshot taken before any change")
    ok(sha256(original) == "d039d759dc69689afbee9c41399a1a9b830a5db321199ca06d6d52c58dd94401", "original uploaded MP4 sha256 unchanged")
    ok(sha256(os.path.join(ROOT, "Chalo_Jantar_Mantar_Lyric_Video.mp4")) == "93e8b527617130db8f24260023cf6ef1f686fa6e1ea1b55516ae58f060f4f8da",
       "phase-1 portrait video unchanged")

    say("\n" + "=" * 100)
    say(f"OVERALL: {'PASS' if not FAILS else 'FAIL  (' + '; '.join(FAILS) + ')'}   [{time.time()-t_start:.0f}s]")
    with open(os.path.join(OUTDIR, "verify_output_hinglish_landscape.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
