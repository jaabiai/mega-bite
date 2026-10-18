"""B-roll cutaway plan (main-timeline seconds).

All clips are from Mixkit's free stock library ("Mixkit Stock Video Free License": commercial use incl. monetised
YouTube allowed, no attribution required). Each clip's page URL is listed in LICENSES.md.
The speaker's voice keeps playing underneath; short gaps between cutaways bring the speaker back on screen.
"""

CUTAWAYS = [
    # intro: "iPhone upayogikkunna oro aalukalkkum ..."
    dict(id=41165, t0=6.60, t1=9.90, src_in=4.0, zoom=(1.00, 1.10), note="man on his phone"),
    # "ariyathavarkku vendi avarilekku ethikkuka"
    dict(id=4837, t0=15.95, t1=19.30, src_in=1.5, zoom=(1.00, 1.09), note="street, using a phone"),
    # S1 demo: "phone oru alarm reethiyil ningalkku buzzer cheyyum"
    dict(id=28902, t0=79.90, t1=81.95, src_in=1.0, zoom=(1.00, 1.06), portrait=True, note="alarm clock"),
    # noise story
    dict(id=309, t0=115.00, t1=118.30, src_in=5.0, zoom=(1.02, 1.10), note="phone call outdoors"),
    dict(id=4401, t0=119.70, t1=122.80, src_in=3.0, zoom=(1.00, 1.08), note="busy crossing"),
    dict(id=39790, t0=123.90, t1=129.00, src_in=1.0, zoom=(1.00, 1.08), note="worried on a call"),
    # crowd / isolated voice
    dict(id=4269, t0=154.90, t1=158.20, src_in=0.8, zoom=(1.00, 1.10), note="concert crowd"),
    dict(id=4390, t0=159.40, t1=162.20, src_in=0.8, zoom=(1.00, 1.07), note="busy station"),
    dict(id=39791, t0=162.20, t1=165.70, src_in=2.0, zoom=(1.00, 1.06), portrait=True, note="clear call"),
    # outro: "videokal ... upload cheyyunnathaayirikkum"
    dict(id=242, t0=241.30, t1=245.10, src_in=1.0, zoom=(1.00, 1.08), note="typing on a laptop"),
]
