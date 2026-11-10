import json, urllib.request
from collections import Counter
B = "https://a1053.github.io/municipal-calendar-v2/data/"
def get(n):
    with urllib.request.urlopen(B + n, timeout=30) as r:
        return json.load(r)
pl = get("players.json")
ps = pl["players"]
print("RES players updated:", pl.get("updated"), "| jugadores:", len(ps))
print("RES claves de comps:", dict(Counter(k for p in ps for k in (p.get("comps") or {}))), "| con comps:", sum("comps" in p for p in ps))
print("RES PJ max:", max((p["pj"] for p in ps), default=0), "| goles totales:", sum(p["goals"] for p in ps))
for p in ps[:5]:
    print("RES  ", p["name"], p["pj"], p["goals"], p.get("comps"))
m = get("matches.json")["matches"]
print("RES partidos:", dict(Counter((x["competition"], x["state"], bool(x.get("detail"))) for x in m)))
