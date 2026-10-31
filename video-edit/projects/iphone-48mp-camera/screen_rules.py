"""Screen-recording clean-up rules for the "48 MP photos on iPhone" video (times = recording seconds).

Private material in this recording: a bank-notification list (Notification Centre pulled down), personal photos in the
Photos app (family poster, selfies, a child's school record with a portrait, a Facebook e-mail screenshot), the photo
location title, an ad banner and the last-photo thumbnail inside the Camera app.  The timeline never maps most of those
stretches; they are blurred anyway.
"""

BLUR_SIGMA = 15

# (S_start, S_end, (u0, v0, u1, v1))
BLUR_RECTS = [
    (76.20, 80.00, (0.00, 0.00, 1.00, 1.00)),        # Notification Centre / lock screen (bank messages)
    (72.50, 139.60, (0.055, 0.900, 0.215, 0.975)),   # Camera app: last-photo thumbnail
    (139.50, 150.30, (0.00, 0.00, 1.00, 0.905)),     # Photos: poster, selfies, other personal pictures
    (139.50, 211.00, (0.00, 0.868, 1.00, 0.915)),    # Photos: thumbnail strip
    (163.60, 171.60, (0.00, 0.00, 1.00, 0.245)),     # ad banner over the photo
    (179.40, 181.30, (0.10, 0.030, 0.90, 0.090)),    # photo location title
    (184.60, 186.60, (0.10, 0.030, 0.90, 0.090)),
    (184.60, 188.30, (0.00, 0.00, 1.00, 0.905)),     # school record, still full screen
    (188.30, 197.00, (0.00, 0.00, 1.00, 0.505)),     # school record with the info panel up
]

# blurs that reach the top edge must not smear the Dynamic Island (S0, S1, (x0, y0, x1, y1) in px)
ISLAND_FIX = [(184.60, 197.00, (472, 42, 848, 152)), (139.50, 150.30, (472, 42, 848, 152))]

# the red / orange recording indicators move around the island: found by colour inside this band (x0, y0, x1, y1)
INDICATOR_BAND = (380, 70, 1015, 125)

# AssistiveTouch bubble (centre x, y, radius) – top-left, over the clock / back button; removed by alpha un-mixing
ASSIST = (158, 131, 95)
BUBBLE_CAL = dict(times=[82.0, 4.0, 150.0, 20.0],  # black (Camera), brown wallpaper, white (Photos header), grey (Settings)
                  centre_in_crop=(150.5, 130.5),  # in the 300x300 box (8, 0)
                  rim=100, lower_valid=299, ring=(105, 135), valid_r=100)
