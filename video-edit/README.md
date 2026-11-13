# video-edit — MEGABYTE tutorial edits

Scripted, repeatable edit of a face-cam + iPhone screen-recording pair. Everything is code, so a different
palette, caption wording or timing is a re-render away. Every video is a *project* (`projects/<name>/`) and every
tool takes `--project <name>` (`prep_screen.py` / `render*.py` / `mix_audio.py`):

| Project | Video |
|---------|-------|
| `lock-google-history` | Lock your Google search history (16:9 + reel) |
| `whatsapp-face-id` | Hide WhatsApp calls from the iPhone call log with "Require Face ID" (16:9 + reel) |
| `iphone-48mp-camera` | Shoot 48 MP photos on iPhone: Settings > Camera > Formats, Camera app Aspect / Format (16:9 + reel, Crimson Red palette) |
| `aadhaar-email-link` | V Create channel: link your email ID to Aadhaar. Cinematic style (`render_cine.py`), illustrated app screens because the app blocks screen recording |
| `own-ai-assistant` | V Create channel: build your own free AI assistant (Tab). Aurora style (`render_aurora.py`): full-screen 3D title, caption dock, no end card, continuous reel |
| `call-recording-tone` | V Create channel: record calls without the spoken announcement (Google Phone app, Android). Studio style (`render_studio.py`), Android phone frame, no end card, the reel is the whole talk |
| `iphone-case-review` | V Create channel: iPhone case review shot as one 4K take. Showcase style (`render_showcase.py`): film grade, virtual camera, 2.39:1 letterbox, tracked feature callouts, no end card, 2-minute reel cut |

A project folder holds `timeline.py` (scenes, screen re-timing, camera, taps, highlights, steps, CTAs, sound effects, grade
overrides), `captions_data.py` (English caption chunks) and `screen_rules.py` (what to blur / remove in the screen recording).
Scene kinds: `face`, `broll` (`clip` landscape id, `reel_clip` vertical id), `graphic` (`graphic`: `search-lock`, `call-log`,
`face-unlock`), `phone`, `end`.

## Pipeline

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `audio_clean.sh` | declip → rumble high-pass → RNNoise (`bd.rnnn`) → EQ → de-ess → soft gate → compression → 2-pass loudnorm (−14 LUFS / −1.5 dBTP) |
| 2 | ffmpeg (see below) | iPhone HDR (HEVC, BT.2020 PQ) → SDR BT.709, constant 60 fps |
| 3 | `prep_screen.py` + `lib/screenprep.py` | blur private text, remove the screen-recording indicators (fixed positions, or found by colour for the wandering ones) and the AssistiveTouch bubble (alpha un-mixing from two flat-background frames, or rebuilding the known background: flat fill / header + search-field redraw) |
| 4 | `render.py` | compositor: cinematic grade, B-roll, phone-in-frame scenes with camera zoom + highlight rings + tap ripples, word-highlight captions, CTAs, wipes, end card → H.264 |
| 5 | `mix_audio.py` | voice + ducked music bed + timeline-synced SFX → `mix.wav` |
| 6 | ffmpeg | mux video + mix (`alimiter=limit=0.89:level=disabled` so the limiter does not add make-up gain, AAC 320k) |
| 4b | `render_reel.py` | vertical 9:16 (1080×1920) version for Reels / Shorts: tall face card on a blurred backdrop, stacked phone scenes with a caption header, B-roll as a rounded card, short outro; audio via `mix_audio.py --total 104.93` |
| QA | `qa_privacy.py`, `qa_privacy_screen.py` | OCR sweeps that fail if any e-mail / account name is still legible |
| Extra | `make_thumbnail.py` | 1280×720 thumbnail |

```bash
# 2) HDR -> SDR, 60 fps
ffmpeg -i RPReplay.mp4 -an -vf "fps=60,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv444p" \
       -c:v libx264 -crf 8 -pix_fmt yuv444p screen_sdr60.mp4
# 3) clean it in 20 s slices (parallel), then concat -> screen_clean60.mp4 (first frame == recording time 8.0 s)
python prep_screen.py screen_sdr60.mp4 8 28 seg0.mp4   # ... 28-48, 48-68, 68-87.7
# 4) render (split in chunks for speed; chunk edges at frame boundaries), then concat
#    16:9 -> render.py ; 9:16 reel -> render_reel.py (same arguments, 5 chunks: 0-26.5667, -48, -70, -91.9, -104.9333)
python render.py --face main.mp4 --screen screen_clean60.mp4 --broll-dir broll/ --start 0 --end 26.5667 --out p0.mp4
```

