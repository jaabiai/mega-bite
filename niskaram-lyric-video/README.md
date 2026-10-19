# حَيَّ عَلَى الصَّلَاةِ — Cinematic Malayalam lyric video

Production source for the *Niskaram / നിസ്കാരം* lyric video by **Miraya Studio**.
Everything is script-driven, so the film can be re-rendered after any change (new lyrics, different shots, new credits).

| | |
|---|---|
| Frame | **2.39:1 widescreen, 1920 × 804**, 24 fps, H.264 + AAC 320 k |
| Intro | **One** adhan call (*Hayya ʿala-ṣ-ṣalāh*, 11.6 s) – the second call and the humming at the start of the song are cut out |
| Song | `inputs/song.mp3` from 0:13.0 (on a strong beat just before the first verse), blooming out of the adhan's echo at 11.3 s |
| Lyrics | Left lower-third, Anek Malayalam ExtraBold, wrapping to 2–3 short lines; Arabic lines switch to Naskh automatically |
| Visuals | One shot per lyric line, chosen for what the line says; every picture change lands on the lyric change |
| Logo | Miraya Studio badge as a quiet corner bug for the whole film, large on the end card |
| Length | 5 min 06 s |

![title](docs/preview_title.jpg)
![lyrics](docs/preview_lyrics.jpg)
![end card](docs/preview_endcard.jpg)

## Timeline

| Time | What |
|---|---|
| 0:00 – 0:11 | Adhan (first call only). Opening credits, each 2.2 s and large: **Music** – Miraya Studio · **Editor** – Jabir Varikkodan · **Mixing & Visuals** – Miraya Studio · **Lyrics** – Jabir Varikkodan. |
| 0:09 – 0:14 | The calligraphic Arabic title **حَيَّ عَلَى الصَّلَاةِ** (the word "Title" is not shown) builds over a moonlit sea while the song fades in under the adhan's echo. |
| 0:13 – 5:00 | Song, 54 lyric lines. Film time = song time − 1.7 s (`project.json → song_in / song_film_start`). |
| 4:52 – 5:06 | End credits, then the full logo card ("Thank you for watching"). |

## Picture

* 55 shot clips + 3 texture overlays from Mixkit (see `docs/FOOTAGE_CREDITS.md`). `tools/plan_edl.py` maps each lyric line to a picture (hourglass for *desires fade*, a lone tree for *alone in the grave*, a storm for *the first question*, sujood for *did you pray*, rain for tears, a waterfall and rainbow for paradise, a sunrise for *success in both worlds* …); the four hook lines get a new picture each time they return. Section changes use light-bloom or dip-to-black transitions.
* Colour: custom teal-gold 3D LUT, highlight bloom, gold dust, soft vignette, fine grain (`tools/make_lut.py`, `tools/compose.py`).
* **Halal check:** all clips were reviewed frame-by-frame. There are no women, no exposed awrah, no music/dance/alcohol; the only people are men at prayer or reading the Quran, and hands.

## Lyrics — please proofread

The SRT that reached me contained only **four cues** (0:15–0:36). Those are exact (`inputs/lyrics_user_supplied_partial.srt`). The other **50 lines were reconstructed from the song itself** (two speech-recognition passes over the vocals, cross-checked, then written out in Malayalam) and may contain wrong words or spellings. They are in `inputs/lyrics.srt`; `docs/LYRICS_REVIEW.md` lists every line with a confidence note.

The song runs at 90 bpm and each lyric line is two bars (5.33 s), so the timings follow the music (the hook's 4th line therefore starts at 0:31.0 rather than the rounded 0:30 in the supplied SRT).

To correct the text, edit `inputs/lyrics.srt` (times relative to `song.mp3`) and run `./build.sh overlays final`. If the line count or meaning changes, adjust `tools/plan_edl.py` (one picture per line) and run `./build.sh shots base final`.

## Re-render

```bash
./build.sh all                 # footage → shots → overlays → audio → base → final   (~50 min on 4 cores)
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

## Swapping footage

Each shot in `edl.json` is `{id, in, t, tr, trd, z0, z1, cy, ...}`. To use your own clip put it at `$WORK/src/<id>.mp4` (any resolution/fps; it is cropped to 2.39:1 automatically) and give the shot that `id`. `in` is the in-point in seconds, `cy` shifts the 2.39:1 crop vertically (0 = top … 1 = bottom), `z0 → z1` is the slow push/pull. Then `./build.sh shots base final`.

## Notes

* Title spelling: the brief wrote `حي عل الصلاة`; the title uses the standard `حَيَّ عَلَى الصَّلَاةِ`.
* **Footage licence – please read before uploading.** All footage is from Mixkit. **23 of the 58 clips** (stars, moon and dusk time-lapses, the desert and several mosque exteriors, the texture overlays) are under the *Mixkit Stock Video Free License* (free for commercial use). The other **35 – including the drone mosque shots, the Quran, the prayer footage and the rain/storm shots – are under the *Mixkit Restricted License*: the clip page offers them "for personal use only"**. If the channel is monetised you need either the Envato licence for those clips or replacement footage. Per-clip status and links: [`docs/FOOTAGE_CREDITS.md`](docs/FOOTAGE_CREDITS.md). Swapping is a one-line change per shot (below).

## Swapping footage

Each shot in `edl.json` is `{id, in, t, tr, trd, z0, z1, cy, ...}`. To use your own clip put it at `$WORK/src/<id>.mp4` (any resolution/fps; it is cropped to 2.39:1 automatically) and give the shot that `id`. `in` is the in-point in seconds, `cy` shifts the 2.39:1 crop vertically (0 = top … 1 = bottom), `z0 → z1` is the slow push/pull. Then `./build.sh shots base final`.

## Notes

* Title spelling: the brief wrote `حي عل الصلاة`; the title uses the standard `حَيَّ عَلَى الصَّلَاةِ`.
* **Footage licence – please read before uploading.** All footage is from Mixkit. Only **11 of the 52 clips** (the stars/moon/dusk time-lapses, three mosque exteriors and the texture overlays) are under the *Mixkit Stock Video Free License* (free for commercial use). The other **41 clips – including the drone mosque shots, the Quran and the prayer footage – are under the *Mixkit Restricted License*: the clip page offers them "for personal use only"**. If the channel is monetised you need either the Envato licence for those clips or replacement footage. Per-clip status and links: [`docs/FOOTAGE_CREDITS.md`](docs/FOOTAGE_CREDITS.md). Swapping is a one-line change per shot (below).
* The song audio is untouched except for gain-neutral summing with the adhan and a −0.3 dB safety limiter; programme loudness is about −13.8 LUFS.
