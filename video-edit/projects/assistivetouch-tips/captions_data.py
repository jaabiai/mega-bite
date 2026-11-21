"""English caption chunks timed to the Malayalam narration (two AssistiveTouch tips: screenshot and restart, V Create).
Each chunk is (start_s, end_s, text[, {word_index: time_s}]); boundaries come from the Malayalam ASR word timestamps.
The 3D title covers the first 3 s (those chunks feed the subtitle file only)."""

CHUNKS = [
    (0.00, 1.48, "For iPhone users,"),
    (1.48, 3.04, "two brilliant features - let me show you.", {0: 1.48, 1: 1.70, 2: 2.14, 4: 2.56}),
    (3.04, 4.60, "Useful for a lot of people."),
    (4.60, 7.00, "It's not new - it's an old feature,", {5: 6.14}),
    (7.00, 10.68, "but far more people don't know it than do,", {2: 8.84}),
    (10.68, 12.60, "so I made this video."),
    (12.69, 14.17, "If you already know it,"),
    (14.17, 16.24, "share this video with those who don't -", {0: 15.57}),
    (16.24, 18.79, "let everyone know this is possible."),
    (18.79, 20.47, "If you like it, hit like", {4: 19.81}),
    (20.47, 22.45, "and drop your thoughts in the comments."),
    (22.52, 23.82, "So, what are the tips?"),
    (23.82, 26.62, "Tip one: taking screenshots.", {2: 24.68}),
    (26.62, 28.89, "Normally, we take a screenshot", {4: 27.68}),
    (28.89, 31.77, "by pressing two buttons - power and volume down -", {6: 30.01, 8: 30.53}),
    (31.77, 33.60, "at the same time,"),
    (33.63, 37.20, "or by adding a shortcut to take one.", {4: 34.72}),
    (37.29, 40.90, "There's something simpler, built into the iPhone.", {2: 38.13}),
    (41.00, 44.70, "Many may know it, but more people don't,", {6: 42.52}),
    (44.70, 46.10, "so here's the video."),
    (46.10, 48.31, "So how do we do it?"),
    (48.31, 51.30, "We can do it with AssistiveTouch.", {5: 48.31}),
    (51.36, 54.00, "Add a screenshot option to it -", {2: 52.36}),
    (54.00, 55.30, "it's very simple."),
    (55.36, 57.02, "Go to your Settings,", {3: 55.98}),
    (57.02, 59.91, "search for AssistiveTouch there,", {2: 57.77}),
    (59.91, 62.83, "and you'll find the option to turn it on."),
    (62.83, 64.23, "Turn it on."),
    (64.23, 67.64, "Once it's on, AssistiveTouch shows up like this.", {3: 66.25}),
    (68.32, 69.53, "Many people know this much."),
    (69.53, 72.55, "From here, select Customise Top Level Menu.", {3: 70.33}),
    (72.93, 76.34, "Now you can add the screenshot option here.", {4: 74.08}),
    (76.34, 77.33, "To add it,"),
    (77.33, 81.38, "tap the plus icon at the bottom.", {2: 78.61}),
    (81.38, 84.64, "After tapping plus, choose Device.", {4: 83.02}),
    (84.64, 87.53, "Under Device, pick Screenshot,", {3: 85.63}),
    (88.03, 90.16, "then tap the check mark at the top.", {3: 88.77}),
    (90.38, 92.60, "You'll see Screenshot added here.", {2: 90.38}),
    (93.04, 95.71, "Now open AssistiveTouch,", {2: 93.48}),
    (95.71, 98.53, "and the screenshot option is right there.", {2: 96.07}),
    (98.53, 101.02, "That's how simply you can take a screenshot.", {7: 99.78}),
    (101.50, 103.11, "Tip two: restart.", {2: 102.29}),
    (103.67, 105.55, "Normally, to restart our iPhone,", {2: 104.61}),
    (105.55, 109.86, "we use a Siri shortcut or the power button.", {3: 106.24, 7: 108.40}),
    (109.86, 111.29, "But there's a simpler way:"),
    (111.29, 113.11, "just like before,"),
    (113.11, 118.24, "in AssistiveTouch, we can add a restart option.", {1: 114.37, 6: 115.75}),
    (118.56, 120.78, "This one, too, many people know -"),
    (121.34, 123.00, "but more people don't."),
    (123.07, 126.13, "The benefit: when your phone hangs,", {5: 125.79}),
    (126.13, 129.34, "you can restart it easily.", {2: 128.58}),
    (129.86, 132.10, "Or any time you want to restart -", {6: 131.50}),
    (132.56, 135.28, "really simply, without pressing any button,", {5: 134.68}),
    (135.66, 138.76, "right from AssistiveTouch, wherever it sits on screen,", {2: 136.01}),
    (138.76, 141.32, "you can restart your phone.", {2: 139.90}),
    (141.91, 143.81, "This is an old option too - not new."),
    (143.81, 145.43, "To set it up, just like before,"),
    (145.43, 148.88, "go to the AssistiveTouch section,", {3: 146.73}),
    (149.36, 152.34, "and select Customise Top Level Menu.", {2: 150.14}),
    (152.56, 155.46, "As before, tap the plus icon,", {4: 153.82}),
    (155.46, 157.70, "then tap the plus again.", {3: 156.42}),
    (157.71, 160.73, "From here, choose System,", {3: 158.77}),
    (160.73, 163.22, "then select Restart.", {2: 161.21}),
    (163.56, 166.42, "Then, as before, enable the check mark.", {5: 165.08}),
    (166.71, 170.96, "Open AssistiveTouch, and the restart option is there.", {1: 167.17, 4: 169.39}),
    (171.92, 175.30, "So - two really useful, simple tips."),
    (175.47, 177.69, "To every iPhone user out there - share it,", {7: 177.37}),
    (178.12, 180.76, "let them know this is possible."),
    (180.76, 183.40, "See you again with a new topic!"),
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
