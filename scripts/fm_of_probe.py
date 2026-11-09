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


def outline(o, depth=0, maxd=7, key=""):
    pad = "  " * depth
    if depth > maxd: return
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("trackingEvents", "image", "link", "uiKey", "darkModePath"): continue
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}: {type(v).__name__}{'[' + str(len(v)) + ']' if isinstance(v, list) else ''}")
                outline(v, depth + 1, maxd, k)
            else:
                print(f"{pad}{k}: {json.dumps(v, ensure_ascii=False)[:80]}")
    elif isinstance(o, list) and o:
        print(f"{pad}[0]:")
        outline(o[0], depth + 1, maxd, key)

kinds = {}
first = True
for mid in sorted(ids):
    try:
        _, d = page(f"https://onefootball.com/es/partido/{mid}")
    except Exception:
        continue
    sc = next(find(d, "matchScore"), None) or {}
    if (sc.get("homeTeam") or {}).get("score") in (None, "-", ""): continue
    if first:
        first = False
        print("== matchScore"); outline(sc, 0, 4)
        print("== matchLineup (esquema)"); outline(next(find(d, "matchLineup")), 0, 9)
        print("== matchInfo"); outline(next(find(d, "matchInfo"), None), 0, 5)
        pp = d["props"]["pageProps"]
        print("== pageProps claves:", [k for k in pp if k != "containers"])
        for k in ("matchId", "seo", "metadata", "kickoff", "date"):
            if k in pp: print(k, json.dumps(pp[k], ensure_ascii=False)[:300])
    for ev in (next(find(d, "matchEvents"), None) or {}).get("events", []):
        t = ev["type"]; c = t["$case"]
        extra = {k: (v.get("type") if isinstance(v, dict) else v) for k, v in t.get(c, {}).items()} if isinstance(t.get(c), dict) else {}
        kinds.setdefault((c, ev.get("name"), json.dumps(extra, sort_keys=True)[:80]), 0)
        kinds[(c, ev.get("name"), json.dumps(extra, sort_keys=True)[:80])] += 1
print("== tipos de evento en 10 partidos")
for k, n in sorted(kinds.items(), key=lambda x: -x[1]): print(" ", n, k)
