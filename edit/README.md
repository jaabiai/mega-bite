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

## Reels (9:16)
The reel tools pick their excerpt set with `REEL_TAG` (`reel2` = demo walk-through, `reel3` = "first / next / third" announcement cut):

```
export REEL_TAG=reel3
python tools/reel2_cuts.py <main_orig.wav> <matte_full.mkv> data/reel3_cuts.json <headx.npy>   # cut points on the quietest dips
python reel2_plan.py && python reel3_build.py                                                  # layout -> shots / overlay events / sfx
REEL_OVERLAY=overlay_reel2 REEL_TIMELINE=reel3_timeline.json python tools/render_overlay_reel.py render 0 1792 <scratch>/reel3/ov
python tools/reel2_shots.py <scratch> data/reel3_shots.json ; python tools/reel2_audio.py <scratch> <scratch>/reel3/audio_final/reel2_audio.wav
python tools/assemble_reel2.py <scratch> MegaByte_Reel_Announce3.mp4
```
