#!/usr/bin/env python3
"""Assemble the film.

  compose.py audio   mix adhan intro + song  ->  $WORK/audio.wav
  compose.py base    xfade the shots, colour grade, bloom, dust, vignette ->  $WORK/base.mp4
  compose.py final   overlays (credits/title/lyrics/end card) + logo bug + grain + fades + audio -> output/*.mp4
  compose.py all
"""
import json, os, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, WORK, load_timeline, load_edl, shot_spans

W, H, FPS = 1920, 804, 24
OUTPUT = ROOT / 'output'; OUTPUT.mkdir(exist_ok=True)

def run(cmd, **kw):
    print('$', ' '.join(str(c) for c in cmd)[:400], flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)

# ---------------------------------------------------------------- audio
def build_audio(tl):
    """Adhan (first call only) -> song without its humming intro.

    * adhan: kept up to `adhan_keep`, eased out and given a short echo tail so it does not stop dead
    * song : starts at `song_in` (just before the first verse), placed at `song_film_start`,
             with a quick fade-in so it blooms out of the adhan's tail
    """
    keep, s_in, s_at, total = tl['adhan_keep'], tl['song_in'], tl['song_film_start'], tl['total_duration']
    fade = 0.55
    fg = (
        f"[0:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{keep:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={keep - fade:.3f}:d={fade}:curve=qsin,apad=pad_dur=1.6,"
        f"aecho=0.85:0.7:85|170|290:0.42|0.30|0.18,afade=t=out:st={keep + 0.2:.3f}:d=1.4[ad];"
        f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=start={s_in:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:d=0.28:curve=qsin,adelay={int(round(s_at * 1000))}|{int(round(s_at * 1000))}[sg];"
        f"[ad][sg]amix=inputs=2:normalize=0:duration=longest,apad=whole_dur={total},"
        f"afade=t=out:st={total - 2.6:.3f}:d=2.6,alimiter=limit=0.97[out]"
    )
    run(['ffmpeg', '-v', 'error', '-y', '-i', ROOT / 'inputs' / 'adhan_intro.m4a', '-i', ROOT / 'inputs' / 'song.mp3',
         '-filter_complex', fg, '-map', '[out]', '-t', f'{total:.3f}', '-c:a', 'pcm_s16le', WORK / 'audio.wav'])

# ---------------------------------------------------------------- base picture
def build_base(tl, edl):
    spans = shot_spans(edl['shots'], tl['total_duration'])
    files = [WORK / 'shots' / f"{s['idx']:03d}_{s['id']}.mp4" for s in spans]
    missing = [f for f in files if not f.exists()]
    if missing:
        sys.exit(f'missing shot renders, run make_shots.py first: {missing[:3]}')
    dust_id = next(o['id'] for o in edl['overlays'] if o['role'] == 'dust')
    cmd = ['ffmpeg', '-v', 'error', '-stats', '-y']
    for f in files: cmd += ['-i', f]
    cmd += ['-stream_loop', '-1', '-i', WORK / 'src' / f'{dust_id}.mp4']
    n = len(files)
    parts = [f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[v{i}]' for i in range(n)]
    prev = 'v0'
    white_windows = []
    for i in range(1, n):
        s = spans[i]
        off = s['t'] - s['trd'] / 2
        tr = s['tr'] if s['tr'] != 'none' else 'fade'
        if tr == 'fadewhite':
            white_windows.append((off, off + s['trd']))
        parts.append(f"[{prev}][v{i}]xfade=transition={tr}:duration={s['trd']:.3f}:offset={off:.3f}[x{i}]")
        prev = f'x{i}'
    warm = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in white_windows) or '0'
    grade = (
        f"[{prev}]format=gbrp,lut3d=file='{WORK / 'cinema.cube'}':interp=tetrahedral,"
        f"colorbalance=rm=0.05:bm=-0.14:rh=0.12:gh=0.04:bh=-0.30:enable='{warm}',"
        f"split=2[g1][g2];"
        f"[g2]scale=480:201:flags=area,curves=all='0/0 0.70/0.0 0.88/0.40 1/1',gblur=sigma=6.5:steps=2,"
        f"scale={W}:{H}:flags=bicubic,colorchannelmixer=rr=1:gg=0.86:bb=0.62[bl];"
        f"[g1][bl]blend=all_mode=screen:all_opacity=0.24[b1];"
        f"[{n}:v]scale=1920:1080:flags=bicubic,crop=1920:{H},format=gbrp,"
        f"colorchannelmixer=rr=1:gg=0.80:bb=0.42[dust];"
        f"[b1][dust]blend=all_mode=screen:all_opacity=0.13:shortest=1,"
        f"vignette=angle=PI/7.5,format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv[vout]"
    )
    script = WORK / 'base_graph.txt'
    script.write_text(';\n'.join(parts + [grade]))
    cmd += ['-filter_complex_script', script, '-map', '[vout]', '-t', f"{tl['total_duration']:.3f}", '-an',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '13', '-pix_fmt', 'yuv420p', '-r', FPS,
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', WORK / 'base.mp4']
    run(cmd)

# ---------------------------------------------------------------- overlays + finish
def make_bug(tl):
    from PIL import Image, ImageFilter
    size = tl['logo']['bug_size']
    badge = Image.open(ROOT / 'inputs' / 'logo_badge.png').convert('RGBA')
    ss = 4
    big = badge.resize((size * ss, size * ss), Image.LANCZOS)
    pad = 28
    canvas = Image.new('RGBA', (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    mask = big.split()[3].resize((size, size), Image.LANCZOS)
    blk = Image.new('RGBA', (size, size), (0, 0, 0, 150)); blk.putalpha(mask.point(lambda v: int(v * 0.6)))
    shadow.alpha_composite(blk, (pad, pad + 3)); shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(big.resize((size, size), Image.LANCZOS), (pad, pad))
    out = WORK / 'bug.png'; canvas.save(out); return out, pad

def make_overlay_list(tl):
    meta = json.load(open(WORK / 'overlay' / 'frames.json'))
    frames = set(meta['frames']); total_frames = round(tl['total_duration'] * FPS)
    from PIL import Image
    blank = WORK / 'overlay' / 'blank.png'
    Image.new('RGBA', (W, H), (0, 0, 0, 0)).save(blank)
    lines = ['ffconcat version 1.0']
    d = 1.0 / FPS
    f = 0
    while f < total_frames:
        if f in frames:
            lines += [f"file 'ov_{f:06d}.png'", f'duration {d:.6f}']; f += 1
        else:
            g = f
            while g < total_frames and g not in frames: g += 1
            lines += [f"file 'blank.png'", f'duration {(g - f) * d:.6f}']; f = g
    lines += [f"file 'blank.png'"]
    lst = WORK / 'overlay' / 'list.ffconcat'; lst.write_text('\n'.join(lines) + '\n'); return lst

def build_final(tl, out_name):
    total = tl['total_duration']
    lst = make_overlay_list(tl)
    bug, pad = make_bug(tl)
    bw = tl['logo']['bug_size'] + 2 * pad
    mx, my = tl['logo']['bug_margin']
    bug_end = tl['end_credits']['logo_card_start'] - 0.8
    fg = (
        f"[1:v]fps={FPS},format=rgba[ov];"
        f"[2:v]format=rgba,fade=t=in:st=0.9:d=0.9:alpha=1,fade=t=out:st={bug_end:.2f}:d=0.8:alpha=1,"
        f"colorchannelmixer=aa={tl['logo']['bug_opacity']}[bug];"
        f"[0:v][ov]overlay=0:0:format=auto:eof_action=pass[v1];"
        f"[v1][bug]overlay=x=W-w-{mx - pad}:y={my - pad}:format=auto:eof_action=pass,"
        f"noise=alls=4:allf=t+u,"
        f"fade=t=in:st=0:d=1.6,fade=t=out:st={total - 1.9:.2f}:d=1.9,"
        f"format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv[vout]"
    )
    out = OUTPUT / out_name
    base = pathlib.Path(os.environ.get('BASE', WORK / 'base.mp4'))
    length = float(os.environ.get('TEST_SECONDS', total))      # TEST_SECONDS renders only the head of the film
    run(['ffmpeg', '-v', 'error', '-stats', '-y',
         '-i', base,
         '-f', 'concat', '-safe', '0', '-i', lst,
         '-framerate', FPS, '-loop', '1', '-t', f'{total:.3f}', '-i', bug,
         '-i', WORK / 'audio.wav',
         '-filter_complex', fg, '-map', '[vout]', '-map', '3:a', '-t', f'{length:.3f}',
         '-c:v', 'libx264', '-preset', 'slow', '-crf', os.environ.get('CRF', '18'), '-profile:v', 'high', '-pix_fmt', 'yuv420p',
         '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
         '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-movflags', '+faststart', out])
    print('wrote', out, f'{out.stat().st_size / 1e6:.1f} MB')

def main():
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    tl, edl = load_timeline(), load_edl()
    if what in ('audio', 'all'): build_audio(tl)
    if what in ('base', 'all'): build_base(tl, edl)
    if what in ('final', 'all'): build_final(tl, os.environ.get('OUT_NAME', 'niskaram_haya_alas_salah_lyric_video_2.39x1.mp4'))

if __name__ == '__main__':
    main()
