"""Render the v3 video as scene-aligned, frame-exact segments (3 in parallel), then join them losslessly."""
import subprocess, sys, os, time, json
from concurrent.futures import ThreadPoolExecutor
B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
FPS = 30
SC = json.load(open(B + 'work3/scenes.json'))
NF = int(round(SC['total'] * FPS))
pts = {0, NF}
for s in SC['scenes']:
    pts |= {int(round(s['t0'] * FPS)), min(int(round(s['t1'] * FPS)), NF)}
    if s.get('broll'):
        pts |= {int(round(s['broll']['t0'] * FPS)), int(round(s['broll']['t1'] * FPS))}
pts = sorted(p for p in pts if 0 <= p <= NF)
BP = [pts[0]]
for a, b in zip(pts, pts[1:]):
    n = -(-(b - a) // 540)
    for k in range(1, n + 1):
        BP.append(a + (b - a) * k // n)
segs = [(i, BP[i], BP[i + 1]) for i in range(len(BP) - 1)]
if '--list' in sys.argv:
    print(len(segs), segs); sys.exit(0)
os.makedirs(B + 'work3/seg', exist_ok=True)
extra = [x for x in sys.argv[1:] if x != '--list']


def run(seg):
    i, a, b = seg
    out = B + f'work3/seg/s{i:02d}.mp4'
    cmd = ['python3', '-I', B + 'scripts/final3.py', '--out', out, '--ss', f'{a / FPS:.6f}', '--t', f'{(b - a) / FPS:.6f}', '--noaudio'] + extra
    t = time.time()
    for attempt in range(3):
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=open(B + f'work3/seg/s{i:02d}.log', 'w'))
        if r.returncode == 0:
            break
        print(f'segment {i:02d} attempt {attempt + 1} failed rc={r.returncode}, retrying', flush=True)
    print(f'segment {i:02d} frames {a}-{b} rc={r.returncode} {time.time() - t:.0f}s', flush=True)
    return r.returncode


order = sorted(segs, key=lambda s: -(s[2] - s[1]))
with ThreadPoolExecutor(3) as ex:
    rcs = list(ex.map(run, order))
print('all rc:', rcs)
if any(rcs):
    sys.exit(1)
with open(B + 'work3/seg/list.txt', 'w') as f:
    for i, _, _ in segs:
        f.write(f"file '{B}work3/seg/s{i:02d}.mp4'\n")
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', B + 'work3/seg/list.txt', '-c', 'copy', B + 'work3/video_only.mp4'], check=True)
print('joined')
