"""English caption chunks timed to the Malayalam narration ("build your own free AI assistant", Tab, V Create).

Each chunk is (start_s, end_s, text[, {word_index: time_s}]).  Chunk boundaries come from the word-level timestamps of the
Malayalam ASR (+/-0.2 s).  The 3D title covers 0-6.95 s, so captions start with the greeting.
See captions/own-ai-assistant_script_en.md for the readable script.
"""

CHUNKS = [
    (6.95, 8.66, "Hello, I'm Jabir Varikkodan."),
    (8.72, 10.36, "Welcome to V Create!"),
    (10.62, 12.28, "We can build our very own"),
    (12.29, 15.20, "free AI assistant."),
    (15.73, 17.90, "And it's 100% free!"),
    (18.68, 21.14, "It does many things automatically -"),
    (21.23, 23.70, "just hand them to your AI assistant."),
    (23.78, 25.49, "For example, if you want a restaurant"),
    (25.50, 27.57, "that suits your taste,"),
    (27.58, 29.70, "it finds one and shows you."),
    (29.86, 31.86, "Want to book a room there?"),
    (31.87, 33.98, "It does that too."),
    (34.08, 36.60, "If you need help with a phone call,"),
    (36.65, 38.20, "it handles that for you."),
    (38.38, 40.65, "Likewise, flight or hotel tickets,"),
    (40.68, 43.42, "any tickets you want booked -"),
    (43.99, 45.10, "it books them too."),
    (45.18, 46.98, "While you're scrolling on your phone,"),
    (47.00, 49.45, "if you spot a dress or a bag"),
    (49.53, 51.70, "that you want to order,"),
    (51.73, 53.45, "just send it a screenshot"),
    (53.49, 56.45, "and ask it to find and order it -"),
    (56.50, 57.98, "it does everything automatically"),
    (58.00, 60.90, "and confirms the order for you."),
    (61.10, 63.16, "Need a flight ticket"),
    (63.17, 65.85, "or anything like that?"),
    (65.90, 67.10, "It books it for you."),
    (67.30, 68.95, "Or if you need to send an email,"),
    (68.96, 70.80, "or set a reminder,"),
    (70.85, 73.20, "whatever it is, it can do that too."),
    (73.30, 76.05, "So many things, done automatically."),
    (76.15, 78.75, "We can build this AI assistant for free."),
    (78.78, 79.85, "It's very simple -"),
    (79.86, 82.25, "you can do it right on your phone."),
    (82.41, 84.30, "For more useful videos like this,"),
    (84.31, 86.25, "subscribe to the channel and follow me."),
    (86.32, 87.80, "Share this video with everyone,"),
    (87.82, 90.20, "so more people know this is possible."),
    (90.25, 91.85, "Even if it's not useful right now,"),
    (91.90, 93.75, "it may come in handy later,"),
    (93.80, 95.30, "so save this video."),
    (95.70, 96.88, "Let's see how to do it."),
    (96.91, 99.05, "I've put the link in the description."),
    (99.10, 101.30, "Open that link,"),
    (101.34, 104.00, "and you'll see a Create your AI assistant button."),
    (104.05, 107.45, "Tap it to reach this page."),
    (107.84, 109.90, "Here, enter your first name."),
    (109.96, 112.40, "Then, with the country code,"),
    (112.41, 114.20, "enter your mobile number."),
    (114.35, 116.62, "It works whichever country you're in."),
    (116.76, 118.95, "After that, tick the agreement"),
    (119.00, 120.40, "checkbox you see here."),
    (120.44, 123.58, "Then, once you tap Sign up,"),
    (123.61, 126.50, "you'll see that you're on the waiting list."),
    (126.56, 128.70, "You need to wait about a day."),
    (128.76, 130.13, "Once you've waited,"),
    (130.14, 132.50, "connect it with WhatsApp,"),
    (132.55, 135.80, "and the two work together for you."),
    (135.94, 139.00, "A really, really useful AI assistant."),
    (139.36, 142.95, "Once you get Tab from the waitlist,"),
    (143.06, 144.95, "tap Sign in,"),
    (144.96, 147.65, "enter your mobile number,"),
    (147.71, 150.25, "then tap Send code"),
    (150.29, 152.65, "and enter your OTP."),
    (152.70, 155.00, "You'll get into its chat,"),
    (155.01, 157.00, "and from there, everything I mentioned,"),
    (157.01, 158.85, "you can get it done."),
    (158.86, 160.98, "And I mean everything -"),
    (161.04, 163.30, "from photo editing to video editing,"),
    (163.31, 166.90, "this AI assistant does it for you, free."),
    (167.48, 168.95, "It's really useful."),
    (168.98, 171.80, "So don't forget to share this video,"),
    (171.89, 174.40, "let people know this is possible."),
    (174.67, 177.30, "See you again with a new topic!"),
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
