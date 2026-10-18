"""Final assembly: graded base + screen scenes + B-roll cutaways + HTML overlay frames + final audio -> MP4.

Layer order (bottom -> top):
  base (graded/blurred main video, video timeline never altered -> voice sync is untouched)
  stinger dim/blur (during "Welcome to Mega Byte")
  S1, S2 screen scenes   (slide-up in, fade out)
  B-roll cutaways        (cross-fade in/out)
  overlay PNG frames     (captions, key phrases, step lists, CTAs, logo ...)

usage: assemble.py <scratch> <out.mp4> [--proxy]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from broll import CUTAWAYS  # noqa: E402
import scenes  # noqa: E402

DUR = 263.0333


def main(scratch, out, proxy=False):
    W, H = (640, 360) if proxy else (1920, 1080)
    inputs = [f"{scratch}/base/base.mp4", f"{scratch}/scenes/S1.mp4", f"{scratch}/scenes/S2.mp4"]
    for c in CUTAWAYS:
        inputs.append(f"{scratch}/cuts/cut_{c['id']}.mp4")
    ov_idx = len(inputs)
    audio_idx = ov_idx + 1

    f = []
    f.append(f"[0:v]scale={W}:{H}:flags=bicubic,format=yuv420p,setsar=1[b0]")
    # stinger: blur + dim the picture behind the big logo / "Welcome to Mega Byte"
    f.append("[b0]split[bm][bs]")
    f.append(f"[bs]trim=start=24.9:end=29.3,setpts=PTS-STARTPTS+24.9/TB,gblur=sigma={18 if not proxy else 6}:steps=2,"
             "eq=brightness=-0.16:saturation=0.85,format=yuva420p,"
             "fade=t=in:st=25.05:d=0.35:alpha=1,fade=t=out:st=28.75:d=0.4:alpha=1[bl]")
    f.append("[bm][bl]overlay=eof_action=pass:enable='between(t,24.9,29.3)'[v1]")

    cur = "v1"
    n = 1
    for k, sc in ((1, scenes.S1), (2, scenes.S2)):
        t0, t1 = sc["t0"], sc["t1"]
        d = t1 - t0
        f.append(f"[{k}:v]scale={W}:{H}:flags=bicubic,format=yuva420p,fade=t=out:st={d - 0.35:.3f}:d=0.35:alpha=1,"
                 f"setpts=PTS-STARTPTS+{t0}/TB[s{k}]")
        n += 1
        f.append(f"[{cur}][s{k}]overlay=x=0:y='if(lt(t-{t0},0.5),{H}*pow(1-(t-{t0})/0.5,3),0)':eof_action=pass:"
                 f"enable='between(t,{t0},{t1})'[v{n}]")
        cur = f"v{n}"
    for i, c in enumerate(CUTAWAYS):
        k = 3 + i
        t0, t1 = c["t0"], c["t1"]
        d = t1 - t0
        f.append(f"[{k}:v]scale={W}:{H}:flags=bicubic,format=yuva420p,fade=t=in:st=0:d=0.30:alpha=1,"
                 f"fade=t=out:st={d - 0.30:.3f}:d=0.30:alpha=1,setpts=PTS-STARTPTS+{t0}/TB[c{i}]")
        n += 1
        f.append(f"[{cur}][c{i}]overlay=eof_action=pass:enable='between(t,{t0},{t1})'[v{n}]")
        cur = f"v{n}"
    f.append(f"[{ov_idx}:v]format=rgba,scale={W}:{H}[ovl]")
    f.append(f"[{cur}][ovl]overlay=0:0:format=auto:eof_action=pass,format=yuv420p[vout]")

    cmd = ["ffmpeg", "-v", "error", "-stats", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-framerate", "30", "-start_number", "0", "-i", f"{scratch}/ov/%06d.png"]
    cmd += ["-i", f"{scratch}/audio_final/final_audio.wav"]
    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", f"{audio_idx}:a", "-t", f"{DUR}"]
    if proxy:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-profile:v", "high", "-level", "4.2",
                "-maxrate", "30M", "-bufsize", "60M", "-g", "60", "-bf", "2",
                "-c:a", "aac", "-b:a", "320k", "-ar", "48000"]
    cmd += ["-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-movflags", "+faststart", out]
    open(out + ".cmd.txt", "w").write(" ".join(f"'{c}'" if " " in c or ";" in c else c for c in cmd))
    print("running ffmpeg ...", flush=True)
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--proxy" in sys.argv)
