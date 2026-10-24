#!/usr/bin/env python3
"""Render overlay frames for a time range and composite them over the base picture.

  compose.py --out out.mp4 [--from 0 --to 16.6] [--palette A_ember --font montserrat]
             [--scale 1] [--audio mix.wav] [--crf 18] [--workers 3]

The base picture (render_base.py) and the audio are cut to the same range.  With --scale 2
the overlay is rendered at 3840x2160 and the base is upscaled to match.
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MAIN, ROOT, WORK, sh, style_for  # noqa: E402
from edl import EDL  # noqa: E402
import build_timeline  # noqa: E402

FPS = 30

# narration clean-up: rumble/car-noise cut, de-mud, presence, gentle compression, safety limiter
VOICE_CHAIN = ("volume=-4dB,highpass=f=85,afftdn=nr=12:nf=-42,"
               "equalizer=f=220:t=q:w=1.2:g=-2.5,equalizer=f=3200:t=q:w=1.0:g=2.5,equalizer=f=9500:t=h:w=0.7:g=1.2,"
               "acompressor=threshold=-22dB:ratio=3:attack=8:release=140:makeup=4,alimiter=limit=0.89")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--palette", default="A_ember")
    ap.add_argument("--font", default="montserrat")
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--audio", default=None, help="pre-mixed audio for the FULL timeline (default: cleaned narration)")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--layout", default="wide", choices=["wide", "vertical"], help="wide 16:9 video or vertical 9:16 Reel")
    ap.add_argument("--keep", action="store_true", help="keep the overlay PNG frames (needed for --reuse)")
    ap.add_argument("--reuse", action="store_true", help="reuse base video + overlay frames of an earlier --keep run")
    ap.add_argument("--patch", action="append", default=[], metavar="A,B",
                    help="with --reuse: re-render only overlay frames in [A,B) seconds (repeatable)")
    a = ap.parse_args()

    full = build_timeline.build()["duration"]
    t1 = a.t1 if a.t1 is not None else full
    t0 = a.t0
    work = os.path.join(WORK, "compose", a.tag)
    if not a.reuse:
        shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)

    # 1 timeline + style
    tl = build_timeline.build(upto=t1 if a.t1 is not None and t1 < full else None, layout=a.layout)
    json.dump(tl, open(f"{work}/tl.json", "w"))
    json.dump(style_for(a.palette, a.font), open(f"{work}/style.json", "w"))

    # 2 base picture (presenter + B-roll), padded with a frozen last frame for the end card
    base = f"{work}/base.mp4"
    spoken_end = min(t1, EDL["main_duration"])
    if not (a.reuse and os.path.exists(base)):
        sh(f'python3 -I "{ROOT}/scripts/render_base.py" "{base}" --from {t0} --to {spoken_end} --layout {a.layout}')
    if t1 > spoken_end and not a.reuse:
        pad = t1 - spoken_end
        sh(f'ffmpeg -v error -y -i "{base}" -vf "tpad=stop_mode=clone:stop_duration={pad:.3f}" -c:v libx264 -preset veryfast -crf 12 '
           f'-pix_fmt yuv420p -r {FPS} "{work}/base_pad.mp4" && mv "{work}/base_pad.mp4" "{base}"')

    # 3 overlay frames
    ov = f"{work}/ov"
    ranges = [tuple(map(float, p.split(","))) for p in a.patch] if a.reuse else [(t0, t1)]
    for r0, r1 in ranges:
        sh(f'node "{ROOT}/render/render_overlay.js" --tl "{work}/tl.json" --style "{work}/style.json" --out "{ov}" '
           f'--from {r0} --to {r1} --fps {FPS} --scale {a.scale} --workers {a.workers}', cwd=f"{ROOT}/render")

    # 4 audio
    if a.audio:
        aud = f"-ss {t0} -t {t1 - t0} -i \"{a.audio}\""
    else:
        wav = f"{work}/voice.wav"
        sh(f'ffmpeg -v error -y -ss {t0} -t {min(t1, EDL["main_duration"]) - t0} -i "{MAIN}" -vn -af "{VOICE_CHAIN},loudnorm=I=-16:TP=-1.5:LRA=9" '
           f'-ar 48000 -ac 2 "{wav}"')
        aud = f'-i "{wav}"'

    # 5 composite
    fades = ""                                     # short fade in from black / out to black on the full video
    if t0 == 0:
        fades += ",fade=t=in:st=0:d=0.3"
    if t1 >= full - 1e-6:
        fades += f",fade=t=out:st={t1 - t0 - 0.8:.3f}:d=0.8"
    start_no = round(t0 * FPS) + 1
    W, H = (1080, 1920) if a.layout == "vertical" else (1920, 1080)
    W, H = W * a.scale, H * a.scale
    up = f"[0:v]scale={W}:{H}:flags=lanczos[b];[b][1:v]" if a.scale != 1 else "[0:v][1:v]"
    sh(f'ffmpeg -v error -y -i "{base}" -framerate {FPS} -start_number {start_no} -i "{ov}/%05d.png" {aud} '
       f'-filter_complex "{up}overlay=format=auto:shortest=1{fades},format=yuv420p[v]" -map "[v]" -map 2:a '
       f'-c:v libx264 -preset slow -crf {a.crf} -profile:v high -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 '
       f'-c:a aac -b:a 256k -movflags +faststart -shortest "{a.out}"')
    if not a.keep:
        shutil.rmtree(ov, ignore_errors=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
