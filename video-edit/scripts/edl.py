"""Edit decision list for the "Invisible Messages" iPhone tip.

All times are seconds on the MAIN video timeline (= final timeline; the end card
extends the video after the last spoken word).  They are tied to the real speech
(captions/words.json), not to the delivered SRT timing.

Screen-recording coordinates (zoom / hl) are in the recording's own pixel space
(1320 x 2868).  `src` maps output time to recording time:
    [n0, n1, s0, s1]   n0..n1 = output seconds, s0..s1 = recording seconds
    (s0 == s1 holds a single frame)
"""

# ---- UI rectangles in recording pixels (x, y, w, h, radius) ---------------------------
R_MSG_ICON = (405, 1575, 220, 220, 52)
R_HEADER = (470, 170, 380, 320, 70)
R_BUBBLES = (50, 1690, 1230, 830, 70)         # received + sent bubble (thread view)
R_FIELD = (205, 1548, 1075, 262, 110)
R_SEND = (1110, 1636, 140, 140, 70)           # send arrow while typing
R_MENU_PILL = (1100, 940, 170, 660, 85)       # the 4 effect dots
R_SLAM = (140, 940, 960, 250, 70)
R_LOUD = (140, 1115, 960, 255, 70)
R_GENTLE = (120, 1275, 990, 255, 70)
R_INK = (140, 1470, 960, 255, 70)
R_ARROW_INK = (1113, 1463, 140, 120, 60)
R_SENT = (300, 1255, 990, 290, 70)
R_PAIR = (40, 1000, 1240, 520, 70)            # received + sent bubble after the reveal

CENTER = dict(fx=660, fy=1434)


def spot_ring(rect, t0, t1, spot=True):
    x, y, w, h, r = rect
    out = [{"type": "ring", "x": x, "y": y, "w": w, "h": h, "r": r, "t0": t0, "t1": t1}]
    if spot:
        out.insert(0, {"type": "spot", "x": x, "y": y, "w": w, "h": h, "r": r, "t0": t0, "t1": t1})
    return out


EFFECTS = ["Slam", "Loud", "Gentle", "Invisible Ink"]


def eff_title(i, sub):
    return {"kicker": f"Bubble effect {i + 1} of 4", "lines": [EFFECTS[i].upper().replace(" ", " ")],
            "size": 130, "chips": EFFECTS, "active": i, "sub": sub, "y": 330}


