#!/bin/sh
# 2-pass H.264 encode of the rendered intermediate (work/inter.mp4) + bit-exact copy of the ORIGINAL audio stream.
# usage: sh tools/final_encode.sh [src/original.mp4] [out.mp4]
cd "$(dirname "$0")/.." || exit 1
SRC=${1:-src/original.mp4}
OUT=${2:-Chalo_Jantar_Mantar_Lyric_Video.mp4}
V="-c:v libx264 -preset medium -b:v 2500k -maxrate 5500k -bufsize 11000k -profile:v high -level 4.1 -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -x264-params aq-mode=3:aq-strength=0.9:ref=4:bframes=3:rc-lookahead=50:keyint=60:min-keyint=30:scenecut=40"
ffmpeg -v error -y -i work/inter.mp4 -an $V -pass 1 -passlogfile work/x264pass -f null /dev/null
ffmpeg -v error -y -i work/inter.mp4 -i "$SRC" -map 0:v:0 -map 1:a:0 $V -pass 2 -passlogfile work/x264pass \
  -c:a copy -movflags +faststart -metadata title="चलो जंतर-मंतर — आवाज़ जनता की (Lyric Video)" "$OUT"
