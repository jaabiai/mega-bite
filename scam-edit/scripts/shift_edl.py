"""work/edl.json -> work/edl_s.json with the Megabyte welcome stinger (84 frames) inserted at output frame 719."""
import json
B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
INS_F, DLT_F = 719, 84
e = json.load(open(B + 'work/edl.json'))
for p in e['pieces']:
    if p['out_a'] >= INS_F:
        p['out_a'] += DLT_F
        p['out_b'] += DLT_F
        for w in p['words']:
            w['out'] = round(w['out'] + DLT_F / e['fps'], 4)
    else:
        assert p['out_b'] <= INS_F, p
e['total_frames'] += DLT_F
e['stinger'] = dict(frame=INS_F, frames=DLT_F)
json.dump(e, open(B + 'work/edl_s.json', 'w'))
print('edl_s: total frames', e['total_frames'])
