# Mega Byte – "WhatsApp / GPay anniversary scam links" edit

Scripted, reproducible edit of the Malayalam talking-head video (source: 1920×1080, 30 fps, HEVC 10-bit HLG, 343 s).
Media is not in git. Output: 1080p30 H.264 (High, level 4.2, CRF 14, BT.709) + AAC 320 kbps, −14 LUFS.

```
source ─► asr_words.py / vad.py        Malayalam ASR (IndicConformer ONNX) + VAD  ─► words_indic.json
        ─► build_edl.py                cut list: best takes, silences / fillers removed ─► edl.json
        ─► shift_edl.py                opens the 2.8 s gap for the "Welcome to Mega Byte" stinger ─► edl_s.json
        ─► matte.py + plate.py         person matte (RVM) → HDR→SDR → background blur → ProRes plate
        ─► build_audio.py              edited voice (room-tone pads, crossfaded splices) + stinger gap / welcome clip
        ─► mix.py                      RNNoise + EQ + de-ess + compression, ducked BGM, synthesized SFX, 2-pass loudnorm
        ─► captions_spec.py / build_captions.py   Manglish captions (+ .srt)
        ─► overlay/ (HTML + GSAP)      all on-screen graphics, rendered frame by frame (render.js) to PNG
        ─► final2.py / render_all.py   grade, vignette, punch-ins, split-screen scenes, stock cut-aways, logo, overlays
```

* Every script has a `B = '…/scratchpad/'` working-directory constant at the top; point it at your own work folder.
* `overlay/overlay.js`, `overlay2.js`, `overlay3.js` are on the "pre-insert" timeline; `overlay3.js` opens the 2.8 s gap at 23.967 s
  (everything that starts at / after it moves) and draws the Mega Byte welcome stinger inside the gap.
* `overlay/assets/` is not committed: `logo.png` is the Mega Byte logo (`edit/assets/logo_megabyte.png` on the iOS 27 branch),
  the four phone screenshots (GPay / PhonePe) were supplied separately; the backdrops are generated gradients.
* Welcome voice: put the trimmed clip (mono, 48 kHz, float `.npy`) at `work/audio/welcome_clip.npy`; `build_audio.py` drops it into the
  stinger at `WELCOME_AT` seconds after the stinger start, `mix.py` then masters it with the rest of the voice.
* Stock clips and BGM are from Mixkit (free licence). SFX are synthesized in `mix.py`.
