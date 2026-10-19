#!/usr/bin/env bash
# Rebuild the film.  Usage:  ./build.sh [all|footage|shots|overlays|audio|base|final]...
# Set WORK=/path/to/scratch to keep intermediates (~3 GB) elsewhere.  Needs: ffmpeg >= 6, node + playwright (chromium), python3 + Pillow.
set -euo pipefail
cd "$(dirname "$0")"
export WORK="${WORK:-$PWD/work}"
steps=("${@:-all}")
has() { for s in "${steps[@]}"; do [[ "$s" == all || "$s" == "$1" ]] && return 0; done; return 1; }

python3 -I tools/prep.py                    # SRT -> timeline.json (lyrics are offset by project.json:song_offset)
python3 -I tools/analyze_song.py            # musical onsets: cuts snap to strong accents
has footage  && python3 -I tools/fetch_footage.py
has shots    && { python3 -I tools/make_lut.py; python3 -I tools/make_shots.py --jobs "${JOBS:-4}"; }
has overlays && node tools/render_overlays.mjs "$WORK" "${JOBS:-3}"
has audio    && python3 -I tools/compose.py audio
has base     && { python3 -I tools/make_lut.py; python3 -I tools/compose.py base; }
has final    && python3 -I tools/compose.py final
