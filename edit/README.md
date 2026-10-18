# Mega Byte – "3 Kidilan iPhone features (iOS 27)" edit

Everything needed to rebuild the video from the original footage. Media files are not in git.

```
main video ─► build_base.py ──► base.mp4  (grade + Gaussian background blur, person matte by RVM)
screen rec ─► screen_scene.py ► S1.mp4 / S2.mp4  (HDR→SDR, phone window, zoom camera, highlights, taps)
stock clips ► prep_broll.py ──► cut_*.mp4
SRT text ───► align_captions.py ► words_aligned.json ─► timeline.py ─► timeline.json ─► render_overlay.py ─► PNG frames
music_synth.py ─► music_bed.wav + sfx.wav ─► mix_audio.py (voice untouched) ─► final_audio.wav
                                              └──────────────► assemble.py ─► final MP4
```

* `data/captions_manglish.srt` – your script, unchanged. `data/captions_manglish_synced.srt` – same words with the real timing
  (`tools/make_srt.py` also proves the on-screen words are identical to your script).
* `scenes.py` – the retiming of the screen recording: every tap / swipe / toggle sits on the spoken word that describes it
  (`python tools/screen_scene.py check S1` verifies each jump-cut skips only identical, idle UI).
* `timeline.py` – every on-screen graphic with its trigger word. `overlay/` – the "Sunset Amber" theme (HTML/CSS/JS).
* `broll.py` – B-roll plan. `LICENSES.md` – sources and licences.

Audio rule: the voice from `Main Video .mp4` is mixed at unity gain; music/SFX are added below it and duck for a few ms
when voice+music would clip. Screen-recording audio is never used.
