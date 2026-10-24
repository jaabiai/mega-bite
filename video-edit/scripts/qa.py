#!/usr/bin/env python3
"""Automatic checks on a rendered video.

  qa.py VIDEO [--sheet out.jpg]

* container facts (resolution, fps, frame count, duration, audio)
* black / blank frames
* the logo is present on every sampled frame (top-right, same position)
* loudness / true peak
* contact sheet (one frame every 4 s)
"""
import argparse
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--sheet", default=None)
    a = ap.parse_args()
    v = a.video

    p = run(f'ffprobe -v error -count_frames -show_entries stream=codec_name,width,height,r_frame_rate,nb_read_frames,duration,'
            f'sample_rate,channels -of default=nw=1 "{v}"').stdout
    print("== container\n" + p.strip().replace("\n", " | "))

    bd = run(f'ffmpeg -hide_banner -nostats -i "{v}" -vf blackdetect=d=0.04:pix_th=0.06 -an -f null -').stderr
    black = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd)
    print("== black frames:", black if black else "none")

    # logo presence: sample every 1 s, check blue-dominant pixels in the logo box
    dur = float(re.search(r"duration=([\d.]+)", p).group(1))
    ts = np.arange(1.0, dur - .2, 1.0)
    missing = []
    for t in ts:
        raw = subprocess.run(f'ffmpeg -v error -ss {t:.2f} -i "{v}" -frames:v 1 -vf "crop=112:112:1712:56" -f rawvideo -pix_fmt rgb24 -',
                             shell=True, capture_output=True).stdout
        px = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(int)
        blue = ((px[:, 2] > px[:, 0] + 40) & (px[:, 2] > 120)).mean()
        silver = ((px.min(1) > 150) & (np.abs(px[:, 0] - px[:, 2]) < 40)).mean()
        if blue < .06 or silver < .02:
            missing.append((round(float(t), 1), round(float(blue), 3), round(float(silver), 3)))
    print(f"== logo present on {len(ts) - len(missing)}/{len(ts)} sampled frames", "" if not missing else f"| MISSING: {missing}")

    o = run(f'ffmpeg -hide_banner -nostats -i "{v}" -af ebur128=peak=true -vn -f null -').stderr
    tail = o[o.rindex("Summary:"):]
    print("== loudness: I =", re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1), "LUFS | LRA =",
          re.search(r"LRA:\s+(-?[\d.]+) LU", tail).group(1), "| peak =", re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1), "dBFS")

    if a.sheet:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        times = np.arange(2, dur, 4.0)
        tiles = []
        for t in times:
            raw = subprocess.run(f'ffmpeg -v error -ss {t:.2f} -i "{v}" -frames:v 1 -vf scale=480:270 -f rawvideo -pix_fmt rgb24 -',
                                 shell=True, capture_output=True).stdout
            im = Image.fromarray(np.frombuffer(raw, np.uint8).reshape(270, 480, 3))
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 78, 30), fill=(0, 0, 0))
            d.text((6, 3), f"{t:.0f}s", font=f, fill=(255, 235, 80))
            tiles.append(im)
        cols = 6
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 484, rows * 274), (20, 20, 20))
        for i, im in enumerate(tiles):
            sheet.paste(im, ((i % cols) * 484, (i // cols) * 274))
        sheet.save(a.sheet, quality=88)
        print("== contact sheet:", a.sheet)


if __name__ == "__main__":
    main()
