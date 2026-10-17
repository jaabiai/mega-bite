import re, json, sys, html, subprocess, concurrent.futures as cf
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
slugs = sys.argv[2:]; out = sys.argv[1]
def fetch(slug):
    items = {}
    for page in (1, 2):
        url = f"https://mixkit.co/free-stock-video/{slug}/" + (f"?page={page}" if page > 1 else "")
        r = subprocess.run(["curl","-sS","-L","-m","40","-A",UA,url], capture_output=True)
        h = r.stdout.decode("utf8","ignore")
        for m in re.finditer(r'data-item-grid--video-player-item-id-value="(\d+)".*?overlay-video-title">\s*(.*?)\s*</span>.*?href="(/free-stock-video/[^"]+)"', h, re.S):
            items[m.group(1)] = dict(id=m.group(1), title=html.unescape(m.group(2)), page=m.group(3), slug=slug)
    return slug, items
cat = {}
with cf.ThreadPoolExecutor(6) as ex:
    for slug, items in ex.map(fetch, slugs):
        print(slug, len(items)); 
        for k, v in items.items(): cat.setdefault(k, v)
json.dump(cat, open(out, "w"), indent=1)
print("total", len(cat))
