"""Edit decision list for the 'AI free video generator' episode.

Every time below is in seconds on the narration timeline (= main video timeline).  Times that depend on a spoken
word come from the forced alignment (`A.find(cue, word)`), so the graphics land exactly when the word is said.
"""
from mbedit.common import Align, DUR
import os
from mbedit.common import WORK
from mbedit.scenes import THScene, BrollScene, DemoScene, DemoTimeline, Step, Hl, ResultScene
from mbedit.overlays import (Headline, CountUp, SubscribeCTA, EngagePill, LinkBelow, Logo, TitleCard, Dim)
from mbedit.captions import build_chunks, CaptionRenderer
from mbedit.timeline import Timeline

A = Align()


def T(cue, word, nth=0, end=False):
    return A.find(cue, word, nth, end)


# ====================================================================== screen-recording demo
# narration time -> screen-recording time (T0, T1, S0, S1); S jumps cross-fade
DEMO_SEGS = [
    # --- part A: open link / sign up / google login / home
    (54.14, 57.2, 6.0, 9.0),
    (57.2, 60.2, 9.0, 11.5),
    (60.2, 65.0, 11.5, 14.8),
    (65.0, 68.8, 14.8, 19.0),            # 'sign in or join' modal at S 15.5
    (68.8, 69.6, 27.4, 28.2),            # tap Sign up at S 28.2
    (69.6, 71.9, 28.2, 30.7),            # create-account page, tap 'Sign in with Google' at S 30.7
    (71.9, 75.9, 30.7, 32.8),            # google account chooser, select at S 32.8
    (75.9, 77.0, 32.8, 35.5),
    (77.0, 80.5, 38.0, 41.5),            # logged-in home
    (80.5, 96.3, 41.5, 57.5),
    # --- part B: video generator
    (104.94, 109.3, 75.4, 79.8),         # tap 'Generate videos' at S 79.8
    (109.3, 110.3, 79.8, 81.9),
    (110.3, 112.4, 81.9, 84.0),
    (112.4, 128.6, 84.0, 84.0),          # hold: badges (Free / 100 videos per day / sign-in / commercial)
    (128.6, 133.8, 106.4, 106.4),        # hold: 'Your prompt' box
    (133.8, 137.6, 110.4, 116.8),        # tap box, paste
    (137.6, 147.9, 119.0, 119.0),        # hold: pasted prompt
    (147.94, 150.0, 126.0, 130.4),
    (150.0, 153.4, 131.0, 131.0),        # hold: photo-library menu
    (153.4, 155.0, 134.8, 137.4),        # photo picker (blurred, first tile = our photo stays sharp)
    (155.0, 156.3, 138.0, 140.0),        # image added (thumbnail mid-screen)
    (156.3, 157.0, 140.0, 142.2),        # page scrolls up
    (157.0, 194.95, 146.0, 146.0),       # hold: model / orientation / enhance / generate all on screen
    (195.2, 197.0, 195.0, 196.8),        # tap Generate at S 196.8
    (197.0, 200.0, 196.8, 199.8),
    (200.1, 209.9, 210.8, 214.9),        # queue card: '6m 30s left' is on screen from S 207 to 215.9
    (209.9, 213.2, 214.9, 223.0),        # fast-forward: scroll down to 'Your recent videos'
    (213.2, 215.0, 223.0, 226.0),        # result thumbnail appears at S 224
    (215.0, 230.7, 226.0, 232.0),        # result thumbnail
]

# privacy: blur other people's / private content shown in the recording (S = screen-recording time)
PRIVACY = [
    (30.9, 36.6, [(30, 940, 1260, 1480), (150, 2485, 800, 70)]),                 # google account chooser (emails)
    (134.9, 135.5, [(0, 300, 1320, 2568)]),                                       # photo picker sliding in
    (135.5, 137.4, [(440, 430, 880, 450), (0, 880, 1320, 1988)]),                 # photo picker: private gallery
]