## Design tokens (approved)
* Palette **Volt Lime**: accent `#C6F432`, secondary `#FF5C39`, background `#0A0D0B → #18221B`, text white. No blue anywhere.
* Fonts: Poppins ExtraBold / Black (captions, titles), Poppins SemiBold / Medium (labels) — SIL OFL, in `assets/fonts/`.
* Logo: drop the real file at `assets/logo/logo.png` (RGBA). Until then a placeholder "MB" mark is drawn.

## Timing data
`projects/<name>/timeline.py` and `projects/<name>/captions_data.py`. `captions/*script_en.md` list the captions for review.

## Licences
Music / SFX / stock clips: Mixkit (Mixkit licence — free for commercial use, no attribution required).
Music "Lo-Fi 05" by Lily J; clips 39782, 25451, 144 (Google video), 41165, 4805, 4915 (wide) and 41173, 49939, 39833 (reel) (WhatsApp video); SFX 1492, 1489, 1109, 3005, 3124, 2856, 2852, 2354, 933.

## Cinematic style (V Create)

`render_cine.py --project NAME --format wide|reel` renders projects whose timeline sets `STYLE = "cine"`: a 2.29:1
letterbox, centred subtitles with a gold active word (Plus Jakarta Sans), chrome / gold Cinzel titles, a logo sting,
whole-phone camera moves with spotlight highlights and callout labels, light-leak / whip / dip transitions, and
subscribe / like / comment / share prompts (`TL.CTAS`). Graphics live in `lib/cine.py`; illustrated phone screens in
`lib/appmock.py` + the project's `screens.py`. `tools/face_track.py` (OpenCV YuNet) writes `face_track.json`, which the
face shots follow. In 9:16 the presenter is a full-bleed vertical crop lowered under a blurred ceiling
extension (text never sits on the face or body), and `TL.REEL_CUTS` / `TL.REEL_CTAS` make the reel a shorter edit
(`mix_audio.py --cuts` builds its audio). Fonts: Cinzel and Plus Jakarta Sans (SIL OFL). Music "Drawing the Sky" (Mixkit 678); SFX 1491, 1492,
2596, 1485, 2350, 2354, 933, 1109; clips 14669, 47735 (wide) and 41174, 18307 (reel).

## Aurora style (V Create, second look)

`render_aurora.py --project NAME --format wide|reel` renders projects whose timeline sets `STYLE = "aurora"`: ink-plum
backdrops with an orchid / rose / amber gradient, Anton + Outfit type (SIL OFL), and a full-screen extruded 3D title for
the topic (`lib/text3d.py`: the text block is drawn once and re-posed per frame as a stack of perspective-warped layers;
`TL.TITLE_BEATS`, section headers in `TL.HEADERS_3D`). Captions never sit on the picture: in 16:9 they live in a dock under
it, in 9:16 in a header above a rounded picture window. Calm karaoke captions (spoken words white, current word in the
gradient with a gliding underline), prism and light-sweep transitions, step chip on the empty side of phone scenes, no
end card (`TL.END_SWELL = 0` keeps the music flat at the end). The reel is the narration in order with a few whole
sentences left out (`TL.REEL_CUTS` at pauses, `TL.REEL_JOIN_SFX = False`). Kit: `lib/aurora.py` (re-skins `lib/cine.py`
through `cine.set_theme()`).

Screen clean-up for this project uses `screen_rules.FPS = 30` and a radial AssistiveTouch profile
(`BUBBLE["cal"]`, `screenprep.calibrate_bubble_profile`): flat surroundings are filled, otherwise the translucent overlay is
un-mixed. Music "Infinity" (Mixkit 440); clips 49042, 29050, 32457, 4196, 23073, 3298, 17999, 42123, 49381, 51123, 42130, 1787.

## Studio style (V Create, third look)

