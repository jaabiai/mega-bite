"""Build and run the final ffmpeg graph for one time window (or a single PNG frame).

usage: final2.py --out file.mp4 [--ss 0 --t 30] [--crf 14] [--fast] [--noaudio]
Everything runs in 10-bit planar RGB until the very last conversion. Expressions use absolute timeline time
(window offset = --ss) so any window can be rendered for review and the full video can be rendered in parallel chunks.
Streams that only exist for a short scene are trimmed to that scene, so they cost nothing outside it.
"""
import argparse, json, subprocess, sys, os

B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--ss', type=float, default=0.0)
ap.add_argument('--t', type=float, default=0.0)
ap.add_argument('--crf', type=int, default=14)
ap.add_argument('--fast', action='store_true')
ap.add_argument('--audio', default=B + 'work/audio/final_mix.wav')
ap.add_argument('--noaudio', action='store_true')
ap.add_argument('--print', action='store_true')
a = ap.parse_args()
OFF = a.ss
FPS = 30
INS_T, DLT = 719 / 30, 84 / 30      # welcome stinger inserted at 23.967 s (2.8 s)
TOTAL = 206.6 + DLT


def sh(t):
    return t + DLT if t >= INS_T - 1e-6 else t

PNG = a.out.endswith('.png')
edl = json.load(open(B + 'work/edl_s.json'))['pieces']
WIN_END = (OFF + a.t) if a.t else TOTAL + 1

# ------------------------------------------------------------------ zoom (jump-cut punch-ins)
runs = []
for p in edl:
    runs.append(dict(t0=p['out_a'] / FPS, t1=p['out_b'] / FPS, a_src=p['a'], b_src=p['b']))
merged = []
for r in runs:     # pieces that are contiguous in the source form one run: one continuous slow push / pull
    if merged and abs(r['a_src'] - merged[-1]['b_src']) <= 1 and abs(r['t0'] - merged[-1]['t1']) < 1e-6:
        merged[-1]['t1'] = r['t1']
        merged[-1]['b_src'] = r['b_src']
    else:
        merged.append(dict(r))
STYLES = [(1.000, 1.040), (1.090, 1.120), (1.030, 1.000), (1.115, 1.085), (1.000, 1.035), (1.085, 1.115)]
zparts = [(r['t0'], r['t1']) + STYLES[i % len(STYLES)] for i, r in enumerate(merged)]


def zexpr(tv):
    e = '1'
    for t0, t1, z0, z1 in reversed(zparts):
        e = f"if(lt({tv},{t1:.4f}),{z0}+({z1 - z0:.4f})*max(0,{tv}-{t0:.4f})/{t1 - t0:.4f},{e})"
    return e


# ------------------------------------------------------------------ scene tables
SPLITS = [(sh(a), sh(b)) for a, b in [(104.9667, 129.1), (138.8, 152.3667), (155.9667, 170.9667)]]
DIMS = [(sh(a), sh(b), f) for a, b, f in [(152.3667, 155.60, 'bg_fake.png'), (200.0, 206.6, 'bg_end.png')]]
FADE = 0.35
STOCK = [  # file, clip start, out t0, out t1, mode, grade
    ('s_41165.mp4', 3.0, 8.30, 12.25, 'full', 'eq=brightness=-0.16:contrast=1.06:saturation=0.9'),
    ('s_42136.mp4', 0.3, 12.4667, 16.4, 'portrait', 'eq=brightness=-0.10:contrast=1.04:saturation=0.95'),
    ('s_46627.mp4', 3.5, 71.60, 75.00, 'full', 'eq=brightness=-0.10:contrast=1.10:saturation=1.0'),
    ('s_46639.mp4', 9.0, 75.10, 79.40, 'full', 'eq=brightness=-0.14:contrast=1.08:saturation=0.95'),
    ('s_47321.mp4', 3.0, 79.50, 83.30, 'full', 'eq=brightness=-0.14:contrast=1.08:saturation=0.95'),
    ('s_34838.mp4', 5.0, 83.5667, 87.2, 'full', 'eq=brightness=-0.20:contrast=1.10:saturation=0.9'),
]
STOCK = [(f, cs, sh(t0), sh(t1), m, g) for f, cs, t0, t1, m, g in STOCK]
SF = 0.22


def live(w0, w1):
    return w1 > OFF and w0 < WIN_END


# ------------------------------------------------------------------ inputs
inputs = []


def add_input(args):
    inputs.append(args)
    return len(inputs) - 1


