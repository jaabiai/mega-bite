#!/usr/bin/env python3
"""Vertical (9:16, 1080x1920, 30 fps) reels cut from the film.

  reels.py prep   [id]   reel.json (+ cues in reel time) for every reel
  reels.py audio  [id]   cut the song, fade, phone master      -> $WORK/reels/<id>/audio_master.wav
  reels.py shots  [id]   one 1080x1920 clip per shot           -> $WORK/reels/<id>/shots/
  reels.py base   [id]   xfade + grade + bloom + dust          -> $WORK/reels/<id>/base.mp4
  reels.py overlays [id] caption/hook/logo layer (headless Chromium) -> $WORK/reels/<id>/overlay/
  reels.py final  [id]   picture + overlay + grain + fades + audio -> output/<id>.mp4
  reels.py all    [id]

Picture: full-bleed 9:16.  Native vertical Mixkit clips wherever one exists for the line (moon, hourglass, sky, desert, waterfall,
candle, stars ...); mosque / prayer / Qur'an have no vertical clip on the free sites, so those landscape clips are reframed to a
9:16 slice.  No blurred bars.  Captions are the film's (one sung word at a time, Uroob, neon underline) but left-aligned in the
lower-left, above the reel interface.  Shot cuts snap to the strongest musical onsets.
"""
import json, os, pathlib, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, WORK, load_timeline, snap_to_onsets, shot_spans
import compose

CFG = json.load(open(ROOT / 'reels' / 'reels.json', encoding='utf8'))
W, H = CFG['size']; FPS = CFG['fps']
OUTPUT = ROOT / 'output'

def rdir(r):
    d = WORK / 'reels' / r['id']; d.mkdir(parents=True, exist_ok=True); return d

def sh(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)

def duration(r): return round(r['song_out'] - r['song_in'], 3)

# ---------------------------------------------------------------- prep
def reel_shots(r, tl):
    """Shot list in reel time, cuts snapped to musical onsets."""
    off = tl['song_offset'] if 'song_offset' in tl else 9.2
    film = [dict(s, t=s['song'] + off, anchor=(i == 0)) for i, s in enumerate(r['shots'])]
    film = snap_to_onsets(film, off, window=0.25)
    base = r['song_in'] + off
    out = []
    for s in film:
        s = dict(s); s['t'] = round(s['t'] - base, 3); s['trd'] = 0.0 if s['t'] <= 0.001 else s.get('trd', 0.6)
        out.append(s)
    return out

def prep(r, tl):
    off = tl.get('song_offset', 9.2); a, b = r['song_in'], r['song_out']
    cues = []
    for c in tl['cues']:
        ws = c['words']; t0, t1 = ws[0]['t0'] - off, ws[-1]['t1'] - off
        if t0 >= a - 0.01 and t1 <= b + 0.01:
            cues.append({'start': round(t0 - a, 3), 'end': round(t1 - a, 3), 'words': [{'w': w['w'], 't0': round(w['t0'] - off - a, 3), 't1': round(w['t1'] - off - a, 3)} for w in ws]})
    reel = {k: r[k] for k in ('capX', 'capY', 'capSize', 'capMaxW', 'hook', 'endStart', 'endY') if k in r}
    job = {'fps': FPS, 'duration': duration(r), 'reel': reel, 'cues': cues}
    json.dump(job, open(rdir(r) / 'reel.json', 'w', encoding='utf8'), ensure_ascii=False)
    json.dump(reel_shots(r, tl), open(rdir(r) / 'shots.json', 'w'))
    print(f"{r['id']}: {len(cues)} cues, {duration(r):.1f}s, shots at", [round(s['t'], 2) for s in reel_shots(r, tl)])

# ---------------------------------------------------------------- audio
def audio(r, tl):
    d = rdir(r); dur = duration(r)
    cut = d / 'audio_cut.wav'
    fi, fo = r.get('audio_fade_in', 0.5), r.get('audio_fade_out', 1.8)
    sh(['ffmpeg', '-v', 'error', '-y', '-ss', f"{r['song_in']:.3f}", '-t', f'{dur:.3f}', '-i', ROOT / 'inputs' / 'song.mp3',
        '-af', f"aresample=48000,aformat=channel_layouts=stereo,afade=t=in:st=0:d={fi},afade=t=out:st={dur - fo:.3f}:d={fo}:curve=qsin",
        '-c:a', 'pcm_s16le', cut])
    compose.master_audio(cut, d / 'audio_master.wav', tl)

