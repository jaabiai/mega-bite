"""Scrape Mixkit free-music listings -> catalog json (id, title, author, tags, duration).  Licence: Mixkit Stock Music Free License."""
import re, sys, json, html, subprocess, concurrent.futures as cf
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
out = sys.argv[1]; paths = sys.argv[2:]

def fetch(path):
    items = {}
    for page in (1, 2, 3):
        url = f"https://mixkit.co/free-stock-music/{path}/" + (f"?page={page}" if page > 1 else "")
        h = subprocess.run(["curl", "-sS", "-L", "-m", "40", "-A", UA, url], capture_output=True).stdout.decode("utf8", "ignore")
        anchors = [(m.start(), m.group(1)) for m in re.finditer(r'data-audio-player-item-id-value="(\d+)"', h)]
        for k, (pos, iid) in enumerate(anchors):
            seg = h[pos: anchors[k + 1][0] if k + 1 < len(anchors) else pos + 6000]
            title = re.search(r'item-grid-card__title">\s*(.*?)\s*</h2>', seg, re.S)
            author = re.search(r'preview__author">\s*by\s*(.*?)\s*</p>', seg, re.S)
            tags = re.findall(r'class="meta-links__link"[^>]*href="[^"]*">([^<]+)<', seg)
            dur = re.search(r'\b(\d{1,2}:\d{2})\b', re.sub(r'<[^>]+>', ' ', seg))
            items[iid] = dict(id=iid, title=html.unescape(title.group(1)) if title else "?", author=html.unescape(author.group(1)) if author else "?",
                              tags=[html.unescape(t) for t in tags], dur=dur.group(1) if dur else "?", src=path)
    return path, items

cat = {}
with cf.ThreadPoolExecutor(6) as ex:
    for path, items in ex.map(fetch, paths):
        print(path, len(items))
        for k, v in items.items():
            if k in cat: cat[k]["src"] += "," + path
            else: cat[k] = v
json.dump(cat, open(out, "w"), indent=1, ensure_ascii=False)
print("total", len(cat))
