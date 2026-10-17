import json, re, subprocess, sys, concurrent.futures as cf
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
cat = json.load(open(sys.argv[1])); ids = sys.argv[2:]
def chk(i):
    v = cat[i]
    h = subprocess.run(["curl","-sS","-L","-m","40","-A",UA,"https://mixkit.co"+v["page"]],capture_output=True).stdout.decode("utf8","ignore")
    free = bool(re.search(r'Free Download[^<]{0,80}Commercial|for commercial and personal|Mixkit Free License',h)) and 'data-license="videoRestricted"' not in h
    restricted = 'data-license="videoRestricted"' in h
    vids = sorted(set(re.findall(r'https://assets\.mixkit\.co/[^"\' ]+-(?:720|1080)\.mp4',h)))
    return i, v["title"], ("RESTRICTED" if restricted else "FREE" if 'videoFree' in h else "?"), vids
with cf.ThreadPoolExecutor(6) as ex:
    for r in ex.map(chk, ids): print(*r, sep=" | ")
