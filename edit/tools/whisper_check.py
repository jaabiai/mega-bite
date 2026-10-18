"""Independent timing cross-check: Malayalam ASR segments (text quality is irrelevant, only timing)."""
import json, sys
from faster_whisper import WhisperModel
import soundfile as sf
wav, out = sys.argv[1:3]
audio, _ = sf.read(wav, dtype="float32")
m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe(audio, language="ml", vad_filter=True, word_timestamps=True, beam_size=1)
res = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(len(res), "segments", info.language, info.duration)
