"""Full-resolution (1920x1080) person matte of single frames, for thumbnails (the video matte is 1280x720).

RVM is run on `warm` frames before the target so its recurrent state is settled, then the target alpha is written as PNG.

usage: thumb_matte.py <main.mp4> <rvm.onnx> <out_dir> <warm> <frame> [frame ...]
"""
import os
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

FPS = 30
IW, IH = 1920, 1080


def main(src, model, out_dir, warm, *frames):
    os.makedirs(out_dir, exist_ok=True)
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
    for target in map(int, frames):
        start = max(0, target - int(warm))
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start / FPS:.5f}", "-i", src, "-frames:v", str(target - start + 1),
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        st = [np.zeros((1, 1, 1, 1), np.float16) for _ in range(4)]
        ds = np.array([0.4], np.float32)
        pha = None
        for _ in range(target - start + 1):
            buf = dec.stdout.read(IW * IH * 3)
            if len(buf) < IW * IH * 3:
                break
            fr = np.frombuffer(buf, np.uint8).reshape(IH, IW, 3)
            t = (fr.astype(np.float16) / 255).transpose(2, 0, 1)[None]
            _, pha, *st = sess.run(None, {"src": t, "r1i": st[0], "r2i": st[1], "r3i": st[2], "r4i": st[3], "downsample_ratio": ds})
        dec.wait()
        a = (np.clip(pha[0, 0].astype(np.float32), 0, 1) * 255 + 0.5).astype(np.uint8)
        cv2.imwrite(f"{out_dir}/alpha_{target:05d}.png", a)
        print("alpha", target, a.shape, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
