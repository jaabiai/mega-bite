"""Screen-recording clean-up for the "record calls without the announcement" video (Android, 720x1608).
Times = seconds of the 30 fps copy.  The Recents list shows other people's names and photos: every row is blurred while it
is on screen (including the app-open animation and behind the menu drawer).  No recording indicator or floating bubble."""

FPS = 30
BLUR_SIGMA = 14

BLUR_RECTS = [
    (11.15, 11.55, (0.00, 0.20, 1.00, 0.95)),        # Phone app zooming open: rows fading in
    (11.45, 36.20, (0.03, 0.322, 0.97, 0.874)),      # Recents rows (names, photos, call times)
]
