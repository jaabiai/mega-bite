#!/usr/bin/env python3
"""Generate edl.json: one shot per lyric line, chosen for what the line says.

Film time of every cut = start of the lyric cue (from inputs/lyrics.srt via timeline.json), so each picture
change lands exactly on a lyric change (and, because the song runs on a 2-bar line grid, on the bar line).

Table: cue number -> (Mixkit id, in-point s, why)
"""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, WORK, load_timeline

# ------------------------------------------------------------------ the picture for each line
LINES = {
 # --- hook, 1st time
 1: (33934, 0.0, 'worldly desires vanish: hourglass in the desert at sunset'),
 2: (46061, 0.0, 'alone in the grave: lone tree under a desert night sky'),
 3: (9810, 2.0, 'the first question comes: storm front'),
 4: (34223, 2.3, 'did you pray? a man in sujood'),
 # --- hook, 2nd time (lines 1-2)
 5: (9665, 18.0, 'day fades into night over a city: the dunya passing'),
 6: (15453, 8.0, 'alone: bare trees in morning fog'),
 # --- verse 1
 7: (4311, 0.0, 'five times a day, from the mosque'),
 8: (17263, 1.0, 'the Allahu Akbar call: minarets lit at dusk'),
 9: (31629, 0.0, 'do not lie in laziness: night turns to sunrise'),
 10: (28897, 0.0, 'life runs out: clock'),
 11: (25375, 6.0, 'prayer washes sins away: soft rain and sun'),
 12: (34285, 2.0, 'duty to the Creator: mosque from above'),
 13: (2846, 2.0, 'the heart\'s pain: rain on a window'),
 14: (34223, 5.0, 'no medicine like sujood'),
 # --- hook, 3rd time
 15: (3132, 0.0, 'desires fade: town lights at dusk'),
 16: (5032, 4.0, 'alone: dry tree at sunset'),
 17: (4422, 2.0, 'the first question: thunderstorm at night'),
 18: (34251, 2.0, 'did you pray? the mosque hall'),
 # --- verse 2
 19: (40047, 0.0, 'those who dropped the prayer: a bleak moonlit desert'),
 20: (4428, 0.0, 'burned in the fire: glowing volcano at night'),
 21: (46898, 3.0, 'the day of reckoning: full moon in cloud'),
 22: (28085, 8.0, 'tears will not help then: rain at a window'),
 23: (14468, 3.0, 'in the Lord\'s court, what will you say: the vast night sky'),
 24: (4310, 3.0, 'standing helpless: empty desert road'),
 25: (34857, 4.0, 'when the soul reaches the throat: the last light of dusk'),
 26: (9670, 1.0, 'regret and weeping: heavy rain'),
 # --- hook, 4th time
 27: (4240, 0.0, 'desires fade: the night traffic rush'),
 28: (4357, 0.0, 'alone: a mountain silhouette in the night'),
 29: (9681, 1.0, 'the first question: thunderstorm over the plain'),
 30: (34208, 3.0, 'did you pray? the Quran'),
 # --- verse 3
 31: (9843, 1.0, 'the purity of wudu: clean water over stones'),
 32: (39179, 3.0, 'standing before the Master: the mosque interior'),
 33: (2562, 1.0, 'flowers of humility in the heart'),
 34: (34250, 2.0, 'prayer with khushu: reading Quran in the mosque'),
 35: (6925, 3.0, 'du\'a mixed with tears: a single candle'),
 36: (26532, 3.0, 'seek Allah\'s mercy: sun breaking through clouds'),
 37: (11185, 3.0, 'paradise: waterfalls and a rainbow'),
 38: (9998, 6.0, 'prayer, do not forget it: mosque at dawn in the mist'),
 39: (9888, 20.0, 'firm on the path of prayer: the road up to the mosque'),
 40: (20425, 20.0, 'success in both worlds: sunrise'),
 41: (34223, 0.0, 'Ya Rabb: in sujood'),
 42: (34189, 2.0, 'the forehead to the ground, the Quran'),
 43: (30911, 2.0, 'seeking His mercy: stars turning to dawn'),
 # --- hook, 5th time
 44: (3147, 0.0, 'desires fade: moon dissolving in cloud'),
 45: (52012, 0.0, 'alone: empty desert'),
 46: (48854, 2.0, 'the first question: storm front over the sea'),
 47: (15694, 0.0, 'did you pray? the mosque dome and calligraphy'),
 # --- hook, 6th time
 48: (35096, 3.0, 'desires fade: the sun sets over a field'),
 49: (4149, 0.0, 'alone: empty dunes'),
 50: (1518, 0.0, 'the first question: dark clouds'),
 51: (11925, 1.0, 'did you pray? the Quran and prayer beads'),
 # --- outro
 52: (9595, 15.0, 'firm on the path of prayer: mosque on a hill above the clouds'),
 53: (9736, 6.0, 'success in both worlds: sun above the clouds'),
 54: (4148, 2.0, 'Ya Rabb, Ya Rabb: the Milky Way'),
}
SECTION_STARTS = {7: 'fadewhite', 15: 'fadewhite', 19: 'fadeblack', 27: 'fadewhite', 31: 'fadeblack', 44: 'fadewhite', 48: 'fadewhite', 52: 'fadeblack'}

