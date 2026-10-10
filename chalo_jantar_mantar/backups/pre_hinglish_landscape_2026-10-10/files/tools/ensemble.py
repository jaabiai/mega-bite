"""Combine several forced-alignment runs into one per-line start estimate (median vote)."""
import os
import json, sys, glob, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lyrics import parse
T = os.environ.get("CJM_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/")

def load_runs(names):
    runs = []
    for n in names:
        try:
            runs.append((n, json.load(open(T + f"work/align/{n}.json"))))
        except Exception as e:
            print("skip", n, e)
    return runs

def ensemble(names):
    L = parse()
    runs = load_runs(names)
    out = {}
    for l in L:
        k = str(l["id"])
        vals = np.array([r[k]["start"] for _, r in runs if k in r])
        med = float(np.median(vals))
        # consensus = largest cluster within 0.35 s
        best = max(vals, key=lambda v: (np.abs(vals - v) <= 0.35).sum())
        cl = vals[np.abs(vals - best) <= 0.35]
        out[l["id"]] = {"start": float(np.median(cl)), "n": int(len(cl)), "of": int(len(vals)), "spread": float(cl.max() - cl.min()), "all": [round(float(v), 2) for v in vals]}
    return L, out

if __name__ == "__main__":
    names = sys.argv[1:] or ["turbo_l1.0", "turbo_l2.5", "turbo_l4.0", "turbo_l0.4"]
    L, e = ensemble(names)
    bad = 0
    for l in L:
        x = e[l["id"]]
        flag = "" if x["n"] >= 3 else "  <== weak consensus"
        if x["n"] < 3: bad += 1
        print(f"{l['id']:3d} {x['start']:7.2f}  votes {x['n']}/{x['of']}  {x['all']}{flag}  {l['text']}")
    print("weak:", bad)
