"""English caption chunks timed to the Malayalam narration.

Each chunk is (start_s, end_s, text[, {word_index: time_s}]).  Chunk boundaries come from the word-level
timestamps of the Malayalam ASR (+/-0.2 s).  Word order is adapted where Malayalam and English differ so the
highlighted word stays close to the spoken one.  See captions/script_en.md for the human-readable script.
"""

CHUNKS = [
    (0.30, 0.78, "You probably"),
    (0.79, 1.85, "have a phone lock,"),
    (1.87, 3.35, "or app locks."),
    (3.85, 5.40, "But something different:"),
    (5.45, 6.80, "your search history"),
    (6.82, 7.50, "needs a lock."),
    (7.52, 8.30, "Let me tell you."),
    (8.30, 9.90, "Just like your phone lock,"),
    (9.91, 11.80, "or an app lock,"),
    (11.80, 13.20, "your Google"),
    (13.22, 14.15, "search history"),
    (14.18, 15.80, "can be locked too."),
    (15.75, 17.05, "That's today's topic."),
    (17.10, 17.95, "Welcome to"),
    (18.00, 19.00, "MEGA BYTE!"),
    (19.01, 20.38, "To get videos like this,"),
    (20.41, 20.95, "right now,"),
    (20.99, 21.85, "subscribe"),
    (21.90, 22.70, "and join us!"),
    (22.80, 23.95, "Share this video,"),
    (24.00, 24.95, "let people know"),
    (25.00, 26.55, "such features exist."),
    (26.50, 27.62, "So, how's it done?"),
    (27.68, 29.70, "Let's see. On your phone,"),
    (29.76, 31.40, "open the Google app."),
    (31.27, 32.55, "At the top"),
    (32.57, 33.90, "right corner,"),
    (33.92, 35.60, "your profile icon is there."),
    (35.64, 36.75, "Just tap it."),
    (36.67, 38.05, "From there,"),
    (38.11, 39.60, "Manage your Google Account"),
    (39.62, 40.45, "is the option."),
    (40.47, 41.35, "Tap it."),
    (41.42, 43.10, "Depending on the app you use,"),
    (43.14, 45.30, "this part may look different."),
    (46.33, 47.20, "Wherever you see"),
    (47.21, 48.50, "Manage your Google Account"),
    (48.56, 50.05, "— select that one."),
    (50.10, 51.85, "Then scroll down a little,"),
    (51.90, 53.80, "Data & privacy"),
    (53.83, 54.65, "you'll find it."),
    (54.52, 56.40, "Tap on it,"),
    (56.46, 58.60, "and there you'll see"),
    (58.70, 60.00, "My Activity"),
    (61.09, 62.60, "Just tap on it."),
    (62.62, 63.90, "After that,"),
    (63.98, 65.30, "scroll down a little."),
    (65.17, 67.78, "Manage My Activity verification"),
    (67.79, 68.75, "is right there."),
    (68.79, 70.00, "Just tap on it."),
    (70.02, 71.90, "You get two options,"),
    (72.20, 73.45, "and the top one —"),
    (73.47, 75.50, "Require extra verification"),
    (75.51, 76.30, "is the one —"),
    (76.35, 77.40, "select it,"),
    (77.44, 79.70, "then tap Save.", {2: 78.26}),
    (79.82, 80.88, "After that,"),
    (80.90, 81.40, "your history"),
    (81.43, 82.55, "or search history"),
    (82.61, 84.20, "if anyone checks it,"),
    (84.25, 85.90, "they'll have to"),
    (85.95, 87.55, "log in first."),
    (87.56, 89.25, "Only after that"),
    (89.28, 90.15, "can that history"),
    (90.18, 91.85, "be viewed by anyone."),
    (91.73, 93.00, "A very useful"),
    (93.01, 94.40, "trick, isn't it?"),
    (94.45, 95.20, "With everyone"),
    (95.22, 95.90, "share it,"),
    (95.92, 97.15, "let people know"),
    (97.20, 98.90, "you can do this."),
    (98.97, 99.93, "With a new video,"),
    (99.95, 101.50, "see you again!"),
]


def word_times(chunk):
    """-> list of (word, t_start, t_end) with anchors honoured, otherwise length-weighted."""
    start, end, text = chunk[0], chunk[1], chunk[2]
    anchors = chunk[3] if len(chunk) > 3 else {}
    words = text.split()
    w = [max(len("".join(c for c in x if c.isalnum())), 1) + 1.2 for x in words]
    # piecewise: split at anchors
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
