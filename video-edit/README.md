# video-edit — MEGABYTE "Lock your Google search history"

Scripted, repeatable edit of the face-cam + iPhone screen-recording pair. Everything is code, so a different
palette, caption wording or timing is a re-render away.

## Pipeline

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `audio_clean.sh` | declip → rumble high-pass → RNNoise (`bd.rnnn`) → EQ → de-ess → soft gate → compression → 2-pass loudnorm (−14 LUFS / −1.5 dBTP) |
| 2 | ffmpeg (see below) | iPhone HDR (HEVC, BT.2020 PQ) → SDR BT.709, constant 60 fps |
| 3 | `prep_screen.py` + `lib/screenprep.py` | blur every e-mail / account name, remove the screen-recording indicators, remove the AssistiveTouch bubble (alpha un-mixing calibrated from two flat-background frames) |
| 4 | `render.py` | compositor: cinematic grade, B-roll, phone-in-frame scenes with camera zoom + highlight rings + tap ripples, word-highlight captions, CTAs, wipes, end card → H.264 |
| 5 | `mix_audio.py` | voice + ducked music bed + timeline-synced SFX → `mix.wav` |
| 6 | ffmpeg | mux video + mix (`alimiter`, AAC 320k) |
| QA | `qa_privacy.py`, `qa_privacy_screen.py` | OCR sweeps that fail if any e-mail / account name is still legible |
| Extra | `make_thumbnail.py` | 1280×720 thumbnail |

```bash
# 2) HDR -> SDR, 60 fps
ffmpeg -i RPReplay.mp4 -an -vf "fps=60,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv444p" \
       -c:v libx264 -crf 8 -pix_fmt yuv444p screen_sdr60.mp4
# 3) clean it in 20 s slices (parallel), then concat -> screen_clean60.mp4 (first frame == recording time 8.0 s)
python prep_screen.py screen_sdr60.mp4 8 28 seg0.mp4   # ... 28-48, 48-68, 68-87.7
# 4) render (split in chunks for speed; chunk edges at frame boundaries), then concat
python render.py --face main.mp4 --screen screen_clean60.mp4 --broll-dir broll/ --start 0 --end 26.5667 --out p0.mp4
```

## Design tokens (approved)
* Palette **Volt Lime**: accent `#C6F432`, secondary `#FF5C39`, background `#0A0D0B → #18221B`, text white. No blue anywhere.
* Fonts: Poppins ExtraBold / Black (captions, titles), Poppins SemiBold / Medium (labels) — SIL OFL, in `assets/fonts/`.
* Logo: drop the real file at `assets/logo/logo.png` (RGBA). Until then a placeholder "MB" mark is drawn.

## Timing data
`lib/timeline.py` (scenes, screen-recording re-timing, camera, taps, highlights, steps) and
`lib/captions_data.py` (English caption chunks). `captions/script_en.md` lists the captions for review.

## Licences
Music / SFX / stock clips: Mixkit (Mixkit licence — free for commercial use, no attribution required).
Music "Lo-Fi 05" by Lily J; clips 39782, 25451, 144; SFX 1492, 1489, 1109, 3005, 3124, 2856, 2852, 2354, 933.
