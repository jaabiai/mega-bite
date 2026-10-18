"""Base layer: the main video colour-graded, with a mild Gaussian background blur behind the person.

* talking-head frames  : subject graded + sharpened, background Gaussian-blurred (sigma ~5.5 px @1080p, i.e. the
                         requested 20-30 % strength) and slightly darkened/de-glared, matte from RVM.
* physical phone shots : matte is white (no blur), same subject grade.
Audio is NOT touched here (the original track is muxed untouched in the final render).

usage: build_base.py <main.mp4> <matte_dir> <out_dir>
"""
import concurrent.futures as cf
import os
import subprocess
import sys

FPS = 30
TOTAL = 7891
CUT_A, CUT_B = 5187, 7037  # physical-phone shots live in [CUT_A, CUT_B)
BLUR_SIGMA = 5.5

GRADE_FG = (
    "eq=brightness=0.02:contrast=1.07:saturation=1.08:gamma=0.98,"
    "curves=master='0/0 0.18/0.155 0.5/0.52 0.82/0.85 1/0.975':red='0/0 0.5/0.515 1/1':blue='0/0.012 0.5/0.49 1/0.985',"
    "colorbalance=rs=-0.02:bs=0.04:rm=0.025:bm=-0.02:rh=0.03:bh=-0.03,"
    "unsharp=5:5:0.45:5:5:0"
)
# background: a touch less glare (sky detail comes back), slightly cooler shadows
GRADE_BG = (
    "eq=brightness=-0.012:contrast=1.05:saturation=1.04,"
    "curves=master='0/0 0.5/0.49 0.85/0.83 1/0.94',"
    "colorbalance=rs=-0.01:bs=0.025:rh=0.015:bh=-0.02"
)


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(" ".join(cmd) + "\n" + r.stderr[-2000:])


def build_matte(matte_dir):
    out = os.path.join(matte_dir, "matte_full.mkv")
    if os.path.exists(out):
        return out
    gap = CUT_B - CUT_A
    sh(["ffmpeg", "-v", "error", "-y",
        "-i", f"{matte_dir}/m0.mkv", "-i", f"{matte_dir}/m1.mkv", "-i", f"{matte_dir}/m2.mkv",
        "-f", "lavfi", "-i", f"color=c=white:s=1280x720:r={FPS},format=gray",
        "-i", f"{matte_dir}/m3.mkv",
        "-filter_complex",
        f"[3:v]trim=end_frame={gap},setpts=N/{FPS}/TB[gap];"
        "[0:v][1:v][2:v][gap][4:v]concat=n=5:v=1:a=0,format=gray[v]",
        "-map", "[v]", "-c:v", "ffv1", "-level", "3", out])
    return out


def render_chunk(args):
    main, matte, out, f0, n = args
    ss = f"{f0 / FPS:.5f}"
    fg = f"[b]{GRADE_FG},format=gbrp[fg]"
    bg = f"[a]gblur=sigma={BLUR_SIGMA}:steps=3,{GRADE_BG},format=gbrp[bg]"
    graph = (
        "[0:v]split=2[a][b];" + bg + ";" + fg + ";"
        "[1:v]scale=1920:1080:flags=bicubic,gblur=sigma=0.8,format=gbrp[m];"
        "[bg][fg][m]maskedmerge,vignette=angle=0.38:mode=forward:eval=init,format=yuv420p[o]"
    )
    sh(["ffmpeg", "-v", "error", "-y", "-ss", ss, "-i", main, "-ss", ss, "-i", matte,
        "-filter_complex", graph, "-map", "[o]", "-frames:v", str(n),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-g", "30", "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", out])
    return out


def main(main_mp4, matte_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    matte = build_matte(matte_dir)
    k = 4
    step = -(-TOTAL // k)
    jobs = []
    for i in range(k):
        f0 = i * step
        n = min(step, TOTAL - f0)
        jobs.append((main_mp4, matte, f"{out_dir}/base_{i}.mp4", f0, n))
    with cf.ThreadPoolExecutor(k) as ex:
        for r in ex.map(render_chunk, jobs):
            print("done", r, flush=True)
    lst = f"{out_dir}/list.txt"
    open(lst, "w").write("".join(f"file 'base_{i}.mp4'\n" for i in range(k)))
    sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", f"{out_dir}/base.mp4"])
    print("base.mp4 ready")


if __name__ == "__main__":
    main(*sys.argv[1:4])
