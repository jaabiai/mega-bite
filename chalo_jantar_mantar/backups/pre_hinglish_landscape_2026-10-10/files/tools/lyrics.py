import os
import re
LYR=os.environ.get("CJM_LYRICS", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lyrics.txt")))
def parse():
    """Returns list of dict(id, section, text) for every sung line, in order."""
    lines=open(LYR,encoding="utf-8").read().split("\n")
    # header = first 5 lines (title, FINAL LYRICS, Language, Instruction, blank)
    sec=None; out=[]
    for ln in lines[5:]:
        s=ln.strip()
        if not s: continue
        m=re.match(r"^\[(.+)\]$",s)
        if m:
            sec=m.group(1); continue
        out.append({"id":len(out)+1,"section":sec,"text":s})
    return out
def norm(t):
    """Model-facing text: drop punctuation (keeps Devanagari + latin letters)."""
    t=re.sub(r"[…!?,।.\-–—]"," ",t)
    t=t.replace("-"," ")
    return " "+re.sub(r"\s+"," ",t).strip()
if __name__=="__main__":
    L=parse(); print(len(L)); 
    for l in L[:12]: print(l)
