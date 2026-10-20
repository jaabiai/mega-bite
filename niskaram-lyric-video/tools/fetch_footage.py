#!/usr/bin/env python3
"""Download the Mixkit clips referenced in edl.json into $WORK/src.

Mixkit clips are free for commercial and non-commercial use (Mixkit Video
License, no attribution required).  We take the 1080p rendition when it is
reasonably small, otherwise 720p.
"""
import json, os, pathlib, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work'))
SRC = WORK / 'src'; SRC.mkdir(parents=True, exist_ok=True)
MAX_1080 = 70 * 1024 * 1024

def head_len(url):
    r = subprocess.run(['curl', '-sS', '-I', '-m', '30', '-o', '/dev/null', '-w', '%{http_code} %header{content-length}', url],
                       capture_output=True, text=True)
    parts = r.stdout.split()
    if parts and parts[0] == '200' and len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return None

def fetch(cid):
    dst = SRC / f'{cid}.mp4'
    if dst.exists() and dst.stat().st_size > 100_000:
        return cid, 'cached'
    for q in ('1080', '720', '360'):
        url = f'https://assets.mixkit.co/videos/{cid}/{cid}-{q}.mp4'
        n = head_len(url)
        if n is None or (q == '1080' and n > MAX_1080):
            continue
        tmp = dst.with_suffix('.part')
        r = subprocess.run(['curl', '-sS', '-f', '-m', '900', '-o', str(tmp), url])
        if r.returncode == 0:
            tmp.rename(dst)
            return cid, f'{q}p {n/1e6:.1f}MB'
    return cid, 'FAILED'

if __name__ == '__main__':
    edl = json.load(open(ROOT / 'edl.json'))
    ids = sorted(i for i in {s['id'] for s in edl['shots']} | {o['id'] for o in edl.get('overlays', [])} if i < 900000)   # 9000xx = stills, see fetch_stills.py
    with ThreadPoolExecutor(6) as ex:
        for cid, status in ex.map(fetch, ids):
            print(cid, status, flush=True)
