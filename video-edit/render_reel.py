#!/usr/bin/env python3
"""Render driver for the 9:16 Reels / Shorts cut.

  python render_reel.py plan                     -> print the reel plan (clip timings)
  python render_reel.py sheet name 1 5 20 ...    -> contact sheet of reel-time stills
  python render_reel.py full [--workers 4]       -> $MB_WORK/render/reel_video.mp4 (silent)
  python render_reel.py audio                    -> $MB_WORK/render/reel_voice.wav (cut from the cleaned narration)
  python render_reel.py mux <out.mp4>            -> final reel with audio
"""
import math
import multiprocessing as mp
import os
import subprocess
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mbedit.common import WORK, FPS   # noqa: E402
from mbedit.reel import RW, RH       # noqa: E402

OUT = os.path.join(WORK, "render")


def _setup():
    import edl_reel
    from mbedit.scenes import Ctx
    return edl_reel.build(), Ctx(), edl_reel


def nframes():
    import edl_reel
    return int(math.ceil(edl_reel.TOTAL * FPS))


def encoder(path, crf=17, preset="medium"):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-color_range", "tv", "-x264-params", "keyint=60:min-keyint=60:scenecut=0",
           "-threads", "1", "-movflags", "+faststart", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def plan():
    import edl_reel
    for c in edl_reel.PLAN:
        print(f"{c['k']:2d} {c['kind']:6s} {c['r0']:6.2f}-{c['r1']:6.2f}  ({c['r1']-c['r0']:.2f}s)")
    print(f"audio spans kept: {edl_reel.audio_cuts()}  (removed {edl_reel.CUT_A}-{edl_reel.CUT_B} s, one edit inside silence)  presets {list(edl_reel.VOICES)}")
    print(f"speech {edl_reel.SPEECH_END:.2f}s + end card {edl_reel.END_CARD}s = {edl_reel.TOTAL:.2f}s  ({nframes()} frames)")


def sheet(name, times, cols=4, w=360):
    tl, ctx, _ = _setup()
    tiles = []
    for t in times:
        f = tl.frame(ctx, int(round(float(t) * FPS)))
        s = cv2.resize(f, (w, int(w * RH / RW)), interpolation=cv2.INTER_AREA)
        cv2.putText(s, f"{float(t):.2f}s", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
        tiles.append(s)
    ctx.close()
    rows = []
    for k in range(0, len(tiles), cols):
        r = tiles[k:k + cols]
        while len(r) < cols:
            r.append(np.zeros_like(tiles[0]))
        rows.append(np.concatenate(r, 1))
    out = os.path.join(WORK, "preview", name + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cv2.imwrite(out, cv2.cvtColor(np.concatenate(rows, 0), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(out)


def render_range(a, b, path):
    tl, ctx, _ = _setup()
    enc = encoder(path)
    t0 = time.time()
    for i in range(a, b):
        enc.stdin.write(tl.frame(ctx, i).tobytes())
        if (i - a) % 100 == 0:
            print(f"[{a}-{b}] {i-a}/{b-a}  {(i-a+1)/max(time.time()-t0,1e-6):.2f} fps", flush=True)
    enc.stdin.close()
    enc.wait()
    ctx.close()


def full(workers=4):
    os.makedirs(OUT, exist_ok=True)
    n = nframes()
    per = ((n + workers - 1) // workers + 59) // 60 * 60
    jobs = [(k * per, min((k + 1) * per, n), os.path.join(OUT, f"reel_chunk_{k}.mp4")) for k in range(workers) if k * per < n]
    procs = [mp.Process(target=render_range, args=j) for j in jobs]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    lst = os.path.join(OUT, "reel_chunks.txt")
    open(lst, "w").write("".join(f"file '{j[2]}'\n" for j in jobs))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(OUT, "reel_video.mp4")], check=True)
    print("done ->", os.path.join(OUT, "reel_video.mp4"))




def audio(voice="loud"):
    """Original narration (source 0-60 s) with ONE invisible edit - the repeated 'subscribe' sentence is removed at two room-tone
    silences - then a plain make-up gain (edl_reel.VOICES) and a peak limiter. No EQ / denoise / compression: speech and background
    rise together, so nothing sounds dirtier, only louder."""
    import edl_reel
    v = edl_reel.VOICES[voice]
    src = os.path.join(WORK, "work", "main.mp4")
    cuts = edl_reel.audio_cuts()
    parts, labels = [], []
    for k, (a, b) in enumerate(cuts):
        d = b - a
        fin = "afade=t=in:d=0.008," if a > 0 else ""            # a take that starts at 0.0 is left sample-exact
        fout = (f"afade=t=out:st={d-0.008:.4f}:d=0.008" if k < len(cuts) - 1 else f"afade=t=out:st={d-0.05:.4f}:d=0.05")
        parts.append(f"[0:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS,{fin}{fout}[a{k}]")
        labels.append(f"[a{k}]")
    limit = f"alimiter=limit={v['ceiling']}:attack=5:release=60:level=disabled:latency=1"     # ceiling leaves room for the AAC encode
    chain = f"volume={v['gain']}dB," + ("asoftclip=type=tanh:threshold=0.9," if v["softclip"] else "") + limit
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(cuts)}:v=0:a=1,{chain},apad=whole_dur={edl_reel.TOTAL:.3f}[o]"
    out = os.path.join(OUT, f"reel_voice_{voice}.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[o]", "-t", f"{edl_reel.TOTAL:.3f}",
                    "-ar", "48000", "-c:a", "pcm_s16le", out], check=True)
    print(f"audio -> {out}  (+{v['gain']} dB, softclip={v['softclip']})")


def mux(out, voice="loud"):
    import edl_reel
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(OUT, "reel_video.mp4"), "-i", os.path.join(OUT, f"reel_voice_{voice}.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
                    "-t", f"{edl_reel.TOTAL:.3f}", "-movflags", "+faststart", out], check=True)
    print("final ->", out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        plan()
    elif cmd == "sheet":
        sheet(sys.argv[2], [float(x) for x in sys.argv[3:]])
    elif cmd == "full":
        full(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4)
    elif cmd == "audio":
        audio(sys.argv[2] if len(sys.argv) > 2 else "loud")
    elif cmd == "mux":
        mux(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "loud")
