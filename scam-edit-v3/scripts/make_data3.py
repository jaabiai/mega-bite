"""overlay3/data.js (icons + aligned SRT words + scene table) and work3/scenes.json (shared with final3.py)."""
import json, re, glob, os
B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
FPS = 30
q = lambda t: round(t * FPS) / FPS
# id, t0, t1, broll(optional)
RAW = [
    ('wa', 2.40, 8.17, None),
    ('b1', 8.17, 12.17, dict(file='s_41165.mp4', start=3.0, mode='full', grade='eq=brightness=-0.16:contrast=1.06:saturation=0.9')),
    ('b2', 12.17, 15.50, dict(file='s_42136.mp4', start=0.3, mode='portrait', cx=1180, grade='eq=brightness=-0.10:contrast=1.04:saturation=0.95')),
    ('never', 19.33, 21.17, None),
    ('loss', 24.37, 32.65, dict(file='s_34838.mp4', start=5.0, mode='full', grade='eq=brightness=-0.22:contrast=1.10:saturation=0.9')),
    ('link', 35.97, 46.50, dict(file='s_46627.mp4', start=3.5, mode='full', t0=38.9, grade='eq=brightness=-0.16:contrast=1.10:saturation=0.95')),
    ('rules', 57.97, 78.70, None),
    ('domain', 82.40, 96.53, None),
    ('official', 96.53, 105.10, None),
    ('gpay', 113.73, 130.55, None),
    ('careful', 146.15, 151.55, dict(file='s_46639.mp4', start=9.0, mode='full', grade='eq=brightness=-0.16:contrast=1.08:saturation=0.95')),
    ('recap', 151.55, 158.40, None),
    ('share', 158.40, 163.70, None),
    ('end', 166.80, 176.00, None),
]
scenes = []
for i, (sid, t0, t1, br) in enumerate(RAW):
    prev_t1 = RAW[i - 1][2] if i else None
    nxt = RAW[i + 1][1] if i + 1 < len(RAW) else None
    s = dict(id=sid, t0=q(t0), t1=q(t1), wipeIn=(prev_t1 is None or abs(prev_t1 - t0) > 1e-6), wipeOut=(nxt is not None))
    if br:
        br = dict(br)
        br['t0'] = q(br.get('t0', t0)); br['t1'] = q(br.get('t1', t1))
        s['broll'] = br
    scenes.append(s)
json.dump(dict(scenes=scenes, total=176.0), open(B + 'work3/scenes.json', 'w'), indent=1)

icons = {}
for f in glob.glob(B + 'overlay/node_modules/lucide-static/icons/*.svg'):
    n = os.path.basename(f)[:-4]
    s = open(f).read()
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S).strip()
    m = re.match(r'<svg[^>]*>', s, flags=re.S)
    root = re.sub(r'\s+(class|width|height|stroke-width|fill|stroke|stroke-linecap|stroke-linejoin)="[^"]*"', '', m.group(0))
    s = root + s[m.end():]
    icons[n] = re.sub(r'\s+', ' ', s)
w = json.load(open(B + 'work3/words_srt.json'))
words = [dict(w=x['w'], cue=x['cue'], t0=round(x['t0'], 3), t1=round(x['t1'], 3)) for x in w['words']]
open(B + 'overlay3/data.js', 'w').write('window.DATA=' + json.dumps(dict(icons=icons, words=words, scenes=scenes), ensure_ascii=False) + ';')
js = open(B + 'overlay3/scenes1.js').read() + open(B + 'overlay3/scenes2.js').read()
used = set(re.findall(r"icon\('([a-z0-9-]+)'", js)) | set(re.findall(r"\['([a-z0-9-]+)', '", js)) | set(re.findall(r"ic: '([a-z0-9-]+)'", js)) | set(re.findall(r"ic, '", js))
print(len(icons), 'icons;', len(words), 'words;', len(scenes), 'scenes')
print('missing icons:', sorted(n for n in used if n not in icons))
