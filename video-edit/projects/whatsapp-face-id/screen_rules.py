"""Screen-recording clean-up rules for the "hide WhatsApp calls from the iPhone call log" video (times = recording seconds)."""

BLUR_SIGMA = 15

# (S_start, S_end, (u0, v0, u1, v1))   -- the Recents list holds names of real contacts: blur every row
BLUR_RECTS = [
    (94.93, 95.12, (0.00, 0.28, 1.00, 0.895)),      # Phone app growing out of the dock icon (rows already readable)
    (95.12, 95.30, (0.00, 0.245, 1.00, 0.93)),      # nearly full window, still settling
    (95.30, 109.0, (0.00, 0.232, 1.00, 0.915)),     # Recents list, final position
]

# the red / orange recording indicators wander around the island while Face ID runs: found by colour inside this band (x0, y0, x1, y1)
INDICATOR_BAND = (380, 70, 1015, 125)


# AssistiveTouch bubble (centre x, y in the 1320x2868 recording): the wallpaper behind it is flat, the Recents page is not
BUBBLE = dict(centre=(1202.6, 442.6), radius=99, feather=4,
              modes=[(0.0, 94.95, "flat"), (94.95, 95.35, "inpaint"), (95.35, 1e9, "patch")],
              patch=dict(header_px=(1040, 320), fill_px=(1040, 525), pill=(60, 504, 1260, 646), line_y=347))
