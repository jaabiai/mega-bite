# video-edit

Scripted edit of the MEGA BYTE "lock your Google search history" video.

* `audio_clean.sh` – declip → rumble high-pass → RNNoise → EQ → de-ess → gate → compress → 2-pass loudnorm (-14 LUFS / -1.5 dBTP)
* `lib/grade.py` – cinematic grade for the face-cam footage (face window, highlight roll-off, split-tone, foliage control, vignette, clarity)
* `lib/phone.py` – procedurally drawn phone frame + screen mask (own design, no third-party mock-up assets)
* `lib/scene.py`, `lib/caption.py`, `lib/brand.py` – branded background, left-aligned word-highlight captions, palette/font tokens
* `preview_palettes.py` – renders the palette previews in `previews/`
* `captions/` – raw Malayalam ASR output and the English caption script

Fonts: Poppins (SIL OFL 1.1), Bebas Neue (SIL OFL 1.1) in `assets/fonts/`.
Music / SFX / stock clips: Mixkit (Mixkit licence – free for commercial use, no attribution required).
