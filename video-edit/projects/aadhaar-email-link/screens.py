"""Illustrated app screens for "link your email to Aadhaar" (the real app blocks screen recording).

render(T) -> 1320x2868 RGB uint8 for output time T.  Generic, unbranded UI drawn with lib/appmock; every private value is
a placeholder (masked numbers, yourname@gmail.com).  RECTS holds the screen-space boxes the timeline highlights.
"""
import math
from appmock import *

EMAIL = "yourname@gmail.com"
U = lambda x0, y0, x1, y1: (x0 / SW, y0 / SH, x1 / SW, y1 / SH)

RECTS = {
    "login_btn":    U(80, 1200, 1240, 1360),
    "tab_services": U(500, 2590, 820, 2800),
    "row_email":    U(60, 550, 1260, 740),
    "free_badge":   U(905, 600, 1110, 690),
    "free_note":    U(215, 655, 860, 718),
    "add_link":     U(100, 530, 1220, 700),
    "no_email":     U(100, 750, 1220, 870),
    "btn_continue": U(80, 2520, 1240, 2690),
    "email_field":  U(80, 520, 1240, 690),
    "btn_send":     U(80, 1640, 1240, 1800),
    "otp_boxes":    U(70, 550, 1250, 770),
    "btn_review":   U(80, 1640, 1240, 1800),
    "review_email": U(100, 540, 1220, 720),
    "btn_face":     U(80, 2380, 1240, 2550),
    "other_option": U(300, 2585, 1020, 2665),
    "face_ok":      U(90, 1840, 1230, 1970),
    "btn_submit":   U(80, 2520, 1240, 2690),
    "btn_ack":      U(80, 2520, 1240, 2690),
    "banner":       U(40, 60, 1280, 350),
}

# output-time schedule: (T0, T1, screen)
SEQ = [
    (0.0, 51.95, "login"), (51.95, 60.0, "home"), (60.0, 74.3, "services"), (74.3, 94.7, "email"),
    (94.7, 104.6, "enter"), (104.6, 108.8, "enter"), (108.8, 112.65, "otp"), (112.65, 124.6, "review"),
    (124.6, 133.6, "face"), (133.6, 138.1, "submit1"), (138.1, 148.15, "submit2"), (148.15, 1e9, "done"),
]
TAPS_AT = {"login": 51.25, "home": 59.6, "services": 73.9, "email": 94.45, "enter": 102.6, "otp": 112.4,
           "review": 121.0, "submit1": 137.4, "submit2": 144.4, "done": 159.4}
_cache = {}


def _typed(text, t0, t1, T):
    k = 0 if T < t0 else len(text) if T >= t1 else int((T - t0) / (t1 - t0) * len(text))
    return text[:k]


def _pressed(name, T):
    tt = TAPS_AT.get(name)
    return tt is not None and 0 <= T - tt < 0.35


def _key(name, T):
    if name == "login":
        return (name, len(_typed("0000 0000 0000", 48.9, 50.2, T)), _pressed(name, T))
    if name == "enter":
        return (name, len(_typed(EMAIL, 97.3, 99.0, T)), _pressed(name, T), int(T * 2) % 2)
    if name == "otp":
        return (name, len(_typed("000000", 109.0, 110.4, T)), _pressed(name, T))
    if name == "face":
        return (name, round(T * 30) if T < 129.8 else "ok", min(1.0, max(0.0, (T - 129.8) / 0.4)))
    if name == "done":
        b = min(max((T - 150.6) / 0.35, 0), 1) * (1 - min(max((T - 155.6) / 0.35, 0), 1))
        return (name, round(b, 2), _pressed(name, T), round(min(max((T - 148.4) / 0.5, 0), 1), 2))
    return (name, _pressed(name, T))


