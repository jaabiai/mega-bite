#!/usr/bin/env python3
"""Regenerate docs/FOOTAGE_CREDITS.md from edl.json + footage.json (+ reels/)."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
edl = json.load(open(ROOT / 'edl.json')); fj = json.load(open(ROOT / 'footage.json', encoding='utf8'))
used = {str(s['id']) for s in edl['shots']} | {str(o['id']) for o in edl['overlays']}
vid = [i for i in used if fj[i].get('kind') != 'still']; stl = [i for i in used if fj[i].get('kind') == 'still']
assert not [i for i in used if 'Restricted' in fj[i]['license']], 'restricted clip in the edit'
L = ['# Footage and image credits, licences', '',
     'Every picture in the film and in the three reels is free for **commercial use on a monetised channel**; no clip is under a "personal use only" licence.', '',
     f'* **{len(vid)} stock clips - Mixkit Stock Video Free License** (https://mixkit.co/license/#videoFree): free for commercial and non-commercial use, no attribution required. The licence label was re-read from every clip page on 2026-10-20 (`tools/audit_licences.py`, result in `LICENCE_AUDIT.txt`).',
     f'* **{len(stl)} still images - public-domain works and museum open-access scans**, turned into camera-move clips by `tools/still_clip.py` (no footage of prayer, sujood, mosque interiors or the Qur\'an with a verifiable commercial-use licence could be found on the free sites): the Metropolitan Museum of Art **Open Access (CC0 1.0)** scans, and paintings by Jean-L\u00e9on G\u00e9r\u00f4me (d. 1904), Osman Hamdi Bey (d. 1910) from Wikimedia Commons / the Met - all in the **public domain**. No attribution is legally required; the credits below are given as a courtesy. Authors, dates, source pages and licences: `stills/sources.json`.', '',
     'The shot list is in `edl.json`; to change a picture change its `id` (see README -> *Swapping footage*).', '',
     'Content check: every second of the film and of the reels was checked on contact sheets; no women, no uncovered awrah, no music/dance/alcohol. The only people are men at prayer / reading the Qur\'an, and painted worshippers.', '',
     '| Film time (s) | ID | Title | Licence | Used for |', '|---:|---:|---|---|---|']
seen = set()
for s in edl['shots']:
    i = str(s['id'])
    if i in seen: continue
    seen.add(i); v = fj[i]
    L.append(f"| {s['t']:.1f} | [{i}]({v['page']}) | {v['title']} | {v['license']} | {s['note']} |")
L += ['', '## Texture overlays', '', '| Mixkit ID | Title | Licence | Role |', '|---:|---|---|---|']
for o in edl['overlays']:
    v = fj[str(o['id'])]; L.append(f"| [{o['id']}]({v['page']}) | {v['title']} | {v['license']} | {o['role']} |")
rf = ROOT / 'reels' / 'footage_reels.json'
if rf.exists():
    fr = json.load(open(rf, encoding='utf8')); rc = json.load(open(ROOT / 'reels' / 'reels.json', encoding='utf8'))
    L += ['', '## Reels (9:16)', '',
          'Native vertical Mixkit clips wherever the free sites have one for the line; the prayer / mihrab / Qur\'an shots are the public-domain / CC0 still images above, framed vertically.', '',
          '| Reel | ID | Title | Licence |', '|---|---:|---|---|']
    for r in rc['reels']:
        for i in dict.fromkeys(str(x['id']) for x in r['shots']):
            v = fr[i]; assert 'Restricted' not in v['license']; L.append(f"| {r['id']} | [{i}]({v['page']}) | {v['title']} | {v['license']} |")
(ROOT / 'docs' / 'FOOTAGE_CREDITS.md').write_text('\n'.join(L) + '\n', encoding='utf8')
print('wrote docs/FOOTAGE_CREDITS.md')