EDL = {
    "main_duration": 113.0,
    # owner chose "no end card"; set to {"start": 112.6, "length": 5.6, "lines": [...]} to add one (engine supports it)
    "end_card": None,

    # ---------------------------------------------------------------- base (picture under the overlay)
    # talk = presenter (graded, optional punch-in), broll = free Mixkit stock footage
    "base": [
        {"start": 0.0, "end": 3.6, "kind": "talk", "zoom": 1.18, "cx": .445, "cy": .50, "push": .035},
        {"start": 3.6, "end": 6.3, "kind": "broll", "clip": "4915", "ss": 3.0, "push": .05},
        {"start": 6.3, "end": 10.7, "kind": "talk", "zoom": 1.12, "cx": .52, "cy": .50, "push": .03},
        {"start": 10.7, "end": 22.5, "kind": "talk", "zoom": 1.0, "cx": .5, "cy": .5, "push": 0},
        {"start": 22.5, "end": 25.4, "kind": "broll", "clip": "39780", "ss": 7.0, "push": .04},
        {"start": 25.4, "end": 30.4, "kind": "talk", "zoom": 1.0, "cx": .5, "cy": .5, "push": 0},
        {"start": 30.4, "end": 33.5, "kind": "talk", "zoom": 1.12, "cx": .445, "cy": .5, "push": .03},
        {"start": 33.5, "end": 51.7, "kind": "talk", "zoom": 1.0, "cx": .5, "cy": .5, "push": 0},
        {"start": 51.7, "end": 57.4, "kind": "talk", "zoom": 1.14, "cx": .445, "cy": .5, "push": .03},
        {"start": 57.4, "end": 90.8, "kind": "talk", "zoom": 1.0, "cx": .5, "cy": .5, "push": 0},
        {"start": 90.8, "end": 92.7, "kind": "broll", "clip": "39773", "ss": 4.0, "push": .04},
        {"start": 92.7, "end": 100.8, "kind": "talk", "zoom": 1.0, "cx": .5, "cy": .5, "push": 0},
        {"start": 100.8, "end": 104.6, "kind": "talk", "zoom": 1.16, "cx": .47, "cy": .5, "push": .035},
        {"start": 104.6, "end": 109.9, "kind": "broll", "clip": "4857", "ss": 3.0, "push": .04},
        {"start": 109.9, "end": 113.0, "kind": "talk", "zoom": 1.1, "cx": .52, "cy": .5, "push": .02},
    ],

    # titles that sit on top of presenter / B-roll shots (left column, dark scrim)
    "titles": [
        {"start": .35, "end": 3.5, "kicker": "iPhone tip", "lines": ["*INVISIBLE*", "MESSAGES"], "size": 116, "y": 340, "scrim": True},
        {"start": 22.95, "end": 25.3, "kicker": "On their phone", "lines": ["MESSAGE", "*RECEIVED*"], "size": 104, "y": 340, "scrim": True},
        {"start": 30.85, "end": 33.4, "kicker": "Quick note", "lines": ["SIMPLE &", "*HANDY*"], "size": 116, "y": 340, "scrim": True},
        {"start": 52.1, "end": 57.3, "kicker": "Coming up", "lines": ["4 BUBBLE", "*EFFECTS*"], "size": 116, "y": 300, "scrim": True,
         "chips": EFFECTS, "chipStagger": [52.3, 52.7, 53.1, 53.5], "active": 3, "activeFrom": 54.4},
        {"start": 91.25, "end": 92.6, "kicker": "Sent", "lines": ["DELIVERED", "*HIDDEN*"], "size": 100, "y": 340, "scrim": True},
        {"start": 101.3, "end": 102.45, "kicker": "That's it", "lines": ["NEAT", "*TRICK!*"], "size": 120, "y": 340, "scrim": True},
        {"start": 104.7, "end": 109.8, "kicker": "Share it", "lines": ["SHARE WITH", "*FRIENDS*"], "size": 104, "y": 340, "scrim": True},
    ],

    # ---------------------------------------------------------------- phone scenes
    "blocks": [
        {"id": "B1", "start": 12.6, "end": 22.5, "subs": [
            {"id": "A", "n0": 12.8, "n1": 16.2,
             "src": [[12.8, 15.0, 5.5, 5.5], [15.0, 16.2, 6.3, 6.75]],
             "title": {"kicker": "Step 1", "lines": ["OPEN", "*MESSAGES*"], "size": 124, "sub": "Find the green icon on your home screen"},
             "zoom": [dict(t=12.8, z=1, **CENTER), dict(t=13.9, z=2.0, fx=520, fy=1640)],
             "hl": spot_ring(R_MSG_ICON, 13.4, 16.2)},
            {"id": "B1a", "n0": 16.2, "n1": 19.2, "src": [[16.2, 19.2, 9.0, 12.0]],
             "title": {"kicker": "Step 2", "lines": ["PICK A", "*CONTACT*"], "size": 124, "sub": "Open the chat with the person you want to message"},
             "zoom": [dict(t=16.2, z=1.5, fx=660, fy=420), dict(t=18.4, z=1.5, fx=660, fy=520)],
             "hl": spot_ring(R_HEADER, 16.7, 19.2)},
            {"id": "B1b", "n0": 19.2, "n1": 22.4, "src": [[19.2, 22.4, 12.0, 15.2]],
             "title": {"kicker": "Invisible ink", "lines": ["SEND IT", "*HIDDEN*"], "size": 124, "sub": "Messages arrive covered by a scratch layer"},
             "zoom": [dict(t=19.2, z=1.0, **CENTER), dict(t=20.2, z=1.25, fx=660, fy=2050)],
             "hl": spot_ring(R_BUBBLES, 19.9, 22.4)},
        ]},
        {"id": "B2", "start": 25.3, "end": 30.4, "subs": [
            {"id": "C", "n0": 25.4, "n1": 30.3, "src": [[25.4, 30.3, 19.4, 24.3]],
             "title": {"kicker": "On their phone", "lines": ["SCRATCH", "TO *READ*"], "size": 124, "sub": "Swipe over the bubble to reveal the text"},
             "zoom": [dict(t=25.4, z=1.2, fx=660, fy=2050)],
             "hl": spot_ring(R_BUBBLES, 25.9, 30.3)},
        ]},
        {"id": "B3", "start": 33.4, "end": 51.7, "subs": [
            {"id": "T", "n0": 33.5, "n1": 42.4, "src": [[33.5, 42.4, 36.2, 45.1]],
             "title": {"kicker": "Step 3", "lines": ["TYPE YOUR", "*MESSAGE*"], "size": 120, "sub": "Write it like any normal iMessage"},
             "zoom": [dict(t=33.5, z=1.0, **CENTER), dict(t=34.6, z=1.25, fx=720, fy=1700)],
             "hl": spot_ring(R_FIELD, 35.2, 42.4)},
            {"id": "D", "n0": 42.5, "n1": 48.5, "src": [[42.5, 48.5, 44.2, 47.9]],
             "title": {"kicker": "Step 4", "lines": ["LONG-PRESS", "*SEND*"], "size": 120, "sub": "Hold the blue arrow instead of tapping"},
             "zoom": [dict(t=42.5, z=1.25, fx=720, fy=1700)],
             "hl": [{"type": "ring", "x": 1108, "y": 1634, "w": 144, "h": 144, "r": 72, "t0": 43.3, "t1": 48.5},
                    {"type": "tap", "x": 1180, "y": 1706, "t0": 45.0, "t1": 48.5}]},
            {"id": "E", "n0": 48.5, "n1": 51.7, "src": [[48.5, 51.7, 47.9, 51.1]],
             "title": {"kicker": "Step 5", "lines": ["PICK AN", "*EFFECT*"], "size": 120, "sub": "Four bubble effects appear on the right"},
             "zoom": [dict(t=48.5, z=1.0, **CENTER), dict(t=49.4, z=1.35, fx=880, fy=1280)],
             "hl": spot_ring(R_MENU_PILL, 49.4, 51.7)},
        ]},
        {"id": "B4", "start": 57.4, "end": 90.8, "subs": [
            {"id": "F", "n0": 57.5, "n1": 64.7, "src": [[57.5, 64.7, 60.6, 67.8]],
             "title": eff_title(0, "The message slams onto the screen"),
             "zoom": [dict(t=57.5, z=1.0, **CENTER), dict(t=58.5, z=1.2, fx=690, fy=1150)],
             "hl": spot_ring(R_SLAM, 58.6, 64.7)},
            {"id": "G", "n0": 64.7, "n1": 71.5, "src": [[64.7, 71.5, 67.9, 74.7]],
             "title": eff_title(1, "A loud, animated notification effect"),
             "zoom": [dict(t=64.7, z=1.2, fx=690, fy=1250)],
             "hl": spot_ring(R_LOUD, 65.6, 71.5)},
            {"id": "H", "n0": 71.5, "n1": 77.4, "src": [[71.5, 77.4, 77.2, 83.1]],
             "title": eff_title(2, "A soft, subtle visual effect"),
             "zoom": [dict(t=71.5, z=1.2, fx=690, fy=1380)],
             "hl": spot_ring(R_GENTLE, 72.4, 77.4)},
            {"id": "I", "n0": 77.4, "n1": 84.0, "src": [[77.4, 84.0, 84.7, 91.3]],
             "title": eff_title(3, "The message stays hidden until scratched"),
             "zoom": [dict(t=77.4, z=1.2, fx=690, fy=1520)],
             "hl": spot_ring(R_INK, 78.4, 84.0)},
            {"id": "J", "n0": 84.0, "n1": 90.8, "src": [[84.0, 90.8, 93.5, 100.3]],
             "title": {"kicker": "Step 6", "lines": ["TAP", "*SEND*"], "size": 130, "sub": "Choose Invisible Ink, then tap the arrow"},
             "zoom": [dict(t=84.0, z=1.2, fx=690, fy=1520)],
             "hl": spot_ring(R_INK, 84.6, 88.8) + [
                 {"type": "ring", "x": 1113, "y": 1463, "w": 140, "h": 120, "r": 60, "t0": 88.4, "t1": 90.8},
                 {"type": "tap", "x": 1183, "y": 1523, "t0": 89.4, "t1": 90.8}]},
        ]},
        {"id": "B5", "start": 92.6, "end": 100.8, "subs": [
            {"id": "K", "n0": 92.7, "n1": 95.7, "src": [[92.7, 95.7, 101.0, 104.0]],
             "title": {"kicker": "Sent", "lines": ["SENT", "*HIDDEN*"], "size": 130, "sub": "Only the sparkle layer is visible"},
             "zoom": [dict(t=92.7, z=1.0, **CENTER), dict(t=93.8, z=1.25, fx=660, fy=1400)],
             "hl": spot_ring(R_SENT, 94.2, 95.7)},
            {"id": "L", "n0": 95.7, "n1": 100.8, "src": [[95.7, 100.8, 108.2, 113.3]],
             "title": {"kicker": "On their phone", "lines": ["SCRATCH", "TO *READ*"], "size": 124, "sub": "The text appears only where they swipe"},
             "zoom": [dict(t=95.7, z=1.2, fx=660, fy=1260)],
             "hl": spot_ring(R_PAIR, 96.2, 100.8)},
        ]},
    ],

    # ---------------------------------------------------------------- calls to action
    # "word": the caption chunk (after `after`) at which the click should land
    "cta": [
        {"type": "subscribe", "word": "subscribe", "after": 6.0, "clickAt": 1.55, "len": 4.4, "y": 735},
        {"type": "subscribe", "word": "Follow", "after": 100.0, "clickAt": .95, "len": 2.5, "y": 735},
        {"type": "icons", "start": 104.7, "end": 109.8, "y": 735, "items": ["share", "link"], "hitAt": 1.2},
    ],
    "toasts": [
        {"start": 37.0, "end": 40.6, "title": "MEGA BITE", "body": "New iPhone tip every week - hit Subscribe"},
        {"start": 79.8, "end": 83.4, "title": "MEGA BITE", "body": "Enjoying this? Like, share & subscribe"},
    ],
}