def main():
    tl = load_timeline()
    cues = tl['cues']; off = tl['song_offset']
    assert len(cues) == len(LINES), f'{len(cues)} cues but {len(LINES)} planned lines'
    shots = []
    # ---- intro (film time): stars -> mosque at night -> moon over the sea behind the Arabic title
    T = tl['title_card']
    shots += [
        dict(id=4124, t=0.0, tr='none', trd=0.0, z0=1.0, z1=1.10, note='intro: stars, the call of the adhan', **{'in': 0.0}),
        dict(id=4312, t=4.9, tr='fade', trd=1.2, z0=1.0, z1=1.10, note='intro: mosque at night', **{'in': 0.0}),
        dict(id=4166, t=round(T['start'], 2), tr='fadewhite', trd=1.1, z0=1.04, z1=1.0, note='title card: moon over the sea', **{'in': 2.0}),
        dict(id=9736, t=round(T['end'], 2), tr='fade', trd=1.4, z0=1.0, z1=1.06, note='humming: sun rising above the clouds', **{'in': 2.0}),
    ]
    for i, c in enumerate(cues, start=1):
        cid, a, note = LINES[i - 1 + 1] if False else LINES[i]
        shots.append(dict(id=cid, t=round(c['start'], 3), tr=SECTION_STARTS.get(i, 'fade'), trd=1.3 if i in SECTION_STARTS else 1.0,
                          z0=1.0 if i % 2 else 1.06, z1=1.06 if i % 2 else 1.0, note=f'L{i}: {note}', **{'in': a}))
    # first lyric shot follows the humming shot: a gentle dissolve
    shots[4]['trd'] = 1.2
    # ending: fade the last picture to black under the end card
    shots[-1]['tr'] = 'fadeblack'; shots[-1]['trd'] = 1.6
    for s in shots:
        s.setdefault('cy', 0.5); s.setdefault('px0', 0.0); s.setdefault('px1', 0.0); s.setdefault('speed', 1.0); s['anchor'] = True
    # a few clips need a different vertical crop
    for s in shots:
        if s['id'] == 34223: s['cy'] = 0.92
        if s['id'] in (9998, 9888): s['cy'] = 0.55
        if s['id'] == 4357: s['speed'] = 0.8      # 5.3 s clip stretched to fill a 6.3 s shot
    old = json.load(open(ROOT / 'edl.json'))
    json.dump({'shots': shots, 'overlays': old['overlays']}, open(ROOT / 'edl.json', 'w'), indent=1, ensure_ascii=False)
    print(len(shots), 'shots ->', ROOT / 'edl.json')

if __name__ == '__main__':
    main()
