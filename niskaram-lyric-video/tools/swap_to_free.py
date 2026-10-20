#!/usr/bin/env python3
"""v8 -> v9 of the picture: replace every shot whose clip was under the Mixkit *Restricted* ("personal use only") licence by
footage / images that may be used in a monetised channel, and leave everything else (timing, transitions, grade, captions, audio) alone.

Run once; it rewrites edl.json and footage.json in place (git has the previous versions).  The table says, per shot index:
  (new id, in-point, why)
Ids 9000xx are still images turned into camera-move clips by tools/still_clip.py (see stills/sources.json for author + licence).
"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
edl = json.load(open(ROOT / 'edl.json')); fj = json.load(open(ROOT / 'footage.json'))
CHECKED = '2026-10-20'
FREE = 'Mixkit Stock Video Free License'

# shot index -> (id, in, cy, note)
SWAP = {
 3:  (4695, 0.3, 0.5, 'humming: the last light above a sea of clouds'),
 4:  (28889, 0.5, 0.5, 'L1: worldly desires vanish: the hourglass'),
 5:  (4093, 0.5, 0.6, 'L2: alone in the grave: a starry sky over a dark land'),
 6:  (4423, 0.5, 0.5, 'L3: the first question comes: a storm over the mountains'),
 7:  (900007, 0.0, 0.5, 'L4: did you pray? the mihrab and minbar (Bonfils, Cairo, 1870s)'),
 8:  (4308, 5.0, 0.5, 'L5: day fades into night over a city: the dunya passing'),
 9:  (2221, 0.0, 0.5, 'L6: alone: a forest disappearing in the fog'),
 11: (900011, 0.0, 0.5, 'L8: the Allahu Akbar call: a minaret and dome (Teynard, Cairo, 1851-52)'),
 12: (1944, 8.0, 0.5, 'L9: do not lie in laziness: the sun rising over the mist'),
 14: (1707, 2.0, 0.5, 'L11: prayer washes sins away: rain on green leaves'),
 15: (4313, 2.0, 0.5, 'L12: duty to the Creator: the mosque'),
 17: (900017, 0.0, 0.5, 'L14: no medicine like sujood (Gérôme, Evening Prayer, Cairo, 1865)'),
 21: (900021, 0.0, 0.5, 'L18: did you pray? the arches and lamps of the mosque hall (Gérôme)'),
 24: (4433, 9.0, 0.5, 'L21: the day of reckoning: the full moon in haze'),
 25: (2716, 1.0, 0.5, 'L22: tears will not help then: rain from the roof'),
 26: (1610, 3.0, 0.5, 'L23: in the Lord\'s court, what will you say: the vast night sky'),
 28: (2125, 0.5, 0.5, 'L25: when the soul reaches the throat: the last light of dusk'),
 29: (2202, 4.0, 0.5, 'L26: regret and weeping: rain in the woods'),
 32: (4060, 3.0, 0.5, 'L29: the first question: a thunderstorm'),
 33: (900033, 0.0, 0.5, 'L30: did you pray? the Qur\'an (illuminated Qur\'an, Met)'),
 34: (2186, 0.5, 0.5, 'L31: the purity of wudu: clean water over stones'),
 35: (900035, 0.0, 0.5, 'L32: standing before the Master: the mosque interior (Moti Masjid, 1860s-70s)'),
 37: (900037, 0.0, 0.5, 'L34: prayer with khushu: a page of the Qur\'an (Qur\'an of Ibrahim Sultan, 1427)'),
 38: (3438, 0.2, 0.5, 'L35: du\'a mixed with tears: candle flames'),
 39: (4113, 1.0, 0.5, 'L36: seek Allah\'s mercy: light breaking through the clouds'),
 40: (4323, 0.2, 0.5, 'L37: paradise: a waterfall and a rainbow'),
 41: (900041, 0.0, 0.5, 'L38: prayer, do not forget it: a man at prayer at the mosque door (Osman Hamdi Bey, 1879)'),
 42: (2392, 1.0, 0.55, 'L39: firm on the path of prayer: the road through the mountains'),
 43: (1086, 5.0, 0.5, 'L40: success in both worlds: sunrise over the ocean'),
 44: (900044, 0.0, 0.5, 'L41: Ya Rabb: the prayer niche of a prayer rug (Met)'),
 45: (900045, 0.0, 0.5, 'L42: the forehead to the ground, the Qur\'an (portable Qur\'an, Met)'),
 46: (1704, 0.5, 0.5, 'L43: seeking His mercy: stars over a calm lake'),
 49: (4059, 3.0, 0.5, 'L46: the first question: a storm over the sea'),
 50: (900050, 0.0, 0.5, 'L47: did you pray? the mihrab and its calligraphy (Met)'),
 51: (2639, 0.3, 0.5, 'L48: desires fade: the sun sets over a field'),
 54: (900054, 0.0, 0.5, 'L51: did you pray? the Qur\'an binding (Met)'),
 55: (900055, 0.0, 0.5, 'L52: firm on the path of prayer: the mosque on the hill (Citadel of Cairo, 1870s)'),
 56: (4282, 1.0, 0.5, 'L53: success in both worlds: a summit above the clouds'),
}
MIXKIT = {   # id -> (title, slug) read from the Mixkit listing; licence re-read from every clip page on CHECKED
 4695: ('Clouds covering the mountains', 'clouds-covering-the-mountains'), 4113: ('Sun rays pass through the clouds in the mountains', 'sun-rays-pass-through-the-clouds-in-the-mountains'),
 4282: ('Clouds touching the tip of Matterhorn Mountain', 'clouds-touching-the-tip-of-matterhorn-mountain'), 28889: ('Glass hourglass close up on a black background', 'glass-hourglass-close-up-on-a-black-background'),
 4093: ('Starry sky at night, time lapse', 'starry-sky-at-night-time-lapse'), 1610: ('Stars in space background', 'stars-in-space-background'),
 1704: ('Night sky with stars at a calm lake, time lapse', 'night-sky-with-stars-at-a-calm-lake-time-lapse'), 4423: ('Electrical storm in the mountains', 'electrical-storm-in-the-mountains'),
 4060: ('Thunderstorm timelapse', 'thunderstorm-timelapse'), 4059: ('Electric storm over the ocean', 'electric-storm-over-the-ocean'),
 4308: ('Aerial view of a city during the night', 'aerial-view-of-a-city-during-the-night'), 2221: ('Forest disappearing in the fog', 'forest-disappearing-in-the-fog'),
 2202: ('Rain in the woods', 'rain-in-the-woods'), 1944: ('Beautiful sunrise landscape', 'beautiful-sunrise-landscape'),
 1707: ('Large green plant leaves in the rain', 'large-green-plant-leaves-in-the-rain'), 4433: ('Full moon with a soft haze', 'full-moon-with-a-soft-haze'),
 2716: ('Rain falling from the roof on a rainy day', 'rain-falling-from-the-roof-on-a-rainy-day'), 2125: ('Beautiful sunset over mountains', 'beautiful-sunset-over-mountains'),
 2186: ('Water falling over stones', 'water-falling-over-stones'), 4323: ('Niagara Waterfalls', 'niagara-waterfalls'),
 2392: ('Road surrounded by mountains', 'road-surrounded-by-mountains'), 1086: ('Sunrise on the ocean', 'sunrise-on-the-ocean'),
 2639: ('Sunset over fields of tall dry grass', 'sunset-over-fields-of-tall-dry-grass'), 4313: ('Symmetrical mosque', 'symmetrical-mosque'), 3438: ('Flames in candles close up', 'flames-in-candles-close-up'),
}
STILLS = json.load(open(ROOT / 'stills' / 'sources.json'))     # id -> {title, creator, date, licence, page, ...}

for i, (t, slug) in MIXKIT.items():
    fj[str(i)] = {'title': t, 'page': f'https://mixkit.co/free-stock-video/{slug}-{i}/', 'license': FREE, 'checked': CHECKED}
for k, v in STILLS.items():
    fj[k] = {'title': f"{v['title']} ({v['creator']}, {v['date']})", 'page': v['page'], 'license': v['licence'], 'checked': CHECKED, 'kind': 'still'}

EQ = {14: 'saturation=0.8', 15: 'saturation=0.88'}      # tame the two most saturated replacements
for idx, (cid, inp, cy, note) in SWAP.items():
    s = edl['shots'][idx]
    s.update({'id': cid, 'in': inp, 'cy': cy, 'note': note})
    if idx in EQ: s['eq'] = EQ[idx]
bad = [s['id'] for s in edl['shots'] if 'Restricted' in fj[str(s['id'])]['license']]
assert not bad, bad
json.dump(edl, open(ROOT / 'edl.json', 'w'), indent=1, ensure_ascii=False); json.dump(fj, open(ROOT / 'footage.json', 'w'), indent=1, ensure_ascii=False)
print('shots swapped:', len(SWAP), '| restricted shots left:', len(bad))
