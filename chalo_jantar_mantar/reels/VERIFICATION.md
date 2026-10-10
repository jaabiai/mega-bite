# Verification — `Chalo_Jantar_Mantar_Reel_01m44s_to_02m35s_1080x1920.mp4`

Measured on the finished file by `tools/verify_reel.py` (raw output: [`verify_output_reel.txt`](verify_output_reel.txt), `OVERALL: PASS`).

## 1. Format and duration

| Requirement | Measured |
|---|---|
| 1080 × 1920, 9:16 | 1080 × 1920 → width/height = 0.5625 exactly, square pixels |
| 30 fps, H.264 MP4 | constant 30/1, H.264 High, yuv420p, BT.709, 5.73 Mb/s, 37.85 MB |
| exactly 51 seconds | **container duration 51.000000 s**, video stream 51.000000 s, 1530 frames at exact 1/30 s steps (0.000 … 50.9667 s) |

## 2. Audio

* **2,390 / 2,390 AAC packets are byte-identical** (SHA-256 per packet) to the landscape/original packets from 104.000 s to 154.9867 s; the first one sits at 0.000 s of the Reel (no offset, no pre-roll). Codec, rate, channels unchanged (AAC-LC 48 kHz stereo).
* Audio stream length 50.987 s: the last whole AAC frame before 155.000 s ends at 154.9867 s (**13.3 ms short**; AAC frames are 21.3 ms and 155.000 s is not a frame boundary). The container's 51.000 s comes from the video.
* Decoded audio vs the song decoded from its start: lag 0 samples; SNR 35.7 dB; below 2 kHz the difference is 103 dB under the signal (vocals, bass and beat are untouched). 91 % of decoded samples are bit-identical; the rest differ only in noise-filled high-frequency content, because a decoder started at the cut has a different noise-substitution state — the packets themselves are identical. The first 2 AAC frames (43 ms) lack their overlap partner (inherent to any AAC cut).
* A first encode of this file carried 33 hidden pre-roll packets (0.7 s of earlier audio) behind an edit list; that was found by this suite and removed (`-copypriorss 0`) before the final encode.
* Nothing was added or mixed: no music, no effects.

## 3. Lyrics, hooks, branding

* Lines L35-L54 — all 20 sung lines of 01:44-02:35, none missing, none from outside the section; Roman letters only (every one of the 151 strings the engine drew); 0 spelling-check problems; OCR of 50 frames (1 per second) of the final MP4 finds no SUNO / Mira / @handle text and no Devanagari.
* Hooks present at their own positions: **Vote Chori! Gaddi Chor!** (L39), **Ye Mulk Tera Baap Ka Nahin!** (L43), **Chalo Jantar-Mantar!** (L51, L52).

## 4. Layout

* Settled lyric text (932 placements checked): ≥ 81 px from the left, ≥ 85 px from the right, top margin ≥ 411 px, bottom margin ≥ 464 px → inside the frame and clear of the Reels header and caption/button zones. (During hook entrances words intentionally fly in from outside the frame for a few frames.)
* No pillar/letter-boxing: side-edge columns are never black; the only top-edge near-black run is a single whip-transition frame; the bottom edge has a dark crowd/ground silhouette strip of at most 88 px (scene content, not a bar). Picture fades 0.2 s in / 0.3 s out.

## 5. Synchronisation — what was measured

* Mapping: Reel frame *n* shows song time 104.000 + *n*/30; the audio starts at the packet that sits at 104.000 s.
* Hook onsets measured from pixels of the finished MP4 vs the timing file: red banner of "Vote Chori!" first visible at frame 290 (timing file: 289.2) = **+27 ms**; saffron "Chalo" slab at frame 1223 (timing file: 1221.0) = **+67 ms**.
* Per-line onsets measured by bisection with OCR on the MP4 (8 lines): the line's first word becomes readable **−20 … +60 ms** around the timing file's start (median −2 ms).
* OCR of every line once fully built: regular lines 0.95 mean letter match (16 lines; italic or flag-covered lines read worst: L53 0.58, L45 0.75, L47 0.82), "Vote Chori!" 0.78, "Ye Mulk Tera Baap Ka Nahin," 1.00, both "Chalo Jantar-Mantar" lines 1.00.
* Not independently proven: that the phase-1 line times are exact against the vocals. Coarse check on this file's own audio: the strongest vocal-band onset within ±0.35 s of a line start is a median 200 ms away (drums share the band, so this is not precise). Word reveals inside a line are proportional to syllable counts.

## 6. Existing files

Landscape MP4 SHA-256 unchanged (`2d9bc934…99f`); `git status` outside `reels/` clean and `git diff` empty; all 52 files of the pre-work SHA-256 manifest (original MP4, portrait video, lyrics, timing, overrides, docs, tools, assets) match.
