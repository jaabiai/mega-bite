"""English caption chunks timed to the Malayalam narration ("shoot 48 MP photos on iPhone").

Each chunk is (start_s, end_s, text[, {word_index: time_s}]).  Chunk boundaries come from the word-level
timestamps of the Malayalam ASR (+/-0.2 s).  Word order is adapted where Malayalam and English differ so the
highlighted word stays close to the spoken one.  See captions/iphone-48mp-camera_script_en.md for the readable script.
"""

CHUNKS = [
    (0.02, 1.34, "A simple and useful"),
    (1.36, 2.70, "iPhone camera setting —"),
    (2.72, 3.32, "let me tell you."),
    (3.34, 4.70, "You've seen many videos"),
    (4.72, 6.84, "about iPhone camera settings,"),
    (6.86, 7.38, "I'm sure."),
    (7.40, 8.40, "But in all of them,"),
    (8.41, 9.62, "many don't mention"),
    (9.63, 10.88, "one feature —"),
    (10.89, 12.05, "this is it."),
    (12.10, 13.82, "So, all your iPhone friends —"),
    (13.83, 14.96, "share this video.", {0: 14.26}),
    (14.98, 16.14, "For more useful videos"),
    (16.16, 17.30, "like this, right now,"),
    (17.31, 18.44, "subscribe to the channel"),
    (18.45, 19.15, "and follow me."),
    (19.18, 20.80, "So, let's look at the setting."),
    (20.82, 21.40, "Welcome to"),
    (21.42, 22.34, "MEGABYTE!"),
    (22.36, 23.22, "To a new video,"),
    (23.23, 24.38, "everyone's welcome."),
    (24.40, 26.24, "For that, here's what to do:"),
    (26.26, 27.66, "on your phone,"),
    (27.67, 28.40, "open Settings."),
    (28.42, 29.36, "From Settings,"),
    (29.37, 31.08, "select Camera."),
    (31.10, 31.90, "In Camera,"),
    (31.92, 33.85, "you'll see an option called Formats."),
    (33.86, 35.28, "Select it —"),
    (35.29, 36.16, "the top one,"),
    (36.17, 37.54, "High Efficiency —"),
    (37.55, 39.06, "select and keep it."),
    (39.07, 40.18, "After that, below,"),
    (40.19, 41.30, "Photo Capture,"),
    (41.32, 42.48, "under it, Photo Mode"),
    (42.49, 43.48, "is an option;"),
    (43.49, 45.40, "currently 24 MP."),
    (45.46, 46.72, "Select it,"),
    (46.73, 47.73, "go back,"),
    (47.74, 48.70, "and right below,"),
    (48.71, 49.84, "ProRAW Format"),
    (49.85, 50.58, "is an option;"),
    (50.59, 51.45, "the top one,"),
    (51.46, 53.13, "JPEG Lossless"),
    (53.14, 54.35, "(Most Compatible)."),
    (54.36, 55.50, "Select that option,"),
    (55.51, 56.46, "then go back"),
    (56.47, 57.45, "again."),
    (57.60, 59.44, "Now open your Camera app."),
    (59.46, 61.40, "Once it's open,"),
    (61.42, 63.17, "at the very bottom"),
    (63.18, 64.70, "you'll see a menu icon."),
    (64.71, 65.67, "Just tap it."),
    (65.70, 66.87, "Once it opens,"),
    (66.88, 68.01, "Aspect is there —"),
    (68.02, 69.16, "you'll see it"),
    (69.17, 70.60, "at the top right."),
    (70.71, 72.22, "Select it,"),
    (72.23, 72.86, "and there,"),
    (72.87, 74.64, "4:3 —"),
    (74.65, 75.84, "select that."),
    (75.86, 77.01, "After that,"),
    (77.02, 78.87, "tap the same icon again"),
    (78.88, 79.91, "and a Format option"),
    (79.92, 80.82, "appears."),
    (80.84, 81.90, "Tap Format,"),
    (81.92, 83.72, "then choose 48 MP", {2: 81.92}),
    (83.73, 85.28, "and select it."),
    (85.30, 86.86, "Only after all this"),
    (86.87, 87.76, "can you get"),
    (87.77, 89.17, "perfect 48 MP"),
    (89.18, 90.31, "photos with your"),
    (90.32, 91.95, "iPhone camera."),
    (91.97, 93.84, "So, after you set it,"),
    (93.85, 95.04, "if you take a photo,"),
    (95.05, 96.87, "48 MP photos —"),
    (96.88, 98.90, "that's what you'll get."),
    (98.91, 100.22, "Until you do this,"),
    (100.23, 101.80, "the photos you take"),
    (101.81, 102.76, "won't be in the"),
    (102.77, 104.16, "right resolution."),
    (104.17, 105.32, "Now I'll show you"),
    (105.33, 106.83, "the photos I took here."),
    (106.84, 108.31, "This one is 8 MP —"),
    (108.32, 109.73, "from the main camera,"),
    (109.74, 111.58, "taken without changing"),
    (111.59, 113.11, "any settings."),
    (113.12, 114.31, "Now, the same way,"),
    (114.32, 115.85, "a macro shot"),
    (115.86, 117.15, "is 12 MP."),
    (117.16, 118.00, "Similarly,"),
    (118.01, 119.44, "another photo I took"),
    (119.46, 121.10, "is 24 MP."),
    (121.11, 123.12, "It should have been 48 MP,"),
    (123.13, 123.92, "but"),
    (123.93, 125.07, "it came out as"),
    (125.08, 126.03, "24 MP."),
    (126.04, 127.00, "The reason:"),
    (127.04, 128.02, "as I explained,"),
    (128.03, 130.43, "we hadn't set it up."),
    (130.44, 131.62, "After setting it,"),
    (131.64, 132.91, "from now on, you"),
    (132.92, 134.47, "can shoot 48 MP"),
    (134.48, 136.51, "photos in great resolution."),
    (136.52, 137.90, "No doubt about it!"),
    (137.92, 138.92, "Definitely —"),
    (138.93, 140.10, "for iPhone users,"),
    (140.11, 141.85, "very useful knowledge."),
    (141.86, 142.80, "So, with everyone"),
    (142.81, 143.59, "share it,"),
    (143.60, 144.47, "let people know"),
    (144.48, 146.42, "this can be done."),
    (146.43, 147.43, "Anyway, with a new topic"),
    (147.44, 149.00, "see you again!"),
]


def word_times(chunk):
    """-> list of (word, t_start, t_end) with anchors honoured, otherwise length-weighted."""
    start, end, text = chunk[0], chunk[1], chunk[2]
    anchors = chunk[3] if len(chunk) > 3 else {}
    words = text.split()
    w = [max(len("".join(c for c in x if c.isalnum())), 1) + 1.2 for x in words]
    pts = [(0, start)] + sorted(anchors.items()) + [(len(words), end)]
    out = []
    for (i0, t0), (i1, t1) in zip(pts[:-1], pts[1:]):
        seg = w[i0:i1]
        tot = sum(seg) or 1.0
        t = t0
        for k in range(i0, i1):
            d = (t1 - t0) * w[k] / tot
            out.append((words[k], t, t + d))
            t += d
    return out