# SR rectangles (x, y, w, h) in screen-recording pixels
R_URL = (270, 2612, 790, 160)
R_TITLE = (90, 480, 1180, 125)
R_SIGNUP = (1010, 203, 275, 98)
R_MODAL_TXT = (100, 1020, 1020, 200)
R_MODAL_GOOGLE = (65, 1500, 1190, 120)
R_CREATE_GOOGLE = (100, 700, 1115, 140)
R_CHOOSER_HEAD = (60, 600, 1200, 330)
R_CHOOSER_ROWS = (60, 950, 1200, 1580)
R_MEGABYTE = (60, 2395, 1200, 170)
R_BTN_IMG = (50, 1335, 565, 130)
R_BTN_VID = (730, 1335, 560, 130)
R_BTN_BOTH = (50, 1335, 1240, 130)
R_B_FREE = (515, 1470, 150, 90)
R_B_100 = (680, 1470, 450, 90)
R_B_SIGNIN = (100, 1572, 395, 92)
R_B_COMM = (505, 1572, 485, 92)
R_PROMPT_EMPTY = (160, 1830, 1000, 640)
R_PROMPT = (170, 585, 985, 520)
R_IMG_BOX = (162, 857, 995, 310)
R_PHOTO_LIB = (288, 1038, 740, 100)
R_THUMB = (162, 148, 336, 300)
R_THUMB_A = (162, 860, 336, 355)
R_PICKED = (0, 430, 440, 450)
R_UP3 = (162, 610, 998, 300)
R_BOTH_CARDS = (162, 1250, 998, 510)
R_FAST = (162, 1250, 998, 240)
R_QUALITY = (162, 1524, 998, 233)
R_FAST_TIME = (262, 1396, 520, 64)
R_QUAL_TIME = (262, 1668, 520, 64)
R_ORIENT = (160, 1790, 600, 140)
R_LAND = (160, 1855, 300, 70)
R_PORT = (500, 1855, 230, 70)
R_ENH_CARD = (162, 1957, 998, 235)
R_ENH_TOGGLE = (1000, 1985, 125, 75)
R_GENERATE = (110, 1545, 1095, 205)
R_GENERATE_B = (110, 1411, 1095, 205)        # page nudges up ~134px right after the tap
R_QUEUE_TIME = (1040, 1038, 240, 64)
R_QUEUE_CARD = (50, 1025, 1230, 190)
R_RESULT = (0, 1085, 650, 365)

