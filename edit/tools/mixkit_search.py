"""List Mixkit free stock-video candidates for a set of keywords (title + 1080p url)."""
import html, json, re, sys, urllib.parse, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "ignore")


def search(kw):
    s = fetch("https://mixkit.co/free-stock-video/discover/" + urllib.parse.quote(kw.replace(" ", "-")) + "/")
    out = []
    for m in re.finditer(r'<video src="https://assets\.mixkit\.co/videos/(\d+)/\d+-360\.mp4".*?overlay-video-title">\s*(.*?)\s*</span>', s, re.S):
        out.append({"id": int(m.group(1)), "title": html.unescape(m.group(2).strip())})
    return out


if __name__ == "__main__":
    res = {}
    for kw in sys.argv[2:]:
        try:
            res[kw] = search(kw)
        except Exception as e:  # noqa: BLE001
            res[kw] = [{"error": str(e)}]
        print(f"== {kw}: {len(res[kw])}")
        for r in res[kw][:14]:
            print("  ", r.get("id"), r.get("title") or r.get("error"))
    json.dump(res, open(sys.argv[1], "w"), indent=1)
