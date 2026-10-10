# Verification — `Chalo_Jantar_Mantar_Hinglish_Landscape_1080p.mp4`

Everything below was measured on the finished file. Raw output of the automated suite: [`verify_output_hinglish_landscape.txt`](verify_output_hinglish_landscape.txt)
(`hinglish_landscape/tools/verify_landscape.py`, run as `OVERALL: PASS`). Where a check is weaker than it sounds, that is said.

## 1. File and format (automated, PASS)

| Check | Result |
|---|---|
| Resolution / aspect | **1920 × 1080**, 16:9, square pixels |
| Frame rate / count | constant **30 fps**, **8,016** frames = 267.2 s × 30 |
| Duration | container 267.200 s = original 267.200 s; video and audio streams equal length |
| Codec / size | H.264 High @4.1, yuv420p, BT.709, two-pass 2.64 Mb/s + AAC 197 kb/s, **95.1 MB** (< GitHub's 100 MB limit) |
| Encode fidelity | PSNR 49.8 dB (mean) between the final H.264 and the near-lossless render it was made from |

## 2. Audio (automated, PASS)

* Audio stream MD5 `250eedb6e69647ad0ee51cc62d0c750c` in **both** the final file and the original upload → bit-identical (`-c:a copy`); decoded PCM identical too; codec/bit-rate identical (AAC 48 kHz stereo 196,563 b/s).
* No music, vocals or sound effects were added. (The audio is read only to derive a kick-drum envelope that drives visual pulses.)
* I cannot *listen* in this environment, so audio–picture feel was not judged by ear.

## 3. Lyrics, Roman Hindi and branding

| Check | Result |
|---|---|
| Lines | 95 in the timing file; ids, order, start/end times and Devanagari source text are identical to the phase-1 timing file; the supplied `lyrics.txt` equals the 95 source lines (none added, dropped, reordered) |
| Spelling (Devanagari → Roman) | word-by-word consonant-skeleton comparison, vowels/anusvara/glide-y ignored by design: **0 problems in 95 lines**; a negative control (3 injected errors) is caught. **Vowel spellings are conventions, not machine-verified → human proofreading recommended** (`data/roman_map.json`). |
| Devanagari on screen | none: the text engine refuses any non-Latin string (`assert_roman`), every one of the 315 distinct strings drawn is Latin-only, and an OCR sweep of 133 frames (every 2 s) of the **final MP4** found no non-Latin character |
| Words drawn | every drawn word is a lyric word or part of the song title; the only single-letter sprites are the per-letter hook animations (12) |
| Branding | OCR sweep found no SUNO / MIRA / studio / @handle / credit text; the background code contains no text drawing and never reads the original video; the compositor draws only lyrics and the 3-s song-title card |
| Legibility (OCR) | letters recovered when each line is fully built: regular lines **98 %** (n=71), march 100 %, people 100 %, stamp 100 %, wake 93 %, defiant 78 % — the one sub-60 % reading (L94) is a sample taken before the second row had appeared |
| Safe area | settled lyric text (5,573 sprite placements): smallest margin to a frame edge **69 px** (bottom), 155 px left, 162 px right — inside the 5 % action-safe area. While hook words slide in/out, 26 of 2,672 sampled frames show a word box crossing the frame edge momentarily (deliberate entrance/exit moves) |

## 4. Synchronisation — what is and is not verified

* Line timing = the **phase-1 timing, reused unchanged** (confirmed identical): Whisper-turbo forced alignment of the supplied lyrics, 4-run vote (48 lines 4/4, 18 lines 3/4, 5 lines 2/4) plus 24 lines refined manually from the spectrogram; confidence: 88 high / 5 medium / 2 low (±0.3 s). Its evidence is in the project's `VERIFICATION.md` §3.
* New in this run (coarse, informational): distance between each line start and the strongest vocal-band onset within ±0.35 s — median 188 ms, 90th percentile 311 ms, 44 % of lines within 150 ms. Drum transients in the same band make this noisy; it is **not** proof of sync.
* Inside a line, words are revealed over the line's sung span in proportion to syllable counts — **approximate, not word-level aligned**.
* The video was decoded and checked to show the intended line at the right time (OCR table above); nothing else about sync was measured.

## 5. Hooks

Each hook has its own typeface, colours, motion and effects and appears only at its own lines (7 / 10 / 2 / 3 / 2 lines — see `README.md`); they are never shown together. Full-resolution frames of every hook, taken from the encoded MP4 at several moments each, were inspected by eye.

## 6. Project safety (automated, PASS)

* 52 pre-existing files compared with the SHA-256 snapshot taken before any change: **0 differences** (original MP4, phase-1 portrait video, lyrics, timing, overrides, docs, tools, assets).
* Original uploaded MP4 SHA-256 `d039d759…94401` unchanged; phase-1 portrait video SHA-256 `93e8b527…f4f8da` unchanged.
* New files live only in `hinglish_landscape/`, `output_hinglish_landscape/`, `backups/`; the untouched starting point is git commit `6a8cf89` (a local tag `pre-hinglish-landscape` marks it too, but the tag could not be pushed).

## 7. Visual review (manual)

The whole video was reviewed as contact sheets at 2-second intervals (134 frames) plus full-resolution hook frames from the final MP4. One defect was found and fixed before encoding:
two consecutive shots (pre-chorus and chorus) both used the large tricolour in the same position for ~20 s; the pre-chorus shot was replaced by a rising-sun/mountain/birds shot.

Known limitations of the look: the background is procedurally generated, so it is stylised and slightly soft rather than photographic; the large out-of-focus flag shots (four, spread through the song) are a deliberate depth-of-field look and a matter of taste.

## 8. Not met

* **Requirement 4 (fresh stock footage from Pexels/Pixabay etc., with licence check): not met.** Network policy blocked all those hosts. The background is original generated footage instead (see `README.md`).
