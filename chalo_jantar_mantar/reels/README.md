# Vertical Reel — song 01:44.000 → 02:35.000

**File:** [`Chalo_Jantar_Mantar_Reel_01m44s_to_02m35s_1080x1920.mp4`](Chalo_Jantar_Mantar_Reel_01m44s_to_02m35s_1080x1920.mp4)
(37.9 MB) · review sheet: [`Chalo_Jantar_Mantar_Reel_ContactSheet.png`](Chalo_Jantar_Mantar_Reel_ContactSheet.png) · proof: [`VERIFICATION.md`](VERIFICATION.md), [`verify_output_reel.txt`](verify_output_reel.txt)

| | |
|---|---|
| Format | H.264 High, **1080 × 1920 (9:16)**, **30 fps**, 1530 frames, yuv420p / BT.709, 5.7 Mb/s, AAC-LC 48 kHz stereo, `+faststart` |
| Duration | **exactly 51.000000 s** (container and video stream) = song 104.000 s … 155.000 s |
| Audio | the **original AAC packets, copied byte-for-byte** (2,390 packets, 104.000 s → 154.987 s). No music, no sound effects, no re-encode, no fade, no mix. |
| Lyrics | Roman Hindi (Hinglish), lines L35–L54 (all 20 sung lines of the section), timing = the existing `lyric_timing_hinglish.json`, unchanged |
| Hooks in this section | **Vote Chori! Gaddi Chor!** (L39, 01:53.6) · **Ye Mulk Tera Baap Ka Nahin!** (L43, 02:04.5) · **Chalo Jantar-Mantar!** (L51 02:24.7, L52 02:26.8) |
| Background | generated graphics from the project's own procedural engine, re-framed for 9:16 — **not stock footage** (same as the landscape video) |

## How it was recomposed for vertical (not rotated, not stretched, not cropped from the landscape picture)

* **Backgrounds** — the five shots of this section (red protest dusk → storm → fists against a saffron sky → flags in dark smoke → Jantar-Mantar sunrise)
  are re-rendered *natively* at 720 × 1280 and upscaled 1.5× (same pipeline as the landscape build): taller sky, sun placed for portrait, bigger skyline /
  crowd / flag sprites, vertical whip transitions between shots, same cut points on the song's bar grid.
* **Typography** — rebuilt for the tall frame: lyric lines are stacked in 1-4 centred rows inside a 900 px safe width, in the lower-middle of the frame
  (rap lines in condensed capitals with word-by-word punch-ins and tricolour underline; the melodic lines in gold italic with blur-in and a light sweep).
  Safe zones: ≥ 81 px from the sides, ≥ 411 px from the top, ≥ 464 px from the bottom (clear of the Reels header and caption/button areas).
* **Hooks** re-staged as tall stacks: *stamp* (two rotated two-line banners, shake, ink splatter, red pulse) · *defiant* (3 rows, "NAHIN," enlarged, cracks,
  shock ring; the landscape version's letterbox bars are replaced by a red vignette pinch because black bars are unwanted here) ·
  *march* (saffron slab + giant Anton word(s) slamming in from alternating sides, split at the hyphen when too wide, speed lines, tricolour bar).
* **Picture-only fades:** 0.2 s in and 0.3 s out. The audio is not touched.
* A 3-second title card is not used here (the Reel starts mid-song).

## Things worth knowing

* The Reel starts **0.15 s inside line L35** ("Vote chori ke uthte sawaal,"), because the line begins at 103.85 s: its first word is already up when the picture fades in.
  The next line (L55 starts 154.94 s) is not shown — the picture fades out first.
* **Audio length:** the container is exactly 51.000 s because the video is. AAC frames are 21.333 ms, 104.000 s is exactly a frame boundary but 155.000 s is not, so
  the copied audio ends at the last whole frame before it: 154.9867 s (**13.3 ms short of 155.000 s**, i.e. less than half a video frame). Re-encoding the
  audio would have given sample-exact length but would no longer be the original stream. The first two AAC frames (43 ms) of any cut decode without their
  overlap partner, so the very start is a ~40 ms soft onset (hidden by the picture fade-in).
* Line timing is the phase-1 timing (Whisper forced alignment + manual refinement) reused unchanged; word-by-word reveals inside a line are proportional to
  syllable counts, not word-level aligned. See `VERIFICATION.md` §5 for what was measured on this file.
* Nothing existing was modified; all new files are in this `reels/` folder.

## Rebuild

```bash
cd chalo_jantar_mantar/reels/tools
export RL_WORK=/path/to/scratch  RL_SOURCE_MP4=../../output_hinglish_landscape/Chalo_Jantar_Mantar_Hinglish_Landscape_1080p.mp4
python rl_render.py preview OUTDIR 106.6 115.2 126.0        # single frames, by SONG seconds
python render_reel.py render --workers 4                    # 17 chunks of 90 frames, ~5 min on 4 cores
python render_reel.py encode ../Chalo_Jantar_Mantar_Reel_01m44s_to_02m35s_1080x1920.mp4   # refuses to overwrite
python verify_reel.py ../Chalo_Jantar_Mantar_Reel_01m44s_to_02m35s_1080x1920.mp4          # needs rapidocr-onnxruntime for the OCR checks
```

| File | Role |
|---|---|
| `tools/rl_common.py` | installs a 1080×1920 / 720×1280 copy of the landscape `hl_common` before the (read-only, unmodified) landscape engine is imported; clip constants |
| `tools/rl_timeline.py` | the five vertical shot specs, grades, transitions |
| `tools/rl_text.py` | vertical typography + hook staging |
| `tools/rl_render.py` | frame compositor (frame *n* ↔ song time 104.0 + n/30) |
| `tools/render_reel.py` | parallel chunk render + x264 encode with the original audio packets copied |
| `tools/verify_reel.py` | the verification suite |
