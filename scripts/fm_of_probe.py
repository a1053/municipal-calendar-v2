"""¿OneFootball trae formación/posiciones o estadísticas del partido? (solo lectura)"""
import json, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "es"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return getattr(e, "code", type(e).__name__), ""
def nd(h):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    return json.loads(m.group(1)) if m else None
def find(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: yield v
            yield from find(v, key)
    elif isinstance(o, list):
        for v in o: yield from find(v, key)
_, h = get("https://onefootball.com/es/equipo/csd-municipal-6195/resultados")
ids = sorted(set(re.findall(r"/es/partido/(\d+)", h)))
variants, comps, names, order = {}, {}, set(), []
for i in ids:
    s, page = get(f"https://onefootball.com/es/partido/{i}")
    d = nd(page)
    if not d: continue
    for lu in find(d, "matchLineup"):
        lin = ((lu or {}).get("variant") or {}).get("lineup") or {}
        for side in ("homeTeam", "awayTeam"):
            v = (lin.get(side) or {}).get("variant") or {}
            variants[v.get("$case")] = variants.get(v.get("$case"), 0) + 1
            if i == ids[0] and side == "homeTeam":
                flat = (v.get("flat") or {}).get("players") or []
                print("orden titulares:", [(p.get("name"), p.get("jerseyNumber")) for p in flat])
                print("claves de jugador:", sorted(flat[0].keys()) if flat else None)
                print("claves de equipo:", sorted((lin.get(side) or {}).keys()))
                print("claves del lineup:", sorted(lin.keys()))
    txt = json.dumps(d)
    for kw in ("possession", "posesi", "shots", "tiros", "estad", "statistic", "formation", "formaci"):
        comps[kw] = comps.get(kw, 0) + len(re.findall(kw, txt, re.I))
print("variantes de alineación:", variants)
print("menciones en 10 partidos:", comps)
for sub in ("/estadisticas", "/stats", "/alineaciones"):
    s, page = get(f"https://onefootball.com/es/partido/{ids[0]}{sub}")
    print("subpágina", sub, s, len(page))
