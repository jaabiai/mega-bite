"""Builds edit/data/reel_timeline.json (reel seconds): caption pages + every on-screen graphic of the 9:16 reel.
All times are derived from the forced-aligned narration, so each graphic lands on the word that triggers it."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reel_plan as rp  # noqa: E402
import timeline as tl  # noqa: E402  (re-uses split_sentence / SENT_END and the aligned words)

OFF, END = rp.OFF, rp.END_MAIN


def R(t_main):
    return round(t_main - OFF, 3)


def words():
    ws = [w for w in tl.WORDS if w["start"] >= OFF - 0.02 and w["end"] <= END + 0.05]
    return ws


def caption_pages():
    ws = words()
    sents, cur = [], []
    for w in ws:
        cur.append(w)
        if w["text"].endswith(tl.SENT_END):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    pages = []
    for s in sents:
        pages.extend(tl.split_sentence(s, max_chars=34, max_words=5))
    out = []
    for i, p in enumerate(pages):
        t0 = R(p[0]["start"]) - 0.08
        nxt = R(pages[i + 1][0]["start"]) - 0.08 if i + 1 < len(pages) else R(END)
        t1 = min(nxt, R(p[-1]["end"]) + 0.40)
        out.append({"t0": round(max(t0, 0), 3), "t1": round(t1, 3),
                    "words": [{"t": w["text"], "a": R(w["start"]), "b": R(w["end"])} for w in p]})
    return out


def wt(cue, prefix, nth=0):
    return R(tl.word(cue, prefix, nth))


def events():
    ev = []

    def add(type_, a_main, b_main, **kw):
        ev.append(dict(type=type_, t0=R(a_main), t1=R(b_main), **kw))

    # ---- hook (speaker, 0 - 2.6 s)
    add("hook", 115.0, 117.55, kicker="iOS 27  •  iPHONE TIP", lines=["NOISY PLACE?", "CALL VANNAL?"])
    # ---- story over B-roll
    add("kp", 119.75, 122.85, kicker="PROBLEM", text="SURROUNDING NOISE", sub="call-il shallyam")
    add("kp", 123.20, 128.95, kicker="THE FEAR", text="BACKGROUND SOUND", sub="avar kettu ennulla pedi")
    add("kp", 129.35, 131.55, kicker="THE FIX", text="ONE SETTING", sub="valare simple aanu")
    # ---- demo steps
    steps = [("OPEN SETTINGS", "Settings-ilekku povuka", 131.65, 133.45),
             ("ACCESSIBILITY", "option select cheyyuka", 133.45, 139.60),
             ("AUDIO & VISUAL", "thaazhekk scroll cheythu select cheyyuka", 139.60, 144.30),
             ("VOICE ISOLATION", "'Add Voice Isolation' option", 144.30, 151.00)]
    for i, (title, sub, a, b) in enumerate(steps):
        add("step", a, b, n=i + 1, total=4, text=title, sub=sub)
    add("step_on", 151.00, 154.90, text="TURN IT ON", sub="button enable cheyyuka")
    # ---- result over B-roll
    add("kp", 154.95, 158.50, kicker="IN A CROWD?", text="NOISY CROWD", sub="program-ilum matte sthalangalilum")
    add("voice", 160.95, 165.70, kicker="THE RESULT", text="ONLY YOUR VOICE", sub="ningal parayunna shabdam mathram")
    # ---- recap + end card
    add("recap", 165.90, 169.85, kicker="SET IT UP", lines=["Settings › Accessibility", "Audio & Visual › Add Voice Isolation"])
    add("endcard", 170.23, END + rp.TAIL, at=56.55, lines=["FULL VIDEO", "ON MEGA BYTE"])
    return ev


def main():
    out = {"duration": rp.DUR, "n_frames": rp.N_FRAMES, "captions": caption_pages(), "events": events(),
           "demo": [R(rp.DEMO[0]), R(rp.DEMO[1])]}
    p = f"{HERE}/data/reel_timeline.json"
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    pg = out["captions"]
    print("wrote", p, len(pg), "caption pages,", len(out["events"]), "events | max chars",
          max(len(" ".join(w['t'] for w in q['words'])) for q in pg), "| min page", round(min(q['t1'] - q['t0'] for q in pg), 2))
    for q in pg[:6]:
        print(f"  {q['t0']:6.2f}-{q['t1']:6.2f}  {' '.join(w['t'] for w in q['words'])}")


if __name__ == "__main__":
    main()
