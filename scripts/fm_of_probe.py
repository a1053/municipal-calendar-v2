"""Explora la estructura de datos de OneFootball (solo lectura)."""
import json, re, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "es"}

def page(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        h = r.read().decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    return h, json.loads(m.group(1)) if m else None


ids = set()
for suffix in ("resultados", "partidos", ""):
    try:
        h, _ = page("https://onefootball.com/es/equipo/csd-municipal-6195" + ("/" + suffix if suffix else ""))
        found = set(re.findall(r'/es/partido/(\d+)', h))
        print("pagina", suffix or "home", "ids:", sorted(found))
        ids |= found
    except Exception as e:  # noqa: BLE001
        print("pagina", suffix, "error", type(e).__name__, getattr(e, "code", ""))

def comps(d):
    out = []
    for i, c in enumerate((d["props"]["pageProps"].get("containers") or [])):
        def rec(o, depth=0):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "contentType" and isinstance(v, dict):
                        out.append((i, list(v)))
                    rec(v, depth + 1)
            elif isinstance(o, list):
                for v in o: rec(v, depth + 1)
        rec(c)
    return out

def find(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: yield v
            yield from find(v, key)
    elif isinstance(o, list):
        for v in o: yield from find(v, key)

shown = 0
for mid in sorted(ids):
    try:
        _, d = page(f"https://onefootball.com/es/partido/{mid}")
    except Exception as e:  # noqa: BLE001
        print(mid, "error", getattr(e, "code", type(e).__name__)); continue
    sc = next(find(d, "matchScore"), None) or {}
    hs = (sc.get("homeTeam") or {}).get("score"); as_ = (sc.get("awayTeam") or {}).get("score")
    lu = next(find(d, "matchLineup"), None)
    variant = list((lu or {}).get("variant", {}))[:2]
    print("partido", mid, "marcador", hs, as_, "| alineación variante:", variant)
    if hs not in (None, "-", "") and shown < 1:
        shown += 1
        print(" componentes (contenedor, claves):", comps(d))
        if lu:
            print(" matchLineup:", json.dumps(lu, ensure_ascii=False)[:1800])
        for key in ("matchEvents", "matchTimeline", "matchSummary", "keyEvents", "events", "matchFacts"):
            v = next(find(d, key), None)
            if v is not None:
                print(" ", key, "=>", json.dumps(v, ensure_ascii=False)[:1800])
