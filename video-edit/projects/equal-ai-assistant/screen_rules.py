"""Screen-recording clean-up for the Equal AI video.  The three iPhone recordings (1320x2868) are joined into one
30 fps SDR file: recording 1 (onboarding) from S 0, recording 2 (instructions, presets, languages, voice, silent
mode) from S 90.4333, recording 3 (call handling, languages, premium card) from S 394.9667.

Private material, found by template matching (work notes: detect_priv.py) and blurred with a margin:
* the profile header on the "You" page: full name + phone number;
* the chat-list preview "Hi <full name>!";
* the Recents list in the Phone app (other people's names and a phone number) and the app switcher.
The red recording dot in the Dynamic Island is painted out wherever it sits.
"""

FPS = 30
BLUR_SIGMA = 18
O1, O2, O3 = 0.0, 2713 / 30, (2713 + 9136) / 30

HEADER = (0.21, 0.084, 0.96, 0.170)          # name + phone number under the avatar
PREVIEW = (0.12, 0.449, 0.82, 0.492)         # "Hi <name>!..." under "Equal AI Assistant"


def _r(o, spans, rect, m=0.12):
    return [(o + a - m, o + b + m, rect) for a, b in spans]


BLUR_RECTS = (
    [(O1 + 49.80, O1 + 53.60, (0.0, 0.0, 1.0, 1.0)),          # app switcher / home screen
     (O1 + 53.55, O1 + 62.45, (0.0, 0.318, 1.0, 0.905))]      # Recents: contacts and a number
    + _r(O1, [(74.7, 86.2)], PREVIEW)
    + _r(O2, [(4.7, 8.3), (152.1, 154.5), (254.2, 256.8), (266.5, 280.8), (290.0, 294.3)], HEADER)
    + _r(O2, [(0.0, 4.7), (294.2, 296.0), (301.8, 304.6)], PREVIEW)     # hidden behind the "makes calls" popup between
    + _r(O3, [(0.0, 5.7), (40.7, 46.5), (131.5, 140.1), (165.1, 173.4)], HEADER)
    + _r(O3, [(173.4, 179.9)], PREVIEW)
)

INDICATOR_BAND = (380, 60, 1015, 132)        # red recording dot, found by colour (it shifts a few px)
