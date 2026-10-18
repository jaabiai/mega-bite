"""Write a correctly-timed Manglish SRT from the caption pages and verify the on-screen words equal the original script.

usage: make_srt.py <timeline.json> <original.srt> <out.srt>
"""
import json
import re
import sys


def ts(t):
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def main(tl_p, orig_p, out_p):
    tl = json.load(open(tl_p))
    pages = tl["captions"]
    lines = []
    for i, p in enumerate(pages, 1):
        lines += [str(i), f"{ts(p['t0'])} --> {ts(p['t1'])}", " ".join(w["t"] for w in p["words"]), ""]
    open(out_p, "w", encoding="utf-8").write("\n".join(lines))

    shown = [w["t"] for p in pages for w in p["words"]]
    raw = open(orig_p, encoding="utf-8").read().strip().replace("\r", "")
    orig = []
    for block in re.split(r"\n\s*\n", raw):
        orig += " ".join(block.strip().split("\n")[2:]).split()
    ok = shown == orig
    print(f"captions words on screen: {len(shown)} | words in your script: {len(orig)} | identical sequence: {ok}")
    if not ok:
        for i, (a, b) in enumerate(zip(shown, orig)):
            if a != b:
                print("first mismatch at", i, repr(a), repr(b))
                break
        sys.exit(1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
