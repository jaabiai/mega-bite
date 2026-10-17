#!/usr/bin/env python3
"""Background music for the long video and the reels (voice untouched, music ducked under it).

  python render_bgm.py long                 -> output/MegaByte_AI_Free_Video_Generator_FINAL_BGM.mp4
  python render_bgm.py reel loud|max        -> output/MegaByte_Reel_<LOUD|MAX>_BGM_9x16.mp4

Tracks: Mixkit (Stock Music Free License: commercial use incl. YouTube / social video allowed, no attribution required).
See data/music_credits.md for the exact tracks and licence note.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import bgm                                         # noqa: E402
from mbedit.common import WORK                     # noqa: E402

TRACKS = os.path.join(WORK, "music", "mp3")        # <id>.mp3 downloaded from assets.mixkit.co/music/<id>/<id>.mp3
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
RENDER = os.path.join(WORK, "render")

# long video: calm tech bed that changes with the topic (crossfades land on topic changes)
LONG_SECTIONS = [
    dict(track=1168, t0=0.0),                      # Coffee or Tea  - hook / intro (positive, futuristic)
    dict(track=184, t0=54.14, xf=5.0),             # Vastness       - the walkthrough (calm, very steady)
    dict(track=661, t0=215.0, xf=5.0),             # Fashion 01     - result + outro (positive, motivational)
]
LONG_TOTAL = 247.6
# reel: one upbeat-but-smooth track
REEL_SECTIONS = [dict(track=1168, t0=0.0)]


def long_video():
    os.makedirs(OUTDIR, exist_ok=True)
    voice = os.path.join(RENDER, "voice_original.wav")                       # the original narration, decoded untouched
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WORK, "work/main.mp4"), "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", voice], check=True)
    bed = bgm.make_bed(LONG_SECTIONS, LONG_TOTAL, TRACKS, os.path.join(RENDER, "bed_long.wav"), fade_in=2.0, fade_out=4.0)
    vl = bgm.lufs_of(bgm.decode(voice))
    mixed = bgm.mix(voice, bed, os.path.join(RENDER, "mix_long.wav"), vl, under_db=12.0, duck_db=6.0, ceiling=0.93, total=LONG_TOTAL)
    out = os.path.join(OUTDIR, "MegaByte_AI_Free_Video_Generator_FINAL_BGM.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(RENDER, "video.mp4"), "-i", mixed, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-t", f"{LONG_TOTAL}", "-movflags", "+faststart", out], check=True)
    print("long ->", out)


def reel(voice_name):
    import edl_reel
    total = edl_reel.TOTAL
    voice = os.path.join(RENDER, f"reel_voice_{voice_name}.wav")
    bed = bgm.make_bed(REEL_SECTIONS, total, TRACKS, os.path.join(RENDER, "bed_reel.wav"), fade_in=1.2, fade_out=2.4)
    vl = bgm.lufs_of(bgm.decode(voice)[: int((total - 2.6) * bgm.SR)])
    mixed = bgm.mix(voice, bed, os.path.join(RENDER, f"mix_reel_{voice_name}.wav"), vl, under_db=9.0, duck_db=6.0, ceiling=0.841, total=total)
    out = os.path.join(OUTDIR, f"MegaByte_Reel_{voice_name.upper()}_BGM_9x16.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(RENDER, "reel_video.mp4"), "-i", mixed, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart", out], check=True)
    print("reel ->", out)


if __name__ == "__main__":
    if sys.argv[1] == "long":
        long_video()
    else:
        reel(sys.argv[2] if len(sys.argv) > 2 else "loud")
