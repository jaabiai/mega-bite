"""Screen-recording clean-up for the "build your own free AI assistant (Tab)" video.  Times = recording seconds of the
30 fps SDR copy.  The presenter's mobile number is blurred wherever it shows (form field, AutoFill suggestion, sign-in field);
the recording dot and the AssistiveTouch bubble are removed."""

FPS = 30
BLUR_SIGMA = 15

BLUR_RECTS = [
    (9.05, 10.30, (0.18, 0.630, 0.82, 0.712)),      # AutoFill suggestion above the keypad: "mobile +91 ..."
    (10.10, 24.00, (0.33, 0.290, 0.645, 0.336)),     # sign-up form: number field
    (82.30, 92.50, (0.32, 0.228, 0.640, 0.276)),     # sign-in: number field while the keypad is up
    (92.40, 93.40, (0.32, 0.228, 0.640, 0.545)),     # keypad closing, page sliding down
    (93.30, 112.0, (0.33, 0.497, 0.610, 0.540)),     # sign-in: number field after "Send code"
]

INDICATOR_BAND = (380, 60, 1020, 140)                # red recording dot in the Dynamic Island

# AssistiveTouch bubble: one translucent-overlay profile fitted on flat backgrounds, then un-mixed wherever it sits
BUBBLE = dict(radius=92, feather=4,
              cal=[(30.0, (117, 1939)), (86.0, (333, 2751)), (22.0, (117, 1939)), (125.0, (117, 1939))],
              modes=[(0.0, 15.30, "unmix", (116.5, 1443.0)),
                     (15.30, 20.05, "inpaint", (118.5, 1939.0)),
                     (20.05, 81.20, "unmix", (117.0, 1939.5)),
                     (81.20, 92.70, "unmix", (333.5, 2751.0)),
                     (92.70, 1e9, "unmix", (117.0, 1940.0))])
BUBBLE["centre"] = (117.0, 1939.5)
