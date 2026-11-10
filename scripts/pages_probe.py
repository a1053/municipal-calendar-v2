import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, "scripts")
import build_site_data as b
out = Path(tempfile.mkdtemp())
code = b.build(out, None)
print("RES build:", code)
pl = json.loads((out / "data" / "players.json").read_text(encoding="utf-8")) if (out / "data" / "players.json").exists() else json.loads((out / "players.json").read_text(encoding="utf-8"))
ps = pl["players"]
print("RES jugadores:", len(ps), "| PJ máx:", max(p["pj"] for p in ps), "| goles:", sum(p["goals"] for p in ps), "| amarillas:", sum(p["yellow"] for p in ps))
comps = {}
for p in ps:
    for k, v in p["comps"].items():
        c = comps.setdefault(k, dict(pj=0, goals=0))
        c["pj"] += v["pj"]; c["goals"] += v["goals"]
print("RES por competencia:", comps)
for p in ps[:8]:
    print("RES  ", p["name"], p["jersey"], "PJ", p["pj"], "G", p["goals"], "TA", p["yellow"], {k[:6]: (v["pj"], v["goals"]) for k, v in p["comps"].items()})
names = [p["name"] for p in ps]
print("RES nombres:", sorted(names))
