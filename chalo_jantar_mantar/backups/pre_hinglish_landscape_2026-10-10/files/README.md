# चलो जंतर-मंतर — आवाज़ जनता की · Cinematic Hindi Lyric Video

`Chalo_Jantar_Mantar_Lyric_Video.mp4` is the original song video re-edited into a lyric video:
**1080 × 1920 (9:16), 30 fps, 267.2 s, H.264 + the original AAC audio stream copied bit-for-bit.**
The original MP4 was never modified.

See **[EDITING_PLAN.md](EDITING_PLAN.md)** for what was inspected and why each decision was made, and
**[VERIFICATION.md](VERIFICATION.md)** for the measured results (sync, text, audio, duration).

## Files

| File | What it is |
|---|---|
| `Chalo_Jantar_Mantar_Lyric_Video.mp4` | The finished video |
| `lyric_timing.json` | **Editable sync data** – one entry per lyric line (`start`/`end` seconds, section, style, source/confidence of the timing) |
| `Chalo_Jantar_Mantar_lyrics.srt` / `.ass` | The same timing exported for other players/editors |
| `lyrics.txt` | The supplied lyrics (the text in the video is byte-identical to this file) |
| `tools/` | Alignment, timing, rendering, export and verification scripts |
| `assets/` | Fonts (SIL OFL: Hind, Rozha One, Khand), cover tile, silhouette art, emblems |

## Adjusting the synchronisation later

1. Edit `lyric_timing.json`: change a line's `start` / `end` (seconds), or set `meta.global_offset_s` to shift everything.
   The renderer shows each line 0.05 s before `start` and holds it 0.30 s after `end` (`Scene.LEAD` / `Scene.HOLD`).
2. Re-render only what changed (frames are a pure function of time):

```bash
# one-time: rebuild cached assets from the ORIGINAL mp4 (colour field, cover tile, credit marks, art)
python tools/build_assets.py            # expects the source video at src/original.mp4

# preview any moments as PNGs
CJM_TIMING=lyric_timing.json python tools/render.py preview work/prev 28.5 114.5 232

# full render: 4 workers -> near-lossless segments, then encode + stream-copy the original audio
python tools/render_video.py lyric_timing.json work/seg 4
ffmpeg -f concat -safe 0 -i work/seg/list.txt -c copy work/inter.mp4
sh tools/final_encode.sh                # 2-pass H.264, audio = -c:a copy of the original
python tools/export_subs.py lyric_timing.json Chalo_Jantar_Mantar_lyrics     # refresh .srt/.ass
python tools/verify.py Chalo_Jantar_Mantar_Lyric_Video.mp4 src/original.mp4 lyrics.txt lyric_timing.json
```

(`tools/*.py` locate the project root from their own path; set `CJM_ROOT` / `CJM_LYRICS` / `CJM_MODELS` to override.
`final_encode.sh` and the paths inside it reflect the build machine — adjust them for your layout.)

## How the timing was derived (short)

Whisper (turbo, ONNX) was run as a *forced aligner*: the supplied Devanagari lyrics are fed as the transcript and the model only
predicts the timestamp tokens, so the text can never drift from the file. Four runs with different window phases were voted per
line; spoken/sparse passages (intro, bridge, outro, pauses) were refined to the real vocal onset from 1–4 kHz energy bursts and
spectrograms; the result was checked against a 92.66 BPM bar grid, Whisper's free transcription, and Suno's own scroll layer
burned into the source video. Details and numbers are in `VERIFICATION.md`.

## Re-deriving the timing from scratch

```bash
# needs sherpa-onnx-whisper-turbo in models/ (see requirements.txt) and the song as work/audio16k.wav (16 kHz mono)
python tools/align_seq.py turbo 1.0 work/align/turbo_l1.0.json      # repeat with leads 2.5, 0.4, 3.0
python tools/build_timing.py lyric_timing.json 264.4                 # vote + work/overrides.json
```
