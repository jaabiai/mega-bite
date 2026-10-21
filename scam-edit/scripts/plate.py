"""Render the 'plate': edited talking-head frames, HLG->SDR, background softly blurred behind the speaker.

usage: plate.py <worker_index> <n_workers> [max_pieces]
Each worker renders a contiguous block of EDL pieces into plate_part_<k>.mov (ProRes 422 HQ, 10-bit, BT.709).
"""
import sys, json, subprocess, time
import numpy as np
import cv2

cv2.setNumThreads(2)
B = '/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
SRC = B + 'src2/scam_main.mp4'
ALPHA = B + 'work/matte/alpha_full.mkv'
W, H, FPS = 1920, 1080, 30
TM = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
      "zscale=t=bt709,format=rgb48le")

# background look
SIG_NEAR, SIG_FAR = 4.5, 11.0          # gaussian sigma (px @1080p) near the speaker / far from the speaker
FAR_DIST = 300.0                       # px from the speaker where the strong blur is fully reached
BG_GAIN, BG_SAT = 0.95, 0.93           # tiny dim / desaturate so the speaker separates from the wall

wk, nw = int(sys.argv[1]), int(sys.argv[2])
pieces = json.load(open(B + 'work/edl.json'))['pieces']
if len(sys.argv) > 3:
    pieces = pieces[:int(sys.argv[3])]
# split by frame count so workers take about the same amount of work
tot = sum(p['b'] - p['a'] for p in pieces)
acc, bounds, k = 0, [0], 1
for i, p in enumerate(pieces):
    acc += p['b'] - p['a']
    if acc >= tot * k / nw and k < nw:
        bounds.append(i + 1)
        k += 1
bounds.append(len(pieces))
mine = pieces[bounds[wk]:bounds[wk + 1]]
print(f"worker {wk}: pieces {bounds[wk]}..{bounds[wk + 1] - 1}, {sum(p['b'] - p['a'] for p in mine)} frames", flush=True)

out = B + f'work/plate_part_{wk}.mov'
enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
     '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv422p10le',
     '-c:v', 'prores_ks', '-profile:v', '3', '-vendor', 'apl0', '-pix_fmt', 'yuv422p10le',
     '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', out],
    stdin=subprocess.PIPE)


def readn(f, n):
    buf = bytearray()
    while len(buf) < n:
        c = f.read(n - len(buf))
        if not c:
            return None
        buf += c
    return bytes(buf)


def nconv(rgb, w, sig):
    """Blur only background pixels (normalised convolution) so the speaker never bleeds into the blur."""
    num = cv2.GaussianBlur(rgb * w[..., None], (0, 0), sig)
    den = cv2.GaussianBlur(w, (0, 0), sig)
    bg = num / np.maximum(den, 1e-4)[..., None]
    return bg, den


t0 = time.time()
done = 0
for p in mine:
    a0, n = p['a'], p['b'] - p['a']
    ss = (a0 - 0.4) / FPS
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{ss:.5f}', '-i', SRC, '-frames:v', str(n), '-vf', TM,
                            '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-'], stdout=subprocess.PIPE, bufsize=W * H * 6 * 2)
    adec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{ss:.5f}', '-i', ALPHA, '-frames:v', str(n),
                             '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE, bufsize=W * H * 2)
    for i in range(n):
        fb = readn(dec.stdout, W * H * 6)
        ab = readn(adec.stdout, W * H)
        if fb is None or ab is None:
            raise SystemExit(f'short read in piece {p["chunk"]} frame {i}/{n}')
        rgb = np.frombuffer(fb, np.uint16).reshape(H, W, 3).astype(np.float32) / 65535.0
        a = np.frombuffer(ab, np.uint8).reshape(H, W).astype(np.float32) / 255.0
        a = np.clip((a - 0.03) / 0.94, 0, 1)                         # kill faint matte noise, keep soft hair edges

        # background is blurred anyway -> compute it at half resolution (identical look, ~4x cheaper)
        rs = cv2.resize(rgb, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        as_ = cv2.resize(a, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        subj = (as_ > 0.02).astype(np.uint8)
        subj_d = cv2.dilate(subj, np.ones((5, 5), np.uint8))
        w = 1.0 - subj_d.astype(np.float32)
        dist = cv2.distanceTransform((1 - subj).astype(np.uint8), cv2.DIST_L2, 3) * 2.0     # px (full-res units)
        t = np.clip(dist / FAR_DIST, 0, 1)[..., None]
        b1, d1 = nconv(rs, w, SIG_NEAR / 2)
        b2, d2 = nconv(rs, w, SIG_FAR / 2)
        full = cv2.GaussianBlur(rs, (0, 0), SIG_FAR / 2)
        m1 = np.clip(d1 * 6, 0, 1)[..., None]
        m2 = np.clip(d2 * 6, 0, 1)[..., None]
        b1 = b1 * m1 + full * (1 - m1)
        b2 = b2 * m2 + full * (1 - m2)
        bg = b1 * (1 - t) + b2 * t
        lum = bg.mean(2, keepdims=True)
        bg = (lum + (bg - lum) * BG_SAT) * BG_GAIN
        bg = cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR)
        res = rgb * a[..., None] + bg * (1 - a[..., None])
        enc.stdin.write((np.clip(res, 0, 1) * 65535 + 0.5).astype(np.uint16).tobytes())
        done += 1
        if done % 60 == 0:
            print(f"worker {wk}: {done} frames  {done / (time.time() - t0):.2f} fps", flush=True)
    dec.stdout.close()
    adec.stdout.close()
    dec.wait()
    adec.wait()
enc.stdin.close()
enc.wait()
print(f"worker {wk} DONE {done} frames in {time.time() - t0:.0f}s", flush=True)
