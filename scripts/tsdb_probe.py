"""Prueba de TheSportsDB (clave gratis 123) para la Liga Nacional de Guatemala. Solo lectura."""
import json, urllib.request, time

B = "https://www.thesportsdb.com/api/v1/json/123/"

def get(p):
    try:
        with urllib.request.urlopen(urllib.request.Request(B + p, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001
        print("  !", p, type(e).__name__, getattr(e, "code", ""))
        return {}

for season in ("2026-2027", "2025-2026"):
    ev = get(f"eventsseason.php?id=4817&s={season}").get("events") or []
    print("== temporada", season, "partidos:", len(ev))
    mine = [e for e in ev if "Municipal" in (e.get("strHomeTeam") or "") + (e.get("strAwayTeam") or "")]
    done = [e for e in mine if e.get("intHomeScore") not in (None, "")]
    print("  de Municipal:", len(mine), "| jugados:", len(done))
    for e in done[-4:]:
        i = e["idEvent"]
        tl = get(f"lookuptimeline.php?id={i}").get("timeline") or []
        lu = get(f"lookuplineup.php?id={i}").get("lineup") or []
        kinds = {}
        for t in tl:
            k = t.get("strTimeline") or "?"
            kinds[k] = kinds.get(k, 0) + 1
        starters = sum(1 for p in lu if str(p.get("strSubstitute", "")).lower() in ("no", ""))
        print(f"  {e['dateEvent']} {e['strHomeTeam']} {e['intHomeScore']}-{e['intAwayScore']} {e['strAwayTeam']} (id {i}): timeline={len(tl)} {kinds} | alineación={len(lu)} (titulares ~{starters})")
        if tl:
            print("    ej:", {k: tl[0].get(k) for k in ("strTimeline", "strTimelineDetail", "strPlayer", "intTime")})
        time.sleep(2)
    if done:
        break
