"""Timestamped contact sheet of the SDR screen recording: sheet.py <src> <out> <t0> <t1> <fps> [cols]"""
import subprocess, sys
src, out, t0, t1, fps = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 8
n = int((t1 - t0) * fps)
rows = -(-n // cols)
F = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
vf = (f"fps={fps},scale=200:434,drawtext=fontfile={F}:text='%{{expr\\:{t0}+n/{fps}}}':x=6:y=h-30:fontsize=22:"
      f"fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=3,tile={cols}x{rows}")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", src, "-vf", vf,
                "-frames:v", "1", out], check=True)
