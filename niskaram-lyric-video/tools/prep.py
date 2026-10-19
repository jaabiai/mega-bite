#!/usr/bin/env python3
"""Resolve the project timeline: SRT cues -> video time, total duration, adhan splice, etc.
Writes $WORK/timeline.json (read by the overlay renderer and the composer)."""
import json, os, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get('WORK', ROOT / 'work')); WORK.mkdir(parents=True, exist_ok=True)

def probe_duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())

def parse_srt(text):
    text = text.replace('﻿', '').replace('\r\n', '\n').replace('\r', '\n')
    cues = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = [l for l in block.split('\n') if l.strip() != '']
        if len(lines) < 2:
            continue
        i = 0
        if re.fullmatch(r'\d+', lines[0].strip()):
            i = 1
        m = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', lines[i])
        if not m:
            continue
        g = list(map(int, m.groups()))
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 10 ** len(m.group(4))
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 10 ** len(m.group(8))
        cues.append({'start': start, 'end': end, 'text': ' '.join(l.strip() for l in lines[i + 1:])})
    return cues

def main():
    proj = json.load(open(ROOT / 'project.json'))
    song_len = probe_duration(ROOT / 'inputs' / 'song.mp3')
    off = proj['song_offset']
    cues = [{'start': round(c['start'] + off, 3), 'end': round(c['end'] + off, 3), 'text': c['text']}
            for c in parse_srt(open(ROOT / proj['lyrics_srt'], encoding='utf8').read())]
    proj['song_length'] = song_len
    proj['total_duration'] = round(off + song_len + proj['end_extension'], 3)
    proj['cues'] = cues
    json.dump(proj, open(WORK / 'timeline.json', 'w'), ensure_ascii=False, indent=1)
    print(f'timeline: {proj["total_duration"]:.2f}s total, {len(cues)} lyric cues -> {WORK / "timeline.json"}')

if __name__ == '__main__':
    main()
