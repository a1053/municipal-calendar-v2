"""Prueba (solo lectura) de FotMob y OneFootball desde GitHub Actions: ¿responden y traen eventos/alineaciones?"""
import json, re, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "es"}

def get(url, headers=None, raw=False):
    try:
        req = urllib.request.Request(url, headers={**UA, **(headers or {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, body if raw else json.loads(body)
    except Exception as e:  # noqa: BLE001
        return getattr(e, "code", type(e).__name__), None

def keys(o, n=12):
    return list(o)[:n] if isinstance(o, dict) else type(o).__name__

print("== FotMob")
s, d = get("https://www.fotmob.com/api/searchapi/suggest?term=municipal&lang=es")
print(" buscar:", s, keys(d))
team_id = None
if d:
    txt = json.dumps(d)[:600]
    print(" muestra:", txt)
    m = re.search(r'"id":\s*"?(\d+)"?[^{}]*"name":\s*"CSD Municipal"', json.dumps(d))
    team_id = m.group(1) if m else None
for tid in ([team_id] if team_id else []) + ["583560"]:
    s, d = get(f"https://www.fotmob.com/api/teams?id={tid}&ccode3=GTM")
    print(" equipo", tid, s, keys(d))
    if isinstance(d, dict):
        det = d.get("details") or {}
        print("  nombre:", det.get("name"), "| liga:", (det.get("primaryLeagueName")))
        fx = ((d.get("fixtures") or {}).get("allFixtures") or {}).get("fixtures") or []
        past = [f for f in fx if (f.get("status") or {}).get("finished")]
        print("  partidos:", len(fx), "| jugados:", len(past))
        for f in past[-2:]:
            mid = f.get("id")
            s2, md = get(f"https://www.fotmob.com/api/matchDetails?matchId={mid}")
            print("  detalle", mid, s2, keys(md))
            if isinstance(md, dict):
                c = md.get("content") or {}
                ev = ((c.get("matchFacts") or {}).get("events") or {}).get("events") or []
                lu = c.get("lineup") or {}
                print("   eventos:", len(ev), "| alineación:", keys(lu, 6))
        break

print("== OneFootball")
s, html = get("https://onefootball.com/es/equipo/csd-municipal-6195/partidos", raw=True)
print(" equipo/partidos:", s, len(html or ""))
if html:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    print(" NEXT_DATA:", bool(m))
    links = sorted(set(re.findall(r'/es/partido/(\d+)', html)))[:6]
    print(" ids de partido:", links)
    for mid in links[:2]:
        s2, h2 = get(f"https://onefootball.com/es/partido/{mid}", raw=True)
        print("  partido", mid, s2, len(h2 or ""))
        if h2:
            nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h2, re.S)
            if nd:
                j = json.loads(nd.group(1))
                txt = json.dumps(j)
                print("   ¿eventos?:", len(re.findall(r'"(?:goal|yellow|red|substitution)', txt, re.I)), "| ¿alineación?:", "lineup" in txt.lower())
