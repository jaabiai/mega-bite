"""Assemble lyric_timing.json from the alignment ensemble + manual overrides.

overrides: work/overrides.json  {"<id>": {"start": s, "end": e, "note": "..."}}  (either key optional)
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ensemble import ensemble, T
from render import classify

RUNS = ["turbo_l1.0", "turbo_l2.5", "turbo_l0.4", "turbo_l3.0"]
DURATION = 267.2

def build(out_path, last_end=None):
    L, e = ensemble(RUNS)
    ov = {}
    if os.path.exists(T + "work/overrides.json"):
        ov = json.load(open(T + "work/overrides.json"))
    lines = []
    for i, l in enumerate(L):
        k = str(l["id"])
        s = round(e[l["id"]]["start"], 2)
        src = f"whisper-forced-align vote {e[l['id']]['n']}/{e[l['id']]['of']}"
        if k in ov and "start" in ov[k]:
            s = ov[k]["start"]; src = "manual: " + ov[k].get("note", "spectrogram onset")
        lines.append({"id": l["id"], "section": l["section"], "text": l["text"], "start": s, "end": None, "source": src,
                      "votes": f"{e[l['id']]['n']}/{e[l['id']]['of']}"})
    # contiguous ends, then end overrides
    for i, l in enumerate(lines):
        nxt = lines[i + 1]["start"] if i + 1 < len(lines) else (last_end or DURATION - 3.0)
        l["end"] = round(nxt, 2)
        k = str(l["id"])
        if k in ov and "end" in ov[k]:
            l["end"] = ov[k]["end"]
            l["source"] += " | end: " + ov[k].get("end_note", "manual")
        l["style"] = classify(l["text"])
    json.dump({"meta": {"title": "चलो जंतर-मंतर — आवाज़ जनता की", "duration_s": DURATION, "fps": 30,
                        "global_offset_s": 0.0,
                        "timing_method": "Whisper(turbo) forced alignment of the supplied lyrics, 4-run vote, manual spectrogram refinement",
                        "how_to_adjust": "edit start/end (seconds) per line, or set meta.global_offset_s to shift everything; re-run render"},
               "lines": lines}, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return lines

if __name__ == "__main__":
    ls = build(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
    print(len(ls), "lines")
