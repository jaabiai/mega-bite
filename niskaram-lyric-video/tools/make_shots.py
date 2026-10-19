#!/usr/bin/env python3
"""Render every EDL shot to a normalised 2.39:1 intermediate (1920x804, 24 fps) with a slow
push/pull + pan.  Usage: make_shots.py [--only idx,idx] [--jobs 4]"""
import json, os, subprocess, sys, pathlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, WORK, load_timeline, load_edl, shot_spans

W, H, FPS = 1920, 804, 24
OUT = WORK / 'shots'; OUT.mkdir(parents=True, exist_ok=True)

def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:format=duration',
                        '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j['streams'][0]
    n, d = s['r_frame_rate'].split('/')
    return int(s['width']), int(s['height']), float(n) / float(d), float(j['format']['duration'])

def build(sp):
    src = WORK / 'src' / f"{sp['id']}.mp4"
    w, h, fps, dur = probe(src)
    speed = sp.get('speed', 1.0)
    need_src = sp['length'] * speed
    nframes = max(2, round(sp['length'] * FPS))
    inp = sp['in']
    if inp + need_src > dur - 0.05:           # clamp so we never run off the end of the clip
        inp = max(0.0, dur - 0.05 - need_src)
        if inp == 0.0 and need_src > dur:
            print(f"  ! shot {sp['idx']} ({sp['id']}) needs {need_src:.2f}s but clip is {dur:.2f}s -> will freeze last frame", file=sys.stderr)
    cy = sp.get('cy', 0.5)
    strip_h = f"iw*{H}/{W}"
    z0, z1 = sp.get('z0', 1.0), sp.get('z1', 1.06)
    px0, px1 = sp.get('px0', 0.0), sp.get('px1', 0.0)
    zexpr = f"{z0}+({z1}-{z0})*on/{nframes - 1}"
    pxexpr = f"({px0}+({px1}-{px0})*on/{nframes - 1})"
    vf = (f"setpts=PTS/{speed},fps={FPS}:round=near,"
          f"crop=w=iw:h={strip_h}:x=0:y=(ih-{strip_h})*{cy},"
          f"scale={W * 2}:{H * 2}:flags=lanczos,"
          f"zoompan=z='{zexpr}':x='(iw-iw/zoom)/2*(1+{pxexpr})':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    if 'eq' in sp:
        vf = vf.replace(',format=yuv420p', f",eq={sp['eq']},format=yuv420p")
    vf += ",setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv"
    out = OUT / f"{sp['idx']:03d}_{sp['id']}.mp4"
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', f'{inp:.3f}', '-t', f'{need_src + 0.5:.3f}', '-i', str(src), '-an', '-vf', vf,
           '-frames:v', str(nframes), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', str(FPS), str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('FAILED', sp['idx'], sp['id'], r.stderr[-600:], file=sys.stderr); return sp['idx'], False
    return sp['idx'], True

def main():
    tl = load_timeline(); edl = load_edl()
    spans = shot_spans(edl['shots'], tl['total_duration'])
    only = None
    if '--only' in sys.argv: only = {int(x) for x in sys.argv[sys.argv.index('--only') + 1].split(',')}
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4
    todo = [s for s in spans if only is None or s['idx'] in only]
    with ThreadPoolExecutor(jobs) as ex:
        for idx, ok in ex.map(build, todo):
            print(f'shot {idx:02d}', 'ok' if ok else 'FAILED', flush=True)

if __name__ == '__main__':
    main()
