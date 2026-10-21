"""Final graph v3: new animated background + speaker cut-out (shifted right) + B-roll + html overlay + logo.
usage: final3.py --out file.mp4 [--ss 0 --t 30] [--crf 14] [--fast] [--noaudio] ; --out x.png renders the first frame of the window.
Everything runs in 10-bit planar RGB until the last conversion; expressions use absolute timeline time (window offset = --ss)."""
import argparse, json, subprocess, sys, os

B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--ss', type=float, default=0.0)
ap.add_argument('--t', type=float, default=0.0)
ap.add_argument('--crf', type=int, default=14)
ap.add_argument('--fast', action='store_true')
ap.add_argument('--audio', default=B + 'work3/audio/final_mix.wav')
ap.add_argument('--noaudio', action='store_true')
ap.add_argument('--print', action='store_true')
ap.add_argument('--passthrough', action='store_true')
a = ap.parse_args()
OFF = a.ss
FPS = 30
SC = json.load(open(B + 'work3/scenes.json'))
TOTAL = SC['total']
PNG = a.out.endswith('.png')
WIN_END = (OFF + a.t) if a.t else TOTAL + 1
NSRC = 5123
PD = NSRC / FPS                                   # speaker material length; later windows clone the last frame
SHIFT = 330                                       # speaker moves right to make room for the captions
AX, AY = 960, 330                                 # zoom anchor in the speaker layer


def live(w0, w1):
    return w1 > OFF and w0 < WIN_END


# ------------------------------------------------------------------ jump-cut smoothing: alternating punch-in + impact at every cut
cuts = [c / FPS for c in json.load(open(B + 'work3/cuts.json'))['cuts']]
shots = [0.0] + cuts + [TOTAL + 10]
BASES = [1.000, 1.060]
zparts = []
for i in range(len(shots) - 1):
    z0 = BASES[i % 2]
    zparts.append((shots[i], shots[i + 1], z0, z0 + 0.025))      # slow push inside the shot


def zexpr(tv):
    e = '1'
    for t0, t1, z0, z1 in reversed(zparts):
        imp = f"+0.045*exp(-({tv}-{t0:.4f})/0.11)" if t0 > 0 else ''
        e = f"if(lt({tv},{t1:.4f}),{z0}+({z1 - z0:.4f})*({tv}-{t0:.4f})/{t1 - t0:.4f}{imp},{e})"
    return e


hide = [(s['t0'], s['t1']) for s in SC['scenes']]
hexpr = '1-(' + '+'.join(f"gte(T,{a0 - 0.001:.4f})*lt(T,{a1 - 0.001:.4f})" for a0, a1 in hide if live(a0, a1)) + ')' if any(live(*h) for h in hide) else '1'
hexpr = hexpr.replace('T', '(t+%s)' % OFF)

# ------------------------------------------------------------------ inputs
inputs = []


def add_input(args):
    inputs.append(args)
    return len(inputs) - 1


i_bg = add_input(['-stream_loop', '-1', '-ss', f'{OFF % 20:.4f}', '-i', B + 'work3/bgloop.mov'])
PS = OFF if OFF < PD - 0.5 else PD - 0.5
i_per = add_input(['-ss', f'{PS}', '-i', B + 'work3/person_all.mov'])
i_alp = add_input(['-ss', f'{PS}', '-i', B + 'work3/alpha_v2.mkv'])
i_logo = add_input(['-loop', '1', '-framerate', '30', '-i', B + 'overlay3/assets/logo.png'])
i_vig = add_input(['-loop', '1', '-framerate', '30', '-i', B + 'overlay/assets/vignette.png'])
i_col = add_input(['-f', 'lavfi', '-i', 'color=c=0x2D8CFF:s=1920x1080:r=30'])
i_ovl = add_input(['-thread_queue_size', '512', '-framerate', '30', '-start_number', str(int(round(OFF * FPS))), '-i', B + 'overlay3/seq/%05d.png'])
brolls = []
for s in SC['scenes']:
    br = s.get('broll')
    if not br or not live(br['t0'], br['t1']):
        continue
    skip = max(0.0, OFF - br['t0'])
    idx = add_input(['-ss', f"{br['start'] + skip:.3f}", '-t', f"{min(br['t1'], WIN_END) - max(br['t0'], OFF) + 0.1:.3f}", '-i', B + 'stock/vid/' + br['file']])
    brolls.append((idx, br))
i_aud = None
if not a.noaudio and not PNG:
    i_aud = add_input(['-ss', f'{OFF}', '-i', a.audio])

tv_ = f"(t+{OFF})"
RGB = 'gbrp10le'
G = []
# ------------------------------------------------------------------ speaker layer (premultiplied, colour-decontaminated) + alpha
PTRIM = f"trim=start={OFF - PS:.4f},setpts=PTS-STARTPTS," if PS != OFF else ''
CURVES = ("curves=r='0/0 0.12/0.10 0.30/0.275 0.50/0.50 0.74/0.785 0.90/0.935 1/1':"
          "g='0/0 0.12/0.098 0.30/0.272 0.50/0.50 0.74/0.775 0.90/0.925 1/1':"
          "b='0/0.010 0.12/0.125 0.30/0.292 0.50/0.495 0.74/0.755 0.90/0.905 1/0.985'")
G.append(f"[{i_per}:v]fps={FPS},format=yuv422p10le,tpad=stop_mode=clone:stop_duration=8,{PTRIM}"
         f"scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=lanczos+accurate_rnd+full_chroma_int,format={RGB},"
         f"{CURVES},eq=saturation=1.06:gamma=0.97[pc]")
