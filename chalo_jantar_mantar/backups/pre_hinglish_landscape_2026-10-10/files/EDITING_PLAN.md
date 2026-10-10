# चलो जंतर-मंतर — Cinematic Lyric Video: Editing Plan

## 1. What was inspected

| Item | Finding |
|---|---|
| Source file | `99f29bcc-…mp4` (left untouched; SHA-256 `d039d759…c9401`) |
| Video | H.264, **824 × 1464 portrait (≈9:16)**, **10 fps**, 267.2 s, ~85 kbps (very low bit-rate) |
| Audio | AAC-LC stereo 48 kHz, ~197 kbps, 267.2 s |
| Content | A Suno-style visualizer export: slowly drifting blurred pastel colour field, a crayon sunburst/ballot-ring cover tile, `by @mirayastudio`, `MADE WITH SUNO`, and Suno's own scrolling lyric layer. That layer **cannot draw Devanagari**, so only punctuation (`! … , -`) and the Latin section labels (`[Beat Begins – Low Male Chant]`, `Vote Chori!` …) are visible and appear as stray ghost text. |
| Lyrics file | 95 sung lines in 13 sections (Intro → Final Voice), Devanagari with a few Latin words (`Vote Chori!`) |
| Audio structure | Steady **92.66 BPM** (bar = 2.59 s, beat phase stable to ±0.03 s across the song): spoken intro (0–30 s) → chant → rap verses on a 1-bar-per-line cadence → choruses → sparse bridge (≈180–202 s) → outro |
| Tooling available | FFmpeg 6.1 (libx264/libass), Python 3.13 + NumPy/PIL(Raqm)/SciPy/onnxruntime, sherpa-onnx Whisper models (no GPU, no internet to stock-footage or model hubs other than GitHub releases / PyPI / Google-Fonts repo) |

## 2. Key decisions

* **Edit, not replace.** The original footage is kept as the base layer: its animated colour field drives the graded background (so lighting still "breathes" with the original), its cover art becomes the hero tile, and its attribution marks (`by @mirayastudio`, `MADE WITH SUNO`) are lifted from the source frames and kept (small, bottom/top). Only Suno's unreadable ghost-lyric layer is removed (it cannot render Devanagari and would collide with the real captions).
* **Audio is not re-encoded.** The finished file's audio stream is a bit-exact stream copy (`-c:a copy`) of the original AAC track.
* **Aspect ratio:** 9:16 portrait kept. **Resolution:** 1080 × 1920 (the source is only 824 × 1464 and extremely soft, so 4K would be a 2.6× upscale of blur; the type and vector art are crisp at 1080p, which is the practical maximum for this format).
* **Frame rate:** 30 fps instead of the source 10 fps — necessary for smooth text motion; the footage itself is time-interpolated.
* **Imagery:** no stock footage/photos are reachable from the build environment, and fabricating photoreal people would be inappropriate, so the "dignified" imagery is *procedural silhouette art*: a peaceful crowd with tricolor flags, the Samrat Yantra stair-gnomon (Jantar Mantar), a 24-spoke wheel ring, and small line-art emblems keyed to the words (voting finger → वोट, Constitution → संविधान/अधिकार, scales → इंसाफ़, diya → दीप).
* **Palette / type:** deep navy + saffron / white / green accents. Hind Bold (lyrics), Rozha One (patriotic lines), Khand Bold (slogans) — all SIL OFL fonts, shaped with HarfBuzz/Raqm so conjuncts and nuqta forms are correct.

## 3. Lyric synchronisation method

1. Whisper (turbo, ONNX) used as a **forced aligner**: the supplied lyrics are teacher-forced as the transcript and the model predicts only the timestamp tokens, so the text is exactly the supplied Devanagari.
2. Several passes with different window phases/sizes → per-line **majority vote** (outliers at window junctions rejected).
3. Cross-checks: free transcription (independent segment boundaries), the 92.66 BPM bar grid, spectrogram review of all 14 × 20 s sections, a statistical onset-bias test,
   and Suno's own scroll layer burned into the source video (see `VERIFICATION.md`).
4. Sparse passages (spoken intro, bridge, outro, pauses) refined to the real vocal onset from 1–4 kHz energy bursts and spectrograms (Whisper's boundary there marks the *end* of the previous line); 24 lines are hand-set this way and labelled in the timing file.
5. Everything lands in the editable `lyric_timing.json` (see below).

## 4. Special treatments

| Phrase | Treatment |
|---|---|
| देशवासियो… जागो! | Rozha One, rising "dawn" bloom, soft wipe reveal; "जागो!" lands with flash + shock-ring |
| चलो जंतर-मंतर | Khand slam-in, camera shake, tricolor underline draws on, Jantar Mantar silhouette lights up |
| Vote Chori! गद्दी चोर! | Rubber-stamp slam in a saffron-framed plate, rotation, flash, ring, shake |
| ये मुल्क तेरा बाप का नहीं! | Word-by-word punch-in timed to character count, tricolor underline + flash on the last word |
| ये जनता का हिंदुस्तान है! | Rozha One in a saffron→white→green gradient, rotating Ashoka-style wheel behind, rising sun bloom |

## 5. Deliverables
`Chalo_Jantar_Mantar_Lyric_Video.mp4`, `lyric_timing.json` (+ `.srt`, `.ass` exports), the renderer (`tools/`), fonts, and a verification report.
