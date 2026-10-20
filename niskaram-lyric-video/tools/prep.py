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

def lyric_lines(proj):
    """The sung lines of the song, in order.  inputs/lyrics.txt (one line per row, blank rows ignored, no times needed)
    wins over inputs/lyrics.srt."""
    txt = ROOT / 'inputs' / 'lyrics.txt'
    if txt.exists():
        return [l.strip() for l in txt.read_text(encoding='utf8').replace('\ufeff', '').splitlines() if l.strip()]
    return [c['text'] for c in parse_srt(open(ROOT / proj['lyrics_srt'], encoding='utf8').read())]

def build_cues(proj, off):
    """Cue list in FILM time with per-word timing.  Word times come from inputs/words.json (tools/align_words.py);
    a cue whose text changed since the alignment falls back to an even split of its SRT window."""
    srt_path = ROOT / proj['lyrics_srt']
    srt = parse_srt(open(srt_path, encoding='utf8').read()) if srt_path.exists() else []
    if (ROOT / 'inputs' / 'lyrics.txt').exists() or not srt:
        srt = [{'start': 0, 'end': 0, 'text': t} for t in lyric_lines(proj)]
    wpath = ROOT / 'inputs' / 'words.json'
    aligned = {w['cue']: w for w in json.load(open(wpath))} if wpath.exists() else {}
    cues, fallback = [], []
    for i, c in enumerate(srt, 1):
        a = aligned.get(i)
        if a and a['text'] == c['text'] and len(a['words']) == len(c['text'].split()):
            words = [{'w': w['w'], 't0': round(w['t0'] + off, 3), 't1': round(w['t1'] + off, 3)} for w in a['words']]
            start, end = a['start'] + off, a['end'] + off
        else:
            fallback.append(i)
            ws = c['text'].split(); n = len(ws); d = max(c['end'] - c['start'], 0.5 * n)
            words = [{'w': w, 't0': round(c['start'] + off + d * k / n, 3), 't1': round(c['start'] + off + d * (k + 1) / n, 3)} for k, w in enumerate(ws)]
            start, end = c['start'] + off, c['end'] + off
        if end <= proj['song_in'] + off: continue
        cues.append({'start': round(start, 3), 'end': round(end, 3), 'text': c['text'], 'words': words})
    if fallback: print('! no word alignment for cue(s)', fallback, '- run tools/align_words.py (see README)')
    return cues

def main():
    proj = json.load(open(ROOT / 'project.json'))
    song_len = probe_duration(ROOT / 'inputs' / 'song.mp3')
    # film time = song time + song_offset
    off = proj['song_film_start'] - proj['song_in']
    proj['song_offset'] = round(off, 3)
    cues = build_cues(proj, off)
    proj['song_length'] = song_len
    proj['total_duration'] = round(proj['song_film_start'] + (song_len - proj['song_in']) + proj['end_extension'], 3)
    proj['cues'] = cues
    json.dump(proj, open(WORK / 'timeline.json', 'w'), ensure_ascii=False, indent=1)
    print(f'timeline: {proj["total_duration"]:.2f}s total, {len(cues)} lyric cues -> {WORK / "timeline.json"}')

if __name__ == '__main__':
    main()