`render_studio.py --project NAME --format wide|reel` renders projects whose timeline sets `STYLE = "studio"`: a
broadcast-desk layout on a midnight grid with teal / cyan accents and a red REC dot, Archivo Black + Manrope type (SIL OFL).
The picture (face, B-roll or phone) sits in a rounded card with a thin teal edge; in 16:9 the left sidebar carries the logo
bug, the topic (`TL.TOPIC_KICKER`, `TL.TOPIC`), a transcript-style caption block (previous line dimmed, current line large
with a teal marker on the spoken word) and a numbered step badge (`TL.STEPS`, `TL.N_STEPS`); in 9:16 the card is on top and
topic / step / captions are stacked under it, so text never covers the presenter. The opening uses the full-screen 3D title
(`TL.TITLE_BEATS`, one beat at a time, `faces` white / accent / rec) and `TL.HEADERS_3D` for section headers; captions step
aside while a header or the logo sting is on screen. Transitions: push, scan and prism. Kit: `lib/studio.py`.

`TL.DEVICE = "android"` with `TL.SCREEN_SIZE = (720, 1608)` frames the recording in `lib/phone_android.py`: slim even
bezels, flat aluminium rails, keys on the right and a punch-hole camera in the top-left corner of the display
(`phonescene.PhoneScene(device=..., src=...)`). Music "Digital Clouds" (Mixkit 175); clips 42123, 39803, 309;
SFX 1485, 1491, 1492, 2596, 2350, 2354, 933, 1109.

## Showcase style (V Create, product film)

`render_showcase.py --project NAME --format wide|reel` renders projects whose timeline sets `STYLE = "showcase"`: a single
4K face-cam take treated as a product film.

* **Grade** (`lib/grade_cine.py`): a colourist-style node chain at output resolution: exposure / white balance, dehaze of the
  milky background, filmic tone curve with a long highlight shoulder, hue-selective work (skin kept natural and protected
  from the split tone, loud reds calmed, foliage pushed to olive, sky to cyan), teal shadows / warm highlights, a face power
  window that follows `face_track.json`, clarity, halation, bloom, vignette and per-frame grain.  `TL.GRADE` trims any
  parameter.
* **Virtual camera**: the source is decoded at 2880x1620 and reframed per keyframe (`TL.CAM_WIDE`, `TL.CAM_REEL`:
  `(t, cx, cy, zoom[, "cut"])`, linear drift between rows, instant change on a `"cut"` row) — slow push-ins, punch-ins on
  sentence boundaries, and close-ups on the product details.
* **Edit**: `TL.WIDE_CUTS` / `TL.REEL_CUTS` are the kept source ranges; every timeline time is a source time and the
  renderer, `mix_audio.py --cut-list WIDE_CUTS` (or `--cuts` for the reel) and `tools/make_srt.py --cut-list WIDE_CUTS` map
  through them.
* **Layout**: 16:9 plays in a 2.39:1 letterbox; the bars carry the logo bug, the chapter label (`TL.CHAPTERS`, with a
  progress hairline), big chapter titles, prompts and the subtitles, so text never sits on the presenter or the product.
  The 9:16 reel is laid out for the Reels / Shorts safe zone (no text in the top ~220 px, the bottom ~420 px or the
  right-hand button column, x > 940): logo + chapter row at y 240, product panels / big chapter titles at y 316-470, the
  picture as a large rounded, shadowed card (1000x880 at y 484, punched in by `TL.REEL_ZOOM`), subtitles at y ~1432, and
  only the blurred extension of the frame in the unsafe areas.  Opening titles are three lines (`TL.TITLE_BEATS_REEL`).
* **Callouts** (`TL.CALLOUTS`): an ember ring pinned to the product, a leader and a glass label.  Anchor points are
  tracked with `tools/track_points.py` (Lucas-Kanade on features around a hand-picked seed, forward-backward checked) into
  `tracks.json`; keep each callout inside the part of the track that holds.
* **Cards** (`lib/showcase.py`): opening 3D title, "not sponsored" chip, name tag, info rows, lens-protector card,
  raised-lip side-view diagram, price card (struck MRP, counting price), heat-vent wisps, summary checklist.
  Unbounded + Barlow Condensed + Inter (SIL OFL); ember / graphite / paper palette taken from the product.

Music "Deep Urban" (Mixkit 623); SFX 1485, 1491, 1492, 2596, 3005, 2350, 2354, 933.