# ---------------------------------------------------------------- shots
def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration', '-of', 'json', str(path)],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j['streams'][0]
    return int(s['width']), int(s['height']), float(j['format']['duration'])

def source_path(cid):
    """vsrc/ holds the vertical (and 1080p) downloads, src/ the original landscape library."""
    for d in ('vsrc', 'src'):
        f = WORK / d / f"{cid}.mp4"
        if f.exists(): return f
    raise FileNotFoundError(cid)

def build_shot(args):
    """Full-bleed 9:16 shot.  Native vertical clips are used as they are; landscape clips are reframed (a 9:16 slice
    around `cx`) - never shown with blurred bars.  A slow push (z0 -> z1) runs over every shot."""
    r, sp = args
    d = rdir(r); (d / 'shots').mkdir(exist_ok=True)
    src = source_path(sp['id'])
    w, h, dur = probe(src)
    need = sp['length']
    nframes = max(2, round(need * FPS))
    inp = sp['in']
    if inp + need > dur - 0.05:
        inp = max(0.0, dur - 0.05 - need)
    cx, cy = sp.get('cx', 0.5), sp.get('cy', 0.5)
    z0, z1 = sp.get('z0', 1.0), sp.get('z1', 1.08)
    zexpr = f"{z0}+({z1}-{z0})*on/{nframes - 1}"
    # a slice that is enlarged more than 1.4x gets a touch of sharpening
    slice_h = min(h, w * 16 / 9)
    sharp = ",unsharp=5:5:0.55:5:5:0.0" if slice_h < H / 1.4 else ""
    g = (f"[0:v]fps={FPS}:round=near,format=yuv420p,"
         f"crop=w='min(iw,ih*{W}/{H})':h='min(ih,iw*{H}/{W})':x='(iw-ow)*{cx}':y='(ih-oh)*{cy}',"
         f"scale={W * 2}:{H * 2}:flags=lanczos,"
         f"zoompan=z='{zexpr}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={FPS}{sharp},"
         f"format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv[out]")
    out = d / 'shots' / f"{sp['idx']:02d}_{sp['id']}.mp4"
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', f'{inp:.3f}', '-t', f'{need + 0.5:.3f}', '-i', src, '-an', '-filter_complex', g, '-map', '[out]',
           '-frames:v', str(nframes), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p',
           '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', str(FPS), out]
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if p.returncode != 0:
        print('FAILED', r['id'], sp['idx'], sp['id'], p.stderr[-500:], file=sys.stderr); return False
    return True

def shots(r, tl):
    prep(r, tl)
    d = rdir(r)
    spans = shot_spans(json.load(open(d / 'shots.json')), duration(r))
    json.dump(spans, open(d / 'spans.json', 'w'))
    with ThreadPoolExecutor(3) as ex:
        ok = list(ex.map(build_shot, [(r, s) for s in spans]))
    print(r['id'], 'shots', 'ok' if all(ok) else 'FAILED')
    if not all(ok): sys.exit(1)

# ---------------------------------------------------------------- base
LUT = f"lut3d=file='{WORK / 'cinema.cube'}':interp=tetrahedral"
GRADES = {   # picked on stills: the first two sit on the film's teal-gold LUT, 'bright' is LUT-free for an airy look
    'cold':   f"{LUT},eq=saturation=0.62:contrast=1.14:brightness=-0.02,colorbalance=rs=-0.03:gs=0.02:bs=0.04:rm=-0.05:gm=0.01:bm=0.03:rh=-0.06",
    'warm':   f"{LUT},colorbalance=rs=0.02:bs=-0.02:rm=0.04:bm=-0.05:rh=0.05:bh=-0.07,eq=saturation=1.05:contrast=1.06",
    'bright': "eq=saturation=1.08:contrast=1.05:brightness=0.01,colorbalance=rs=0.01:bs=-0.02:rm=0.02:bm=-0.03:rh=0.03:bh=-0.05",
}

