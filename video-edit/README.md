# Mega Byte – "Free AI video generator" episode (edit project)

Scripted, reproducible edit of the Malayalam tutorial video (talking head + phone screen recording).
Everything is code: change `edl.py`, re-render.

## What the edit does
| Request | How it is done |
|---|---|
| Colour correction / grading | `mbedit/grade.py` – filmic S-curve, warm-neutral skin, teal shadows, saturation, vignette (BT.709 end-to-end) |
| Smooth background blur | Robust Video Matting (ONNX) → temporally stable person matte → blur computed from *background pixels only* (no halo around hair); phone/hands held close to the camera stay sharp |
| B-roll | 8 Mixkit clips, **free-licence only** (see `data/broll_credits.md`) |
| Manglish captions | Text taken verbatim from `data/script.srt`; timing from CTC forced alignment of the script to the real voice (`tools/align.py`, `data/align.json`). The word being spoken is big + cyan, the rest of the phrase is small |
| Key-point text effects | Kinetic headlines / count-up (`mbedit/overlays.py`) timed to the spoken words |
| Like / Comment / Share / Subscribe | Big animated CTAs fired on the exact word (`SubscribeCTA`, `EngagePill`) |
| Logo | Top-right from the first to the last frame; flies to centre for "Welcome to Mega Byte" |
| Screen-record demo | HDR→SDR tone-mapped, audio removed, time-warped so every tap happens when it is narrated; phone + zoom card + spotlight + highlight ring + tap ripple (`DEMO_SEGS`, `DEMO_STEPS` in `edl.py`) |
| Privacy | Other Google accounts / e-mails and the private photo library in the recording are blurred (`PRIVACY` in `edl.py`) |
| Transitions | zoom / push / swipe / fade between shots (`TRANS_BY_T0`) |
| Voice | Original narration only (screen-record audio dropped), **untouched**: the long video copies the original AAC stream bit-exact, the reel is cut from it at word boundaries with no EQ/denoise/compression/loudness change (same level as the original, verified 0.00 dB). `tools/audio.sh` (clean-up + -14 LUFS) exists but is intentionally not used |

## Re-render
```bash
export MB_WORK=<folder with work/main.mp4, work/screen_sdr.mp4, work/matte.mkv, broll/hd/*.mp4>
python render.py preview 52.8 105        # JPEG stills
python render.py sheet mysheet 1 5 9     # contact sheet
python render.py full --workers 4        # video only  -> $MB_WORK/render/video.mp4
```
Mux (original audio, bit-exact): `ffmpeg -i video.mp4 -i $MB_WORK/work/main.mp4 -map 0:v -map 1:a -c:v copy -c:a copy -t 247.6 out.mp4`

## Pipeline helpers
* `tools/rvm_matte.py` – person matte for the whole main video (ffv1 gray)
* `tools/align.py` – forced alignment of the Manglish script (digits are replaced by their spoken form for alignment only)
* `tools/mixkit_*.py` – stock-clip search + licence check

## Adding the generated "tortoise vs hare" clip
Drop it at `$MB_WORK/assets/result.mp4` and re-render the chunk(s) covering 219–231 s:
`edl.py` then plays it full-size (rounded player, "AI-GENERATED VIDEO" tag) while the narration says
"Kandille, aamayum muyalum ... ottamalsaram". Until then the screen recording's own result thumbnail is highlighted.

## Reel / Short (9:16)
```bash
python render_reel.py plan                 # clip list (source -> reel time)
python render_reel.py full --workers 4     # silent video   -> $MB_WORK/render/reel_video.mp4
python render_reel.py audio                # original narration cut at word boundaries (level unchanged)
python render_reel.py mux out.mp4
```
`edl_reel.py` picks the key moments (source times snap to word boundaries) and re-uses the long video's demo
time-warp + highlight list; `mbedit/reel.py` holds the vertical scenes (camera follows the highlighted UI element)
and the end card ("Full video on YouTube - MEGA BYTE", Malayalam text).
