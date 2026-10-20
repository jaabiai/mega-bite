#!/usr/bin/env python3
"""Re-read the licence of every Mixkit clip used by the film and the reels from its Mixkit page (one polite request per clip) and
fail if any clip is not under the 'Mixkit Stock Video Free License' (free for commercial use, no attribution).  Stills (ids 9000xx,
Met Open Access CC0 / Wikimedia Commons public domain) are listed with their licence from stills/sources.json.

  python3 tools/audit_licences.py            -> prints a table, writes docs/LICENCE_AUDIT.txt, exit code 1 on any problem
"""
import json, pathlib, re, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
fj = json.load(open(ROOT / 'footage.json', encoding='utf8')); fr = json.load(open(ROOT / 'reels' / 'footage_reels.json', encoding='utf8'))
edl = json.load(open(ROOT / 'edl.json')); reels = json.load(open(ROOT / 'reels' / 'reels.json', encoding='utf8'))
ids = {str(s['id']) for s in edl['shots']} | {str(o['id']) for o in edl['overlays']}
rids = {str(s['id']) for r in reels['reels'] for s in r['shots']} | {str(o['id']) for r in reels['reels'] for o in r.get('overlays', [])}
meta = {**fr, **fj}

def page(url):
    for k in range(6):
        time.sleep(1.3)
        p = subprocess.run(['curl', '-sS', '-m', '40', '-L', '-A', 'Mozilla/5.0', url], capture_output=True)
        t = p.stdout.decode('utf8', 'ignore')
        if p.returncode == 0 and len(t) > 20000 and 'Just a moment' not in t[:3000]: return t
        time.sleep(30 * (k + 1))
    return ''

rows, bad = [], []
for i in sorted(ids | rids, key=int):
    m = meta[i]
    if m.get('kind') == 'still':
        ok = m['license'].startswith(('CC0', 'Public domain'))
        rows.append((i, 'still', m['title'][:60], m['license'][:40], 'OK' if ok else 'PROBLEM')); (bad.append(i) if not ok else None); continue
    h = page(m['page'])
    free = 'Mixkit Stock Video Free License' in re.sub(r'<[^>]+>', ' ', h) and 'videoRestricted' not in h
    rows.append((i, 'film' if i in ids else '', 'reel' if i in rids else '', m['title'][:50], 'Free' if free else 'NOT FREE / unreadable'))
    if not free: bad.append(i)
    print(rows[-1], flush=True)
out = ['Licence audit', ''] + ['\t'.join(map(str, r)) for r in rows] + ['', f'problems: {bad or "none"}']
(ROOT / 'docs' / 'LICENCE_AUDIT.txt').write_text('\n'.join(out) + '\n', encoding='utf8')
print('problems:', bad or 'none'); sys.exit(1 if bad else 0)