DEMO_STEPS = [
    Step(54.14, 57.3, "STEP 1", "OPEN THE LINK", [
        Hl(54.3, 57.2, R_URL, "LINK FROM THE DESCRIPTION")]),
    Step(57.3, 60.15, "THE WEBSITE", "THERE'S AN AI FOR THAT", [
        Hl(57.36, 60.1, R_TITLE, "SITE NAME")]),
    Step(60.15, 64.84, "STEP 2", "TAP SIGN UP", [
        Hl(60.2, 62.9, R_TITLE, "EXACT SITE OPENS", ring=False, spot=False),
        Hl(T(18, "sign") - 0.3, 64.8, R_SIGNUP, "SIGN UP")]),
    Step(64.84, 68.8, "LOGIN NEEDED", "SIGN IN REQUIRED", [
        Hl(64.9, 66.9, R_MODAL_TXT, "FREE ACCOUNT NEEDED"),
        Hl(66.9, 68.8, R_MODAL_GOOGLE, "SIGN IN WITH GOOGLE")]),
    Step(68.8, 74.38, "STEP 3", "SIGN UP WITH GOOGLE", [
        Hl(68.8, 69.95, R_SIGNUP, "SIGN UP", tap=69.6),
        Hl(70.0, 72.1, R_CREATE_GOOGLE, "SIGN IN WITH GOOGLE", tap=71.9),
        Hl(72.15, 74.38, R_CHOOSER_HEAD, "CHOOSE AN ACCOUNT")]),
    Step(74.38, 77.3, "STEP 4", "SELECT YOUR ACCOUNT", [
        Hl(74.4, 75.3, R_CHOOSER_ROWS, "YOUR GOOGLE ACCOUNT", ring=False),
        Hl(75.3, 77.2, R_MEGABYTE, "SELECT ACCOUNT", tap=75.9)]),
    Step(77.3, 80.56, "DONE!", "LOGGED IN", [
        Hl(77.4, 78.4, (90, 330, 1180, 110), "WELCOME BACK", ring=False, spot=False),
        Hl(78.5, 80.5, R_BTN_BOTH, "NEW INTERFACE")]),
    Step(80.56, 86.2, "TWO OPTIONS", "IMAGE  /  VIDEO", [
        Hl(80.6, T(23, "Generate", 0) - 0.15, R_BTN_BOTH, "2 OPTIONS"),
        Hl(T(23, "Generate", 0) - 0.15, T(23, "Generate", 1) - 0.2, R_BTN_IMG, "GENERATE IMAGE"),
        Hl(T(23, "Generate", 1) - 0.2, 86.2, R_BTN_VID, "GENERATE VIDEOS")]),
    Step(86.2, 96.3, "TOPIC + PROMPT", "WHAT TO MAKE?", [
        Hl(86.3, 90.65, R_BTN_VID, "GENERATE VIDEOS"),
        Hl(90.7, 96.3, R_BTN_IMG, "GENERATE IMAGES")]),
    # ---------------------------------------------------------------- part B
    Step(104.94, 109.95, "STEP 5", "GENERATE VIDEOS", [
        Hl(105.0, 109.95, R_BTN_VID, "SELECT GENERATE VIDEOS", tap=109.3)]),
    Step(109.95, 112.9, "VIDEO GENERATOR", "THE INTERFACE", [
        Hl(110.0, 112.9, (95, 1462, 1040, 210), "VIDEO GENERATION", ring=False, spot=False)]),
    Step(112.9, 120.9, "FREE DAILY LIMIT", "100 VIDEOS / DAY", [
        Hl(113.0, T(29, "100") - 0.2, R_B_FREE, "FREE"),
        Hl(T(29, "100") - 0.2, 120.9, R_B_100, "100 VIDEOS PER DAY")]),
    Step(120.9, 127.3, "GOOD TO KNOW", "SIGN IN + COMMERCIAL USE", [
        Hl(120.95, T(30, "commercial") - 0.3, R_B_SIGNIN, "SIGN-IN REQUIRED"),
        Hl(T(30, "commercial") - 0.3, 127.3, R_B_COMM, "FREE COMMERCIAL USE")]),
    Step(127.3, 135.7, "STEP 6", "PASTE YOUR PROMPT", [
        Hl(128.7, 133.8, R_PROMPT_EMPTY, "YOUR PROMPT"),
        Hl(133.9, 135.7, R_PROMPT, "PASTE HERE", ring=False)]),
    Step(135.7, 142.55, "CHATGPT PROMPT", "TORTOISE vs HARE", [
        Hl(137.6, 142.55, R_PROMPT, "OUR PROMPT")]),
    Step(142.55, 147.94, "PROMPT + IMAGE", "MADE WITH CHATGPT", [
        Hl(142.6, 147.9, R_PROMPT, "PROMPT PASTED")]),
    Step(147.94, 155.0, "STEP 7", "ADD AN IMAGE", [
        Hl(T(34, "Images") - 0.4, 150.7, R_IMG_BOX, "IMAGES (OPTIONAL)"),
        Hl(150.7, 153.85, R_PHOTO_LIB, "PHOTO LIBRARY", tap=153.5),
        Hl(153.9, 155.0, R_PICKED, "SELECT YOUR PHOTO")]),
    Step(155.0, 159.2, "PICK A PHOTO", "UP TO 3 IMAGES", [
        Hl(155.1, 157.0, R_THUMB_A, "PHOTO ADDED", rect_keys=[(155.1, R_THUMB_A), (156.3, R_THUMB_A), (157.0, R_THUMB)]),
        Hl(157.1, 159.2, R_UP3, "UP TO 3 PHOTOS")]),
    Step(159.28, 168.64, "STEP 8", "FAST  or  QUALITY", [
        Hl(159.3, 164.35, R_BOTH_CARDS, "TWO OPTIONS"),
        Hl(164.4, 166.6, R_QUALITY, "QUALITY  =  NOT URGENT"),
        Hl(166.7, 168.64, R_FAST, "FAST  =  QUICKER")]),
    Step(168.64, 177.72, "TIME NEEDED", "ESTIMATED TIME", [
        Hl(168.7, 171.25, R_FAST_TIME, "FAST: TIME SHOWN HERE"),
        Hl(171.3, 174.5, R_QUAL_TIME, "QUALITY: TIME SHOWN HERE"),
        Hl(174.6, 177.7, R_BOTH_CARDS, "ONLY AN APPROXIMATION")]),
    Step(177.72, 184.54, "STEP 9", "LANDSCAPE / PORTRAIT", [
        Hl(177.75, T(40, "landscape") - 0.25, R_ORIENT, "ORIENTATION"),
        Hl(T(40, "landscape") - 0.25, 182.1, R_LAND, "LANDSCAPE"),
        Hl(182.15, 184.54, R_PORT, "PORTRAIT")]),
    Step(184.54, 190.52, "STEP 10", "ENHANCE MY PROMPT", [
        Hl(184.6, T(42, "Enhance") - 0.2, R_ENH_CARD, "ENHANCE MY PROMPT"),
        Hl(T(42, "Enhance") - 0.2, 190.5, R_ENH_TOGGLE, "ENABLE THIS BUTTON")]),
    Step(190.52, 195.2, "BETTER RESULT", "PROMPT IMPROVED", [
        Hl(190.55, 195.2, R_ENH_CARD, "PROMPT IS ENHANCED")]),
    Step(195.22, 200.1, "STEP 11", "CLICK GENERATE", [
        Hl(195.3, 200.0, R_GENERATE, "GENERATE", tap=197.0,
           rect_keys=[(195.3, R_GENERATE), (196.6, R_GENERATE), (197.0, R_GENERATE_B), (200.0, R_GENERATE_B)])]),
    Step(200.14, 204.4, "WAITING TIME", "ESTIMATED TIME", [
        Hl(200.2, 204.4, R_QUEUE_TIME, "TIME LEFT SHOWN HERE")]),
    Step(204.42, 210.05, "BE PATIENT", "6 MIN 30 SEC", [
        Hl(204.5, 210.0, R_QUEUE_TIME, "6 MIN 30 SEC ESTIMATE")]),
    Step(210.05, 215.0, "ALL DONE", "VIDEO READY", [
        Hl(210.1, 215.0, R_RESULT, "YOUR VIDEO", rect_keys=[
            (210.1, (0, 1973, 650, 365)), (211.3, (0, 1973, 650, 365)), (211.7, (0, 1919, 650, 365)), (212.0, (0, 1554, 650, 365)),
            (212.5, (0, 1554, 650, 365)), (212.8, (0, 1089, 650, 365)), (215.0, (0, 1089, 650, 365))])]),
    Step(215.0, 219.1, "DOWNLOAD", "SAVE IT TO YOUR DEVICE", [
        Hl(215.05, 219.1, R_RESULT, "DOWNLOAD OPTION")]),
    Step(219.1, 230.7, "THE RESULT", "TORTOISE vs HARE RACE", [
        Hl(219.2, 230.6, R_RESULT, "AI-GENERATED VIDEO")]),
]

