"""Frame sources: ffmpeg rawvideo pipes with cheap forward-seek and restart-on-jump."""
import os
import subprocess

import numpy as np

from .common import WORK, W, H, FPS, NF
from . import grade


class PipeReader:
    """Read frames idx = 0,1,2.. (at FPS) of `path` (+offset seconds) through an ffmpeg pipe.
    `get(idx)` is cheap for forward reads; a backwards / far jump restarts ffmpeg with -ss."""

    def __init__(self, path, w, h, vf="", offset=0.0, pix="rgb24", ch=3, fps=FPS):
        self.path, self.w, self.h, self.vf, self.offset = path, w, h, vf, offset
        self.pix, self.ch, self.fps = pix, ch, fps
        self.fsz = w * h * ch
        self.proc = None
        self.cur = -1
        self.last = None
        self.eof = False

    def _start(self, idx):
        self.close()
        t = max(self.offset + idx / self.fps, 0.0)
        vf = f"fps={self.fps}" + ("," + self.vf if self.vf else "")
        if self.pix == "rgb24":      # explicit BT.709 limited->full conversion (some stock clips are untagged)
            vf += ",scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24"
        cmd = ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.4f}", "-i", self.path, "-vf", vf,
               "-f", "rawvideo", "-pix_fmt", self.pix, "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.fsz * 2)
        self.cur = idx - 1
        self.eof = False

    def _read(self):
        buf = self.proc.stdout.read(self.fsz)
        if len(buf) < self.fsz:
            return None
        shape = (self.h, self.w, self.ch) if self.ch > 1 else (self.h, self.w)
        return np.frombuffer(buf, np.uint8).reshape(shape)

    def get(self, idx):
        idx = max(int(idx), 0)
        if self.proc is None or idx < self.cur or idx > self.cur + 60:
            self._start(idx)
        while self.cur < idx and not self.eof:
            fr = self._read()
            if fr is None:
                self.eof = True
                break
            self.last = fr
            self.cur += 1
        return self.last

    def close(self):
        if self.proc is not None:
            try:
                self.proc.stdout.close()
                self.proc.kill()
                self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None


class MainSource:
    """Presenter footage + person matte; `graded(idx)` returns the colour-graded, background-blurred frame."""

    def __init__(self, start_idx=0):
        self.video = PipeReader(os.path.join(WORK, "work/main.mp4"), W, H)
        self.matte = PipeReader(os.path.join(WORK, "work/matte.mkv"), W, H, pix="gray", ch=1)
        self._gcache = (-1, None)

    def raw(self, idx):
        return self.video.get(min(idx, NF - 1))

    def graded(self, idx):
        idx = min(max(idx, 0), NF - 1)
        if self._gcache[0] == idx:
            return self._gcache[1]
        rgb = self.video.get(idx)
        m = self.matte.get(idx).astype(np.float32) / 255.0
        t = idx / FPS
        keep = 1.0 if 50.3 <= t <= 231.0 else (max(0.0, 1 - (t - 231.0) / 0.8) if 231.0 < t < 231.8 else 0.0)
        out = grade.grade_frame(rgb, m, keep=keep)
        self._gcache = (idx, out)
        return out

    def close(self):
        self.video.close()
        self.matte.close()
