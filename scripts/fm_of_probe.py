"""Explora la estructura de datos de OneFootball (solo lectura)."""
import json, re, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "es"}

def page(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        h = r.read().decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    return h, json.loads(m.group(1)) if m else None

h, nd = page("https://onefootball.com/es/equipo/csd-municipal-6195/partidos")
ids = re.findall(r'/es/partido/(\d+)', h)
print("ids:", sorted(set(ids)))
# estados de partidos en la página del equipo
def walk(o, path="", out=None, pat=None, depth=0):
    if out is None: out = []
    if depth > 14: return out
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}.{k}"
            if pat.search(k): out.append((p, v))
            walk(v, p, out, pat, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:60]):
            walk(v, f"{path}[{i}]", out, pat, depth + 1)
    return out

def show(label, nd, pat, n=14):
    print("==", label)
    for p, v in walk(nd, "", None, re.compile(pat, re.I))[:n]:
        s = json.dumps(v, ensure_ascii=False)
        print(" ", p[:110], "=>", (s[:260] + "…") if len(s) > 260 else s)

# probamos todos los partidos hasta hallar uno jugado
for mid in sorted(set(ids)):
    h2, d2 = page(f"https://onefootball.com/es/partido/{mid}")
    txt = json.dumps(d2)
    print("\n##### partido", mid, "| eventos(goal):", len(re.findall(r'"goal', txt, re.I)), "| len", len(txt))
    show("timeline/events", d2, r"^(events|timeline|matchEvents|keyEvents)$", 4)
    show("lineup", d2, r"lineup|formation", 6)
    show("marcador/estado", d2, r"^(score|period|matchState|status)$", 6)
    break