# ---------------------------------------------------------------- Reel (9:16) framing of the presenter shots
# keys = start time of a base shot; values override zoom / cx / cy / push for the vertical crop
# (the face sits at x ~ 0.58 of the 16:9 frame, so the 9:16 window is centred there)
V_FRAMING = {
    0.0: dict(zoom=1.0, cx=.58, cy=.46, push=.03),
    6.3: dict(zoom=1.12, cx=.58, cy=.44, push=.03),
    10.7: dict(zoom=1.0, cx=.58, cy=.46, push=0),
    25.4: dict(zoom=1.0, cx=.58, cy=.46, push=0),
    30.4: dict(zoom=1.08, cx=.58, cy=.45, push=.03),
    33.5: dict(zoom=1.0, cx=.58, cy=.46, push=0),
    51.7: dict(zoom=1.04, cx=.58, cy=.46, push=.03),
    57.4: dict(zoom=1.0, cx=.58, cy=.46, push=0),
    92.7: dict(zoom=1.0, cx=.58, cy=.46, push=0),
    100.8: dict(zoom=1.14, cx=.57, cy=.44, push=.03),
    109.9: dict(zoom=1.08, cx=.58, cy=.45, push=.02),
}


def base_shots(layout="wide"):
    """Base shot list for a layout ("wide" 16:9 or "vertical" 9:16)."""
    shots = [dict(s) for s in EDL["base"]]
    if layout == "vertical":
        for s in shots:
            if s["kind"] == "talk":
                s.update(V_FRAMING[s["start"]])
    return shots
