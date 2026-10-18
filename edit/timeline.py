"""Builds edit/data/timeline.json: caption pages (word-level highlight times) + every on-screen graphic event.

All times are seconds on the MAIN timeline and come from the forced-aligned narration words
(edit/data/words_aligned.json), so each graphic lands on the word that triggers it.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(f"{HERE}/data/words_aligned.json"))["words"]
DURATION = 263.0333


def word(cue, prefix, nth=0, end=False):
    """time of the nth word in `cue` whose text starts with `prefix` (case-insensitive)"""
    hits = [w for w in WORDS if w["cue"] == cue and w["text"].lower().lstrip("'\"").startswith(prefix.lower())]
    w = hits[nth]
    return round(w["end"] if end else w["start"], 2)


def cue_span(cue):
    ws = [w for w in WORDS if w["cue"] == cue]
    return round(ws[0]["start"], 2), round(ws[-1]["end"], 2)


# ------------------------------------------------------------------------------------- captions
SENT_END = (".", "?", "!", "...", "…")


def split_sentence(ws, max_chars=54, max_words=8):
    """balanced split of one sentence into caption pages (prefers breaking after commas / at pauses)"""
    total = sum(len(w["text"]) + 1 for w in ws) - 1
    k = max(1, -(-total // max_chars), -(-len(ws) // max_words))
    if k == 1:
        return [ws]
    # candidate break scores: after comma/semicolon, long pause
    cum, c = [], 0
    for w in ws:
        c += len(w["text"]) + 1
        cum.append(c)
    pages, start = [], 0
    for i in range(1, k):
        target = total * i / k
        best, best_cost = None, 1e9
        for j in range(start, len(ws) - (k - i)):
            gap = ws[j + 1]["start"] - ws[j]["end"] if j + 1 < len(ws) else 0
            cost = abs(cum[j] - target)
            if ws[j]["text"].endswith((",", ";", ":")):
                cost -= 9
            cost -= min(gap, 0.8) * 10
            if cost < best_cost:
                best, best_cost = j, cost
        pages.append(ws[start:best + 1])
        start = best + 1
    pages.append(ws[start:])
    return pages


def caption_pages():
    sents, cur = [], []
    for w in WORDS:
        cur.append(w)
        if w["text"].endswith(SENT_END):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    merged = []
    for s_ in sents:
        merged.extend(split_sentence(s_))
    out = []
    for i, p in enumerate(merged):
        t0 = p[0]["start"] - 0.10
        nxt = merged[i + 1][0]["start"] - 0.10 if i + 1 < len(merged) else DURATION
        t1 = min(nxt, p[-1]["end"] + 0.45)
        out.append({
            "t0": round(max(t0, 0), 3), "t1": round(t1, 3),
            "words": [{"t": w["text"], "a": round(w["start"], 3), "b": round(w["end"], 3)} for w in p],
        })
    return out


# ------------------------------------------------------------------------------------- events
def build():
    ev = []

    def add(type_, t0, t1, **kw):
        ev.append(dict(type=type_, t0=round(t0, 2), t1=round(t1, 2), **kw))

    # ---------------- intro (talking head)
    add("hero", 0.25, 4.40, kicker="iOS 27  •  MUST WATCH", lines=["3 KIDILAN", "iPHONE", "FEATURES"], grad=2)
    add("hero", 4.45, 6.50, kicker="VIDEO", lines=["SKIP", "CHEYYATHE", "KAANUKA"], grad=2)
    add("badge", word(4, "iOS"), word(4, "feature-ukalaanu", end=True) + 0.2, text="iOS 27", sub="NEW FEATURES")
    add("cta_share", word(6, "ellavarilekkum"), cue_span(6)[1] + 0.5, at=word(6, "share"))
    add("stinger", word(8, "Welcome") - 0.15, 29.0,
        words=[["WELCOME", word(8, "Welcome")], ["TO", word(8, "to")], ["MEGA", word(8, "Mega")], ["BYTE.", word(8, "Byte")]])

    # ---------------- feature 1 : screen demo (S1)
    s1 = (29.60, 108.70)
    add("scene", *s1, name="S1", num="01", l1="MISS CALL", l2="REMINDER", kicker="FEATURE", show_card_from=33.2,
        pre_label="SCREEN DEMO")
    k = [
        (36.8, 41.7, "MISS CALL?", "call back cheyyanam"),
        (43.6, 46.4, "MISSED CALL", "ee contact-inu"),
        (46.5, 50.45, "SET A REMINDER", "free time-il thirichu vilikkan"),
        (53.8, 56.0, "SWIPE LEFT", "idathuvashaththekk swipe"),
        (56.45, 58.6, "CLOCK ICON", "icon select cheyyuka"),
        (59.4, 64.2, "PICK A TIME", "1 hour • tonight • tomorrow"),
        (66.5, 69.7, "REMIND ME LATER…", "custom date & time"),
        (70.8, 75.2, "DATE & TIME", "samayam set cheyyam"),
        (75.3, 83.0, "URGENT = ALARM", "phone alarm pole buzz cheyyum"),
        (83.9, 86.2, "REPEAT", "oronnoronnayi set cheyyam"),
        (86.5, 89.5, "ADD TO LIST", "puthiya list add cheyyam"),
        (90.2, 94.3, "TAP ✓ TO SAVE", "notification labhikkum"),
        (95.4, 99.8, "SWIPE AGAIN", "athe contact-inu nere"),
        (100.9, 102.0, "CLOCK ICON", "veendum select cheyyuka"),
        (104.0, 105.9, "EDIT", "reminder edit cheyyam"),
        (105.9, 108.6, "MARK AS COMPLETED", "complete aayittundu ennu mark cheyyam"),
    ]
    for a, b, big, sub in k:
        add("kp", a, b, text=big, sub=sub, scene="S1")
    add("steps", *s1, scene="S1", items=[
        ["Swipe left on the missed call", 53.6],
        ["Tap the clock icon", 56.2],
        ["Choose a reminder time", 59.2],
        ["Remind Me Later…", 66.4],
        ["Set date & time", 70.6],
        ["Urgent → phone alarm", 75.2],
        ["Repeat, List & ✓ Save", 83.8],
        ["Edit / Mark as Completed", 95.3],
    ])
    add("cta_like", word(29, "Ishttappettittundenkil"), 112.3, at=word(29, "like"))

    # ---------------- feature 2 intro + noise story (talking head + b-roll)
    add("hero", 112.7, 115.0, kicker="FEATURE 02", lines=["VOICE", "ISOLATION"], grad=1)
    add("kp", 120.0, 123.0, text="SURROUNDING NOISE", sub="call-il shallyam", scene=None, pos="hero")
    add("kp", 123.4, 129.0, text="BACKGROUND SOUND", sub="avar kettu ennulla pedi", scene=None, pos="hero")
    add("kp", 129.6, 131.5, text="THE SOLUTION", sub="valare simple", scene=None, pos="hero")

    # ---------------- feature 2 : screen demo (S2)
    s2 = (131.60, 154.70)
    add("scene", *s2, name="S2", num="02", l1="VOICE", l2="ISOLATION", kicker="FEATURE", show_card_from=131.6)
    for a, b, big, sub in [
        (131.7, 133.4, "OPEN SETTINGS", "Settings-ilekku povuka"),
        (134.5, 136.4, "ACCESSIBILITY", "option select cheyyuka"),
        (140.2, 143.9, "AUDIO & VISUAL", "thaazhekk scroll cheyyuka"),
        (147.7, 152.0, "VOICE ISOLATION", "'Add Voice Isolation'"),
        (152.2, 154.7, "TURN IT ON ✓", "button enable cheyyuka"),
    ]:
        add("kp", a, b, text=big, sub=sub, scene="S2")
    add("steps", *s2, scene="S2", items=[
        ["Open Settings", 131.6],
        ["Accessibility", 134.5],
        ["Audio & Visual", 136.8],
        ["Add Voice Isolation", 144.6],
        ["Turn it ON ✓", 152.0],
    ])

    # ---------------- crowd / isolated voice (talking head + b-roll)
    add("kp", 153.9, 158.6, text="NOISY CROWD?", sub="program-ilum matte sthalangalilum", scene=None, pos="hero")
    add("kp", 161.0, 165.7, text="ONLY YOUR VOICE", sub="ningal parayunna shabdam mathram", scene=None, pos="hero", size=54)

    # ---------------- feature 3 : hold assist (talking head -> physical shots)
    add("hero", 165.9, 172.9, kicker="FEATURE 03", lines=["HOLD", "ASSIST"], grad=1)
    for a, b, big, sub in [
        (175.4, 180.9, "CALL ON HOLD", "unhold cheyyunnathu vare kaathirikkendathilla"),
        (185.9, 189.5, "UNHOLD ALERT", "notification labhikkum"),
        (205.9, 207.0, "HOLD", ""),
        (214.7, 216.6, "TAP  MORE", ""),
        (217.1, 220.2, "HOLD ASSIST", "option select cheyyuka"),
        (221.9, 223.6, "ASSIST ON", ""),
        (227.4, 229.6, "RINGS ON UNHOLD", ""),
        (231.9, 234.5, "ACCEPT & TALK", "ring cheyyum • accept cheythu samsaarikkam"),
    ]:
        add("chip", a, b, text=big, sub=sub)

    # ---------------- outro
    add("recap", word(61, "moonnu"), 241.0, items=[
        ["01", "MISS CALL REMINDER", word(61, "moonnu")],
        ["02", "VOICE ISOLATION", word(61, "valare")],
        ["03", "HOLD ASSIST", word(61, "athiloru")],
    ])
    add("kp", 241.2, 245.2, text="NEW VIDEOS", sub="nirantharam channel-iloode", scene=None, pos="hero")
    add("cta_sub", word(63, "Athukondu"), 248.2, at=word(63, "subscribe"))
    add("cta_trio", word(64, "Video"), 252.6, at=[word(64, "like-um"), word(64, "comment-um"), word(64, "share-um")])
    add("kp", 256.6, 259.0, text="NEXT TOPIC", sub="puthiya topic-umayittu veendum", scene=None, pos="hero")
    add("cta_sub", word(67, "Athuvarekkum"), DURATION, at=word(67, "subscribe"), end=True)
    add("thanks", word(67, "Nanni"), DURATION, text="NANNI • NAMASKARAM")

    # screen-scene key phrases stay up until the next one begins (no empty panel at the moment of a tap)
    for sc in ("S1", "S2"):
        ks = sorted([e for e in ev if e["type"] == "kp" and e.get("scene") == sc], key=lambda e: e["t0"])
        for a, b in zip(ks, ks[1:]):
            if b["t0"] - a["t1"] <= 1.7:
                a["t1"] = round(b["t0"] - 0.02, 2)
    return ev


def main():
    tl = {"duration": DURATION, "captions": caption_pages(), "events": build(),
          "logo_hero": {"t0": 25.15, "t1": 29.0}}
    out = f"{HERE}/data/timeline.json"
    json.dump(tl, open(out, "w"), ensure_ascii=False, indent=1)
    print("wrote", out, len(tl["captions"]), "caption pages,", len(tl["events"]), "events")
    for p in tl["captions"][:12]:
        print(f"  {p['t0']:7.2f}-{p['t1']:7.2f}  {' '.join(w['t'] for w in p['words'])}")


if __name__ == "__main__":
    main()
