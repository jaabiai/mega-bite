"""Reel plan: "Voice Isolation" as one continuous 9:16 reel.

Source range (main video): 114.8333 s .. 170.600 s, cut in silence on both sides (checked on the 10 ms RMS profile),
then a 1.73 s end-card tail.  Reel time  t' = main time - OFF.  Everything inside the range is one unbroken take of
the narration - only pictures change (speaker / B-roll / iPhone demo), the voice never jumps.
"""
OFF = 3445 / 30            # 114.8333 s
END_MAIN = 5118 / 30       # 170.6 s
TAIL = 52 / 30
DUR = (END_MAIN - OFF) + TAIL          # 57.5 s
FPS = 30
N_FRAMES = 1725


def r(t_main):
    """main-timeline seconds -> reel seconds"""
    return round(t_main - OFF, 3)


# B-roll cutaways (times are MAIN-timeline seconds). chain=True: the next shot fades in over this one.
CUTS = [
    dict(id=309,   t0=117.45, t1=119.67, src_in=5.2, cx=0.43, zoom=(1.02, 1.14), chain=True,  note="call comes in"),
    dict(id=4401,  t0=119.67, t1=122.88, src_in=3.2, cx=0.50, zoom=(1.00, 1.12), chain=True,  note="surrounding noise"),
    dict(id=39790, t0=122.88, t1=129.05, src_in=0.8, cx=0.30, zoom=(1.00, 1.12), chain=False, note="afraid they hear the place"),
    dict(id=4269,  t0=154.90, t1=158.55, src_in=0.8, cx=0.50, zoom=(1.00, 1.10), chain=True,  note="crowd"),
    dict(id=4332,  t0=158.55, t1=162.20, src_in=0.8, cx=0.60, zoom=(1.00, 1.10), chain=True,  note="rainy Times Square at night"),
    dict(id=39791, t0=162.20, t1=165.75, src_in=2.0, cx=0.50, zoom=(1.00, 1.08), chain=False, portrait=True, note="clear call"),
]
XFADE = 0.22
CHAIN_PAD = 0.26

# iPhone demo scene (S2 data from scenes.py is reused; only the camera / viewport differ)
DEMO = (131.60, 154.70)