DEMO = DemoTimeline(DEMO_SEGS, DEMO_STEPS, PRIVACY)

# ====================================================================== scenes
# If the AI-generated demo clip is supplied (put it at $MB_WORK/assets/result.mp4) it plays full-size from 219.1 s.
RESULT_VIDEO = os.path.join(WORK, "assets", "result.mp4")
RESULT_VIDEO = RESULT_VIDEO if os.path.exists(RESULT_VIDEO) else None
RESULT_T0 = 219.1

scenes = [
    THScene(0.0, 3.26, zoom=(1.0, 1.06), center=(0.5, 0.40)),
    BrollScene(3.26, 5.78, "99786", start=0.4, zoom=(1.0, 1.1)),
    THScene(5.78, 9.34, zoom=(1.08, 1.16), center=(0.5, 0.38)),
    BrollScene(9.34, 11.66, "41273", start=1.2, zoom=(1.0, 1.1), center=(0.6, 0.5)),
    THScene(11.66, 14.64, zoom=(1.0, 1.07), center=(0.5, 0.40)),
    BrollScene(14.64, 20.88, "1781", start=0.6, zoom=(1.0, 1.12)),
    THScene(20.88, 23.92, zoom=(1.12, 1.04), center=(0.5, 0.40)),
    THScene(23.92, 27.84, zoom=(1.0, 1.06), center=(0.5, 0.40)),
    BrollScene(27.84, 31.2, "4908", start=0.6, zoom=(1.0, 1.1)),
    THScene(31.2, 34.5, zoom=(1.1, 1.18), center=(0.5, 0.38)),
    BrollScene(34.5, 39.28, "44074", start=2.0, zoom=(1.0, 1.1)),
    THScene(39.28, 43.68, zoom=(1.0, 1.08), center=(0.5, 0.40)),
    BrollScene(43.68, 46.54, "1728", start=3.0, zoom=(1.0, 1.1)),
    THScene(46.54, 50.15, zoom=(1.05, 1.0), center=(0.5, 0.40)),
    BrollScene(50.15, 54.14, "41279", start=1.0, zoom=(1.35, 1.45), center=(0.3, 0.72)),     # swipe ends at 50.4 = the camera cut in the footage
    DemoScene(54.14, 96.22, DEMO),
    BrollScene(96.22, 101.0, "242", start=0.5, zoom=(1.0, 1.1)),
    THScene(101.0, 104.94, zoom=(1.1, 1.17), center=(0.5, 0.38)),
    DemoScene(104.94, RESULT_T0 if RESULT_VIDEO else 230.5, DEMO),
    *([ResultScene(RESULT_T0, 230.5, RESULT_VIDEO)] if RESULT_VIDEO else []),
    THScene(230.5, 234.46, zoom=(1.0, 1.08), center=(0.5, 0.40)),
    THScene(234.46, 236.34, zoom=(1.12, 1.2), center=(0.5, 0.38)),
    THScene(236.34, 241.7, zoom=(1.0, 1.05), center=(0.5, 0.40)),
    THScene(241.7, DUR + 0.5, zoom=(1.08, 1.16), center=(0.5, 0.38)),
]
_START = {round(s.t0, 2): i for i, s in enumerate(scenes)}