G.append(f"[{i_alp}:v]fps={FPS},format=gray,tpad=stop_mode=clone:stop_duration=8,{PTRIM}format=gray[al]")
G.append("[pc][al]alphamerge,format=gbrap10le[pa]")
G.append(f"[pa]scale=w='trunc(iw*({zexpr(tv_)})/2)*2':h='trunc(ih*({zexpr(tv_)})/2)*2':eval=frame:flags=lanczos,"
         f"crop=1920:1080:x='{AX}*(iw/1920-1)':y='{AY}*(ih/1080-1)',setsar=1,format=gbrap10le,split[pers][pg]")
# blue rim / aura from the alpha of the zoomed speaker
G.append("[pg]alphaextract,scale=480:270:flags=bilinear,gblur=sigma=7,lut=y='val*0.62',scale=1920:1080:flags=bicubic,format=gray[gal]")
G.append(f"[{i_col}:v]format=gbrp10le[colr]")
G.append("[colr][gal]alphamerge,format=gbrap10le[glow]")

# ------------------------------------------------------------------ background + speaker
G.append(f"[{i_bg}:v]fps={FPS},scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=lanczos+accurate_rnd+full_chroma_int,format={RGB}[bg]")
G.append(f"[bg][glow]overlay=x={SHIFT}:y=0:format=auto:enable='{hexpr}',format={RGB}[b1]")
G.append(f"[b1][pers]overlay=x={SHIFT}:y=0:format=auto:enable='{hexpr}',format={RGB}[b2]")
G.append(f"[{i_vig}:v]format=rgba[vg]")
G.append(f"[b2][vg]overlay=0:0:format=auto,format={RGB}[cur0]")
cur = 'cur0'

# ------------------------------------------------------------------ B-roll cut-aways (full frame, graded; portrait clips as a card on a blurred backdrop)
for n, (idx, br) in enumerate(brolls):
    t0e = max(br['t0'], OFF)
    st = t0e - OFF
    src_fix = f"fps={FPS},scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=lanczos,format={RGB}"
    g = br['grade']
    if br['mode'] == 'full':
        pre = f"{src_fix},scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,unsharp=5:5:0.35,{g},vignette=PI/4"
    else:
        cx = br.get('cx', 960)
        pre = (f"{src_fix},split[q1][q2];[q1]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,"
               f"scale=480:270:flags=bilinear,gblur=sigma=9,scale=1920:1080:flags=bicubic,{g},eq=brightness=-0.10[qb];"
               f"[q2]scale=-2:880:flags=lanczos,{g}[qf];[qb][qf]overlay={cx}-w/2:(H-h)/2:shortest=1")
    G.append(f"[{idx}:v]{pre},format={RGB},setpts=PTS-STARTPTS+{st:.3f}/TB[s{n}]")
    G.append(f"[{cur}][s{n}]overlay=0:0:eof_action=pass:format=auto,format={RGB}[c{n}]")
    cur = f"c{n}"

# ------------------------------------------------------------------ html overlay, grain, logo
G.append(f"[{i_ovl}:v]format=rgba[ov]")
G.append(f"[{cur}]noise=alls=2:allf=t+u,format={RGB}[gr]")
G.append(f"[gr][ov]overlay=0:0:format=auto,format={RGB}[o1]")
LFADE = ",fade=t=in:st=0.2:d=0.6:alpha=1" if OFF < 0.01 else ""
G.append(f"[{i_logo}:v]scale=120:120:flags=lanczos,format=rgba,colorchannelmixer=aa=0.95{LFADE}[lg]")
G.append(f"[o1][lg]overlay=x=W-w-44:y=34:format=auto,format={RGB}[o2]")
if PNG:
    G.append("[o2]scale=in_range=pc:out_range=pc:flags=lanczos,format=rgb24[vout]")
else:
    G.append("[o2]scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p,setsar=1[vout]")

DBG = os.environ.get('DBG', '')
GG = []
for g_ in G:
    if 'nozoom' in DBG and g_.startswith('[pa]scale='):
        g_ = "[pa]crop=1920:1080:0:0,setsar=1,format=gbrap10le,split[pers][pg]"
    if 'nonoise' in DBG:
        g_ = g_.replace('noise=alls=2:allf=t+u,', '')
    if 'noenable' in DBG:
        import re as _re
        g_ = _re.sub(r":enable='[^']*'", '', g_)
    if 'nocurves' in DBG:
        g_ = g_.replace(f"{CURVES},eq=saturation=1.06:gamma=0.97", 'null')
    if 'noglow' in DBG and g_.startswith('[b1]'):
        g_ = g_
    GG.append(g_)
G = GG
gfile = B + f'work3/final_graph_{os.getpid()}.txt'
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
    cmd += ['-frames:v', str(int(round(dur_total * FPS))), '-fps_mode', 'passthrough' if a.passthrough else 'cfr']
if PNG:
    cmd += ['-frames:v', '1']
elif a.fast:
    cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20']
else:
    cmd += ['-threads', '3', '-c:v', 'libx264', '-preset', 'slow', '-crf', str(a.crf), '-maxrate', '40M', '-bufsize', '80M',
            '-profile:v', 'high', '-level:v', '4.2', '-bf', '3', '-refs', '4',
            '-x264-params', 'aq-mode=3:aq-strength=0.9:psy-rd=1.0,0.15:deblock=-1,-1:keyint=60:min-keyint=30']
if not PNG:
    cmd += ['-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv'] + ([] if a.passthrough else ['-r', str(FPS)])
if i_aud is not None:
    cmd += ['-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2']
cmd += ([] if PNG else ['-movflags', '+faststart']) + [a.out]
if a.print:
    print(' '.join(cmd))
    sys.exit(0)
print('running ffmpeg...', flush=True)
r = subprocess.run(cmd)
sys.exit(r.returncode)
