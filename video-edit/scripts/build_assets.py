#!/usr/bin/env python3
"""Prepare per-scene media for the overlay engine.

* Screen-recording frames: for every phone sub-scene in the EDL the HDR recording is
  tone-mapped to SDR, re-timed to the output timeline (slow-down / hold) and written as
  <WORK>/frames/<sub id>/%05d.jpg at 30 fps.
* B-roll: free stock clips from Mixkit (Mixkit Free License: commercial use, no attribution)
  are downloaded at 1080p into <WORK>/broll/.

Usage: build_assets.py [--upto SECONDS] [--only A,B1a]
"""
import argparse
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SCREEN, SCREEN_TONEMAP, WORK, sh  # noqa: E402
from edl import EDL  # noqa: E402

FPS = 30
FRAMES = os.path.join(WORK, "frames")
BROLL = os.path.join(WORK, "broll")


def sub_frame_count(sub):
    return sum(round((n1 - n0) * FPS) for n0, n1, _, _ in sub["src"])


def build_sub(sub):
    out = os.path.join(FRAMES, sub["id"])
    total = sub_frame_count(sub)
    if os.path.isdir(out) and len(os.listdir(out)) >= total:
        return sub["id"], "cached"
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    idx = 1
    for n0, n1, s0, s1 in sub["src"]:
        n = round((n1 - n0) * FPS)
        if abs(s1 - s0) < 1e-6:                                    # hold one frame
            one = os.path.join(out, "_hold.jpg")
            sh(f'ffmpeg -v error -y -ss {s0} -i "{SCREEN}" -an -frames:v 1 -vf "{SCREEN_TONEMAP}" -q:v 3 "{one}"')
            for i in range(n):
                shutil.copyfile(one, os.path.join(out, f"{idx + i:05d}.jpg"))
            os.remove(one)
        else:                                                       # re-time s0..s1 onto n frames
            k = (n1 - n0) / (s1 - s0)
            sh(f'ffmpeg -v error -y -ss {s0} -t {s1 - s0 + 0.2} -i "{SCREEN}" -an '
               f'-vf "{SCREEN_TONEMAP},setpts=(PTS-STARTPTS)*{k:.6f},fps={FPS}" -frames:v {n} '
               f'-start_number {idx} -q:v 3 "{out}/%05d.jpg"')
        idx += n
    last = os.path.join(out, f"{idx - 1:05d}.jpg")
    for i in range(3):                                              # tail for the cross-dissolve
        shutil.copyfile(last, os.path.join(out, f"{idx + i:05d}.jpg"))
    return sub["id"], f"{idx + 2} frames"


def download_broll(clip):
    dst = os.path.join(BROLL, f"{clip}.mp4")
    if os.path.exists(dst) and os.path.getsize(dst) > 100000:
        return clip, "cached"
    os.makedirs(BROLL, exist_ok=True)
    sh(f'curl -sS -L -m 180 -o "{dst}" "https://assets.mixkit.co/videos/{clip}/{clip}-1080.mp4"')
    return clip, f"{os.path.getsize(dst) // 1000} KB"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=float, default=1e9)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    subs = [s for b in EDL["blocks"] for s in b["subs"] if s["n0"] < a.upto and (not a.only or s["id"] in a.only.split(","))]
    clips = sorted({s["clip"] for s in EDL["base"] if s["kind"] == "broll" and s["start"] < a.upto})
    os.makedirs(FRAMES, exist_ok=True)
    with cf.ThreadPoolExecutor(3) as ex:
        for r in ex.map(download_broll, clips):
            print("broll", *r)
        for r in ex.map(build_sub, subs):
            print("frames", *r)
