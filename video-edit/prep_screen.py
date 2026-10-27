"""Write the cleaned (blurred / de-cluttered) screen recording for a slice of recording time.

usage: python prep_screen.py <project> <sdr60.mp4> <start_s> <end_s> <out.mp4>
"""
import sys, os, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, os.path.join(HERE, "projects", sys.argv[1]))
import screenprep, screen_rules

project, src, a, b, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
screenprep.configure(screen_rules)
if getattr(screen_rules, "ASSIST", None):
    screenprep.calibrate_bubble(src)
W, H, FPS = 1320, 2868, 60
n = int(round((b - a) * FPS))
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.4f}", "-i", src, "-frames:v", str(n),
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "8", "-pix_fmt", "yuv444p",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", out], stdin=subprocess.PIPE)
size = W * H * 3
i = 0
while True:
    buf = dec.stdout.read(size)
    if len(buf) < size:
        break
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
    enc.stdin.write(screenprep.prepare(img, a + i / FPS).tobytes())
    i += 1
enc.stdin.close(); enc.wait(); dec.wait()
print(out, i, "frames")
