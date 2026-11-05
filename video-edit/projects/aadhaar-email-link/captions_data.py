"""English caption chunks timed to the Malayalam narration ("link your email ID to Aadhaar", V Create).

Each chunk is (start_s, end_s, text[, {word_index: time_s}]).  Chunk boundaries come from the word-level
timestamps of the Malayalam ASR (+/-0.2 s).  See captions/aadhaar-email-link_script_en.md for the readable script.
"""

CHUNKS = [
    (0.00, 1.00, "Have you linked"),
    (1.02, 2.68, "your email ID to Aadhaar?"),
    (2.70, 4.02, "If you haven't,"),
    (4.04, 5.48, "link it right now,"),
    (5.50, 6.95, "using your phone,"),
    (10.10, 11.90, "for free."),
    (11.92, 13.34, "Earlier, PAN card linking"),
    (13.36, 15.15, "was free for us."),
    (15.17, 16.67, "After that, now,"),
    (16.69, 18.70, "PAN linking costs money."),
    (18.72, 20.14, "In the same way, for this too,"),
    (20.16, 21.88, "after December 31"),
    (21.90, 22.95, "you'll have to pay."),
    (22.97, 25.01, "So, to do it for free,"),
    (25.03, 27.10, "do it now, on your phone."),
    (27.22, 29.10, "Let me tell you how."),
    (29.16, 31.95, "For useful videos like this,"),
    (31.97, 32.69, "subscribe,"),
    (32.71, 34.21, "share it with everyone,"),
    (34.23, 35.07, "let people know"),
    (35.09, 36.50, "this can be done."),
    (36.52, 38.44, "Anyway, let's get into it."),
    (38.46, 39.05, "Welcome to"),
    (39.07, 40.39, "V Create!"),
    (40.41, 42.40, "Welcome, everyone, to a new video."),
    (42.52, 43.52, "For this,"),
    (43.54, 45.72, "download the new mAadhaar app —"),
    (45.74, 47.25, "link in the description."),
    (47.27, 48.97, "Download and open it,"),
    (48.99, 50.27, "enter your Aadhaar details"),
    (50.29, 51.90, "and log in to the app."),
    (51.92, 53.26, "After that,"),
    (53.28, 55.32, "you'll see this interface."),
    (55.34, 56.43, "Here, at the"),
    (56.45, 58.41, "very bottom: Services."),
    (58.43, 59.80, "Select it."),
    (59.82, 61.04, "Once you select it,"),
    (61.06, 63.05, "you'll see many options here."),
    (63.07, 64.51, "Among them,"),
    (64.53, 66.70, "Email Add / Update — that option."),
    (66.72, 68.38, "It'll say Free there,"),
    (68.40, 70.15, "and how long it's free —"),
    (70.17, 72.87, "a date notice is given right here."),
    (72.89, 73.53, "You'll see it."),
    (73.55, 74.40, "Select it."),
    (74.42, 76.28, "Once selected, here"),
    (76.30, 78.45, "you'll see Add / Link email address —"),
    (78.47, 79.51, "that option is there."),
    (79.53, 80.09, "Below it,"),
    (80.11, 83.30, "\"No email linked to your Aadhaar\" shows."),
    (83.32, 85.24, "If it's already linked,"),
    (85.26, 87.65, "it shows here as linked."),
    (87.67, 89.39, "So, to do this,"),
    (89.41, 91.20, "it's very simple."),
    (91.22, 93.64, "Continue to update email address —"),
    (93.66, 94.65, "tap this button."),
    (94.67, 96.05, "Once you tap it,"),
    (96.07, 97.30, "the email you want to add,"),
    (97.32, 98.94, "type it in here."),
    (98.96, 100.66, "After entering the email ID,"),
    (100.68, 102.25, "tap Send OTP."),
    (102.27, 103.35, "Select it."),
    (103.37, 105.39, "After tapping Send OTP,"),
    (105.41, 107.20, "to the email you entered,"),
    (107.22, 108.82, "an OTP will arrive."),
    (108.84, 110.26, "Type it in here."),
    (110.28, 111.02, "Type it,"),
    (111.04, 112.55, "Continue to review —"),
    (112.57, 113.27, "tap it,"),
    (113.29, 115.00, "and the email ID you gave"),
    (115.01, 115.91, "shows up here."),
    (115.93, 117.00, "After that,"),
    (117.02, 118.96, "Continue to face authentication —"),
    (118.98, 120.25, "if you get that option,"),
    (120.27, 121.31, "select it."),
    (121.33, 122.95, "If not, whatever other option"),
    (122.97, 124.50, "appears, select that."),
    (124.52, 126.60, "After that, your photo"),
    (126.62, 128.69, "is captured like this."),
    (128.71, 129.81, "Once it's captured,"),
    (129.83, 131.80, "\"Face authenticated successfully\""),
    (131.82, 133.56, "will appear."),
    (133.58, 134.26, "After that,"),
    (134.28, 136.67, "Continue to submit request —"),
    (136.69, 137.77, "tap that button,"),
    (137.79, 140.26, "and you're back here."),
    (140.28, 141.31, "From there, again,"),
    (141.33, 143.09, "Submit request —"),
    (143.11, 144.65, "tap it, and"),
    (144.67, 146.82, "the request to update your email"),
    (146.84, 148.11, "gets sent."),
    (148.13, 149.71, "Once the request is sent,"),
    (149.73, 151.86, "you'll get a message and"),
    (151.88, 153.54, "a notification,"),
    (153.56, 155.41, "saying it's been submitted."),
    (155.43, 157.61, "If you want the acknowledgement"),
    (157.63, 159.96, "receipt, download it from here."),
    (160.26, 161.58, "So, very simply,"),
    (161.60, 163.35, "with just your phone,"),
    (163.37, 164.95, "add your email ID."),
    (165.11, 166.42, "This video will help"),
    (166.44, 168.98, "everyone — no doubt."),
    (169.00, 170.93, "Share it with everyone,"),
    (170.95, 171.91, "let people know"),
    (171.93, 174.36, "they can do this themselves."),
    (174.38, 176.34, "See you again with"),
    (176.36, 177.24, "a new topic!"),
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
