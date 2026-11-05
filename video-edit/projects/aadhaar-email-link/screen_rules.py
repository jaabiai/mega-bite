"""Screen-recording clean-up for the "link email to Aadhaar" video.

The Aadhaar app blocks screen recording (black frames), so only the Gmail OTP mail (recording 121-126 s) is used; the rest
of the phone scenes are illustrations (screens.py).  The OTP digits are blurred, the recording dot and the AssistiveTouch
bubble are removed.  Times = recording seconds; the cleaned clip starts at 120.0 s.
"""

BLUR_SIGMA = 15

BLUR_RECTS = [
    (120.0, 127.0, (0.415, 0.255, 0.595, 0.292)),     # one-time PIN in the mail body
]

INDICATOR_BAND = (380, 70, 1015, 125)

BUBBLE = dict(centre=(1202.5, 1997.5), radius=96, feather=4, modes=[(120.0, 127.0, "flat")])
