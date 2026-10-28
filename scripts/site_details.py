"""Detalle por partido, jugadores, rival y vista previa para compartir.

Todo es "mejor esfuerzo": si ESPN cambia la forma de sus datos o falla, estas
funciones devuelven datos vacíos y el sitio se publica igual (sin esa parte).
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/summary?event={id}"
FONT = Path(__file__).resolve().parent / "fonts" / "Poppins-Bold.ttf"
TZ = ZoneInfo("America/Guatemala")

STAT_LABELS = [  # (nombre ESPN, etiqueta)
    ("possessionPct", "Posesión", "%"),
    ("totalShots", "Tiros", ""),
    ("shotsOnTarget", "Tiros al arco", ""),
    ("wonCorners", "Tiros de esquina", ""),
    ("foulsCommitted", "Faltas", ""),
    ("offsides", "Fuera de lugar", ""),
    ("saves", "Atajadas", ""),
    ("yellowCards", "Tarjetas amarillas", ""),
    ("redCards", "Tarjetas rojas", ""),
]


def _num(value):
    try:
        f = float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else f


def _truthy_sub(value) -> bool:
    if isinstance(value, dict):
        return bool(value.get("didSub", True))
    return bool(value)


# --------------------------------------------------------------------------
# Resumen de un partido
# --------------------------------------------------------------------------
def classify(ev: dict):
    """(tipo, es_penal) de un evento de ESPN, o (None, False) si no interesa."""
    t = ev.get("type") or {}
    key = str(t.get("type") or t.get("text") or "").lower().replace(" ", "-")
    if "own" in key and "goal" in key:
        return "own_goal", False
    if key.startswith("goal") or "penalty---scored" in key or key == "penalty-scored":
        return "goal", "penalty" in key
    if "red" in key and "card" in key or "yellow-red" in key or "second-yellow" in key:
        return "red", False
    if "yellow" in key and "card" in key:
        return "yellow", False
    if "substitution" in key:
        return "sub", False
    return None, False


def _athlete(p: dict) -> dict:
    a = (p or {}).get("athlete") or p or {}
    return {"id": str(a.get("id", "")), "name": a.get("displayName") or a.get("fullName") or ""}


def parse_events(obj: dict) -> list[dict]:
    out = []
    for ev in (obj or {}).get("keyEvents") or []:
        kind, pen = classify(ev)
        if not kind:
            continue
        parts = [_athlete(p) for p in ev.get("participants") or []]
        team = ev.get("team") or {}
        clock = ev.get("clock") or {}
        out.append({
            "min": clock.get("displayValue") or "",
            "sort": _num(clock.get("value")) or 0,
            "kind": kind, "penalty": pen,
            "team_id": str(team.get("id", "")),
            "team": team.get("displayName") or "",
            "player": parts[0]["name"] if parts else "",
            "player_id": parts[0]["id"] if parts else "",
            "assist": parts[1]["name"] if kind == "goal" and len(parts) > 1 else "",
            "text": (ev.get("text") or ev.get("shortText") or "") if kind == "sub" else "",
        })
    out.sort(key=lambda e: e["sort"])
    return out


def parse_lineups(obj: dict) -> list[dict]:
    out = []
    for r in (obj or {}).get("rosters") or []:
        team = r.get("team") or {}
        players = []
        for p in r.get("roster") or []:
            a = _athlete(p)
            if not a["name"]:
                continue
            players.append({
                **a,
                "jersey": str(p.get("jersey") or (p.get("athlete") or {}).get("jersey") or ""),
                "pos": ((p.get("position") or {}).get("abbreviation")) or "",
                "starter": bool(p.get("starter")),
                "played": bool(p.get("starter")) or _truthy_sub(p.get("subbedIn")),
            })
        if not players:
            continue
        formation = r.get("formation")
        if isinstance(formation, dict):
            formation = formation.get("summary") or formation.get("name")
        out.append({"team_id": str(team.get("id", "")), "team": team.get("displayName") or "",
                    "home_away": r.get("homeAway") or "", "formation": formation or "", "players": players})
    return out


def parse_stats(obj: dict, home_id: str, away_id: str) -> list[dict]:
    by_team = {}
    for t in ((obj or {}).get("boxscore") or {}).get("teams") or []:
        tid = str((t.get("team") or {}).get("id", ""))
        by_team[tid] = {s.get("name"): s.get("displayValue") for s in t.get("statistics") or [] if isinstance(s, dict)}
    home, away = by_team.get(home_id, {}), by_team.get(away_id, {})
    out = []
    for name, label, suffix in STAT_LABELS:
        h, a = home.get(name), away.get(name)
        if h is None and a is None:
            continue
        hv, av = _num(h), _num(a)
        if hv is None or av is None:
            continue
        out.append({"label": label, "home": f"{h}{suffix}" if suffix and "%" not in str(h) else str(h),
                    "away": f"{a}{suffix}" if suffix and "%" not in str(a) else str(a),
                    "home_v": hv, "away_v": av})
    return out


def parse_summary(obj: dict, match: dict) -> dict:
    detail = {
        "events": parse_events(obj),
        "lineups": parse_lineups(obj),
        "stats": parse_stats(obj, match["home"]["id"], match["away"]["id"]),
    }
    detail["has_data"] = bool(detail["events"] or detail["lineups"] or detail["stats"])
    return detail


# --------------------------------------------------------------------------
# Jugadores (se arma con las alineaciones y eventos de los partidos)
# --------------------------------------------------------------------------
def build_players(details: list[dict], team_id: str) -> list[dict]:
    people: dict[str, dict] = {}

    def get(pid, name):
        key = pid or name
        return people.setdefault(key, {"id": pid, "name": name, "jersey": "", "pos": "", "pj": 0,
                                       "starts": 0, "goals": 0, "assists": 0, "yellow": 0, "red": 0})

    by_name: dict[str, dict] = {}
    for d in details:
        for lu in d.get("lineups", []):
            if lu["team_id"] != team_id:
                continue
            for p in lu["players"]:
                row = get(p["id"], p["name"])
                by_name[p["name"]] = row
                row["jersey"] = p["jersey"] or row["jersey"]
                row["pos"] = p["pos"] or row["pos"]
                row["pj"] += 1 if p["played"] else 0
                row["starts"] += 1 if p["starter"] else 0
        for ev in d.get("events", []):
            if ev["team_id"] != team_id or not ev["player"]:
                continue
            row = by_name.get(ev["player"]) or get(ev.get("player_id", ""), ev["player"])
            by_name[ev["player"]] = row
            if ev["kind"] == "goal":
                row["goals"] += 1
                if ev["assist"]:
                    arow = by_name.get(ev["assist"]) or get("", ev["assist"])
                    by_name[ev["assist"]] = arow
                    arow["assists"] += 1
            elif ev["kind"] == "yellow":
                row["yellow"] += 1
            elif ev["kind"] == "red":
                row["red"] += 1
    rows = [r for r in people.values() if r["name"]]
    rows.sort(key=lambda r: (-r["goals"], -r["assists"], -r["pj"], r["name"]))
    return rows


# --------------------------------------------------------------------------
# Rival del próximo partido
# --------------------------------------------------------------------------
def result_for(m: dict, team_id: str) -> str | None:
    if m.get("state") != "post":
        return None
    h, a = m["home"]["score"], m["away"]["score"]
    if h is None or a is None:
        return None
    mine, theirs = (h, a) if m["home"]["id"] == team_id else (a, h)
    return "G" if mine > theirs else "P" if mine < theirs else "E"


def form_of(events: dict, team_id: str, n: int = 5) -> list[dict]:
    played = [m for m in events.values() if m["state"] == "post" and result_for(m, team_id)]
    played.sort(key=lambda m: m["start"], reverse=True)
    out = []
    for m in played[:n]:
        home = m["home"]["id"] == team_id
        opp = m["away"] if home else m["home"]
        out.append({"result": result_for(m, team_id), "vs": opp["name"], "home": home,
                    "score": f"{m['home']['score']}-{m['away']['score']}", "start": m["start"]})
    return out[::-1]


def build_rival(match: dict, my_id: str, standings: dict, rival_events: dict, season: list[dict]) -> dict | None:
    rival = match["away"] if match["home"]["id"] == my_id else match["home"]
    if not rival.get("id"):
        return None
    row = None
    for g in (standings or {}).get("groups", []):
        for r in g["rows"]:
            if r["team_id"] == rival["id"]:
                row = r
    meetings = []
    for m in season:
        if m["id"] != match["id"] and m["state"] == "post" and {m["home"]["id"], m["away"]["id"]} == {my_id, rival["id"]}:
            meetings.append({"start": m["start"], "home": m["home"]["name"], "away": m["away"]["name"],
                             "score": f"{m['home']['score']}-{m['away']['score']}", "id": m["id"]})
    out = {"team_id": rival["id"], "name": rival["name"], "logo": rival.get("logo", ""),
           "pos": row["pos"] if row else None, "pts": row["pts"] if row else None,
           "pj": row["pj"] if row else None, "form": form_of(rival_events, rival["id"]), "meetings": meetings}
    return out if (out["pos"] or out["form"] or meetings) else None


# --------------------------------------------------------------------------
# Vista previa para compartir (Open Graph)
# --------------------------------------------------------------------------
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def _when(iso: str) -> str:
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    h = d.hour % 12 or 12
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}, {h}:{d.minute:02d} {'p. m.' if d.hour >= 12 else 'a. m.'}"


def share_text(matches: list[dict], now: datetime) -> dict:
    """Título, línea grande y descripción para compartir, según el momento."""
    def score(m):
        s = lambda v: "-" if v is None else v
        return f"{m['home']['name']} {s(m['home']['score'])} - {s(m['away']['score'])} {m['away']['name']}"

    def vs(m):
        return f"{m['home']['name']} vs {m['away']['name']}"

    live = [m for m in matches if m["state"] == "in"]
    nxt = [m for m in matches if m["state"] == "pre" and not m["postponed"]
           and datetime.fromisoformat(m["start"].replace("Z", "+00:00")) > now]
    done = [m for m in matches if m["state"] == "post" and not m["postponed"]]
    if live:
        m = live[0]
        return {"kicker": f"En vivo {m.get('clock') or ''}".strip(), "big": score(m),
                "small": m["competition"], "title": f"En vivo: {score(m)}", "desc": f"{score(m)}. Sigue el partido, la tabla y las noticias de Municipal."}
    if nxt:
        m = nxt[0]
        return {"kicker": "Próximo partido", "big": vs(m), "small": _when(m["start"]),
                "title": f"Próximo partido: {vs(m)}", "desc": f"{vs(m)}, {_when(m['start'])}. Tabla de la Liga Bantrab, resultados y noticias de Municipal."}
    if done:
        m = done[-1]
        return {"kicker": "Último resultado", "big": score(m), "small": m["competition"],
                "title": f"Último resultado: {score(m)}", "desc": f"{score(m)}. Tabla de la Liga Bantrab, partidos y noticias de Municipal."}
    return {"kicker": "", "big": "Municipal", "small": "Partidos, tabla y noticias",
            "title": "Municipal en vivo", "desc": "Partidos, resultados, tabla de la Liga Bantrab y noticias de Municipal."}


def make_og_png(path: Path, text: dict) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#2b0a0f")
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 24, W, H], fill="#d01c24")
    d.rectangle([0, 0, 18, H - 24], fill="#d01c24")

    def font(size):
        try:
            return ImageFont.truetype(str(FONT), size)
        except OSError:
            return ImageFont.load_default()

    def fit(txt, size, max_w):
        while size > 28:
            f = font(size)
            if d.textlength(txt, font=f) <= max_w:
                return f
            size -= 4
        return font(28)

    d.text((70, 60), "Municipal en vivo", font=font(40), fill="#f3dfe1")
    if text["kicker"]:
        d.text((70, 200), text["kicker"], font=font(44), fill="#ffb400")
    f = fit(text["big"], 84, W - 140)
    d.text((70, 270), text["big"], font=f, fill="#ffffff")
    if text["small"]:
        d.text((70, 400), text["small"], font=fit(text["small"], 40, W - 140), fill="#f3dfe1")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return True


def inject_og(index_path: Path, site_url: str, text: dict, image: bool) -> None:
    from html import escape

    site_url = site_url.rstrip("/") + "/"
    tags = [
        '<meta property="og:type" content="website">',
        '<meta property="og:locale" content="es_GT">',
        f'<meta property="og:site_name" content="Municipal en vivo">',
        f'<meta property="og:title" content="{escape(text["title"])}">',
        f'<meta property="og:description" content="{escape(text["desc"])}">',
        f'<meta property="og:url" content="{escape(site_url)}">',
        f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">',
        f'<meta name="twitter:title" content="{escape(text["title"])}">',
        f'<meta name="twitter:description" content="{escape(text["desc"])}">',
    ]
    if image:
        import hashlib
        ver = hashlib.sha1((text["title"] + text["big"] + text["small"]).encode("utf-8")).hexdigest()[:8]
        img = escape(f"{site_url}og.png?v={ver}")  # cambia con el contenido: WhatsApp guarda la imagen en caché
        tags += [f'<meta property="og:image" content="{img}">', '<meta property="og:image:width" content="1200">',
                 '<meta property="og:image:height" content="630">',
                 f'<meta property="og:image:alt" content="{escape(text["big"])}">',
                 f'<meta name="twitter:image" content="{img}">']
    html = index_path.read_text(encoding="utf-8")
    block = "<!--og-->\n  " + "\n  ".join(tags) + "\n  <!--/og-->"
    new = re.sub(r"<!--og-->.*?<!--/og-->", lambda _m: block, html, flags=re.S)
    index_path.write_text(new, encoding="utf-8")
