import json, re, subprocess, sys, concurrent.futures as cf
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
cat = json.load(open(sys.argv[1])); out = sys.argv[2]
kw=r"\b(ai|artificial|robot|robotic|hologram|neural|code|coding|program|programming|typing|types|laptop|smartphone|phone|scroll|scrolling|social|like|thumbs|data|digital|network|futuristic|cyber|circuit|server|camera|film|cinema|rabbit|hare|turtle|tortoise|race|forest|tablet|website|app|selfie|vlog|youtuber|creator|content|stream|streaming|video|editing|studio|cloud|chip|processor|matrix|binary|brain|stopwatch|timer|clock|countdown|waiting|hourglass|run|running|runner|grass|meadow|animal|cartoon|3d|animation|abstract|particles|loop|background)\b"
ids = [k for k,v in cat.items() if re.search(kw, v["title"], re.I)]
def chk(i):
    v = cat[i]
    try:
        h = subprocess.run(["curl","-sS","-L","-m","40","-A",UA,"https://mixkit.co"+v["page"]],capture_output=True).stdout.decode("utf8","ignore")
    except Exception as e:
        return i, "ERR"
    lic = "RESTRICTED" if 'data-license="videoRestricted"' in h else "FREE" if 'data-license="videoFree"' in h else "?"
    return i, lic
res = {}
with cf.ThreadPoolExecutor(8) as ex:
    for i, lic in ex.map(chk, ids):
        res[i] = dict(cat[i], license=lic)
json.dump(res, open(out, "w"), indent=1)
from collections import Counter; print(Counter(v["license"] for v in res.values()), len(res))
