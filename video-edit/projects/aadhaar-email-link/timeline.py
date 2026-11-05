"""Edit decision data for "link your email ID to Aadhaar" (V Create, cinematic style: render_cine.py).

T = output (narration) time in seconds.  The phone scenes show illustrated screens (screens.py) because the Aadhaar app
blocks screen recording; only the Gmail OTP mail comes from the real recording (S = recording time).
"""
import numpy as np
from screens import RECTS as R

STYLE = "cine"
FPS = 30
NARR_END = 177.24
END_CARD = 6.0
TOTAL = NARR_END + END_CARD
LETTERBOX = 118

TITLE_T = (0.35, 4.9)
TITLE_LINES = [("LINK YOUR EMAIL", False), ("TO AADHAAR", True)]
STING_T0 = 38.40                                        # "Welcome to V Create"
FACE_ANCHOR = dict(fx=0.48, fy=0.30)
GRADE = dict(clarity=0.08, face_lift=0.16, tint=1.0)

# ---- scenes -----------------------------------------------------------------------------------------
SCENES = [
    dict(kind="face",    t0=0.00,   t1=5.50,   zoom=(1.28, 1.33), name="hook"),
    dict(kind="broll",   t0=5.50,   t1=11.92,  clip="14669", clip_t=0.3, reel_clip="41174", reel_clip_t=0.0, reel_speed=0.9, name="phone-use"),
    dict(kind="broll",   t0=11.92,  t1=18.72,  clip="47735", clip_t=1.0, reel_clip="18307", reel_clip_t=0.0, reel_speed=0.86, name="coins"),
    dict(kind="graphic", t0=18.72,  t1=22.97,  args=dict(month="DECEMBER", day="31", kicker="DEADLINE", note="FREE UNTIL THEN"), name="deadline"),
    dict(kind="face",    t0=22.97,  t1=36.52,  zoom=(1.33, 1.28), name="how"),
    dict(kind="face",    t0=36.52,  t1=47.27,  zoom=(1.28, 1.34), name="welcome"),
    dict(kind="phone",   t0=47.27,  t1=87.67,  name="app-a"),
    dict(kind="face",    t0=87.67,  t1=91.22,  zoom=(1.30, 1.34), name="simple"),
    dict(kind="phone",   t0=91.22,  t1=160.26, name="app-b"),
    dict(kind="face",    t0=160.26, t1=NARR_END, zoom=(1.28, 1.34), name="outro"),
    dict(kind="end",     t0=NARR_END, t1=TOTAL, name="end-card"),
]

TRANSITIONS = [
    (5.50, "flash"), (11.92, "whip"), (18.72, "whip"), (22.97, "flash"), (36.52, "whip"), (47.27, "flash"),
    (87.67, "whip"), (91.22, "whip"), (160.26, "flash"), (NARR_END, "dip"),
]
TRANSITION_SFX = {"flash": ("1491", -0.45, -11), "whip": ("1492", -0.35, -12), "dip": None}

CHAPTERS = [(42.70, 47.05, "LINK IN THE DESCRIPTION", "Install the new app")]

# ---- calls to action: (T0, kind[, dur]) -----------------------------------------------------------
CTAS = [
    (29.45, "subscribe"), (32.95, "share"),
    (61.20, "like"),
    (87.75, "engage", 3.45),
    (124.60, "comment"),
    (149.00, "like"),
    (160.50, "subscribe"), (165.10, "engage"), (169.90, "share"), (173.40, "like"),
]


def _cta_sfx():
    out = []
    for c in CTAS:
        t0, what = c[0], c[1]
        if what == "subscribe":
            out += [(t0 + 1.2, "2354", -10), (t0 + 1.35, "933", -14)]
        elif what in ("like", "share", "comment"):
            out += [(t0 + {"like": 0.8, "share": 1.0, "comment": 0.9}[what], "2350", -14)]
        elif what == "engage":
            out += [(t0 + 0.8, "2350", -15), (t0 + 2.25, "2354", -11)]
    return out


EXTRA_SFX = [(0.45, "1485", -14), (38.32, "2596", -10), (19.40, "1485", -13)] + _cta_sfx()
TAP_SFX = "1109"

# ---- phone screen source ----------------------------------------------------------------------------
SCREEN_T0, SCREEN_END = 120.0, 127.0                     # cleaned clip of the real recording (Gmail OTP mail)
REC_SPANS = [(105.41, 108.84)]
SCREEN_MAP = [(105.41, 121.70), (108.84, 124.90)]


def screen_source(T):
    return "rec" if any(a <= T < b for a, b in REC_SPANS) else "app"


def screen_time(T):
    return float(np.interp(T, [p[0] for p in SCREEN_MAP], [p[1] for p in SCREEN_MAP]))


