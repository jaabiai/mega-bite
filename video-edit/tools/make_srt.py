#!/usr/bin/env python3
"""Write a YouTube-ready .srt from a project's caption chunks (captions_data.CHUNKS).

usage: make_srt.py --project NAME --out subs.srt [--max-chars 62] [--max-dur 4.5] [--cut-list WIDE_CUTS]

Neighbouring chunks are merged into one cue while the text stays short, the gap is small and the cue stays
under --max-dur seconds; cues longer than 42 characters are broken into two balanced lines.  Times follow the
narration, which is also the 16:9 timeline (the reel cut is not covered).
"""
import argparse, importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))


def load_chunks(project):
    path = os.path.join(HERE, "..", "projects", project, "captions_data.py")
    spec = importlib.util.spec_from_file_location("captions_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [(c[0], c[1], c[2]) for c in mod.CHUNKS]


def remap_chunks(project, chunks, list_name):
    """Map source-time chunks through the timeline's cut list (exact ranges, as the main edit plays them)."""
    path = os.path.join(HERE, "..", "projects", project, "timeline.py")
    spec = importlib.util.spec_from_file_location("timeline", path)
    tl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tl)
    cuts, u = [], 0.0
    for a, b in getattr(tl, list_name):
        cuts.append((u, a, b))
        u += b - a

    def m(t):
        for us, a, b in cuts:
            if a - 0.3 <= t <= b + 0.3:
                return us + min(max(t, a), b) - a
        return None
    out = []
    for t0, t1, txt in chunks:
        u0, u1 = m(t0), m(t1)
        if u0 is not None and u1 is not None and u1 > u0:
            out.append((u0, u1, txt))
    return out


def merge(chunks, max_chars, max_dur, max_gap=0.25):
    cues = []
    for t0, t1, txt in chunks:
        if cues:
            c0, c1, ctxt = cues[-1]
            joined = f"{ctxt} {txt}"
            if t0 - c1 <= max_gap and len(joined) <= max_chars and t1 - c0 <= max_dur and not ctxt.endswith(("?", "!", ".")):
                cues[-1] = (c0, t1, joined)
                continue
        cues.append((t0, t1, txt))
    return cues


def two_lines(txt, width=42):
    if len(txt) <= width:
        return txt
    words = txt.split()
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, a, b)
    return f"{best[1]}\n{best[2]}"


def stamp(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-chars", type=int, default=62)
    ap.add_argument("--max-dur", type=float, default=4.5)
    ap.add_argument("--cut-list", default=None, help="timeline cut list the chunks are mapped through (e.g. WIDE_CUTS)")
    a = ap.parse_args()
    chunks = load_chunks(a.project)
    if a.cut_list:
        chunks = remap_chunks(a.project, chunks, a.cut_list)
    cues = merge(chunks, a.max_chars, a.max_dur)
    with open(a.out, "w", encoding="utf-8") as fh:
        for i, (t0, t1, txt) in enumerate(cues, 1):
            fh.write(f"{i}\n{stamp(t0)} --> {stamp(max(t1, t0 + 0.6))}\n{two_lines(txt)}\n\n")
    print(f"wrote {a.out}: {len(cues)} cues")


if __name__ == "__main__":
    main()
