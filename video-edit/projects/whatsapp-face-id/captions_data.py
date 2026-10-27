"""English caption chunks timed to the Malayalam narration ("hide WhatsApp calls from the iPhone call log").

Each chunk is (start_s, end_s, text[, {word_index: time_s}]).  Chunk boundaries come from the word-level
timestamps of the Malayalam ASR (+/-0.2 s).  Word order is adapted where Malayalam and English differ so the
highlighted word stays close to the spoken one.  See captions/script_en.md for the human-readable script.
"""

CHUNKS = [
    (0.02, 1.05, "On iPhone, WhatsApp"),
    (1.06, 2.84, "has a big problem:"),
    (2.85, 3.90, "in the call log itself,"),
    (3.92, 4.95, "WhatsApp calls"),
    (4.97, 6.07, "and phone calls"),
    (6.09, 7.40, "show up together."),
    (7.18, 8.68, "There's a fix for that,"),
    (8.70, 9.45, "and it's today's topic."),
    (9.46, 10.64, "To get more solutions"),
    (10.66, 11.88, "like these,"),
    (11.91, 12.58, "right now,"),
    (12.60, 13.66, "subscribe to the channel", {0: 12.87}),
    (13.67, 14.55, "and follow me."),
    (14.58, 15.38, "This video —"),
    (15.40, 16.34, "share it with everyone,"),
    (16.36, 17.46, "let people know"),
    (17.48, 18.94, "such things are possible."),
    (18.95, 20.03, "So, quite simply,"),
    (20.04, 21.12, "this problem"),
    (21.13, 22.55, "has a solution."),
    (22.58, 23.50, "Let's see how."),
    (23.54, 24.26, "Welcome to"),
    (24.28, 25.34, "MEGABYTE!"),
    (25.40, 26.14, "To a new video,"),
    (26.16, 27.31, "everyone's welcome."),
    (27.33, 28.70, "It's very simple."),
    (28.78, 29.78, "Just, on your"),
    (29.80, 31.46, "WhatsApp app —"),
    (31.48, 32.60, "or rather, on"),
    (32.62, 33.44, "its icon —"),
    (33.46, 34.98, "just long-press and hold."),
    (34.99, 36.28, "Once you hold it,"),
    (36.30, 37.62, "Require Face ID —"),
    (37.64, 39.50, "that option will appear."),
    (39.52, 40.82, "Just select it."),
    (40.84, 42.57, "Require Face ID —"),
    (42.59, 43.75, "turn it on."),
    (43.77, 45.25, "As soon as it's on,"),
    (45.27, 46.64, "go to your call log,"),
    (46.66, 48.02, "and automatically,"),
    (48.04, 48.60, "from there,"),
    (48.62, 50.42, "WhatsApp call history"),
    (50.43, 51.12, "from there"),
    (51.13, 52.40, "disappears."),
    (52.50, 54.34, "In this very simple way,"),
    (54.36, 57.12, "you can solve this problem."),
    (57.20, 58.04, "But here,"),
    (58.05, 60.20, "there's one small catch:"),
    (60.22, 61.94, "To open WhatsApp,"),
    (61.96, 63.34, "you'll need Face ID —"),
    (63.36, 64.38, "only then"),
    (64.40, 65.70, "will it open."),
    (65.72, 67.60, "Or, with the code"),
    (67.62, 69.30, "that unlocks your screen,"),
    (69.32, 70.58, "only then"),
    (70.60, 72.70, "can WhatsApp be opened."),
    (72.75, 74.58, "That's a small issue,"),
    (74.60, 76.14, "but the big headache"),
    (76.16, 77.45, "of WhatsApp calls"),
    (77.47, 78.10, "is solved."),
    (78.12, 78.77, "This new tip"),
    (78.79, 79.85, "will be very useful."),
    (79.86, 81.20, "So, with everyone"),
    (81.22, 81.88, "share it,"),
    (81.89, 82.93, "let people know."),
    (82.96, 84.54, "This problem has a fix too —"),
    (84.56, 85.98, "anyway, with a new tip"),
    (86.00, 87.30, "see you again!"),
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
