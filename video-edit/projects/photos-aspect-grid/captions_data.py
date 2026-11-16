"""English caption chunks timed to the Malayalam narration (iPhone Photos: Aspect Ratio Grid).
Each chunk is (start_s, end_s, text[, {word_index: time_s}]); boundaries come from the Malayalam ASR word timestamps.
The 3D title covers the first 3.6 s (those chunks feed the subtitle file only)."""

CHUNKS = [
    (0.00, 1.24, "For iPhone users -"),
    (1.24, 3.60, "a brilliant feature in the Photos app."),
    (3.60, 6.68, "A really useful, simple tip."),
    (6.98, 8.42, "Many of you may already know it."),
    (8.42, 10.79, "This video is for those who don't."),
    (10.79, 13.11, "If you know it, share it with them,", {4: 12.59}),
    (13.11, 14.58, "then keep scrolling."),
    (14.58, 16.70, "For more useful videos like this,"),
    (16.70, 19.48, "subscribe right now and follow me.", {0: 17.34, 4: 18.80}),
    (19.45, 21.25, "Liked the video? Hit like,", {4: 20.63}),
    (21.25, 23.85, "and share your thoughts in the comments."),
    (24.00, 27.32, "Normally, when we open the Photos app,", {5: 26.46}),
    (27.32, 30.21, "we see everything like this - in squares.", {7: 28.95}),
    (30.39, 33.54, "Videos, photos - every one of them.", {0: 30.79, 1: 31.67}),
    (33.54, 35.22, "So when you post a WhatsApp status,", {5: 33.98, 6: 34.42}),
    (35.22, 36.88, "or upload a reel,", {3: 35.64}),
    (36.88, 39.27, "or use it for anything else,"),
    (39.27, 42.56, "which photo suits a status?", {1: 40.21, 4: 40.80}),
    (42.56, 45.95, "Which video fits a status or a reel?", {1: 43.42, 4: 44.00, 7: 44.52}),
    (45.95, 47.95, "That's hard to tell from here."),
    (47.95, 49.87, "A problem many of us face."),
    (49.60, 53.56, "Which format is this video - or this photo?", {8: 51.90}),
    (53.56, 57.08, "A simple tip to know exactly that.", {1: 55.64}),
    (56.80, 58.90, "So share it with everyone."),
    (58.90, 60.66, "Now, to do this -"),
    (60.45, 61.73, "it's very simple."),
    (61.73, 63.37, "Open the Photos app,", {2: 62.05}),
    (63.37, 66.40, "and at the top you'll see a three-line menu icon.", {7: 64.20, 8: 65.32, 9: 65.80}),
    (66.50, 68.28, "Just tap on it,", {1: 67.24}),
    (68.32, 71.11, "and here you'll find View Options.", {4: 69.05, 5: 69.61}),
    (71.11, 72.39, "Tap that,", {0: 71.35}),
    (72.20, 74.88, "Aspect Ratio Grid is right there.", {1: 72.92, 2: 73.46}),
    (74.88, 75.90, "Select it -", {0: 75.10}),
    (75.90, 78.63, "and then it looks like this:", {4: 77.00}),
    (78.63, 81.85, "every photo and video in your gallery.", {1: 79.99, 3: 80.69}),
    (81.85, 85.23, "So you can see the aspect ratio", {5: 83.65, 6: 83.99}),
    (85.23, 87.80, "of each photo - exactly."),
    (87.80, 90.58, "Uploading to a status or a reel?", {3: 89.34, 6: 89.86}),
    (90.58, 93.23, "No trouble at all.", {0: 90.98}),
    (93.23, 95.23, "If you like, zoom in,", {3: 94.41, 4: 94.73}),
    (95.23, 96.49, "or zoom out,", {1: 95.65, 2: 95.89}),
    (96.49, 100.18, "and set it up the way you want.", {1: 98.68}),
    (100.18, 102.32, "A really useful, simple tip, right?", {2: 100.58, 3: 101.20}),
    (102.34, 104.01, "So share it with everyone -", {1: 103.11}),
    (104.01, 106.56, "let people know this is possible."),
    (106.56, 108.20, "Anyway - with a new topic,", {4: 106.90, 5: 107.20}),
    (108.27, 109.24, "see you again!"),
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
