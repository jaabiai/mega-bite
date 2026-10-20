#!/usr/bin/env python3
"""Regenerate docs/FOOTAGE_CREDITS.md from edl.json + footage.json."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
edl = json.load(open(ROOT / 'edl.json')); fj = json.load(open(ROOT / 'footage.json'))
free = [i for i, v in fj.items() if v['license'].startswith('Mixkit Stock Video Free')]
restr = [i for i, v in fj.items() if 'Restricted' in v['license']]
L = ['# Footage credits and licences', '',
     'All picture material is stock footage from **Mixkit** (https://mixkit.co). Licence labels were read from each clip page on 2026-10-19.', '',
     f'* **{len(free)} clips: Mixkit Stock Video Free License** – free for commercial and non-commercial use, no attribution required.',
     f'* **{len(restr)} clips: Mixkit Restricted License** – the clip page offers the 720p file "for personal use only"; commercial use (e.g. a monetised YouTube channel) needs the Envato licence/4K download for that clip, or a replacement.', '',
     'The shot list is in `edl.json`, so a restricted clip can be swapped for any other footage by changing its `id` (see README → *Swapping footage*).', '',
     'Content check: every clip was inspected frame-by-frame; no women, no uncovered awrah, no music/dance/alcohol. The only people are men at prayer / reading the Quran, and hands.', '',
     '| Film time (s) | Mixkit ID | Title | Licence | Used for |', '|---:|---:|---|---|---|']
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
          'Native vertical Mixkit clips wherever the free sites have one for the line. Mosque, prayer and Qur\'an have no vertical clip on Mixkit/Coverr, so those landscape clips are reframed to a 9:16 slice.', '',
          '| Reel | Mixkit ID | Title | Licence |', '|---|---:|---|---|']
    for r in rc['reels']:
        for i in dict.fromkeys(str(x['id']) for x in r['shots']):
            v = fr[i]; L.append(f"| {r['id']} | [{i}]({v['page']}) | {v['title']} | {v['license']} |")
(ROOT / 'docs' / 'FOOTAGE_CREDITS.md').write_text('\n'.join(L) + '\n', encoding='utf8')
print('wrote docs/FOOTAGE_CREDITS.md')
