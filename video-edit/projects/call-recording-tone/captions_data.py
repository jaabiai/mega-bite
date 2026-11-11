"""English caption chunks timed to the Malayalam narration ("record calls without the announcement", V Create).
Each chunk is (start_s, end_s, text[, {word_index: time_s}]); boundaries come from the Malayalam ASR word timestamps.
The 3D title covers the first 11 s (those chunks feed the subtitle file only)."""

CHUNKS = [
    (0.00, 2.60, "A problem we face when recording calls:"),
    (2.64, 4.62, "that recording announcement -"),
    (4.67, 6.95, "the person on the other side hears it."),
    (7.09, 8.57, "So in today's video,"),
    (8.63, 10.95, "I'll tell you the fix for that."),
    (11.28, 13.30, "For more useful videos like this,"),
    (13.46, 15.00, "subscribe to the channel now,"),
    (15.03, 17.72, "follow me and share the video with everyone -"),
    (17.87, 20.70, "let people know this is possible."),
    (20.72, 23.40, "Welcome to V Create!"),
    (23.47, 25.90, "Welcome, everyone, to a new video."),
    (26.03, 28.50, "Let's see how to do it."),
    (28.85, 30.76, "This one is for Android phone users -"),
    (30.80, 34.08, "I've already made a video for iPhone."),
    (34.19, 35.80, "It's very simple to do;"),
    (35.85, 37.60, "I'll show you on my phone."),
    (37.74, 39.70, "So, here's what to do:"),
    (39.76, 41.30, "open your phone dialer."),
    (41.40, 43.65, "Once it opens, at the very top,"),
    (43.68, 46.00, "on the left, there are three lines - a menu icon."),
    (46.03, 47.95, "In other words, once it's open,"),
    (48.06, 49.70, "at the very top on the left"),
    (49.76, 53.40, "you'll see three lines - the menu icon."),
    (53.61, 55.00, "Tap it,"),
    (55.19, 56.50, "then tap Settings."),
    (56.56, 59.60, "In Settings, tap Call recording."),
    (59.61, 61.95, "Scroll down a little,"),
    (62.17, 64.60, "and you'll see Play audio tone instead of disclaimer -"),
    (64.64, 66.60, "a toggle button."),
    (66.61, 67.90, "Turn it on."),
    (68.19, 69.90, "In the window that opens,"),
    (69.96, 72.20, "tap Agree,"),
    (72.32, 74.30, "and it's turned on."),
    (74.44, 76.10, "Once it's on,"),
    (76.17, 78.50, "from now on, when you record calls -"),
    (78.59, 80.10, "as I said earlier -"),
    (80.13, 82.60, "without the other person hearing"),
    (82.64, 85.40, "that announcement, you can record."),
    (85.59, 87.70, "A really simple, useful tip."),
    (87.75, 89.27, "So share it with everyone,"),
    (89.42, 91.95, "let people know this is possible."),
    (92.09, 95.10, "Anyway, see you again with a new topic!"),
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
