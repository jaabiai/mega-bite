"""Final verification of Chalo_Jantar_Mantar_Lyric_Video.mp4.

usage: verify.py FINAL.mp4 ORIGINAL.mp4 LYRICS.txt TIMING.json
Checks: (1) streams/duration, (2) audio stream bit-identical to the original, (3) lyric text in the timing file is
byte-identical to the supplied lyrics (count/order/spelling), (4) every codepoint has a glyph in the fonts used,
(5) decoded video frames match a fresh render (PSNR), (6) the lyric visible on screen at the middle of every regular
line is the intended one (template match against all candidate lines)."""
import sys, os, re, json, subprocess, hashlib
import numpy as np
from PIL import Image

T = os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")
sys.path.insert(0, T + "tools")


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def probe(path):
    j = json.loads(sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))
    return j


def audio_md5(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"], capture_output=True, text=True, check=True).stdout
    return out.strip()


def decode_frame(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)


def main(final, orig, lyrics, timing):
    ok = True
    # ---- 1. streams ----
    pf, po = probe(final), probe(orig)
    vf = [s for s in pf["streams"] if s["codec_type"] == "video"][0]
    af = [s for s in pf["streams"] if s["codec_type"] == "audio"][0]
    ao = [s for s in po["streams"] if s["codec_type"] == "audio"][0]
    vo = [s for s in po["streams"] if s["codec_type"] == "video"][0]
    df, do = float(pf["format"]["duration"]), float(po["format"]["duration"])
    print(f"[1] video {vf['codec_name']} {vf['width']}x{vf['height']} @ {vf['r_frame_rate']} ({vf.get('nb_frames')} frames); audio {af['codec_name']} {af['sample_rate']} Hz {af['channels']}ch")
    print(f"    source video {vo['width']}x{vo['height']} @ {vo['r_frame_rate']}; duration final {df:.3f}s vs original {do:.3f}s (diff {abs(df-do)*1000:.1f} ms)")
    print(f"    video stream duration {float(vf['duration']):.3f}s, audio stream duration {float(af['duration']):.3f}s")
    ok &= abs(df - do) < 0.05 and abs(float(vf["duration"]) - float(af["duration"])) < 0.05
    ratio_f, ratio_o = vf["width"] / vf["height"], vo["width"] / vo["height"]
    print(f"    aspect ratio final {ratio_f:.4f} vs source {ratio_o:.4f}")
    ok &= abs(ratio_f - ratio_o) < 0.005
    # ---- 2. audio identity ----
    mf, mo = audio_md5(final), audio_md5(orig)
    print(f"[2] audio stream md5  final {mf}\n                      source {mo}   -> {'IDENTICAL' if mf == mo else 'DIFFERENT'}")
    ok &= mf == mo
    # ---- 3. lyric text integrity ----
    from lyrics import parse
    L = parse()
    d = json.load(open(timing, encoding="utf-8"))["lines"]
    same = len(L) == len(d) and all(a["text"] == b["text"] for a, b in zip(L, d))
    print(f"[3] lyric lines supplied {len(L)}, in timing file {len(d)}; text byte-identical & in order: {same}")
    ok &= same
    # starts strictly increasing, positive durations, inside the song
    mono = all(d[i]["start"] < d[i + 1]["start"] for i in range(len(d) - 1)) and all(l["end"] > l["start"] for l in d) and d[-1]["end"] <= do
    print(f"    timing monotonic / positive durations / within song: {mono}")
    ok &= mono
    # ---- 4. glyph coverage ----
    from fontTools.ttLib import TTFont
    fonts = {n: TTFont(T + "assets/" + n) for n in ("Hind-Bold.ttf", "RozhaOne-Regular.ttf", "Khand-Bold.ttf")}
    text = "".join(l["text"] for l in d) + "चलो जंतर-मंतर आवाज़ जनता की"
    cps = sorted({ord(c) for c in text if not c.isspace()})
    bad = {}
    for n, f in fonts.items():
        cmap = f.getBestCmap()
        miss = [hex(c) for c in cps if c not in cmap]
        bad[n] = miss
    print(f"[4] distinct codepoints used: {len(cps)}; missing glyphs per font: " + ", ".join(f"{n}:{len(m)}" for n, m in bad.items()))
    # Rozha/Khand only need the characters they actually render; report but only fail on Hind (all regular lines)
    ok &= len(bad["Hind-Bold.ttf"]) == 0
    from render import classify, Scene
    for n, key in (("RozhaOne-Regular.ttf", ("wake", "people")), ("Khand-Bold.ttf", ("march", "stamp", "defiant"))):
        cmap = fonts[n].getBestCmap()
        t = "".join(l["text"] for l in d if classify(l["text"]) in key)
        miss = sorted({c for c in t if not c.isspace() and ord(c) not in cmap})
        print(f"    {n}: characters it renders but lacks: {miss or 'none'}")
        ok &= not miss
    # ---- 5. fresh render vs decoded video ----
    sc = Scene(timing)
    ts = [2.0, 9.5, 28.5, 33.0, 60.0, 86.0, 114.5, 126.0, 150.0, 188.0, 210.0, 232.5, 246.5, 256.0, 261.0, 266.0]
    ps = []
    for t in ts:
        a = decode_frame(final, t).astype(np.float32)
        b = sc.render_frame(round(t * 30) / 30.0).astype(np.float32)
        mse = ((a - b) ** 2).mean()
        ps.append(10 * np.log10(255 ** 2 / max(mse, 1e-9)))
    print(f"[5] PSNR decoded-video vs fresh render at {len(ts)} times: min {min(ps):.1f} dB, mean {np.mean(ps):.1f} dB")
    ok &= min(ps) > 30
    # ---- 6. which lyric is on screen? ----
    reg = [(i, l) for i, l in enumerate(d) if classify(l["text"]) == "regular"]
    masks = {}
    for i, l in reg:
        card = sc.cards[l["id"]][0]
        a = np.asarray(card.split()[3]).astype(np.float32) / 255
        masks[l["id"]] = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((a.shape[1] // 2, a.shape[0] // 2), Image.BILINEAR)).astype(np.float32) / 255
    from scipy.signal import fftconvolve
    hits, miss_list = 0, []
    for i, l in reg:
        a0, b0 = sc.display_window(i)
        t = (a0 + b0) / 2 if (b0 - a0) > 1.0 else a0 + 0.5 * (b0 - a0)
        t = max(t, a0 + 0.45)
        fr = decode_frame(final, t)
        zone = fr[1130:1460].astype(np.float32)
        wm = ((zone.min(2) > 215)).astype(np.float32)
        wm = np.asarray(Image.fromarray((wm * 255).astype(np.uint8)).resize((540, 165), Image.BILINEAR)).astype(np.float32) / 255
        best, bid = -1, None
        for k, m in masks.items():
            if m.shape[0] > wm.shape[0] or m.shape[1] > wm.shape[1]:
                continue
            c = fftconvolve(wm, m[::-1, ::-1], mode="valid").max()
            sc_ = c / np.sqrt((m ** 2).sum() * (wm ** 2).sum() + 1e-9)
            if sc_ > best:
                best, bid = sc_, k
        same_text = bid is not None and next(x for x in d if x["id"] == bid)["text"] == l["text"]
        if bid == l["id"] or same_text:   # identical lyric text (repeated lines) is indistinguishable by design
            hits += 1
        else:
            miss_list.append((l["id"], bid, round(float(best), 2)))
    print(f"[6] on-screen lyric at mid-line matches the intended line for {hits}/{len(reg)} regular lines; mismatches: {miss_list[:10]}")
    ok &= hits == len(reg)
    print("\nOVERALL:", "PASS" if ok else "CHECK FAILURES ABOVE")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(*sys.argv[1:5]) else 1)
