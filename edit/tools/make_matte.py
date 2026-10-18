"""Person matte (alpha) for the talking-head shots using Robust Video Matting (ONNX, CPU).

Writes a lossless gray FFV1 clip (1280x720, 30 fps) covering frames [f0, f1) of the main video.
The recurrent state is warmed up on `warm` frames before f0 (discarded).

usage: make_matte.py <main.mp4> <rvm.onnx> <f0> <f1> <warm> <out.mkv> [threads]
"""
import subprocess
import sys

import numpy as np
import onnxruntime as ort

FPS = 30
IW, IH = 1280, 720  # RVM input (downsample_ratio keeps the internal pass at ~480x270)


def main(src, model, f0, f1, warm, out, threads=1):
    f0, f1, warm = int(f0), int(f1), int(warm)
    start = max(0, f0 - warm)
    so = ort.SessionOptions()
    so.intra_op_num_threads = int(threads)
    sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])

    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", f"{start / FPS:.5f}", "-i", src, "-frames:v", str(f1 - start),
         "-vf", f"scale={IW}:{IH}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{IW}x{IH}", "-r", str(FPS),
         "-i", "-", "-c:v", "ffv1", "-level", "3", "-pix_fmt", "gray", out],
        stdin=subprocess.PIPE)

    st = [np.zeros((1, 1, 1, 1), np.float16) for _ in range(4)]
    ds = np.array([0.375], np.float32)
    fsize = IW * IH * 3
    n = start
    while n < f1:
        buf = dec.stdout.read(fsize)
        if len(buf) < fsize:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(IH, IW, 3)
        src_t = (frame.astype(np.float16) / 255).transpose(2, 0, 1)[None]
        _, pha, *st = sess.run(None, {"src": src_t, "r1i": st[0], "r2i": st[1], "r3i": st[2], "r4i": st[3],
                                      "downsample_ratio": ds})
        if n >= f0:
            enc.stdin.write((np.clip(pha[0, 0].astype(np.float32), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        n += 1
        if (n - start) % 200 == 0:
            print(f"{out}: {n - start}/{f1 - start}", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print("done", out, n - f0, "frames written", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:8])
