import json, urllib.request
from collections import Counter
d = json.load(urllib.request.urlopen(urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/soccer/gua.1/teams/7258/roster", headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
ath = d["athletes"]
flat = []
for a in ath:
    flat += a["items"] if isinstance(a, dict) and "items" in a else [a]
print("RES top-level athletes tipos:", Counter(type(a).__name__ for a in ath), "| claves d:", list(d), "| team:", (d.get("team") or {}).get("displayName"), "| season:", d.get("season"))
print("RES posiciones:", Counter((a.get("position") or {}).get("displayName") + "/" + (a.get("position") or {}).get("abbreviation", "") for a in flat if a.get("position")))
print("RES status:", Counter(json.dumps(a.get("status"), ensure_ascii=False)[:90] for a in flat))
print("RES citizenship:", Counter(a.get("citizenship") for a in flat).most_common(8))
for a in flat[:3]:
    print("RES ficha:", json.dumps({k: a.get(k) for k in ("displayName", "jersey", "position", "age", "citizenship", "citizenshipCountry", "flag", "birthPlace", "displayHeight", "headshot", "injuries", "status")}, ensure_ascii=False)[:800])
inj = [a for a in flat if a.get("injuries")]
print("RES lesionados:", len(inj))
for a in inj[:3]:
    print("RES lesión:", a["displayName"], json.dumps(a["injuries"], ensure_ascii=False)[:400])
print("RES con jersey:", sum(1 for a in flat if a.get("jersey")), "| con headshot:", [a["displayName"] for a in flat if a.get("headshot")], json.dumps([a["headshot"] for a in flat if a.get("headshot")][:1])[:200])
print("RES nombres:", sorted(a["displayName"] for a in flat))
