"""Reel v2 assembly (1080x1920 / 30 fps).

Every picture layer (shot) is placed on a black canvas at its frame position. A shot enters either with a push-in
dissolve (the push-in is baked into the clip, the dissolve is an alpha fade over the previous shot, which is held
underneath), a slide-up (iPhone demo) or a plain fade (B-roll). Then: static scrim, HTML overlay frames, audio.

usage: assemble_reel2.py <scratch> <out.mp4> [--proxy]
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EDIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, EDIT)
from assemble_reel import make_scrim  # noqa: E402
import reel2_plan as P  # noqa: E402


def main(scratch, out, proxy=False):
    W, H = (360, 640) if proxy else (1080, 1920)
    shots = json.load(open(f"{EDIT}/data/reel2_shots.json"))
    L = P.load_layout()
    n_frames = L["n_frames"]
    inputs = [f"{scratch}/reel2/shots/{s['id']}.mp4" for s in shots]
    scrim = f"{scratch}/reel2/scrim.png"
    make_scrim(scrim)
    scrim_i = len(inputs)
    ov_i = scrim_i + 1
    au_i = ov_i + 1
    f = [f"color=c=black:s={W}x{H}:r=30:d={n_frames / 30:.4f},format=yuv420p[v0]"]
    cur = "v0"
    for k, s in enumerate(shots):
        t0 = s["F0"] / 30
        dur = (s["F1"] - s["F0"] + s["ext"]) / 30
        chain = f"[{k}:v]scale={W}:{H},format=yuva420p"
        if s["fade"] and s["entrance"] != "slide":
            chain += f",fade=t=in:st=0:d={s['fade'] / 30:.4f}:alpha=1"
        chain += f",setpts=PTS-STARTPTS+{t0:.4f}/TB[s{k}]"
        f.append(chain)
        if s["entrance"] == "slide":
            y = f"if(lt(t-{t0:.4f},0.40),{H}*pow(1-(t-{t0:.4f})/0.40,3),0)"
            ov = f"[{cur}][s{k}]overlay=x=0:y='{y}':eof_action=pass:enable='between(t,{t0:.4f},{t0 + dur:.4f})'[v{k + 1}]"
        else:
            ov = f"[{cur}][s{k}]overlay=eof_action=pass:enable='between(t,{t0:.4f},{t0 + dur:.4f})'[v{k + 1}]"
        f.append(ov)
        cur = f"v{k + 1}"
    f.append(f"[{scrim_i}:v]format=rgba,scale={W}:{H}[scr]")
    f.append(f"[{cur}][scr]overlay=0:0:format=auto:shortest=0[vs]")
    f.append(f"[{ov_i}:v]format=rgba,scale={W}:{H}[ovl]")
    f.append("[vs][ovl]overlay=0:0:format=auto:eof_action=pass,format=yuv420p[vout]")

    cmd = ["ffmpeg", "-v", "error", "-stats", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-loop", "1", "-framerate", "30", "-i", scrim]
    cmd += ["-framerate", "30", "-start_number", "0", "-i", f"{scratch}/reel2/ov/%06d.png"]
    cmd += ["-i", f"{scratch}/reel2/audio_final/reel2_audio.wav"]
    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", f"{au_i}:a", "-t", f"{n_frames / 30:.4f}"]
    if proxy:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-profile:v", "high", "-level", "4.2",
                "-maxrate", "24M", "-bufsize", "48M", "-g", "60", "-bf", "2", "-c:a", "aac", "-b:a", "320k", "-ar", "48000"]
    cmd += ["-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-movflags", "+faststart", out]
    print("running ffmpeg ...", flush=True)
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--proxy" in sys.argv)
