"""Export lyric_timing.json -> .srt and .ass (for use in other editors / players).
usage: export_subs.py lyric_timing.json OUT_PREFIX"""
import json, sys

def ts_srt(t):
    t = max(0.0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"

def ts_ass(t):
    t = max(0.0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"

def main(src, prefix):
    d = json.load(open(src, encoding="utf-8"))
    off = d["meta"].get("global_offset_s", 0.0)
    lines = d["lines"]
    with open(prefix + ".srt", "w", encoding="utf-8") as f:
        for i, l in enumerate(lines, 1):
            f.write(f"{i}\n{ts_srt(l['start'] + off)} --> {ts_srt(l['end'] + off)}\n{l['text']}\n\n")
    hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Regular,Hind,80,&H00FFFFFF,&H000000FF,&H00160E05,&H80000000,-1,0,0,0,100,100,0,0,1,4,3,2,60,60,520,1
Style: Wake,Rozha One,150,&H00FFFFFF,&H000000FF,&H00160E05,&H80000000,0,0,0,0,100,100,0,0,1,5,4,5,60,60,0,1
Style: March,Khand,190,&H00FFFFFF,&H000000FF,&H00160E05,&H80000000,-1,0,0,0,100,100,0,0,1,5,4,5,60,60,0,1
Style: Stamp,Khand,210,&H00FFFFFF,&H000000FF,&H003399FF,&H80000000,-1,0,0,0,100,100,0,-3,1,6,4,5,60,60,0,1
Style: Defiant,Khand,160,&H00FFFFFF,&H000000FF,&H00160E05,&H80000000,-1,0,0,0,100,100,0,0,1,5,4,5,60,60,0,1
Style: People,Rozha One,120,&H00FFFFFF,&H000000FF,&H00160E05,&H80000000,0,0,0,0,100,100,0,0,1,5,4,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    names = {"regular": "Regular", "wake": "Wake", "march": "March", "stamp": "Stamp", "defiant": "Defiant", "people": "People"}
    with open(prefix + ".ass", "w", encoding="utf-8") as f:
        f.write(hdr)
        for l in lines:
            st = names.get(l.get("style", "regular"), "Regular")
            fx = "{\\fad(120,150)}"
            f.write(f"Dialogue: 0,{ts_ass(l['start'] + off)},{ts_ass(l['end'] + off)},{st},,0,0,0,,{fx}{l['text']}\n")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
