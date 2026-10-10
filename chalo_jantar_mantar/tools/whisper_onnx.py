"""Minimal Whisper (sherpa-onnx export) wrapper with segment timestamps.

Two decoding modes:
  decode_free   - normal greedy transcription with timestamp tokens
  decode_forced - teacher-forces KNOWN text segments and lets the model predict
                  only the timestamp tokens between them (forced alignment).
"""
import os
import base64
import numpy as np
import onnxruntime as ort

MODELS = os.environ.get("CJM_MODELS", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")) + "/")
SR = 16000
N_FFT = 400
HOP = 160
CHUNK = 30 * SR


def _hz_to_mel(f):
    f = np.asarray(f, dtype=np.float64)
    f_sp = 200.0 / 3
    mels = f / f_sp
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = np.log(6.4) / 27.0
    return np.where(f >= min_log_hz, min_log_mel + np.log(np.maximum(f, 1e-9) / min_log_hz) / logstep, mels)


def _mel_to_hz(m):
    m = np.asarray(m, dtype=np.float64)
    f_sp = 200.0 / 3
    freqs = f_sp * m
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = np.log(6.4) / 27.0
    return np.where(m >= min_log_mel, min_log_hz * np.exp(logstep * (m - min_log_mel)), freqs)


def mel_filters(n_mels, n_fft=N_FFT, sr=SR):
    """librosa.filters.mel (slaney) as used by openai-whisper."""
    n_freqs = 1 + n_fft // 2
    fftfreqs = np.linspace(0, sr / 2, n_freqs)
    mel_pts = _mel_to_hz(np.linspace(_hz_to_mel(0.0), _hz_to_mel(sr / 2), n_mels + 2))
    fdiff = np.diff(mel_pts)
    ramps = mel_pts[:, None] - fftfreqs[None, :]
    lower = -ramps[:-2] / fdiff[:-1, None]
    upper = ramps[2:] / fdiff[1:, None]
    w = np.maximum(0, np.minimum(lower, upper))
    enms = 2.0 / (mel_pts[2: n_mels + 2] - mel_pts[:n_mels])
    return (w * enms[:, None]).astype(np.float32)


def log_mel(audio, n_mels, filters):
    """audio: float32 mono, already padded/trimmed to exactly CHUNK samples."""
    window = np.hanning(N_FFT + 1)[:-1].astype(np.float32)  # periodic hann
    pad = N_FFT // 2
    a = np.pad(audio, (pad, pad), mode="reflect")
    n_frames = 1 + (len(a) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n_frames)[:, None]
    frames = a[idx] * window
    spec = np.fft.rfft(frames, axis=1)
    mag = (spec.real ** 2 + spec.imag ** 2)[:-1].astype(np.float32)  # drop last frame -> 3000
    mel = filters @ mag.T
    lm = np.log10(np.maximum(mel, 1e-10))
    lm = np.maximum(lm, lm.max() - 8.0)
    return ((lm + 4.0) / 4.0).astype(np.float32)


class Whisper:
    def __init__(self, name, threads=4):
        d = MODELS + f"sherpa-onnx-whisper-{name}/"
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        self.enc = ort.InferenceSession(d + f"{name}-encoder.int8.onnx", so, providers=["CPUExecutionProvider"])
        self.dec = ort.InferenceSession(d + f"{name}-decoder.int8.onnx", so, providers=["CPUExecutionProvider"])
        m = self.enc.get_modelmeta().custom_metadata_map
        self.n_mels = int(m["n_mels"])
        self.n_layer = int(m["n_text_layer"])
        self.d_model = int(m["n_text_state"])
        self.n_ctx = int(m["n_text_ctx"])
        self.sot = int(m["sot"])
        self.eot = int(m["eot"])
        self.transcribe = int(m["transcribe"])
        self.no_ts = int(m["no_timestamps"])
        self.ts_begin = self.no_ts + 1
        self.n_vocab = int(m["n_vocab"])
        codes = m["all_language_codes"].split(",")
        toks = [int(t) for t in m["all_language_tokens"].split(",")]
        self.lang = dict(zip(codes, toks))
        self.suppress = [int(t) for t in m["non_speech_tokens"].split(",") if t.strip()]
        self.filters = mel_filters(self.n_mels)
        self.tokens = []
        with open(d + f"{name}-tokens.txt") as f:
            for line in f:
                b64, _ = line.rsplit(" ", 1)
                self.tokens.append(base64.b64decode(b64))
        self.name = name

    # ---------------- text helpers ----------------
    def detok(self, ids):
        out = b""
        for t in ids:
            if t < len(self.tokens):
                out += self.tokens[t]
        return out.decode("utf-8", errors="ignore")

    def tokenize(self, text):
        """Greedy longest-match byte-level tokenization using the vocab itself."""
        if not hasattr(self, "_trie"):
            self._trie = {}
            for i, b in enumerate(self.tokens):
                if b and b not in self._trie:
                    self._trie[b] = i
            self._maxlen = max(len(b) for b in self.tokens)
        data = text.encode("utf-8")
        out = []
        i = 0
        while i < len(data):
            for L in range(min(self._maxlen, len(data) - i), 0, -1):
                t = self._trie.get(data[i:i + L])
                if t is not None:
                    out.append(t)
                    i += L
                    break
            else:
                raise ValueError("cannot tokenize byte")
        return out

    # ---------------- model calls ----------------
    def encode(self, audio):
        a = np.zeros(CHUNK, dtype=np.float32)
        n = min(len(audio), CHUNK)
        a[:n] = audio[:n]
        mel = log_mel(a, self.n_mels, self.filters)[None]
        ck, cv = self.enc.run(None, {"mel": mel})
        return ck, cv

    def _new_cache(self):
        z = np.zeros((self.n_layer, 1, self.n_ctx, self.d_model), dtype=np.float32)
        return z, z.copy()

    def _step(self, tokens, state, ck, cv):
        kc, vc, off = state
        logits, kc, vc = self.dec.run(
            None,
            {
                "tokens": np.asarray([tokens], dtype=np.int64),
                "in_n_layer_self_k_cache": kc,
                "in_n_layer_self_v_cache": vc,
                "n_layer_cross_k": ck,
                "n_layer_cross_v": cv,
                "offset": np.asarray([off], dtype=np.int64),
            },
        )
        return logits[0], (kc, vc, off + len(tokens))

    @staticmethod
    def _logsoftmax(x):
        x = x.astype(np.float64)
        m = x.max()
        return x - (m + np.log(np.exp(x - m).sum()))

    def prompt(self, language="hi"):
        return [self.sot, self.lang[language], self.transcribe]

    # ---------------- free decoding ----------------
    def decode_free(self, ck, cv, language="hi", max_new=200, max_initial_ts=1.0):
        kc, vc = self._new_cache()
        state = (kc, vc, 0)
        seq = self.prompt(language)
        logits, state = self._step(seq, state, ck, cv)
        gen = []
        tsb = self.ts_begin
        for step in range(max_new):
            lg = logits[-1].astype(np.float64).copy()
            lg[self.no_ts] = -np.inf
            lg[self.suppress] = -np.inf
            lg[self.sot] = -np.inf
            if step == 0:
                lg[self.eot] = -np.inf
                lg[220] = -np.inf
                lg[tsb + int(round(max_initial_ts / 0.02)) + 1:] = -np.inf
            last_ts = len(gen) >= 1 and gen[-1] >= tsb
            pen_ts = len(gen) < 2 or gen[-2] >= tsb
            if last_ts:
                if pen_ts:
                    lg[tsb:] = -np.inf
                else:
                    lg[: self.eot] = -np.inf
            tss = [t for t in gen if t >= tsb]
            if tss:
                lim = tss[-1] if (last_ts and not pen_ts) else tss[-1] + 1
                lg[tsb:lim] = -np.inf
            lp = self._logsoftmax(lg)
            if np.logaddexp.reduce(lp[tsb:]) > lp[:tsb].max():
                lp[:tsb] = -np.inf
            tok = int(np.argmax(lp))
            if tok == self.eot:
                break
            gen.append(tok)
            logits, state = self._step([tok], state, ck, cv)
        return gen

    def segments_from_tokens(self, gen, offset_s=0.0):
        segs, cur, t0 = [], [], None
        for t in gen:
            if t >= self.ts_begin:
                ts = (t - self.ts_begin) * 0.02
                if t0 is None:
                    t0 = ts
                elif cur:
                    segs.append((t0 + offset_s, ts + offset_s, self.detok(cur)))
                    cur, t0 = [], None
                else:
                    t0 = ts
            else:
                cur.append(t)
        if cur and t0 is not None:
            segs.append((t0 + offset_s, None, self.detok(cur)))
        return segs

    # ---------------- forced decoding ----------------
    def decode_forced(self, ck, cv, texts, language="hi", first_min_ts=0.0, first_max_ts=None):
        """Teacher-force `texts` (list of str, one per segment).  The model chooses
        only the timestamp tokens (start/end per segment, non-decreasing).
        Returns list of (start_s, end_s, mean_logprob_of_text)."""
        kc, vc = self._new_cache()
        state = (kc, vc, 0)
        seq = self.prompt(language)
        logits, state = self._step(seq, state, ck, cv)
        tsb = self.ts_begin
        n_ts = self.n_vocab - tsb
        out = []
        last_ts = int(round(first_min_ts / 0.02))

        def pick_ts(logits_row, lo, hi=None):
            lg = logits_row.astype(np.float64)
            sub = lg[tsb:tsb + n_ts].copy()
            sub[:lo] = -np.inf
            if hi is not None:
                sub[hi + 1:] = -np.inf
            lp = sub - np.logaddexp.reduce(sub[np.isfinite(sub)])
            return int(np.argmax(sub)), lp

        for i, text in enumerate(texts):
            hi = None if (i > 0 or first_max_ts is None) else int(round(first_max_ts / 0.02))
            k, _ = pick_ts(logits[-1], last_ts, hi)
            start_k = k
            logits, state = self._step([tsb + k], state, ck, cv)
            ids = self.tokenize(text)
            lps = []
            # feed text tokens, collecting their log-probs under the model
            for j, tid in enumerate(ids):
                lp_all = self._logsoftmax(logits[-1])
                lps.append(lp_all[tid])
                logits, state = self._step([tid], state, ck, cv)
            # end timestamp
            k2, _ = pick_ts(logits[-1], start_k)
            end_k = k2
            logits, state = self._step([tsb + end_k], state, ck, cv)
            # (model would now emit the next segment's start timestamp)
            out.append((start_k * 0.02, end_k * 0.02, float(np.mean(lps)) if lps else 0.0))
            last_ts = end_k
        return out
