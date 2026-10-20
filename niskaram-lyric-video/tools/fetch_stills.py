#!/usr/bin/env python3
"""Download the still images listed in stills/sources.json into $WORK/stills (Met Open Access = CC0; Wikimedia Commons = public domain).
Then `python3 tools/still_clip.py stills/spec_film.json` and `... stills/spec_reels.json` turn them into camera-move clips."""
import json, os, pathlib, subprocess, sys, time, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work')); OUT = WORK / 'stills'; OUT.mkdir(parents=True, exist_ok=True)
UA = 'MirayaFootageResearch/1.0 (contact: www.jaabi@gmail.com)'

def curl(url, out):
    for k in range(6):
        r = subprocess.run(['curl', '-sS', '-f', '-m', '180', '-A', UA, '-o', str(out), url], capture_output=True)
        if r.returncode == 0: return True
        time.sleep(20 * (k + 1))
    return False

def commons_url(title, width):
    q = urllib.parse.urlencode({'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': width, 'format': 'json'})
    for k in range(6):
        r = subprocess.run(['curl', '-sS', '-m', '40', '-A', UA, f'https://commons.wikimedia.org/w/api.php?{q}'], capture_output=True, text=True)
        try:
            ii = list(json.loads(r.stdout)['query']['pages'].values())[0]['imageinfo'][0]; return ii.get('thumburl') or ii['url']
        except Exception: time.sleep(30 * (k + 1))
    raise SystemExit('Commons API not answering (rate limit?) - retry later')

if __name__ == '__main__':
    done = set()
    for k, v in json.load(open(ROOT / 'stills' / 'sources.json', encoding='utf8')).items():
        dst = OUT / v['file']
        if v['file'] in done or (dst.exists() and dst.stat().st_size > 50_000): continue
        url = v['url'] if 'url' in v else commons_url(v['commons_title'], v['width'])
        print(k, v['title'], '<-', url[:80], flush=True)
        if not curl(url, dst): sys.exit(f'download failed: {k}')
        done.add(v['file']); time.sleep(2)
