# Hinglish landscape revision — build folder

Everything for the **16:9, 1920×1080, 30 fps Roman-Hindi (Hinglish)** version of *Chalo Jantar-Mantar* lives in this folder
(source/tools) and in `../output_hinglish_landscape/` (results). Nothing outside these two folders (plus `../backups/`) was
modified: the original MP4, the portrait video, `lyric_timing.json`, `lyrics.txt`, `overrides.json`, the docs, `tools/` and
`assets/` are byte-identical to the snapshot in `../backups/pre_hinglish_landscape_2026-10-10/` (`MANIFEST.sha256`).

## Layout

| Path | What |
|---|---|
| `data/roman_map.json` | the 95 Roman-Hindi lines, keyed by the line id of `../lyric_timing.json` |
| `tools/hinglish_check.py` | word-by-word Devanagari → Roman consonant-skeleton checker (+ punctuation, Latin-only checks) |
| `tools/build_hinglish.py` | writes `../output_hinglish_landscape/lyric_timing_hinglish.json`, `lyrics_hinglish.txt`, `lyrics_hinglish.srt` from the **unchanged** phase-1 timing + `roman_map.json` |
| `tools/hl_common.py … hl_post.py` | procedural cinematic background engine (sky/clouds, sun + god-rays, mountains, skylines, crowds, flags, smoke, bokeh, diyas, birds), ACES grade, bloom, dither, transitions |
| `tools/hl_text.py` | typography: 3 regular-lyric families (rap / melodic / emotional) + 5 hook animations; Roman-only guard (`assert_roman`) |
| `tools/hl_timeline.py` | the 29-shot cut list on the song's 92.66 BPM bar grid, grades and transitions |
| `tools/hl_audio.py` | kick envelope from the original audio (drives only camera push / glow; no audio is generated or altered) |
| `tools/hl_render.py` | frame compositor; `python hl_render.py preview OUTDIR t1 t2 …` renders single frames |
| `tools/render_video_landscape.py` | parallel chunked render (`render`) + concat / two-pass x264 / **original-audio stream copy** (`encode`) |
| `tools/verify_landscape.py` | full verification report |
| `tools/hl_library_test.py` | look-development helper only (not used for the final render) |
| `assets/fonts/` | Latin display fonts, all SIL OFL 1.1 (licence texts in `assets/fonts/licenses/`) |

## Rebuild

```bash
python -m venv venv && . venv/bin/activate && pip install numpy scipy pillow soundfile fonttools onnxruntime
cd chalo_jantar_mantar/hinglish_landscape/tools
export HL_SOURCE_MP4=/path/to/original.mp4      # audio source (read-only)
export HL_WORK=/path/to/scratch/work_hl          # chunk files (~0.7 GB)
python hinglish_check.py                          # spelling check, expect 0 problems
python build_hinglish.py                          # Roman timing/lyrics files
python render_video_landscape.py render --workers 4        # ~45 min on 4 cores
python render_video_landscape.py encode ../../output_hinglish_landscape/Chalo_Jantar_Mantar_Hinglish_Landscape_1080p.mp4
python verify_landscape.py ../../output_hinglish_landscape/Chalo_Jantar_Mantar_Hinglish_Landscape_1080p.mp4 /path/to/original.mp4 --chunks $HL_WORK/chunks
```

A chunk is only re-rendered when its file is missing, so a defect in one passage is fixed by deleting that chunk file (240 frames = 8 s)
and re-running `render`, then `encode`. Rendering is deterministic (a frame is a pure function of its number).

## Editing text / timing

* Wrong spelling or a different Roman convention: edit `data/roman_map.json`, run `hinglish_check.py` and `build_hinglish.py`.
* Timing: `../output_hinglish_landscape/lyric_timing_hinglish.json` (`start`/`end` seconds per line). Phase-1 times are reused unchanged.
* The word-by-word reveal inside a line is spread across the line's sung span in proportion to syllable counts — it is **not**
  word-level forced alignment.
