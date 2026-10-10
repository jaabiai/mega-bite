"""Create the Roman-Hindi timing/lyrics files in output_hinglish_landscape/ from the EXISTING (read-only) timing + roman_map.json."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "output_hinglish_landscape")

HOOKS = [  # (style, test on roman text)
    ("wake", lambda r: "deshwasiyo" in r.lower()),
    ("stamp", lambda r: r.startswith("Vote Chori! Gaddi Chor")),
    ("defiant", lambda r: r.lower().startswith("ye mulk tera baap ka nahin")),
    ("people", lambda r: r.lower().startswith("ye janta ka hindustan hai")),
    ("march", lambda r: ("chalo" in r.lower() and "jantar-mantar" in r.lower()) or r.lower().startswith("jantar-mantar chalo")),
]

def ts_srt(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"

def main():
    src = json.load(open(os.path.join(ROOT, "lyric_timing.json"), encoding="utf-8"))
    rom = json.load(open(os.path.join(HERE, "..", "data", "roman_map.json"), encoding="utf-8"))
    lines = []
    for l in src["lines"]:
        r = rom[str(l["id"])]
        style = "regular"
        for name, test in HOOKS:
            if test(r):
                style = name; break
        lines.append({"id": l["id"], "section": l["section"], "start": l["start"], "end": l["end"], "roman": r,
                      "hook": style, "confidence": l.get("confidence"), "timing_source": l.get("source"),
                      "source_text": l["text"]})
    meta = dict(src["meta"]); meta.update({
        "title_roman": "Chalo Jantar-Mantar — Awaaz Janta Ki",
        "derived_from": "chalo_jantar_mantar/lyric_timing.json (unchanged); Roman text from hinglish_landscape/data/roman_map.json",
        "note": "Only the 'roman' field is ever drawn in the video; 'source_text' is kept for traceability only."})
    os.makedirs(OUT, exist_ok=True)
    json.dump({"meta": meta, "lines": lines}, open(os.path.join(OUT, "lyric_timing_hinglish.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "lyrics_hinglish.txt"), "w", encoding="utf-8") as f:
        sec = None
        for l in lines:
            s = re.sub(r"\s+—.*$", "", l["section"]).title()
            if s != sec:
                f.write(("\n" if sec else "") + f"[{s}]\n"); sec = s
            f.write(l["roman"] + "\n")
    with open(os.path.join(OUT, "lyrics_hinglish.srt"), "w", encoding="utf-8") as f:
        for i, l in enumerate(lines, 1):
            f.write(f"{i}\n{ts_srt(l['start'])} --> {ts_srt(l['end'])}\n{l['roman']}\n\n")
    from collections import Counter
    print(len(lines), "lines;", dict(Counter(l["hook"] for l in lines)))

if __name__ == "__main__":
    main()
