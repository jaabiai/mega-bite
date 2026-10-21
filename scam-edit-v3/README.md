# Mega Byte – "WhatsApp / GPay anniversary scam links" – edit v3 (client's final cut)

Input: the client's own final cut (1080p30 H.264, 2:50) + Malayalam SRT text. Nothing is re-cut; the edit adds
colour/grade, a replaced animated background, Malayalam word-by-word captions with a moving underline (left column),
full-screen key-point scenes, B-roll, SFX and a mastered mix.

```
final_cut.mp4 ─► matte3.py            person matte (RVM resnet50)
              ─► plate3.py/pl3lib.py   colour-decontaminated speaker layer + cleaned alpha (edge colours extended from the solid interior)
user.srt + ASR ─► align_srt.py         the SRT words, re-timed to the real speech (IndicConformer word times + monotonic DP)
bg/bg.html     ─► render_bg.js         20 s seamless animated background loop (canvas, deterministic)
make_data3.py  ─► overlay/data.js, data/scenes.json   scene table (shared by the overlay and the ffmpeg graph)
overlay/ (HTML+GSAP)  ─► render.js     captions, underline, headline chips, key-point scenes, wipes -> RGBA PNG frames
mix3.py                                RNNoise + EQ + de-ess + compression, ducked BGM, synthesized SFX, 2-pass loudnorm (-14 LUFS)
final3.py / render_all3.py             background + speaker (shifted right) + zoom punch at jump cuts + B-roll + overlay + logo
```

Notes
* every overlay PNG must be RGBA (a fully opaque frame saved as RGB makes ffmpeg re-configure the graph and drop frames).
* `overlay/assets/` (screenshots, logo) and the media are not committed; the WhatsApp screenshot is cropped to the message so no
  phone number / avatar is visible, the small profile pictures in the other screenshots are blurred.
