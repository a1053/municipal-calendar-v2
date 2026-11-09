import json, sys
sys.path.insert(0, "scripts")
import onefootball as of
db = json.load(open("data/matches.json"))
ms = []
for m in db.values():
    if m["competition"].startswith("Liga") and m["start"] < "2026-11-09":
        ms.append({"id": m["id"], "start": m["start"], "state": "post", "home": {"id": "h" + m["id"], "name": m["home"]}, "away": {"id": "a" + m["id"], "name": m["away"]}})
res, cache = of.collect(ms, None)
print("partidos ESPN de prueba:", len(ms), "| enlazados:", len(res), "| caché:", len(cache["matches"]))
for mid, r in list(res.items())[:4]:
    m = next(x for x in ms if x["id"] == mid)
    print(" ", m["start"][:10], m["home"]["name"], "vs", m["away"]["name"], "| eventos", len(r["events"]), "| titulares", [len(l["players"]) for l in r["lineups"]])
