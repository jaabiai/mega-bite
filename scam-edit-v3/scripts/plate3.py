"""Person layer for the background replacement (v2: straight colour F with edge colours extended from the solid interior + cleaned alpha).
Outputs per worker: person_part_k.mov (F, ProRes 422 HQ 10-bit BT.709) and alpha_part_k.mkv (cleaned alpha, FFV1 gray).
(Older description:)
usage: plate3.py <worker> <n_workers> [first_frame last_frame]
For every frame:  P = clip(I - (1 - a) * B_est, 0, a)   (premultiplied, colour-decontaminated foreground)
where B_est is the old wall colour estimated next to the speaker (normalised convolution) - so no old-background
fringe is left on hair / ears / shirt when the speaker is put in front of the new dark background.
Output: work3/person_part_<k>.mov (ProRes 422 HQ, 10-bit, BT.709)."""
import sys, subprocess, time
import numpy as np
import cv2
sys.path.insert(0, '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/scripts')
from pl3lib import person_layer

cv2.setNumThreads(2)
B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
SRC = B + 'src3/final_cut.mp4'
ALPHA = B + 'work3/alpha_full.mkv'
W, H, FPS = 1920, 1080, 30
NF = 5123
wk, nw = int(sys.argv[1]), int(sys.argv[2])
f0, f1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
bounds = np.linspace(f0, f1, nw + 1).astype(int)
a0, a1 = int(bounds[wk]), int(bounds[wk + 1])
n = a1 - a0
out = B + f'work3/person_part_{wk}.mov'
print(f'worker {wk}: frames {a0}..{a1 - 1}', flush=True)

enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
     '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv422p10le',
     '-c:v', 'prores_ks', '-profile:v', '3', '-vendor', 'apl0', '-pix_fmt', 'yuv422p10le',
     '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', out], stdin=subprocess.PIPE)

encA = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                         '-c:v', 'ffv1', '-level', '3', '-g', '1', B + f'work3/alpha_part_{wk}.mkv'], stdin=subprocess.PIPE)


def readn(f, k):
    buf = bytearray()
    while len(buf) < k:
        c = f.read(k - len(buf))
        if not c:
            return None
        buf += c
    return bytes(buf)


def nconv(rgb, w, sig):
    num = cv2.GaussianBlur(rgb * w[..., None], (0, 0), sig)
    den = cv2.GaussianBlur(w, (0, 0), sig)
    return num / np.maximum(den, 1e-4)[..., None], den


ss = (a0 - 0.4) / FPS
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{ss:.5f}', '-i', SRC, '-frames:v', str(n),
                        '-vf', 'scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=accurate_rnd+full_chroma_int,format=rgb24',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, bufsize=W * H * 3 * 2)
adec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{ss:.5f}', '-i', ALPHA, '-frames:v', str(n),
                         '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE, bufsize=W * H * 2)
t0 = time.time()
for i in range(n):
    fb = readn(dec.stdout, W * H * 3)
    ab = readn(adec.stdout, W * H)
    if fb is None or ab is None:
        raise SystemExit(f'short read frame {a0 + i}')
    rgb = np.frombuffer(fb, np.uint8).reshape(H, W, 3).astype(np.float32) / 255.0
    a = np.frombuffer(ab, np.uint8).reshape(H, W).astype(np.float32) / 255.0
    F, an = person_layer(rgb, a, 0.14, 0.92, 1)
    enc.stdin.write((np.clip(F, 0, 1) * 65535 + 0.5).astype(np.uint16).tobytes())
    encA.stdin.write((np.clip(an, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    if (i + 1) % 60 == 0:
        print(f'worker {wk}: {i + 1}/{n} frames  {(i + 1) / (time.time() - t0):.2f} fps', flush=True)
enc.stdin.close(); encA.stdin.close(); enc.wait(); encA.wait(); dec.stdout.close(); adec.stdout.close()
print(f'worker {wk} DONE {n} frames in {time.time() - t0:.0f}s', flush=True)