PD = 6083 / FPS                       # plate length; later windows clone the last frame
PS = OFF if OFF < PD - 0.5 else PD - 0.5
i_plate = add_input(['-ss', f'{PS}', '-i', B + 'work/plate_all2.mov'])
i_logo = add_input(['-loop', '1', '-framerate', '30', '-i', B + 'overlay/assets/logo.png'])
i_mask = add_input(['-loop', '1', '-framerate', '30', '-i', B + 'overlay/assets/panel_mask.png'])
i_bgs = add_input(['-loop', '1', '-framerate', '30', '-i', B + 'overlay/assets/bg_split.png'])
i_bgd = {}
for d in DIMS:
    if live(d[0], d[1]):
        i_bgd[d[0]] = add_input(['-loop', '1', '-framerate', '30', '-i', B + 'overlay/assets/' + d[2]])
i_vig = add_input(['-loop', '1', '-framerate', '30', '-i', B + 'overlay/assets/vignette.png'])
i_ovl = add_input(['-framerate', '30', '-start_number', str(int(round(OFF * FPS))), '-i', B + 'overlay/seq2/%05d.png'])
stock_idx = []
for s in STOCK:
    f, cs, t0, t1, mode, g = s
    if not live(t0, t1):
        stock_idx.append(None)
        continue
    skip = max(0.0, OFF - t0)
    stock_idx.append(add_input(['-ss', f'{cs + skip:.3f}', '-t', f'{min(t1, WIN_END) - max(t0, OFF) + 0.1:.3f}', '-i', B + 'stock/vid/' + f]))
i_aud = None
if not a.noaudio and not PNG:
    i_aud = add_input(['-ss', f'{OFF}', '-i', a.audio])

tv_ = f"(t+{OFF})"
RGB = 'gbrp10le'
G = []
# ------------------------------------------------------------------ plate: punch-in, grade, vignette
PTRIM = f"trim=start={OFF - PS:.4f},setpts=PTS-STARTPTS," if PS != OFF else ''
G.append(f"[{i_plate}:v]fps={FPS},format=yuv422p10le,tpad=stop_mode=clone:stop_duration=8,{PTRIM}"
         f"scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=lanczos+accurate_rnd+full_chroma_int,format={RGB},"
         f"scale=w='trunc(iw*({zexpr(tv_)})/2)*2':h='trunc(ih*({zexpr(tv_)})/2)*2':eval=frame:flags=lanczos,"
         f"crop=1920:1080:x='(iw-1920)/2':y='(ih-1080)*0.25',setsar=1[z]")
CURVES = ("curves=r='0/0 0.12/0.10 0.30/0.275 0.50/0.50 0.74/0.785 0.90/0.935 1/1':"
          "g='0/0 0.12/0.098 0.30/0.272 0.50/0.50 0.74/0.775 0.90/0.925 1/1':"
          "b='0/0.012 0.12/0.125 0.30/0.292 0.50/0.495 0.74/0.755 0.90/0.905 1/0.985'")
G.append(f"[z]{CURVES},eq=saturation=1.06:gamma=0.97,noise=alls=3:allf=t+u,format={RGB}[pl0]")
G.append(f"[{i_vig}:v]format=rgba[vg]")
G.append(f"[pl0][vg]overlay=0:0:format=auto,format={RGB}[pl]")

win_split = [w for w in SPLITS if live(*w)]
win_dim = [d for d in DIMS if live(d[0], d[1])]


def win(w0, w1):
    return max(w0 - OFF, 0.0), w1 - OFF


def fade_chain(w0, w1, f):
    s0, s1 = w0 - OFF, w1 - OFF
    fin = f"fade=t=in:st={s0:.3f}:d={f}:alpha=1," if s0 >= 0 else ''
    return f"{fin}fade=t=out:st={max(s1 - f, 0):.3f}:d={f}:alpha=1"


n_sp = len(win_split)
if n_sp:
    G.append(f"[pl]split={n_sp + 1}[pa]" + ''.join(f"[pp{x}]" for x in range(n_sp)))
    G.append(f"[{i_mask}:v]format=gray,split={n_sp}" + ''.join(f"[mk{x}]" for x in range(n_sp)))
    G.append(f"[{i_bgs}:v]format={RGB},split={n_sp}" + ''.join(f"[bs{x}]" for x in range(n_sp)))
else:
    G.append("[pl]null[pa]")
cur = 'pa'
for x, w in enumerate(win_split):
    a0, a1 = win(*w)
    G.append(f"[pp{x}]trim=start={a0:.3f}:end={a1 + 0.05:.3f},crop=945:1080:488:0,scale=700:800:flags=lanczos,format=gbrap10le[pn0_{x}]")
    G.append(f"[mk{x}]trim=start={a0:.3f}:end={a1 + 0.05:.3f}[mkt{x}]")
    G.append(f"[pn0_{x}][mkt{x}]alphamerge[pn{x}]")
    G.append(f"[bs{x}]trim=start={a0:.3f}:end={a1 + 0.05:.3f}[bst{x}]")
    G.append(f"[bst{x}][pn{x}]overlay=60:70:format=auto,format=gbrap10le,{fade_chain(w[0], w[1], FADE)}[spf{x}]")
    G.append(f"[{cur}][spf{x}]overlay=0:0:format=auto:eof_action=pass,format={RGB}[ms{x}]")
    cur = f"ms{x}"
