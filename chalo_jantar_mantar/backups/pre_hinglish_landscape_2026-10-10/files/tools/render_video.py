"""Parallel chunked renderer.  usage: render_video.py TIMING OUTDIR [workers] [t0 t1]
Writes near-lossless intermediate segments seg_XXX.mp4 (30 fps, 1080x1920) + concat list."""
import os, sys, subprocess, time
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FPS = 30
CHUNK = 240  # frames per segment

_scene = None

def _init(timing):
    global _scene
    import render
    _scene = render.Scene(timing)

def _work(args):
    idx, f0, f1, outdir = args
    path = f"{outdir}/seg_{idx:03d}.mp4"
    if os.path.exists(path + ".done"):
        return idx, 0.0
    t0 = time.time()
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920", "-r", str(FPS), "-i", "-",
           "-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-g", "30", "-bf", "0",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(f0, f1):
        fr = _scene.render_frame(n / FPS)
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    open(path + ".done", "w").write("ok")
    return idx, time.time() - t0

if __name__ == "__main__":
    timing, outdir = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    t1 = float(sys.argv[5]) if len(sys.argv) > 5 else 267.2
    os.makedirs(outdir, exist_ok=True)
    fa, fb = int(round(t0 * FPS)), int(round(t1 * FPS))
    jobs = []
    for i, f in enumerate(range(fa, fb, CHUNK)):
        jobs.append((i, f, min(fb, f + CHUNK), outdir))
    print(f"{len(jobs)} segments, frames {fa}..{fb}", flush=True)
    start = time.time()
    with mp.get_context("fork").Pool(workers, initializer=_init, initargs=(timing,)) as pool:
        done = 0
        for idx, dt in pool.imap_unordered(_work, jobs):
            done += 1
            print(f"seg {idx:03d} done in {dt:5.1f}s  [{done}/{len(jobs)}]  elapsed {time.time()-start:6.0f}s", flush=True)
    with open(f"{outdir}/list.txt", "w") as fh:
        for i, _ in enumerate(jobs):
            fh.write(f"file 'seg_{i:03d}.mp4'\n")
    print("segments complete")
