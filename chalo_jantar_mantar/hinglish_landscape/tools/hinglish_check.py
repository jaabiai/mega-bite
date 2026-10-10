"""Verify Roman Hindi (Hinglish) lines against the Devanagari source.

For every line the check compares, word by word, the consonant skeleton of the Devanagari with the consonant skeleton of the Roman
spelling (vowels, nasals n/m, non-initial 'y' ignored, doubled consonants collapsed), plus: same word count, same punctuation
sequence, and ASCII-only Roman text.  usage: hinglish_check.py [--quiet]
"""
import json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))          # chalo_jantar_mantar/
DEV = {  # base consonants -> skeleton class ('' = ignored nasal)
    "क": "k", "ख": "K", "ग": "g", "घ": "G", "ङ": "", "च": "c", "छ": "C", "ज": "j", "झ": "J", "ञ": "",
    "ट": "t", "ठ": "T", "ड": "d", "ढ": "D", "ण": "", "त": "t", "थ": "T", "द": "d", "ध": "D", "न": "",
    "प": "p", "फ": "P", "ब": "b", "भ": "B", "म": "", "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "S", "ष": "S", "स": "s", "ह": "h",
}
NUKTA = {"क": "k", "ख": "K", "ग": "g", "ज": "z", "ड": "d", "ढ": "D", "फ": "f"}
PUNCT = "…,!?-"


def dev_skeleton(word):
    w = unicodedata.normalize("NFD", word)
    out = []
    i = 0
    while i < len(w):
        ch = w[i]
        if ch in DEV:
            cls = DEV[ch]
            if i + 1 < len(w) and w[i + 1] == "़" and ch in NUKTA:
                cls = NUKTA[ch]
                i += 1
            out.append(cls)
        i += 1
    return out


def roman_skeleton(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    out = []
    i = 0
    di = {"chh": "C", "ch": "c", "kh": "K", "gh": "G", "jh": "J", "th": "T", "dh": "D", "ph": "P", "bh": "B", "sh": "S"}
    while i < len(w):
        for L in (3, 2):
            if w[i:i + L] in di:
                out.append(di[w[i:i + L]]); i += L; break
        else:
            c = w[i]; i += 1
            if c in "aeiou" or c in "nm":
                continue
            out.append({"q": "k", "w": "v", "x": "k"}.get(c, c))
    return out


def normalize(sk, starts_with_y=False):
    out = []
    for j, c in enumerate(sk):
        if c == "y" and not (j == 0 and starts_with_y):
            continue                    # glide-y (ayi, iyo, aaye) is not reliably written in Devanagari
        if c == "" :
            continue
        if out and out[-1] == c:
            continue                    # collapse doubled consonants (darr/dar, satta/sata)
        out.append(c)
    return out


def words_of(text):
    t = re.sub(r"[…,!?]", " ", text).replace("-", " ")
    return [w for w in t.split() if w]


def puncts(text):
    return [c for c in text if c in PUNCT]


def check(verbose=True):
    src = json.load(open(os.path.join(ROOT, "lyric_timing.json"), encoding="utf-8"))["lines"]
    rom = json.load(open(os.path.join(ROOT, "hinglish_landscape", "data", "roman_map.json"), encoding="utf-8"))
    problems = []
    for l in src:
        r = rom[str(l["id"])]
        if not re.fullmatch(r"[A-Za-z …,!?\-]+", r):
            problems.append((l["id"], "non-ASCII/Latin character in Roman text", r))
        if any("ऀ" <= c <= "ॿ" for c in r):
            problems.append((l["id"], "DEVANAGARI present", r))
        dw, rw = words_of(l["text"]), words_of(r)
        if len(dw) != len(rw):
            problems.append((l["id"], f"word count {len(dw)} != {len(rw)}", r))
            continue
        if puncts(l["text"]) != puncts(r):
            problems.append((l["id"], f"punctuation {puncts(l['text'])} != {puncts(r)}", r))
        for a, b in zip(dw, rw):
            if re.fullmatch(r"[A-Za-z]+", a):           # source word already in Latin (Vote Chori)
                sa = normalize(roman_skeleton(a), a.lower().startswith("y"))
            else:
                sa = normalize(dev_skeleton(a), a.startswith("य"))
            sb = normalize(roman_skeleton(b), b.lower().startswith("y"))
            if sa != sb:
                problems.append((l["id"], f"skeleton mismatch '{a}' {sa} vs '{b}' {sb}", r))
    if verbose:
        print(f"lines checked: {len(src)}; problems: {len(problems)}")
        for p in problems:
            print("  L%-3d %s   [%s]" % p)
    return problems


if __name__ == "__main__":
    sys.exit(1 if check("--quiet" not in sys.argv) else 0)
