# MEGA BITE - "Invisible Messages" iPhone tip (video edit)

Automated, repeatable edit of the channel's iPhone tip video: graded presenter shots, phone
scenes built from the screen recording (zoom + highlights), free B-roll, word-by-word captions
with a moving neon underline, subscribe / share reminders, logo on every frame, and a clean
synthesised sound bed.

Status: **style approval pending** - nothing is rendered to final until a palette and font are
approved (see `previews/`).

## What is in here

| path | what |
|---|---|
| `captions/en.srt` | SRT as delivered (English translation) |
| `captions/boundaries.json` | where each SRT cue really starts in the audio (see *SRT timing* below) |
| `captions/words.json`, `words.retimed.srt` | per-word timings / re-timed SRT (generated) |
| `config/styles.json` | candidate palettes + fonts |
| `scripts/edl.py` | **edit decision list** - what is on screen at every second |
| `scripts/*.py`, `render/` | pipeline (below) |
| `previews/` | style boards + preview clips for approval |
| `assets/` | logo, fonts (SIL OFL), licences |

## Pipeline

```
make_words.py      SRT + audio envelope + boundaries.json  ->  captions/words.json
build_assets.py    HDR screen recording -> SDR frame sequences per scene; free Mixkit B-roll download
build_timeline.py  EDL + words -> timeline.json
render_base.py     presenter (graded, framed, slow push-in) + B-roll  ->  base.mp4
render/overlay.html + render_overlay.js   Chromium draws every overlay frame (captions, logo,
                   phone scenes, highlights, CTAs, end card) deterministically from timeline.json
build_audio.py     synthesised SFX + music, ducking, loudness normalisation -> mix.wav
compose.py         overlay frames over base + audio -> MP4
```

Heavy intermediates (downloaded sources, frames, renders) live outside git under `$MB_WORK`.

```
python3 scripts/build_assets.py
python3 scripts/build_audio.py $MB_WORK/audio/mix.wav
python3 scripts/compose.py --out final.mp4 --palette A_ember --font montserrat --audio $MB_WORK/audio/mix.wav
```

## Notes on the source material

* **SRT timing** - the delivered SRT ends at 1:32 but the speech runs to 1:52 and the cues drift
  by up to ~20 s (e.g. "Slam" is said at 0:57, the SRT has it at 0:47). Cues were re-timed to the
  real speech (offline ASR translation used only as a timing guide, then snapped to the pauses in
  the audio). Wording is exactly the delivered SRT.
* **Screen recording** is HDR (PQ / BT.2020). UI white is recorded at ~100 nit, so it is mapped to
  SDR white (a normal 203-nit mapping makes the UI look grey).
* **Privacy** - the Messages list (bank SMS, phone numbers) at 0:06-0:09 of the screen recording is
  never shown; the cut happens as the app launches.
* **Narration** peaks at +0.7 dBFS (clipped); it is de-noised, EQ'd, compressed and limited.

## Licences

* Fonts: Montserrat / Sora / Poppins - SIL Open Font License 1.1 (free for commercial use).
* B-roll: Mixkit stock clips - Mixkit Free License (commercial use, no attribution required).
  IDs used: see `scripts/edl.py` (`clip`).
* All sound effects and music are synthesised by `scripts/build_audio.py` (no third-party audio).
* Logo: supplied by the channel.
