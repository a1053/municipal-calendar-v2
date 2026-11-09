"""Prueba de cobertura de API-Football para la Liga Nacional de Guatemala (solo lectura).

Usa la clave de la variable API_FOOTBALL_KEY (secreto de GitHub). Nunca imprime la clave.
Consulta pocas veces (el plan gratis da 100 al día).
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://v3.football.api-sports.io"
KEY = os.environ.get("API_FOOTBALL_KEY", "").strip()


def call(path, **params):
    url = f"{BASE}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"x-apisports-key": KEY, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! {path} {params}: {type(exc).__name__} {getattr(exc, 'code', '')}")
        return {}
    if data.get("errors"):
        print(f"  ! {path} {params}: errores de la API: {data['errors']}")
    return data


def main():
    if not KEY:
        print("Falta el secreto API_FOOTBALL_KEY")
        return 1
    print("== Cuenta")
    st = call("status").get("response") or {}
    if isinstance(st, dict):
        print("  plan:", (st.get("subscription") or {}).get("plan"), "| consultas hoy:", (st.get("requests") or {}).get("current"), "de", (st.get("requests") or {}).get("limit_day"))

    print("== Ligas de Guatemala")
    leagues = call("leagues", country="Guatemala").get("response") or []
    target = None
    for lg in leagues:
        info = lg["league"]
        seasons = {s["year"]: s for s in lg.get("seasons", [])}
        s26 = seasons.get(2026) or seasons.get(2025)
        cov = (s26 or {}).get("coverage", {}).get("fixtures", {}) if s26 else {}
        print(f"  {info['id']} {info['name']} ({info['type']}) temporadas={sorted(seasons)[-3:]} 2026: eventos={cov.get('events')} alineaciones={cov.get('lineups')} stats={cov.get('statistics_fixtures')}")
        if "nacional" in info["name"].lower() and info["type"] == "League":
            target = info["id"]
    if not target:
        print("No encontré la Liga Nacional")
        return 0

    for season in (2026, 2025):
        print(f"== Municipal en la liga {target}, temporada {season}")
        teams = call("teams", league=target, season=season).get("response") or []
        muni = next((t["team"] for t in teams if "municipal" in t["team"]["name"].lower()), None)
        print("  equipos:", len(teams), "| Municipal:", muni and (muni["id"], muni["name"]))
        if not muni:
            continue
        fx = call("fixtures", league=target, season=season, team=muni["id"], last=5).get("response") or []
        for f in fx:
            print("  partido", f["fixture"]["id"], f["fixture"]["date"][:10], f["teams"]["home"]["name"], f["goals"]["home"], "-", f["goals"]["away"], f["teams"]["away"]["name"], f["fixture"]["status"]["short"])
        done = [f for f in fx if f["fixture"]["status"]["short"] in ("FT", "AET", "PEN")]
        for f in done[:2]:
            d = (call("fixtures", id=f["fixture"]["id"]).get("response") or [{}])[0]
            ev = d.get("events") or []
            kinds = {}
            for e in ev:
                kinds[e.get("type")] = kinds.get(e.get("type"), 0) + 1
            lu = d.get("lineups") or []
            print(f"  detalle {f['fixture']['id']}: eventos={len(ev)} {kinds} | alineaciones={len(lu)} formaciones={[l.get('formation') for l in lu]} titulares={[len(l.get('startXI') or []) for l in lu]} | estadísticas={len(d.get('statistics') or [])}")
        if done:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
