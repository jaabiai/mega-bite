"""Screen-recording clean-up for the "Photos: Aspect Ratio Grid" video (iPhone, 1320x2868; times = seconds of the 30 fps
SDR copy).

Private material: a photographed receipt / membership slip (names, numbers, signature) in the library grid - blurred
wherever it is uncovered (app-open animation, square grid, beside the View Options menu, aspect grid after the menu
closes).  While the grid is zoomed out to five columns (S 90.9-93.3) every thumbnail outside the menu is blurred: that
view shows other people, a printed document and a parcel label (the edit does not use those frames).
Also removed: the red recording dot in the Dynamic Island and the idle AssistiveTouch bubble on the right edge
(un-mixed with the radial profile in bubble_fit.npz, fitted by tools/bubble_fit.py from bubble_spec.json).
"""
import os

FPS = 30
BLUR_SIGMA = 16

REC_SQ = (0.330, 0.437, 0.670, 0.599)          # receipt in the square grid (column 2, row 3)
REC_AR = (0.072, 0.446, 0.268, 0.607)          # receipt in the aspect-ratio grid after zooming (column 1, row 3)

BLUR_RECTS = [
    (0.70, 1.13, (0.28, 0.38, 0.72, 0.64)),    # Photos opening from the icon: the grid scales up through the middle
    (1.10, 52.80, REC_SQ),                      # square grid, until the menu has grown over the receipt
    (90.05, 90.55, (0.00, 0.28, 0.21, 0.78)),   # zoom-in -> three columns: the receipt slides in on the left
    (90.50, 96.45, (0.072, 0.446, 0.160, 0.607)),   # the strip of the receipt left of the menu
    (96.40, 111.0, REC_AR),                     # menu dismissed: the whole receipt
    # five-column zoom-out: everything around the menu
    (90.85, 93.35, (0.000, 0.145, 0.160, 0.905)),
    (90.85, 93.35, (0.735, 0.145, 1.000, 0.905)),
    (90.85, 93.35, (0.160, 0.610, 0.735, 0.905)),
]

DOT = (446, 97, 22)                             # red recording dot inside the Dynamic Island
BUBBLE_FIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bubble_fit.npz")
