"""Parallel renderer / encoder for the Hinglish landscape lyric video.

  python render_video_landscape.py render  [--workers 4] [--chunk 240] [--only 3,4]   # frames -> chunk_XXXX.mp4 (near-lossless)
  python render_video_landscape.py encode  OUT.mp4 [--kbps 2640]                      # concat chunks, two-pass x264, ORIGINAL audio stream-copied

Environment: HL_WORK (chunk dir, default ../work_hl), HL_SOURCE_MP4 (original MP4: audio source), HL_TIMING (timing json).
Chunks are independent and resumable: a chunk is only (re)rendered when its file is missing, so a defect found in review
can be fixed by deleting just the affected chunk files and running `render` again.
"""
import argparse, os, subprocess, sys, time
import multiprocessing as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hl_common import W, H, FPS

import hl_render as R

DURATION = 267.2                      # original audio / video duration (s)
NFRAMES = int(round(DURATION * FPS))  # 8016
_R = None


def chunk_path(ci):
    return os.path.join(R.WORK, "chunks", f"chunk_{ci:04d}.mp4")


def _init():
    global _R
    _R = R.Renderer()


def _render_chunk(args):
    ci, a, b = args
    path = chunk_path(ci)
    tmp = path + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-g", "30", "-keyint_min", "30",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-an", "-f", "mp4", tmp]
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
    jobs = []
    for ci in range(nch):
        if only is not None and ci not in only:
            continue
        if os.path.exists(chunk_path(ci)):
            continue
        jobs.append((ci, ci * a.chunk, min(NFRAMES, (ci + 1) * a.chunk)))
    print(f"{len(jobs)} chunk(s) to render of {nch} ({NFRAMES} frames, {a.chunk}/chunk) on {a.workers} workers", flush=True)
    t0 = time.time()
    done = 0
    with mp.get_context("fork").Pool(a.workers, initializer=_init) as pool:
        for ci, n, dt in pool.imap_unordered(_render_chunk, jobs):
            done += 1
            el = time.time() - t0
            eta = el / done * (len(jobs) - done)
            print(f"chunk {ci:3d} done ({n} frames, {dt:6.1f}s)  {done}/{len(jobs)}  elapsed {el/60:5.1f} min  eta {eta/60:5.1f} min", flush=True)


def cmd_encode(a):
    nch = (NFRAMES + a.chunk - 1) // a.chunk
    lst = os.path.join(R.WORK, "chunks", "concat.txt")
    missing = [ci for ci in range(nch) if not os.path.exists(chunk_path(ci))]
    if missing:
        sys.exit(f"missing chunks: {missing}")
    with open(lst, "w") as f:
        for ci in range(nch):
            f.write(f"file '{chunk_path(ci)}'\n")
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    log = os.path.join(R.WORK, "x264_2pass")
    vcodec = ["-c:v", "libx264", "-preset", "slow", "-b:v", f"{a.kbps}k", "-maxrate", f"{int(a.kbps * 2.2)}k", "-bufsize", f"{int(a.kbps * 3)}k",
              "-g", "60", "-keyint_min", "30", "-bf", "3", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
              "-x264-params", "aq-mode=3:aq-strength=0.9:deblock=-1,-1:psy-rd=1.0,0.10:ref=5",
              "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-r", str(FPS)]
    base = ["ffmpeg", "-v", "error", "-stats", "-y", "-f", "concat", "-safe", "0", "-i", lst]
    print("pass 1", flush=True)
    subprocess.check_call(base + vcodec + ["-pass", "1", "-passlogfile", log, "-an", "-f", "null", "/dev/null"])
    print("pass 2 (+ original audio, stream copy)", flush=True)
    subprocess.check_call(base + ["-i", R.SOURCE] + vcodec + ["-pass", "2", "-passlogfile", log,
                                                              "-map", "0:v:0", "-map", "1:a:0", "-c:a", "copy",
                                                              "-movflags", "+faststart", "-metadata", "title=Chalo Jantar Mantar (Hinglish lyric video)", out])
    print(out, os.path.getsize(out), "bytes")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--chunk", type=int, default=240)
    r.add_argument("--only", default="")
    e = sub.add_parser("encode")
    e.add_argument("out")
    e.add_argument("--kbps", type=int, default=2640)
    e.add_argument("--chunk", type=int, default=240)
    a = ap.parse_args()
    {"render": cmd_render, "encode": cmd_encode}[a.cmd](a)


if __name__ == "__main__":
    main()
