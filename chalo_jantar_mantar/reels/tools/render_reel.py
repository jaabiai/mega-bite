"""Parallel renderer / encoder for the vertical Reel.

  python render_reel.py render [--workers 4] [--chunk 90] [--only 3,4]     # frames -> near-lossless chunk_XXXX.mp4 in RL_WORK/chunks
  python render_reel.py encode OUT.mp4                                     # concat chunks, x264, ORIGINAL audio packets stream-copied

Environment: RL_WORK (chunk dir), RL_SOURCE_MP4 (the completed landscape MP4: audio source, read-only), RL_TIMING.
A chunk is only (re)rendered when its file is missing.

Audio: the AAC packets of the landscape MP4 are copied untouched from 104.000 s (an exact AAC frame boundary: 4875 x 1024 samples) for 50.98 s.
AAC frames are 21.333 ms long, so the last whole frame that starts before 155.000 s ends at 154.9867 s; the container duration is set by the
video (1530 frames = exactly 51.000 s).  Nothing is re-encoded, faded or mixed.
"""
import rl_common  # noqa: F401  (must be first)
import argparse
import os
import subprocess
import sys
import time
import multiprocessing as mp

from rl_common import FPS, NFRAMES, CLIP_START
from hl_common import W, H
import rl_render as R

_R = None


def chunk_path(ci):
    return os.path.join(R.WORK, "chunks", f"chunk_{ci:04d}.mp4")


def _init():
    global _R
    _R = R.Reel()


def _render_chunk(args):
    ci, a, b = args
    path = chunk_path(ci)
    tmp = path + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-g", "30", "-keyint_min", "30",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-an", "-f", "mp4", tmp]
    t0 = time.time()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(a, b):
        p.stdin.write(_R.render_frame(n).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on chunk {ci}")
    os.replace(tmp, path)
    return ci, b - a, time.time() - t0


def cmd_render(a):
    os.makedirs(os.path.join(R.WORK, "chunks"), exist_ok=True)
    nch = (NFRAMES + a.chunk - 1) // a.chunk
    only = {int(x) for x in a.only.split(",")} if a.only else None
    jobs = [(ci, ci * a.chunk, min(NFRAMES, (ci + 1) * a.chunk)) for ci in range(nch)
            if (only is None or ci in only) and not os.path.exists(chunk_path(ci))]
    print(f"{len(jobs)} chunk(s) to render of {nch} ({NFRAMES} frames) on {a.workers} workers", flush=True)
    t0 = time.time()
    done = 0
    with mp.get_context("fork").Pool(a.workers, initializer=_init) as pool:
        for ci, n, dt in pool.imap_unordered(_render_chunk, jobs):
            done += 1
            el = time.time() - t0
            print(f"chunk {ci:3d} done ({n} frames, {dt:6.1f}s)  {done}/{len(jobs)}  elapsed {el/60:5.1f} min  eta {el/done*(len(jobs)-done)/60:5.1f} min", flush=True)


def cmd_encode(a):
    nch = (NFRAMES + a.chunk - 1) // a.chunk
    missing = [ci for ci in range(nch) if not os.path.exists(chunk_path(ci))]
    if missing:
        sys.exit(f"missing chunks: {missing}")
    out = os.path.abspath(a.out)
    if os.path.exists(out):
        sys.exit(f"refusing to overwrite {out}")
    lst = os.path.join(R.WORK, "chunks", "concat.txt")
    with open(lst, "w") as f:
        for ci in range(nch):
            f.write(f"file '{chunk_path(ci)}'\n")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-stats", "-f", "concat", "-safe", "0", "-i", lst,
           "-ss", f"{CLIP_START:.3f}", "-t", "50.98", "-i", R.SOURCE,
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-maxrate", "14M", "-bufsize", "28M",
           "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-g", "60", "-keyint_min", "30", "-bf", "3", "-r", str(FPS),
           "-x264-params", "aq-mode=3:aq-strength=0.9:deblock=-1,-1:psy-rd=1.0,0.10:ref=5",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "copy", "-copypriorss:a", "0", "-movflags", "+faststart", "-metadata", "title=Chalo Jantar Mantar - Reel (01:44 - 02:35)", out]
    subprocess.check_call(cmd)
    print(out, os.path.getsize(out), "bytes")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--chunk", type=int, default=90)
    r.add_argument("--only", default="")
    e = sub.add_parser("encode")
    e.add_argument("out")
    e.add_argument("--chunk", type=int, default=90)
    e.add_argument("--crf", type=int, default=16)
    a = ap.parse_args()
    {"render": cmd_render, "encode": cmd_encode}[a.cmd](a)


if __name__ == "__main__":
    main()
