"""Screen-recording clean-up for the "AssistiveTouch: screenshot and restart" video (iPhone, 1320x2868; times = seconds
of the 30 fps SDR copy).

Private material: the Apple Account row at the top of Settings (name, photo) - blurred whenever the Settings main page
is on screen, with a wider blur while that page animates in or out.  The red recording indicator in the Dynamic Island
is painted out wherever it sits.  The AssistiveTouch button stays: it is what the video is about.
"""

FPS = 30
BLUR_SIGMA = 16

ACCOUNT = (0.03, 0.168, 0.97, 0.282)

BLUR_RECTS = [
    (12.70, 13.85, (0.00, 0.06, 1.00, 0.46)),     # Settings zooming open from the icon
    (13.80, 16.20, ACCOUNT),
    (16.05, 16.60, (0.00, 0.06, 1.00, 0.40)),     # search field taking over the page
    (259.30, 259.90, (0.00, 0.06, 1.00, 0.46)),   # back to the Settings main page
    (259.85, 331.80, ACCOUNT),
    (331.65, 332.40, (0.00, 0.06, 1.00, 0.40)),   # search again
]

INDICATOR_BAND = (380, 60, 1015, 132)            # red recording dot, found by colour (it shifts a few px)
