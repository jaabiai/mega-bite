# Video plan: Gemini in Chrome + Auto Browse demo

Target length: ~3:45 · Format: 16:9, 4K · Channel: MEGA BITE

## Character reference

- Reference image: `image_2.png` (kept outside the repo; use it as the image-to-video input for every AI clip)
- Base description, pasted at the start of every prompt so the character stays consistent:

> A stylish South Indian man with a thick black beard, wearing reflective green sunglasses and a white collared shirt.

## Scene overview

| Scene | Time          | Purpose                          | Screen footage                                   |
| ----- | ------------- | -------------------------------- | ------------------------------------------------ |
| 1     | 00:00 – 00:30 | Hook                             | none                                             |
| 2     | 00:30 – 01:45 | Gemini in Chrome demo            | `ScreenRecording_10-09-2026 15-25-47_1.mp4` (PIP) |
| 3     | 01:45 – 03:15 | Auto Browse live demo            | Auto Browse screen recording (**not yet supplied**) |
| 4     | 03:15 – 03:45 | Outro and call to action         | none                                             |

---

## Scene 1: The Hook (00:00 – 00:30)

**AI video prompt**

> Cinematic mid-shot of a stylish South Indian man with a thick black beard, wearing reflective green sunglasses and a white collared shirt, standing in a modern tech YouTube studio with subtle neon blue and purple background lights. He is looking directly into the camera, talking enthusiastically and making energetic hand gestures. High quality, 4k resolution, realistic lighting, photorealistic.

**Audio / voiceover:** use the first part of the Malayalam script shared earlier. *(That script is not in this repo yet; paste it here once it is.)*

---

## Scene 2: Gemini in Chrome Demo (00:30 – 01:45)

**AI video prompt**

> Close-up shot of the same man (thick black beard, green sunglasses, white shirt) holding a smartphone. He looks excitedly at the phone screen and then points his finger towards the empty space on the left side of the frame. Tech studio background with dynamic lighting. Highly detailed.

**Editing note (original):** നിങ്ങൾ എഡിറ്റ് ചെയ്യുമ്പോൾ (Final Cut Pro-യിലോ മറ്റോ), ഈ വീഡിയോയുടെ ഇടതുവശത്ത് നിങ്ങൾ നൽകിയ `ScreenRecording_10-09-2026 15-25-47_1.mp4` (GQ India ആർട്ടിക്കിൾ വെച്ച് Gemini 'Summarize' ചെയ്യുന്ന വീഡിയോ) ഒരു മൊബൈൽ ഫ്രെയിമിനുള്ളിൽ PIP (Picture-in-Picture) ആയി ചേർക്കുക.

**Placement:** the prompt leaves the left of the frame empty on purpose, so the phone frame with the screen recording goes there.

### Screen recording: what is in it

Portrait iPhone capture, 1320×2868 (about 9:19.5), HEVC, 60 fps, 36.2 s, with audio. The page is gqindia.com in Chrome with the Gemini panel. Timecodes below are approximate (sampled every 3 s).

| Time     | On screen                                                                                          |
| -------- | -------------------------------------------------------------------------------------------------- |
| 0:00     | GQ India article, "New OTT releases to watch this weekend: 11 new movies & shows"                  |
| 0:03     | Scrolling the article (trailer embeds, Carrie / Amazon Prime Video)                                |
| 0:06     | Chrome "Page tools" sheet opens, tapping **Ask Gemini**                                            |
| 0:09     | Gemini bar opens with the page attached and suggestions ("Summarise page", "List all 11 new OTT releases") |
| 0:12–0:16 | Typing the Malayalam prompt "ഇത് വായിക്കൂ" (transliterated as `vayikku`)                           |
| 0:18–0:21 | "Just a second…" then "Submitting page…"                                                           |
| 0:24     | Gemini starts answering in Malayalam, listing the 11 releases                                      |
| 0:27–0:33 | Answer streams and scrolls (items 1–9 visible, then back to the top)                               |

Good moments to call out in the voiceover: the page attaches automatically as context (0:09), the suggestion chips (0:09), and the Malayalam answer (0:24 onward).

### Edit tips

- The recording is 36 s but the scene window is 75 s. Either intercut with the AI presenter clips, freeze on the Malayalam answer while talking, or slow the section from 0:24 on. Do not stretch the whole clip.
- At 900 px tall in a 1920×1080 timeline the phone frame is roughly 415 px wide, which fits the empty left side of the AI clip.
- The recording is dimmed while the Gemini sheet is open. Raise exposure slightly if it looks flat next to the studio footage.
- The status bar shows the time (3:25/3:26) and battery. Crop or mask it if you want a cleaner look.

---

## Scene 3: Auto Browse Live Demo (01:45 – 03:15)

**AI video prompt**

> Dynamic shot of the same man (thick black beard, green sunglasses, white shirt) looking amazed and gesturing with both hands towards a large glowing virtual screen area on the right side of the frame. He has an excited expression. Cinematic rim lighting on his face, futuristic tech vibe.

**Editing note (original):** ഇവിടെ Auto Browse വർക്ക് ചെയ്യുന്നതിന്റെ സ്ക്രീൻ റെക്കോർഡിംഗ് വീഡിയോ ചേർക്കുക.

**Placement:** the "virtual screen" is on the right, so the Auto Browse recording fills that area, probably as a landscape desktop capture. This footage has not been supplied yet.

---

## Scene 4: Outro & Call to Action (03:15 – 03:45)

**AI video prompt**

> Portrait of the same man (thick black beard, green sunglasses, white shirt) smiling warmly at the camera, pointing downwards with his index finger to gesture 'subscribe' and then waving goodbye. Bright, welcoming tech studio environment, 4k, ultra-realistic.

---

## Notes for generating the clips

- Most AI video tools generate 5–10 s clips, so each scene needs several generations stitched together (Scene 1 alone is about 3–6 clips). Reuse the same prompt and reference image each time.
- Keep the character description identical in every prompt; the "same man (…)" wording in scenes 2–4 already does this.
- The sunglasses are reflective green, so reflections in the lenses should stay consistent. Re-roll any clip where they change colour or shape.
- Scene 4 asks for two actions (point down, then wave). Generating them as two short clips and cutting between them usually works better than one prompt.

## Open items

- [ ] Add the Malayalam voiceover script (Scene 1 and the rest of the video).
- [ ] Add the Auto Browse screen recording for Scene 3.
- [ ] Decide how to fill the 75 s Scene 2 window from a 36 s recording.
- [ ] Generate the AI clips for all four scenes.