def _draw(name, T):
    img = canvas()
    status_bar(img)
    p = _pressed(name, T)
    if name == "login":
        big_title(img, "Welcome", 600, 104, sub="Log in with your Aadhaar number\nto continue")
        n = len(_typed("0000 0000 0000", 48.9, 50.2, T))
        field(img, 980, "Aadhaar number", "".join("•" if c == "0" else " " for c in "0000 0000 0000"[:n]),
              placeholder="Enter 12-digit number", focused=48.6 <= T < 51.3, caret=48.6 <= T < 51.3)
        button(img, 1200, "Login", pressed=p)
        d = ImageDraw.Draw(img)
        d.text((SW / 2, 1460), "Verify with OTP / Face", font=f(42, 600), fill=ACCENT, anchor="mm")
    elif name == "home":
        d = ImageDraw.Draw(img)
        d.text((80, 300), "Hello,", font=f(60, 600), fill=SUB, anchor="ls")
        d.text((80, 400), "Aadhaar holder", font=f(86, 800), fill=INK, anchor="ls")
        card(img, (80, 480, 1240, 900), fill=(32, 32, 36))
        d.text((140, 580), "AADHAAR", font=f(46, 800), fill=(236, 214, 170), anchor="lm")
        d.text((140, 720), "••••  ••••  ••••", font=f(76, 700), fill=(255, 255, 255), anchor="lm")
        d.text((140, 820), "Name and details hidden", font=f(40, 500), fill=(170, 170, 178), anchor="lm")
        labels = ["Download\nAadhaar", "Lock\nBiometrics", "Share\nQR code", "My\nDocuments", "Scan\nQR", "Help &\nSupport"]
        cols = [(156, 120, 60), (90, 120, 110), (120, 100, 140), (150, 110, 90), (90, 110, 140), (120, 120, 120)]
        for i, (lb, c) in enumerate(zip(labels, cols)):
            r, k = divmod(i, 3)
            x0 = 80 + k * (360 + 40)
            y0 = 980 + r * (400 + 40)
            tile(img, (x0, y0, x0 + 360, y0 + 400), lb, icon=c)
        d.rectangle([0, 2580, SW, SH], fill=(255, 255, 255))
        d.line([(0, 2580), (SW, 2580)], fill=LINE, width=3)
        for k, (lb, x) in enumerate((("Home", 220), ("Services", 660), ("Profile", 1100))):
            on = k == 0
            col = INK if on else SUB
            d.rounded_rectangle([x - 46, 2630, x + 46, 2722], radius=24, fill=(32, 32, 36) if on else (205, 205, 212))
            d.text((x, 2775), lb, font=f(44, 700 if on else 600), fill=col, anchor="mm")
    elif name == "services":
        nav(img, "Services")
        rows = [("Update Mobile Number", (90, 120, 110)), ("Email Add / Update", (156, 120, 60)), ("Update Address", (120, 100, 140)),
                ("Download Aadhaar", (150, 110, 90)), ("Lock / Unlock Biometrics", (90, 110, 140)), ("Request Status", (120, 120, 120))]
        card(img, (60, 360, 1260, 360 + 190 * len(rows) + 40))
        for i, (lb, c) in enumerate(rows):
            y = 370 + i * 190 + (20 if i > 1 else 0)
            if i == 1:
                row(img, 560, lb, sub="Free for a limited time", icon=c, h=180, hot=T > 63.0)
                d = ImageDraw.Draw(img)
                d.rounded_rectangle([925, 612, 1090, 678], radius=33, fill=(226, 244, 233))
                d.text((1007, 645), "FREE", font=f(40, 800), fill=OK, anchor="mm")
            else:
                row(img, y, lb, icon=c, h=170)
    elif name == "email":
        nav(img, "Email Add / Update")
        card(img, (80, 380, 1240, 1000))
        d = ImageDraw.Draw(img)
        d.text((140, 455), "Email ID", font=f(60, 800), fill=INK, anchor="lm")
        row(img, 530, "Add / Link email address", icon=(156, 120, 60), h=170, x0=100, x1=1220)
        d.rounded_rectangle([110, 760, 1210, 860], radius=30, fill=(252, 240, 230))
        d.ellipse([150, 788, 194, 832], fill=(214, 120, 60))
        d.text((172, 810), "!", font=f(40, 800), fill=(255, 255, 255), anchor="mm")
        d.text((226, 810), "No email linked to your Aadhaar", font=f(46, 650), fill=(140, 70, 30), anchor="lm")
        d.text((140, 930), "Link an email ID to get updates.", font=f(42, 500), fill=SUB, anchor="lm")
        button(img, 2520, "Continue to update email address", pressed=p, h=170)
    elif name == "enter":
        nav(img, "Update Email")
        typed = _typed(EMAIL, 97.3, 99.0, T)
        field(img, 520, "Email ID", typed, placeholder="Enter your email ID", focused=True, caret=int(T * 2) % 2 == 0)
        d = ImageDraw.Draw(img)
        d.text((80, 760), "An OTP will be sent to this email.", font=f(42, 500), fill=SUB, anchor="ls")
        button(img, 1640, "Send OTP", pressed=p, enabled=len(typed) == len(EMAIL))
        if T < 102.9:
            keyboard(img, "alpha", pressed=EMAIL[len(typed) - 1] if 0 < len(typed) < len(EMAIL) else None)
    elif name == "otp":
        nav(img, "Verify OTP")
        d = ImageDraw.Draw(img)
        d.text((80, 420), "Enter the 6-digit OTP sent to", font=f(46, 500), fill=SUB, anchor="ls")
        d.text((80, 486), "y•••••••@gmail.com", font=f(46, 700), fill=INK, anchor="ls")
        n = len(_typed("000000", 109.0, 110.4, T))
        otp(img, 560, "•" * n, active=min(n, 5) if n < 6 else None)
        button(img, 1640, "Continue to review", pressed=p, enabled=n == 6)
        keyboard(img, "num")
    elif name == "review":
        nav(img, "Review")
        card(img, (80, 380, 1240, 760))
        d = ImageDraw.Draw(img)
        d.text((140, 470), "New email ID", font=f(44, 600), fill=SUB, anchor="lm")
        d.text((140, 620), EMAIL, font=f(60, 800), fill=INK, anchor="lm")
        d.text((140, 860), "Verify it's you to continue.", font=f(44, 500), fill=SUB, anchor="lm")
        button(img, 2380, "Continue to face authentication", pressed=p, h=170)
        d.text((SW / 2, 2625), "Use another option", font=f(46, 700), fill=ACCENT, anchor="mm")
    elif name == "face":
        nav(img, "Face Authentication")
        done = T >= 129.8
        face_scan(img, SW / 2, 1150, T, done=done)
        d = ImageDraw.Draw(img)
        if done:
            d.rounded_rectangle([90, 1840, 1230, 1970], radius=40, fill=(226, 244, 233))
            d.text((SW / 2, 1905), "Face authenticated successfully", font=f(50, 700), fill=OK, anchor="mm")
        else:
            d.text((SW / 2, 1905), "Keep your face inside the frame", font=f(48, 600), fill=SUB, anchor="mm")
    elif name in ("submit1", "submit2"):
        nav(img, "Review" if name == "submit1" else "Submit Request")
        card(img, (80, 380, 1240, 1000))
        d = ImageDraw.Draw(img)
        d.text((140, 470), "New email ID", font=f(44, 600), fill=SUB, anchor="lm")
        d.text((140, 590), EMAIL, font=f(60, 800), fill=INK, anchor="lm")
        d.line([(140, 680), (1180, 680)], fill=LINE, width=3)
        check(img, 180, 800, 40)
        d.text((250, 800), "Face authenticated", font=f(48, 650), fill=OK, anchor="lm")
        if name == "submit2":
            d.text((140, 1120), "Please check the details before", font=f(44, 500), fill=SUB, anchor="lm")
            d.text((140, 1180), "submitting your request.", font=f(44, 500), fill=SUB, anchor="lm")
        button(img, 2520, "Continue to submit request" if name == "submit1" else "Submit request", pressed=p, h=170)
    elif name == "done":
        k = min(max((T - 148.4) / 0.5, 0), 1)
        check(img, SW / 2, 760, 150, prog=k)
        d = ImageDraw.Draw(img)
        d.text((SW / 2, 1080), "Request submitted", font=f(78, 800), fill=INK, anchor="mm")
        d.text((SW / 2, 1170), "Your email update request was sent.", font=f(44, 500), fill=SUB, anchor="mm")
        card(img, (80, 1280, 1240, 1520))
        d.text((140, 1360), "Service Request Number", font=f(42, 600), fill=SUB, anchor="lm")
        d.text((140, 1450), "•••• •••• •••• ••••", font=f(56, 700), fill=INK, anchor="lm")
        button(img, 2520, "Download acknowledgement", kind="secondary", pressed=p, h=170)
        b = min(max((T - 150.6) / 0.35, 0), 1) * (1 - min(max((T - 155.6) / 0.35, 0), 1))
        if b > 0:
            banner(img, "Aadhaar", "Your email update request has\nbeen submitted.", y=int(-320 + 380 * b))
    return to_array(img)


def render(T):
    name = next(s for a, b, s in SEQ if a <= T < b)
    key = _key(name, T)
    if key not in _cache:
        if len(_cache) > 60:
            _cache.clear()
        _cache[key] = _draw(name, T)
    return _cache[key]