def base(r, tl):
    d = rdir(r)
    spans = json.load(open(d / 'spans.json'))
    files = [d / 'shots' / f"{s['idx']:02d}_{s['id']}.mp4" for s in spans]
    n = len(files)
    cmd = ['ffmpeg', '-v', 'error', '-stats', '-y']
    for f in files: cmd += ['-i', f]
    ov = r.get('overlays', [])
    for o in ov: cmd += ['-stream_loop', '-1', '-i', WORK / 'src' / f"{o['id']}.mp4"]
    parts = [f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[v{i}]' for i in range(n)]
    prev = 'v0'
    for i in range(1, n):
        s = spans[i]; off = s['t'] - s['trd'] / 2
        tr = s['tr'] if s['tr'] != 'none' else 'fade'
        parts.append(f"[{prev}][v{i}]xfade=transition={tr}:duration={s['trd']:.3f}:offset={off:.3f}[x{i}]")
        prev = f'x{i}'
    bloom = r.get('bloom', 0.22)
    g = (f"[{prev}]format=gbrp,{GRADES[r['grade']]},format=gbrp,split=2[g1][g2];"
         f"[g2]scale={W // 4}:{H // 4}:flags=area,curves=all='0/0 0.70/0.0 0.88/0.40 1/1',gblur=sigma=5:steps=2,"
         f"scale={W}:{H}:flags=bicubic,colorchannelmixer=rr=1:gg=0.86:bb=0.62,format=gbrp[bl];"
         f"[g1][bl]blend=all_mode=screen:all_opacity={bloom}[b0]")
    parts.append(g)
    cur = 'b0'   # NB: both blend inputs are forced to gbrp: a screen blend on YUV planes pushes chroma towards purple
    for k, o in enumerate(ov):
        rr, gg, bb = o['mix'].split(':')
        parts.append(f"[{n + k}:v]scale=-2:{H}:flags=bicubic,crop={W}:{H},format=gbrp,colorchannelmixer=rr={rr}:gg={gg}:bb={bb},format=gbrp[ov{k}]")
        parts.append(f"[{cur}][ov{k}]blend=all_mode=screen:all_opacity={o['opacity']}:shortest=1[b{k + 1}]")
        cur = f'b{k + 1}'
    parts.append(f"[{cur}]vignette=angle=PI/{r.get('vig', 6)},format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv[vout]")
    script = d / 'base_graph.txt'; script.write_text(';\n'.join(parts))
    cmd += ['-filter_complex_script', script, '-map', '[vout]', '-t', f'{duration(r):.3f}', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14',
            '-pix_fmt', 'yuv420p', '-r', FPS, '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', d / 'base.mp4']
    compose.run(cmd)

# ---------------------------------------------------------------- overlays + final
def overlays(r, tl, workers=4, only=None):
    d = rdir(r); prep(r, tl)
    cmd = ['node', ROOT / 'tools' / 'render_reel_overlays.mjs', d, str(workers)]
    if only: cmd += ['--frames', only]
    sh(cmd)

def final(r, tl):
    d = rdir(r); dur = duration(r)
    out = OUTPUT / f"{r['id']}{os.environ.get('OUT_SUFFIX', '')}.mp4"
    fg = (f"[1:v]format=rgba[ov];[0:v][ov]overlay=0:0:format=auto:eof_action=pass,noise=alls={r.get('noise', 6)}:allf=t+u,"
          f"fade=t=in:st=0:d=0.5,fade=t=out:st={dur - 1.2:.2f}:d=1.2,format=yuv420p,"
          f"setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv[vout]")
    compose.run(['ffmpeg', '-v', 'error', '-stats', '-y', '-i', d / 'base.mp4', '-framerate', FPS, '-i', d / 'overlay' / 'ov_%06d.png', '-i', d / 'audio_master.wav',
                 '-filter_complex', fg, '-map', '[vout]', '-map', '2:a', '-t', f'{dur:.3f}',
                 '-c:v', 'libx264', '-preset', 'slow', '-crf', os.environ.get('CRF', '17'), '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                 '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                 '-c:a', 'aac', '-b:a', '320k', *compose.AAC_SAFE, '-ar', '48000', '-movflags', '+faststart', out])
    print('wrote', out, f'{out.stat().st_size / 1e6:.1f} MB')

STEPS = {'prep': lambda r, tl: prep(r, tl), 'audio': audio, 'shots': shots, 'base': base, 'overlays': overlays, 'final': final}

def main():
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    which = sys.argv[2] if len(sys.argv) > 2 else None
    tl = load_timeline()
    for r in CFG['reels']:
        if which and r['id'] != which: continue
        for step in (['audio', 'shots', 'base', 'overlays', 'final'] if what == 'all' else [what]):
            print(f"== {r['id']}: {step}", flush=True)
            STEPS[step](r, tl)

if __name__ == '__main__':
    main()