TRANS_BY_T0 = {
    3.26: ("zoom", 0.45), 5.78: ("push", 0.4), 9.34: ("swipe", 0.5), 11.66: ("fade", 0.3), 14.64: ("push", 0.4),
    20.88: ("fade", 0.35), 23.92: ("cut", 0), 27.84: ("swipe", 0.5), 31.2: ("fade", 0.3), 34.5: ("push", 0.4),
    39.28: ("zoom", 0.45), 43.68: ("fade", 0.3), 46.54: ("fade", 0.35), 50.15: ("swipe", 0.5), 54.14: ("zoom", 0.55),
    96.22: ("push", 0.45), 101.0: ("fade", 0.3), 104.94: ("swipe", 0.55), 230.5: ("zoom", 0.55), 219.1: ("fade", 0.35),
    234.46: ("cut", 0), 236.34: ("cut", 0), 241.7: ("cut", 0),
}
trans = {_START[round(t, 2)]: v for t, v in TRANS_BY_T0.items() if round(t, 2) in _START}

# ====================================================================== overlays
layers = [
    # hook
    Headline(0.15, 3.3, [[("AI", 1)], [("FREE", 0)], [("VIDEOS", 1)]], size=150, y=170,
             delays=[T(1, "AI"), T(1, "free"), T(1, "videokal")]),
    Headline(3.3, 5.85, [[("NEW", 0), ("AI", 1)], [("WEBSITE", 1)]], size=150, anchor="center", y=300, shade=0,
             delays=[3.38, 3.75, T(2, "website")]),
    Headline(6.2, 8.9, [[("USEFUL", 1)], [("VIDEOS", 0)]], size=150, y=200,
             delays=[T(3, "useful"), T(3, "videokal")]),
    SubscribeCTA(T(3, "subscribe") - 1.25, T(3, "subscribe") + 1.9, cx=1470, cy=330, scale=0.92),
    Headline(9.7, 11.7, [[("MANY", 0), ("MORE", 1)], [("VIDEOS", 0)]], size=150, anchor="center", y=290, shade=0,
             delays=[10.0, 10.2, 10.36]),
    SubscribeCTA(T(5, "subscribe") - 1.25, T(5, "subscribe") + 1.9, cx=430, cy=330, scale=0.95),
    Headline(15.2, 20.9, [[("DIFFERENT", 1)], [("FROM OTHER", 0)], [("PLATFORMS", 1)]], size=130, anchor="center", y=230, shade=0,
             delays=[15.2, 16.7, 17.12]),
    CountUp(25.45, 28.0, 100, size=300, x=400, y=395),
    Headline(25.9, 28.0, [[("VIDEOS", 0), ("PER LOGIN", 1)]], size=78, y=600, shade=0, delays=[26.28, 26.6]),
    Headline(28.1, 31.3, [[("MANY", 0), ("ACCOUNTS", 1)], [("MANY", 0), ("VIDEOS", 1)]], size=130, anchor="center", y=250, shade=0,
             delays=[28.1, T(9, "accountukal"), 29.5, T(9, "niravadhi", 1)]),
    Headline(33.2, 34.6, [[("HIGH", 0)], [("QUALITY", 1)]], size=150, y=190, delays=[T(9, "high"), T(9, "qualityil")]),
    Headline(35.2, 39.3, [[("GOOGLE", 1), ("FLOW", 1)], [("& OTHER SITES", 0)]], size=130, anchor="center", y=270, shade=0,
             delays=[T(10, "google"), T(10, "flow"), T(10, "websitilokke") - 0.4]),
    Headline(39.4, 43.7, [[("SAME", 0)], [("QUALITY", 1)], [("OR", 0), ("BETTER", 1)]], size=118, y=170,
             delays=[39.4, T(11, "qualityil"), T(11, "athinekkal"), T(11, "mikachathu")]),
    Headline(44.7, 46.6, [[("HOW", 0), ("TO USE", 1)], [("IT?", 1)]], size=150, anchor="center", y=250, shade=0,
             delays=[44.8, 45.1, 45.7]),
    # welcome / logo reveal
    Dim(46.4, 49.5, 0.5),
    TitleCard(46.75, 49.5, "WELCOME TO", "MEGA BYTE", y=755),
    # link in description
    Headline(51.0, 54.15, [[("LINK IN", 0)], [("DESCRIPTION", 1)]], size=130, anchor="center", y=170, shade=0,
             delays=[T(15, "link"), T(15, "descriptionil")]),
    LinkBelow(52.0, 54.15, cx=960, cy=650, scale=0.9),
    # ai helpers
    Headline(98.2, 101.1, [[("GEMINI", 1)], [("CHATGPT", 1)]], size=150, anchor="center", y=240, shade=0,
             delays=[T(26, "Gemini"), T(26, "ChatGPT")]),
    Headline(102.4, 105.0, [[("PROMPT", 0)], [("+ IMAGE", 1)]], size=130, anchor="right", x=1830, y=200,
             delays=[T(26, "promptukalum"), T(26, "imageukalum")]),
    # outro
    Headline(232.2, 234.5, [[("USEFUL", 1)], [("VIDEO!", 0)]], size=150, y=200,
             delays=[T(51, "useful"), T(51, "video")]),
    EngagePill("share", T(52, "share") - 0.15, 237.5, cx=470, cy=330, scale=1.15),
    EngagePill("share", T(53, "Shareum"), 241.7, cx=470, cy=250, scale=1.0),
    EngagePill("comment", T(53, "commentum"), 241.7, cx=470, cy=440, scale=1.0),
    EngagePill("like", T(53, "likeum"), 241.7, cx=470, cy=630, scale=1.0),
    SubscribeCTA(T(54, "subscribe") - 1.25, 248.4, cx=1470, cy=360, scale=0.95),
    Headline(246.2, 248.4, [[("THANK", 0)], [("YOU!", 1)]], size=140, y=200, delays=[T(54, "Nanni"), T(54, "Namaskaram")]),
]

logo = Logo(reveal=(46.4, 49.1))


def _zone_at(t):
    for s in scenes:
        if isinstance(s, DemoScene) and s.t0 <= t < s.t1:
            return "left"
    return "full"


chunks = build_chunks(A, _zone_at)
captions = CaptionRenderer(chunks)


def build():
    return Timeline(scenes, trans, layers, captions, logo)
