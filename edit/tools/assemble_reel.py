"""Reel assembly (1080x1920 / 30 fps):

  speaker layer (continuous, tracked 9:16 crop)           <- the narration is never cut; only pictures change
  + iPhone demo scene (slides up, B-roll fades over its end)
  + B-roll cutaways (0.22 s cross-dissolves)
  + HTML overlay frames (hook, step cards, captions, end card, logo, progress)
  + audio

usage: assemble_reel.py <scratch> <out.mp4> [--proxy]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import reel_plan as rp  # noqa: E402


def main(scratch, out, proxy=False):
    W, H = (360, 640) if proxy else (1080, 1920)
    R = rp.r
    inputs = [f"{scratch}/reel/speaker.mp4", f"{scratch}/reel/demo.mp4"]
    inputs += [f"{scratch}/reel/cuts/rcut_{c['id']}.mp4" for c in rp.CUTS]
    ov_i = len(inputs)
    au_i = ov_i + 1
    f = [f"[0:v]scale={W}:{H},format=yuv420p,setsar=1[v0]"]
    cur = "v0"
    d0 = R(rp.DEMO[0])
    d1 = R(155.20)
    f.append(f"[1:v]scale={W}:{H},format=yuva420p,setpts=PTS-STARTPTS+{d0}/TB[demo]")
    f.append(f"[{cur}][demo]overlay=x=0:y='if(lt(t-{d0},0.45),{H}*pow(1-(t-{d0})/0.45,3),0)':eof_action=pass:"
             f"enable='between(t,{d0},{d1})'[v1]")
    cur = "v1"
    n = 1
    for i, c in enumerate(rp.CUTS):
        k = 2 + i
        t0 = R(c["t0"])
        dur = (c["t1"] - c["t0"]) + (rp.CHAIN_PAD if c["chain"] else 0.0)
        fades = f"fade=t=in:st=0:d={rp.XFADE}:alpha=1"
        if not c["chain"]:
            fades += f",fade=t=out:st={dur - rp.XFADE:.3f}:d={rp.XFADE}:alpha=1"
        f.append(f"[{k}:v]scale={W}:{H},format=yuva420p,{fades},setpts=PTS-STARTPTS+{t0}/TB[c{i}]")
        n += 1
        f.append(f"[{cur}][c{i}]overlay=eof_action=pass:enable='between(t,{t0},{t0 + dur:.3f})'[v{n}]")
        cur = f"v{n}"
    f.append(f"[{ov_i}:v]format=rgba,scale={W}:{H}[ovl]")
    f.append(f"[{cur}][ovl]overlay=0:0:format=auto:eof_action=pass,format=yuv420p[vout]")

    cmd = ["ffmpeg", "-v", "error", "-stats", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-framerate", "30", "-start_number", "0", "-i", f"{scratch}/reel/ov/%06d.png"]
    cmd += ["-i", f"{scratch}/reel/audio_final/reel_audio.wav"]
    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", f"{au_i}:a", "-t", f"{rp.N_FRAMES / 30:.4f}"]
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
