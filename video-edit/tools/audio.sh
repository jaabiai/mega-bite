#!/usr/bin/env bash
# Voice clean-up for the narration: gentle, transparent processing (nothing is cut or muted).
# usage: audio.sh <main.mp4> <out.wav>
set -euo pipefail
IN="$1"; OUT="$2"
PRE="highpass=f=75,afftdn=nr=9:nf=-38:tn=1,equalizer=f=170:t=q:w=1:g=-1.5,equalizer=f=3200:t=q:w=1.2:g=2.0,acompressor=threshold=-23dB:ratio=2.2:attack=12:release=160:makeup=2.5"
# pass 1: measure
J=$(ffmpeg -hide_banner -nostats -i "$IN" -vn -af "$PRE,loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$J" | grep input_i | sed -E 's/.*: "(.*)".*/\1/'); mtp=$(echo "$J" | grep input_tp | sed -E 's/.*: "(.*)".*/\1/')
mlra=$(echo "$J" | grep input_lra | sed -E 's/.*: "(.*)".*/\1/'); mth=$(echo "$J" | grep input_thresh | sed -E 's/.*: "(.*)".*/\1/')
off=$(echo "$J" | grep target_offset | sed -E 's/.*: "(.*)".*/\1/')
echo "measured I=$mi TP=$mtp LRA=$mlra thresh=$mth offset=$off"
# pass 2: apply linearly
ffmpeg -hide_banner -v error -y -i "$IN" -vn -af "$PRE,loudnorm=I=-14:TP=-1.5:LRA=9:measured_I=$mi:measured_TP=$mtp:measured_LRA=$mlra:measured_thresh=$mth:offset=$off:linear=true,alimiter=limit=0.84:level=false,atrim=start=0.030,asetpts=PTS-STARTPTS,apad=whole_dur=247.6" -t 247.6 -ar 48000 -c:a pcm_s16le "$OUT"
