"""English caption chunks timed to the Malayalam narration (iPhone case review, V Create).
Each chunk is (start_s, end_s, text[, {word_index: time_s}]) in SOURCE time (Main.mp4); boundaries come from the
Malayalam ASR word timestamps.  Renderers map them through the 16:9 / reel cut lists."""

CHUNKS = [
    (0.42, 3.18, "Looking to buy a case for your iPhone?"),
    (3.20, 5.65, "Then let me show you an excellent one -"),
    (5.70, 9.02, "a great-looking, really useful case."),
    (9.06, 11.75, "This isn't a promotional video -"),
    (11.77, 14.45, "I'm making it from my own experience using it."),
    (14.50, 17.05, "Anyway, for more useful videos like this,"),
    (17.07, 18.85, "subscribe to the channel right now,"),
    (18.87, 20.35, "share this video with others"),
    (20.39, 23.35, "and let people know about things like this."),
    (23.40, 25.10, "Welcome to V Create!"),
    (25.12, 26.05, "Hello, everyone."),
    (26.07, 27.37, "I'm Jabir Varikkodan."),
    (27.39, 29.75, "Today I'm introducing this"),
    (29.78, 31.08, "iPhone case."),
    (31.10, 32.36, "See that? A killer look, right?"),
    (32.38, 34.00, "Coming to the design,"),
    (34.03, 37.62, "the camera area at the back is perfectly designed."),
    (37.68, 41.62, "Anyone who sees it will be drawn to it."),
    (41.66, 44.85, "It comes in about five colours."),
    (45.17, 48.25, "The link to buy it is in the description - check it out."),
    (48.29, 52.80, "Cases like this are available from iPhone 13 onwards.", {1: 48.66}),
    (52.84, 54.60, "Choose the one you need."),
    (54.68, 56.58, "What I like most about it:"),
    (56.62, 59.55, "see - it even covers the Action Button.", {4: 57.36}),
    (59.57, 62.85, "None of the cases I used before covered this part -"),
    (63.56, 65.90, "it used to be open there instead."),
    (65.92, 69.98, "But here, it's properly covered."),
    (70.01, 70.95, "Not only that,"),
    (70.97, 76.05, "it's designed not to get damaged easily if it falls."),
    (76.10, 78.86, "So even if your phone suddenly falls,"),
    (78.90, 80.95, "there's nothing to fear."),
    (80.98, 85.50, "The protection around the camera is done right, too."),
    (85.55, 88.95, "By protection, I mean protection for the lenses."),
    (89.00, 90.72, "If you use a lens protector,"),
    (90.76, 95.95, "you're less likely to get your camera's full quality,"),
    (95.98, 97.78, "so I don't use one."),
    (97.81, 99.08, "There's no need for it."),
    (99.11, 102.95, "What I mean is this border - it sticks out a little more,", {5: 100.37}),
    (102.97, 105.18, "so scratches and the like"),
    (105.20, 109.40, "won't happen when you set it down like this."),
    (109.43, 112.50, "So it's a really useful, perfect case."),
    (112.56, 116.12, "It also feels satisfying to hold."),
    (116.16, 119.74, "And it supports MagSafe too.", {3: 117.89}),
    (119.77, 121.62, "The charging port"),
    (121.66, 124.38, "and this speaker area you can see"),
    (124.41, 127.22, "have precise cut-outs,"),
    (127.25, 129.38, "and they're shaped to stay protected too."),
    (129.41, 133.62, "Nothing blocks the sound at all."),
    (133.66, 137.95, "The charger fits the charging port perfectly, too."),
    (137.97, 141.88, "I haven't had any trouble like that with it."),
    (141.92, 144.90, "And the buttons all have a really good grip."),
    (145.95, 149.95, "So overall, I'd call it one of the best cases."),
    (150.72, 152.55, "Its MRP is ₹1,999,"),
    (152.58, 155.30, "but you can get it from ₹520,", {4: 153.36}),
    (155.34, 159.40, "with the price varying by phone model."),
    (159.60, 161.25, "You get it in a good price range."),
    (161.30, 164.38, "For the price, it really is an excellent case"),
    (164.41, 167.05, "in my opinion - whichever way you look at it."),
    (167.08, 169.80, "It has a really sleek look."),
    (169.82, 172.60, "Once it's on, when you look at the phone,"),
    (172.63, 175.68, "it's designed so anyone would like it."),
    (175.70, 181.15, "Every part is done properly - nothing feels lacking."),
    (181.17, 184.50, "Also, the cut-outs on the back"),
    (184.54, 189.85, "and the holes here and there let the heat out,"),
    (189.87, 193.62, "especially over the parts that get warm."),
    (193.66, 198.15, "So you can use it safely and securely."),
    (198.21, 199.55, "A really useful case."),
    (199.61, 202.00, "If you want one, the link is in the description -"),
    (202.03, 203.65, "you can check it out."),
    (203.68, 206.45, "Pick the one for your phone model,"),
    (206.48, 209.40, "in the colour you like - there are about five."),
    (209.43, 210.88, "The design is the same."),
    (210.91, 212.70, "There's a transparent version, too."),
    (212.74, 215.30, "You can check everything through that link."),
    (215.32, 217.15, "If you liked the video, don't forget to like it."),
    (217.19, 220.08, "For more videos like this, subscribe to the channel."),
    (220.11, 222.70, "See you again soon!"),
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
