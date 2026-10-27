"""Screen-recording clean-up rules for the "lock your Google search history" video (times = recording seconds)."""

BLUR_SIGMA = 15

# (S_start, S_end, (u0, v0, u1, v1))
BLUR_RECTS = [
    # account sheet sliding up / settled: header + every account row
    (21.95, 22.55, (0.00, 0.20, 1.00, 1.00)),
    (22.55, 29.45, (0.03, 0.255, 0.97, 0.845)),
    # "Manage your Google Account" pop-over: e-mail line, tail of the e-mail behind it, account rows under it
    (28.25, 36.95, (0.10, 0.228, 0.56, 0.290)),
    (28.25, 36.95, (0.56, 0.285, 0.80, 0.345)),
    (28.25, 36.60, (0.02, 0.372, 0.98, 0.900)),
    (36.40, 36.95, (0.02, 0.150, 0.98, 0.900)),
    # Google Account page header (name + e-mail + avatar) and the flick-scroll that removes it
    (36.60, 37.95, (0.06, 0.135, 0.70, 0.300)),
    (37.95, 38.50, (0.00, 0.000, 1.00, 0.360)),
    # passkey page: e-mail chip
    (73.55, 88.00, (0.03, 0.498, 0.70, 0.560)),
    (73.50, 73.90, (0.03, 0.405, 0.70, 0.470)),     # chip position during the page's first frames
]


# fixed UI artefacts (pixel coordinates in the 1320x2868 recording)
DOT = (446, 97, 22)                  # red recording dot inside the island
ORANGE = (948, 97, 30)               # orange recording glyph right of the island
ASSIST = (786, 2706, 98)             # AssistiveTouch bubble (centre x, y, radius)
BUBBLE_CAL = dict(t_light=49.0, t_dark=66.0, centre_in_crop=(150.5, 152.0), rim=127, lower_valid=200)
