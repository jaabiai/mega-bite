#!/usr/bin/env python3
"""Quick preview clip of the captions: preview.py START DURATION OUT.mp4   (film seconds)
Re-renders only the overlay frames of that window and composites them on $WORK/base.mp4 with the mastered audio."""
import os, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, WORK, load_timeline
import compose

def main():
    start, dur, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    tl = load_timeline(); fps = tl['fps']
    f0, f1 = int(round(start * fps)), int(round((start + dur) * fps))
    subprocess.run(['node', str(ROOT / 'tools' / 'render_overlays.mjs'), str(WORK), '4', '--frames', ','.join(str(f) for f in range(f0, f1))], check=True)
    bug, pad = compose.make_bug(tl)
    mx, my = tl['logo']['bug_margin']
    wav = WORK / 'audio_master.wav' if (WORK / 'audio_master.wav').exists() else WORK / 'audio.wav'
    fg = (f"[1:v]format=rgba[ov];[2:v]format=rgba,colorchannelmixer=aa={tl['logo']['bug_opacity']}[bug];"
          f"[0:v][ov]overlay=0:0:format=auto[v1];[v1][bug]overlay=x=W-w-{mx - pad}:y={my - pad}:format=auto,noise=alls=4:allf=t+u,"
          f"fade=t=in:st=0:d=0.5,fade=t=out:st={dur - 0.7:.2f}:d=0.7,format=yuv420p[vout];[3:a]afade=t=in:d=0.4,afade=t=out:st={dur - 0.7:.2f}:d=0.7[aout]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', str(WORK / 'base.mp4'),
                    '-framerate', str(fps), '-start_number', str(f0), '-i', str(WORK / 'overlay_test' / 'ov_%06d.png'),
                    '-framerate', str(fps), '-loop', '1', '-t', f'{dur:.3f}', '-i', str(bug),
                    '-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', str(wav),
                    '-filter_complex', fg, '-map', '[vout]', '-map', '[aout]', '-t', f'{dur:.3f}',
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', out], check=True)
    print('wrote', out)

if __name__ == '__main__':
    main()