# ---- camera on the whole phone: (T, zoom, u, v) ---------------------------------------------------------
def _c(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def _focus(t0, t1, r, z, ease=0.6):
    u, v = _c(r)
    return [(t0, z, u, v), (t1, z, u, v)]


OV = lambda t, z=1.0: (t, z, 0.5, 0.5)
CAMERA = (
    [(47.27, 0.86, 0.5, 0.5), OV(48.1), OV(49.6)] + _focus(50.2, 51.6, R["login_btn"], 1.45) +
    [OV(52.4), OV(55.4)] + _focus(56.3, 59.8, R["tab_services"], 1.7) +
    [OV(60.6), OV(62.3)] + _focus(63.0, 66.6, R["row_email"], 1.6) + _focus(67.2, 73.9, R["free_badge"], 1.85) +
    [OV(74.7), OV(75.6)] + _focus(76.3, 79.4, R["add_link"], 1.65) + _focus(80.0, 87.67, R["no_email"], 1.75) +
    [OV(91.22, 1.05)] + _focus(91.8, 94.5, R["btn_continue"], 1.5) +
    [OV(95.3), OV(95.9)] + _focus(96.5, 99.8, R["email_field"], 1.7) + _focus(100.5, 103.2, R["btn_send"], 1.55) +
    [OV(104.6)] + [(105.41, 1.0, 0.5, 0.5), (106.0, 1.75, 0.5, 0.27), (108.7, 1.75, 0.5, 0.27)] +
    _focus(109.0, 110.6, R["otp_boxes"], 1.6) + _focus(111.0, 112.7, R["btn_review"], 1.5) +
    _focus(113.3, 116.0, R["review_email"], 1.7) + _focus(116.8, 121.3, R["btn_face"], 1.5) + _focus(121.6, 124.3, R["other_option"], 1.7) +
    [OV(125.0, 1.05), OV(129.4, 1.1)] + _focus(129.9, 133.4, R["face_ok"], 1.55) +
    [OV(133.9)] + _focus(134.4, 137.6, R["btn_submit"], 1.5) + [OV(138.3), OV(140.6)] + _focus(141.3, 144.6, R["btn_submit"], 1.55) +
    [OV(145.3), OV(148.8)] + _focus(150.8, 155.3, R["banner"], 1.55) + _focus(155.9, 160.26, R["btn_ack"], 1.5)
)

# ---- taps (T, u, v) ---------------------------------------------------------------------------------------
TAPS = [(51.25,) + _c(R["login_btn"]), (59.60,) + _c(R["tab_services"]), (73.90,) + _c(R["row_email"]),
        (94.45,) + _c(R["btn_continue"]), (102.60,) + _c(R["btn_send"]), (112.40,) + _c(R["btn_review"]),
        (124.20,) + _c(R["btn_face"]), (137.40,) + _c(R["btn_submit"]), (144.40,) + _c(R["btn_submit"]),
        (159.40,) + _c(R["btn_ack"])]

# ---- spotlight highlights: (T0, T1, (u0, v0, u1, v1), label) ------------------------------------------
PIN = (0.40, 0.245, 0.62, 0.300)
HIGHLIGHTS = [
    (50.30, 51.50, R["login_btn"], "Log in"),
    (56.45, 59.75, R["tab_services"], "Services"),
    (63.07, 66.65, R["row_email"], "Email Add / Update"),
    (66.72, 68.40, R["free_badge"], "Free"),
    (68.45, 73.50, R["free_note"], "Free-until note"),
    (76.30, 79.45, R["add_link"], "Add / Link email"),
    (80.11, 87.60, R["no_email"], "Not linked yet"),
    (91.80, 94.40, R["btn_continue"], "Continue"),
    (96.60, 99.60, R["email_field"], "Your email ID"),
    (100.68, 102.55, R["btn_send"], "Send OTP"),
    (105.90, 108.70, PIN, "OTP (hidden)"),
    (109.00, 110.50, R["otp_boxes"], "Enter the OTP"),
    (111.04, 112.40, R["btn_review"], "Continue to review"),
    (113.40, 115.90, R["review_email"], "Your email"),
    (117.02, 121.25, R["btn_face"], "Face authentication"),
    (121.70, 124.10, R["other_option"], "Other option"),
    (129.90, 133.40, R["face_ok"], "Authenticated"),
    (134.40, 137.35, R["btn_submit"], "Continue to submit"),
    (141.40, 144.35, R["btn_submit"], "Submit request"),
    (150.90, 155.35, R["banner"], "Notification"),
    (156.00, 159.35, R["btn_ack"], "Acknowledgement"),
]

STEPS = [
    (47.27, 51.92, 1, "Install & log in"),
    (51.92, 60.00, 2, "Open Services"),
    (60.00, 87.67, 3, "Email Add / Update"),
    (91.22, 103.35, 4, "Enter email & Send OTP"),
    (103.35, 115.93, 5, "Verify the OTP"),
    (115.93, 133.58, 6, "Face authentication"),
    (133.58, 148.13, 7, "Submit request"),
    (148.13, 160.26, 8, "Download acknowledgement"),
]
N_STEPS = 8
