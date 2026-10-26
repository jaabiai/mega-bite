#!/usr/bin/env bash
# Voice clean-up chain for the main narration track.
#   usage: audio_clean.sh <in_video_or_audio> <out.wav> <rnnoise_model.rnnn>
# declip -> rumble high-pass -> RNNoise -> EQ -> de-ess -> soft gate -> gentle compression + peak limit -> 2-pass loudnorm (-14 LUFS, -1.5 dBTP)
set -euo pipefail
IN="$1"; OUT="$2"; MODEL="$3"
CHAIN="adeclip,highpass=f=95:poles=2,highpass=f=95:poles=2,arnndn=m=${MODEL}:mix=0.85,\
equalizer=f=220:t=q:w=1.1:g=-2.0,equalizer=f=3000:t=q:w=0.9:g=2.2,treble=g=1.4:f=8000,\
deesser=i=0.30:m=0.5:f=0.5,\
agate=threshold=0.012:ratio=1.8:range=0.3:attack=8:release=220:knee=4,\
acompressor=threshold=-25dB:ratio=2.1:attack=15:release=220:makeup=3dB:knee=6,\
alimiter=limit=0.72:attack=4:release=60:level=false"

STATS=$(ffmpeg -hide_banner -nostats -i "$IN" -vn -af "${CHAIN},loudnorm=I=-14:TP=-1.5:LRA=8:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$STATS" | grep "\"$1\"" | sed 's/[^0-9.-]*\([-0-9.]*\).*/\1/'; }
ffmpeg -hide_banner -v error -y -i "$IN" -vn -af "${CHAIN},\
loudnorm=I=-14:TP=-1.5:LRA=8:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,\
aresample=48000,alimiter=limit=0.89:level=false" -ar 48000 -c:a pcm_s24le "$OUT"