for x, d in enumerate(win_dim):
    a0, a1 = win(d[0], d[1])
    G.append(f"[{i_bgd[d[0]]}:v]trim=start={a0:.3f}:end={a1 + 0.05:.3f},format=gbrap10le,{fade_chain(d[0], d[1], 0.45)}[ddf{x}]")
    G.append(f"[{cur}][ddf{x}]overlay=0:0:format=auto:eof_action=pass,format={RGB}[md{x}]")
    cur = f"md{x}"

# ------------------------------------------------------------------ stock cutaways
n = 0
for s, idx in zip(STOCK, stock_idx):
    if idx is None:
        continue
    f, cs, t0, t1, mode, g = s
    t0e = max(t0, OFF)
    st = t0e - OFF
    fin = f"fade=t=in:st=0:d={SF}:alpha=1," if t0 >= OFF else ''
    fout = f"fade=t=out:st={max(t1 - t0e - SF, 0):.3f}:d={SF}:alpha=1" if t1 <= WIN_END else "null"
    src_fix = f"fps={FPS},scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=lanczos,format={RGB}"
    if mode == 'full':
        pre = f"{src_fix},scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,unsharp=5:5:0.35,{g},vignette=PI/4"
    else:   # portrait clip: blurred copy as backdrop + sharp card in the middle
        pre = (f"{src_fix},split[q1][q2];[q1]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,"
               f"scale=480:270:flags=bilinear,gblur=sigma=9,scale=1920:1080:flags=bicubic,{g},eq=brightness=-0.08[qb];"
               f"[q2]scale=-2:880:flags=lanczos,{g}[qf];[qb][qf]overlay=(W-w)/2:(H-h)/2:shortest=1")
    G.append(f"[{idx}:v]{pre},format=gbrap10le,{fin}{fout},setpts=PTS-STARTPTS+{st:.3f}/TB[s{n}]")
    G.append(f"[{cur}][s{n}]overlay=0:0:eof_action=pass:format=auto,format={RGB}[c{n}]")
    cur = f"c{n}"
    n += 1

# ------------------------------------------------------------------ watermark (under the html overlay) + html overlay + output conversion
LFADE = ",fade=t=in:st=0.2:d=0.6:alpha=1" if OFF < 0.01 else ""      # only the very first window fades the logo in
G.append(f"[{i_logo}:v]scale=120:120:flags=lanczos,format=rgba,colorchannelmixer=aa=0.93{LFADE}[lg]")
G.append(f"[{cur}][lg]overlay=x=W-w-44:y=34:format=auto,format={RGB}[o1]")
G.append(f"[{i_ovl}:v]format=rgba[ov]")
G.append(f"[o1][ov]overlay=0:0:format=auto,format={RGB}[o2]")
if PNG:
    G.append("[o2]scale=in_range=pc:out_range=pc:flags=lanczos,format=rgb24[vout]")
else:
    G.append("[o2]scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p,setsar=1[vout]")

gfile = B + f'work/final_graph_{os.getpid()}.txt'
open(gfile, 'w').write(';\n'.join(G))

cmd = ['ffmpeg', '-y', '-hide_banner', '-v', 'warning', '-stats']
for ia in inputs:
    cmd += ia
cmd += ['-filter_complex_script', gfile, '-map', '[vout]']
if i_aud is not None:
    cmd += ['-map', f'{i_aud}:a']
dur_total = a.t if a.t else TOTAL - OFF
cmd += ['-t', f'{dur_total:.4f}']
if not PNG:
    cmd += ['-frames:v', str(int(round(dur_total * FPS))), '-fps_mode', 'cfr']
if PNG:
    cmd += ['-frames:v', '1']
elif a.fast:
    cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20']
else:
    cmd += ['-threads', '3', '-c:v', 'libx264', '-preset', 'slow', '-crf', str(a.crf), '-maxrate', '38M', '-bufsize', '76M',
            '-profile:v', 'high', '-level:v', '4.2', '-bf', '3', '-refs', '4',
            '-x264-params', 'aq-mode=3:aq-strength=0.9:psy-rd=1.0,0.15:deblock=-1,-1:keyint=60:min-keyint=30']
if not PNG:
    cmd += ['-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv', '-r', str(FPS)]
if i_aud is not None:
    cmd += ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2']
cmd += ([] if PNG else ['-movflags', '+faststart']) + [a.out]
if a.print:
    print(' '.join(cmd))
    sys.exit(0)
print('running ffmpeg...', flush=True)
r = subprocess.run(cmd)
sys.exit(r.returncode)
