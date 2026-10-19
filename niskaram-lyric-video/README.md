# حَيَّ عَلَى الصَّلَاةِ — Cinematic Malayalam lyric video

Production source for the *Niskaram / നിസ്കാരം* lyric video by **Miraya Studio**.
Everything is script-driven, so the film can be re-rendered after any change (new lyrics, different shots, new credits).

| | |
|---|---|
| Frame | **2.39:1 widescreen, 1920 × 804**, 24 fps, H.264 + AAC 320 k |
| Intro | Adhan call (*Hayya ʿala-ṣ-ṣalāh … Hayya ʿala-l-falāḥ*, 24 s) with the opening credits and the Arabic title |
| Song | `inputs/song.mp3`, starts at 23 s so its first beat lands exactly as the adhan fades (24.0 s) |
| Lyrics | Left lower-third, Anek Malayalam ExtraBold; Arabic lines switch automatically to Naskh |
| Logo | Miraya Studio badge as a quiet corner bug for the whole film, large on the end card |
| Length | 5 min 31 s |

## Timeline

| Time | What |
|---|---|
| 0:00 – 0:24 | Adhan intro. Credits: **Music** – Miraya Studio · **Editor** – Jabir Varikkodan · **Mixing & Visuals** – Miraya Studio · **Lyrics** – Jabir Varikkodan, then the calligraphic Arabic title **حَيَّ عَلَى الصَّلَاةِ** (the word "Title" is not shown). |
| 0:11.6 | The adhan is two takes spliced together with a hard cut. The audio is eased out/in around the splice and the picture dissolves through a warm light bloom, so the join is not noticeable. |
| 0:24 – 5:25 | Song. Lyric cues come from `inputs/lyrics.srt` (times are relative to the song file; `project.json → song_offset` shifts them onto the film timeline). |
| 5:05 – 5:31 | End credits, then the full logo card ("Thank you for watching"). |

## Picture

* 49 clips from Mixkit (see `docs/FOOTAGE_CREDITS.md`), cut to the song's energy: slow dissolves in the quiet passages, light-bloom flashes and faster cuts on the peaks.
* The four supplied lines are matched one-to-one: *worldly desires fade* → hourglass in the desert at sunset; *alone in the grave* → lone tree in the desert night; *the first question comes* → storm front; *"did you pray?"* → a light-flash into men in sujood, then the Quran and mosques at dawn.
* Colour: custom teal-gold 3D LUT, highlight bloom, gold dust, soft vignette, fine grain (`tools/make_lut.py`, `tools/compose.py`).
* **Halal check:** all 49 clips were reviewed frame-by-frame. There are no women, no exposed awrah, no music/dance/alcohol; the only people are men at prayer or reading the Quran, and hands.

## Lyrics — what was supplied

The request contained **four SRT cues** (0:15 – 0:36 of the song). They are in `inputs/lyrics.srt` and are rendered exactly as written. The rest of the song therefore has picture but no lyric text.

To add the remaining lines, replace `inputs/lyrics.srt` with the full file (timings relative to `song.mp3`) and run:

```bash
./build.sh overlays final
```

Lines that are mainly Arabic script are set in Arabic (right-to-left, Noto Naskh); everything else in Malayalam. Cues that follow each other within a second share one animated plate and cross-slide.

## Re-render

```bash
./build.sh all                 # footage → shots → overlays → audio → base → final   (~45 min on 4 cores)
./build.sh overlays final      # new lyrics / credits only (~10 min)
WORK=/scratch ./build.sh shots # keep the ~3 GB of intermediates somewhere else
```

Requirements: ffmpeg ≥ 6 (libx264, libass not needed), Node 18+ with Playwright + Chromium, Python 3 with Pillow.

| File | Purpose |
|---|---|
| `project.json` | sizes, song offset, credit texts and timings, logo bug |
| `edl.json` | the shot list (Mixkit id, in-point, start time on the film, transition, zoom) |
| `overlay/overlay.{html,js}` | all animated graphics, rendered frame-exactly in headless Chromium |
| `tools/*.py` / `tools/render_overlays.mjs` | footage download, shot building, LUT, audio mix, compositing |
| `fonts/` | Anek Malayalam, Noto Naskh Arabic, Aref Ruqaa, Cinzel, Cormorant Garamond (SIL OFL) |

## Notes

* Title spelling: the brief wrote `حي عل الصلاة`; the title uses the standard `حَيَّ عَلَى الصَّلَاةِ`.
* Footage licence: Mixkit clips are free for commercial and non-commercial use under the Mixkit Stock Video Free License, no attribution required. The end card still credits Mixkit. Please re-check the licence label on the Mixkit page of each clip before monetising.
* The song audio is untouched except for gain-neutral summing with the adhan and a −0.3 dB safety limiter; programme loudness is about −13.8 LUFS.
