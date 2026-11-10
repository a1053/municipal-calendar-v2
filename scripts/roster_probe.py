"""¿Qué trae ESPN del plantel de Municipal? (solo lectura)"""
import json, urllib.request
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001
        print("RES !", u[-70:], type(e).__name__, getattr(e, "code", ""))
        return None
URLS = [
  "https://site.api.espn.com/apis/site/v2/sports/soccer/gua.1/teams/7258/roster",
  "https://site.api.espn.com/apis/site/v2/sports/soccer/gua.1/teams/7258?enable=roster",
  "https://sports.core.api.espn.com/v2/sports/soccer/leagues/gua.1/seasons/2026/teams/7258/athletes?limit=60",
]
for u in URLS:
    d = get(u)
    if not d: continue
    print("RES ok", u[-60:], "| claves:", list(d)[:10])
    ath = d.get("athletes") or (d.get("team") or {}).get("athletes") or d.get("items") or []
    print("RES atletas:", len(ath))
    flat = []
    for a in ath:
        if isinstance(a, dict) and "items" in a: flat += a["items"]
        else: flat.append(a)
    for a in flat[:4]:
        print("RES  ", json.dumps(a, ensure_ascii=False)[:700])
    if flat:
        keys = set()
        for a in flat:
            if isinstance(a, dict): keys |= set(a)
        print("RES claves de atleta:", sorted(keys))
        print("RES con foto:", sum(1 for a in flat if isinstance(a, dict) and a.get("headshot")), "| con edad:", sum(1 for a in flat if isinstance(a, dict) and a.get("age")), "| con posición:", sum(1 for a in flat if isinstance(a, dict) and a.get("position")), "| con nacionalidad:", sum(1 for a in flat if isinstance(a, dict) and (a.get("citizenship") or a.get("birthPlace"))))
        break
