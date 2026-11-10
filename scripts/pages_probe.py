import re, urllib.request
B = "https://a1053.github.io/municipal-calendar-v2/"
def get(n):
    req = urllib.request.Request(B + n, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace"), dict(r.headers)
js, h = get("app.js")
print("RES app.js: tiene selector:", "players-seg" in js, "| playerComp:", "playerComp" in js, "| cache-control:", h.get("Cache-Control"), "| last-modified:", h.get("Last-Modified"))
sw, _ = get("sw.js")
print("RES sw cache:", re.findall(r"municipal-v\d+", sw)[:1])
css, _ = get("styles.css")
print("RES css .players-seg:", ".players-seg" in css, "| .seg:", ".seg {" in css)
html, _ = get("index.html")
print("RES index: id jugadores:", 'id="jugadores"' in html, 'id="players"' in html)
