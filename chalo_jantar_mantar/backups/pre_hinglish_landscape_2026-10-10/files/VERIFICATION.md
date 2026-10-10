# Verification report

Everything below was measured on the finished file (`Chalo_Jantar_Mantar_Lyric_Video.mp4`) or on the audio.
Raw output of the automated suite: [`verify_output.txt`](verify_output.txt) (`tools/verify.py`).

## 1. File, duration, audio (automated, PASS)

| Check | Result |
|---|---|
| Container | MP4, H.264 High, 1080 × 1920, **30 fps**, 8,016 frames, yuv420p, BT.709, ~2.5 Mbps (two-pass), 90.4 MB |
| Duration | **267.200 s** video = 267.200 s audio = 267.200 s original (difference 0.0 ms) |
| Stream start times | video 0.000 s, audio 0.000 s; first audio packets have identical timestamps to the original |
| Aspect ratio | 0.5625 (9:16) vs source 0.5628 (824 × 1464) |
| **Audio** | stream **bit-identical** to the original: MD5 of the AAC stream `250eedb6e69647ad0ee51cc62d0c750c` in both files (`-c:a copy`, no re-encode) |
| Original MP4 | untouched (SHA-256 `d039d759dc69689afbee9c41399a1a9b830a5db321199ca06d6d52c58dd94401`) |

## 2. Lyric text and spelling (automated, PASS)

* The 95 lines in `lyric_timing.json` are **byte-identical, in the same order,** to the 95 sung lines of the supplied lyrics file
  (nothing missed, duplicated, reworded or invented). Ellipses/punctuation such as `…`, `!`, `,` are kept exactly as written.
  The only extra text in the video is the title line taken from the lyrics file header ("चलो जंतर-मंतर — आवाज़ जनता की", first 3 s) and the source credits.
* All 60 distinct code points used have glyphs in the fonts that render them (Hind Bold / Rozha One / Khand Bold): **0 missing glyphs**,
  so no "tofu" boxes. Text is shaped with HarfBuzz (Raqm), so conjuncts (गद्दी, उँगली, ख़ामोशी …) render correctly.
* Decoded-video template match: at the middle of each of the **71/71 regular lines** the lyric actually visible on screen is the intended
  one (two repeated lines with identical text are indistinguishable by construction and counted as matches).
* The decoded video matches a fresh render of the same timeline (PSNR 35–37 dB at 16 sample times; the difference is H.264 compression only).
* Visual inspection of frames pulled from the encoded MP4: title, intro, each of the five special treatments (several moments each), chorus alternation,
  bridge emblems, outro, closing fade.

## 3. Synchronisation — how it was checked, and how far it can be trusted

There is no ground-truth lyric timing for this song, and the audio could not be *listened* to in the build environment, so sync was established
and cross-checked **from the signal**, with four independent kinds of evidence:

1. **Forced alignment, 4-run vote.** Whisper-turbo used with the supplied lyrics as the forced transcript (it only predicts timestamps).
   Two runs with different window phases agree on 77/95 line starts to within 0.4 s (median |Δ| = 0.02 s); the 18 disagreements cluster at window
   junctions, where the other runs outvote them (85/95 lines end up with ≥ 3 of 4 runs in agreement). Whisper's *free* transcription (independent segmentation)
   reproduced the vote in most places (e.g. 51.64, 103.56, 154.94 s) and exposed where the forced pass had gone wrong — the outro (line 94 at 254.3 s, line 95 at 258.9 s)
   and the "Vote Chori!" entry (≈ 222.8–223.0 s) — which were then corrected from the audio.
2. **Acoustic refinement of sparse passages.** In the spoken intro, the bridge and the outro Whisper's boundary marks the *end* of the previous line,
   not the vocal onset (e.g. line 3 was ~1.3 s early). 24 lines were set by hand from the acoustic evidence (1–4 kHz energy bursts, lulls, spectrograms, bar grid, free-decode boundaries); they are marked
   `manual` in `lyric_timing.json` (22 high-confidence, 2 flagged ambiguous). Review sheets of all 14 × 20 s spectrogram sections were inspected with line marks and bar lines overlaid.
3. **Statistical bias test.** Averaging vocal-onset strength around all 95 line starts: the average onset peak is at **+0.04 s** after the marks
   (rap/chorus lines, n = 85: +0.04 s; intro lines, n = 9: +0.04 s) — i.e. no systematic early/late bias beyond a few tens of milliseconds.
4. **Suno's own lyric-scroll layer burned into the source video** (its text can't render Devanagari, but its scroll steps are visible):
   91/95 lines have a scroll step within the expected window (random marks: 73 % ± 4 %), and the lag between my line start and Suno's step is tightly clustered
   (median +0.50 s, interquartile width 0.38 s vs 0.83 s for random marks) — consistent with its scroll-animation latency.

Also consistent: the track is a steady 92.66 BPM (bar = 2.59 s, phase stable to ±0.03 s); the outro chant lines each occupy exactly one bar, and the
abrupt energy cut at 254.1 s coincides with the end of line 93.

**Honest limits**
* Typical accuracy for sung/rap lines is about ±0.2–0.3 s; sparse spoken lines (intro/bridge/outro) are tighter (~±0.1 s).
  Lines whose timing is least certain are labelled in `lyric_timing.json` (`confidence`): **35** (103.85 s; held chorus note vs first rap syllable) and **89** (240.8 s)
  are ±0.3 s; lines 25, 45, 77, 85, 86 had only 2/4 votes (45 and 86 were confirmed by free decoding).
* A Whisper-small run was tried as a second model but was unusable (timestamps quantised to 1 s and drifting); it only reproduced the same intro boundaries as turbo.
* A coarse spectral-flux diagnostic (percentile of line starts vs random times, 61.8 vs 43–58 for shifted controls) is only weakly informative in dense rap and is not relied on.
* Please watch it once with sound: if any line feels early/late, edit `start`/`end` (or `meta.global_offset_s`) in `lyric_timing.json` and re-render (see README).

## 4. Deliberate deviations from "keep everything as is"

| Item | What was done and why |
|---|---|
| Resolution | **1080 × 1920**, not 4K. The source is 824 × 1464 and very soft (85 kbps); 4K would be a 2.6× upscale of blur. Type and vector art are sharp at 1080 p. |
| Frame rate | **30 fps** (source 10 fps): needed for smooth text motion; the footage colour field is linearly interpolated between source frames. |
| File size | 90 MB (two-pass ~2.5 Mbps) so the file can live in the git repo (100 MB per-file limit). A higher-bitrate master can be produced with `tools/final_encode.sh` (raise `-b:v`). |
| Suno layer | Suno's unreadable ghost lyric layer was removed from the footage (it would collide with real captions). The source credits `by @mirayastudio` and `MADE WITH SUNO` were **kept** (lifted from the source frames and re-placed top/bottom). |
| Imagery | No photographs/stock footage were reachable, so crowd, flags, Jantar Mantar (Samrat Yantra), wheel and emblems are **procedural silhouette art**, not photoreal images. |
