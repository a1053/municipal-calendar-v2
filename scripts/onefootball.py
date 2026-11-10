"""Complemento de OneFootball: eventos y alineaciones que ESPN no publica.

Solo LEE las páginas públicas de OneFootball (el JSON que ya viene dentro de la página) y
solo se usa como COMPLEMENTO: nunca cambia lo que ya trae ESPN. Si OneFootball falla o cambia
su formato, el sitio sigue igual con ESPN.

Cuidado con los pedidos: 3 páginas del equipo + los partidos que aún no tenemos guardados.
Los partidos terminados se guardan en data/onefootball.json y no se vuelven a pedir.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://onefootball.com"
TEAM_PATH = "/es/equipo/csd-municipal-6195"
TEAM_PAGES = ("/resultados", "/partidos", "")
UA = "Mozilla/5.0 (compatible; MunicipalSitioNoOficial/1.0; +https://github.com/a1053/municipal-calendar-v2)"
MAX_NEW = 12            # páginas de partido nuevas por corrida
MAX_KEEP = 80          # partidos guardados en la caché
PAUSE = 1.0             # segundos entre pedidos
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
IDS = re.compile(r"/es/partido/(\d+)")
NOISE = {"csd", "cd", "fc", "club", "deportivo", "de", "gfc", "cso", "sc", "gt"}


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es"})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (https fijo)
        return r.read().decode("utf-8", "replace")


def _next_data(html: str):
    m = NEXT_DATA.search(html or "")
    return json.loads(m.group(1)) if m else None


def match_ids(html: str) -> list[str]:
    return sorted(set(IDS.findall(html or "")))


def _find(o, key):
    """Primer valor de `key` en cualquier parte del JSON (la página anida los bloques)."""
    stack = [o]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if key in cur:
                return cur[key]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def _minute(label: str) -> tuple[str, float]:
    """"38'" -> ("38'", 38.0); "90'+3" -> ("90'+3", 90.003)."""
    nums = [int(n) for n in re.findall(r"\d+", label or "")]
    if not nums:
        return label or "", 0.0
    return label, nums[0] + (nums[1] / 1000 if len(nums) > 1 else 0)


def _side_id(side, ids: tuple[str, str]) -> str:
    return ids[0] if side == 0 else ids[1]


def parse_events(block: dict, ids: tuple[str, str], names: tuple[str, str]) -> list[dict]:
    """Eventos con la misma forma que usa el sitio para ESPN."""
    out = []
    for ev in (block or {}).get("events") or []:
        typ = ev.get("type") or {}
        case = typ.get("$case")
        data = typ.get(case) or {}
        side = ev.get("teamSide")
        label, sort = _minute(ev.get("timeline"))
        row = {"min": label, "sort": sort, "penalty": False, "team_id": _side_id(side, ids),
               "team": names[0] if side == 0 else names[1], "player": "", "player_id": "", "assist": "", "text": ""}
        if case == "goal":
            gtype = data.get("type")
            row["kind"] = "own_goal" if gtype == 1 else "goal"
            row["penalty"] = gtype == 2
            row["player"] = (data.get("scorer") or {}).get("name", "")
        elif case == "card":
            row["kind"] = "yellow" if data.get("type") == 0 else "red"
            row["player"] = (data.get("player") or {}).get("name", "")
        elif case == "substitution":
            pin = (data.get("playerIn") or {}).get("name", "")
            pout = (data.get("playerOut") or {}).get("name", "")
            row["kind"] = "sub"
            row["player"] = pin
            row["player_out"] = pout
            row["text"] = f"Entra {pin}, sale {pout}".strip(", ") if pin or pout else ""
        else:
            continue
        out.append(row)
    out.sort(key=lambda e: e["sort"])
    return out


def parse_lineups(block: dict, ids: tuple[str, str], names: tuple[str, str]) -> list[dict]:
    lineup = ((block or {}).get("variant") or {}).get("lineup") or {}
    out = []
    for i, key in enumerate(("homeTeam", "awayTeam")):
        team = lineup.get(key) or {}
        variant = team.get("variant") or {}
        players = (variant.get(variant.get("$case", "flat")) or {}).get("players") or []
        rows = []
        for p in players:
            name = p.get("name") or ""
            if not name:
                continue
            rows.append({"id": "", "name": name, "jersey": str(p.get("jerseyNumber") or ""), "pos": "",
                         "starter": True, "place": 0, "played": True})
        if rows:
            out.append({"team_id": ids[i], "team": team.get("teamName") or names[i],
                        "home_away": "home" if i == 0 else "away", "formation": "", "players": rows})
    return out


def parse_match(nd: dict, of_id: str) -> dict | None:
    """Lee un partido de OneFootball. None si la página no trae marcador/equipos."""
    sc = _find(nd, "matchScore")
    if not isinstance(sc, dict):
        return None
    home, away = sc.get("homeTeam") or {}, sc.get("awayTeam") or {}
    if not home.get("name") or not away.get("name"):
        return None
    names = (home["name"], away["name"])
    ids = ("home", "away")
    kick = (sc.get("kickoff") or {}).get("utcTimestamp") or ""
    score = lambda t: int(t["score"]) if str(t.get("score", "")).isdigit() else None  # noqa: E731
    return {
        "of_id": str(of_id), "url": f"{BASE}/es/partido/{of_id}", "kickoff": kick,
        "competition": (sc.get("competition") or {}).get("name", ""),
        "home": names[0], "away": names[1], "hs": score(home), "as": score(away),
        "finished": sc.get("period") == 11 or "fin" in str(sc.get("timePeriod", "")).lower(),
        "events": parse_events(_find(nd, "matchEvents"), ids, names),
        "lineups": parse_lineups(_find(nd, "matchLineup"), ids, names),
    }


# --------------------------------------------------------------------------
def _tokens(name: str) -> set[str]:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return {t for t in re.findall(r"[a-z]+", s) if t not in NOISE}


def _same_team(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    return bool(ta and tb and (ta & tb))


def _utc(iso: str):
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def link(espn_matches: list[dict], of_matches: list[dict], window_h: float = 6) -> dict[str, dict]:
    """{id del partido en ESPN: partido de OneFootball} por hora y nombres de equipos."""
    out, used = {}, set()
    for m in espn_matches:
        start = _utc(m.get("start"))
        if not start or m.get("state") not in ("in", "post"):
            continue
        best, gap = None, timedelta(hours=window_h)
        for o in of_matches:
            k = _utc(o.get("kickoff"))
            if not k or o["of_id"] in used or abs(k - start) > gap:
                continue
            if _same_team(o["home"], m["home"]["name"]) and _same_team(o["away"], m["away"]["name"]):
                best, gap = o, abs(k - start)
        if best:
            used.add(best["of_id"])
            out[m["id"]] = best
    return out


def _retag(of: dict, m: dict) -> dict:
    """Pone los ids de equipo de ESPN en los eventos y alineaciones (home/away -> id real)."""
    ids = {"home": m["home"]["id"], "away": m["away"]["id"]}
    names = {"home": m["home"]["name"], "away": m["away"]["name"]}
    out = {k: of[k] for k in ("of_id", "url", "finished")}
    out["events"] = [{**e, "team_id": ids.get(e["team_id"], e["team_id"]), "team": names.get(e["team_id"], e["team"])}
                     for e in of["events"]]
    out["lineups"] = [{**lu, "team_id": ids.get(lu["home_away"], lu["team_id"]),
                       "team": names.get(lu["home_away"], lu["team"])} for lu in of["lineups"]]
    return out


def collect(espn_matches: list[dict], cache: dict | None, fetch=None, sleep=None) -> tuple[dict, dict]:
    """(datos por partido de ESPN, caché nueva). Nunca lanza: si falla, devuelve lo que se tenga."""
    fetch, sleep = fetch or _fetch, sleep or time.sleep
    cached = {str(k): v for k, v in ((cache or {}).get("matches") or {}).items()}
    found: list[str] = []
    for suffix in TEAM_PAGES:
        try:
            found += match_ids(fetch(BASE + TEAM_PATH + suffix))
        except Exception as exc:  # noqa: BLE001
            print(f"Aviso: OneFootball {suffix or 'inicio'} no disponible ({type(exc).__name__})")
        sleep(PAUSE)
    fresh, new = dict(cached), 0
    for of_id in sorted(set(found)):
        old = cached.get(of_id)
        if old and old.get("finished") and (old.get("events") or old.get("lineups")):
            continue  # terminado y completo: no se vuelve a pedir
        if new >= MAX_NEW:
            break
        new += 1
        try:
            parsed = parse_match(_next_data(fetch(f"{BASE}/es/partido/{of_id}")), of_id)
        except Exception as exc:  # noqa: BLE001
            print(f"Aviso: OneFootball partido {of_id} ({type(exc).__name__})")
            parsed = None
        if parsed:
            fresh[of_id] = parsed
        sleep(PAUSE)
    # solo se guardan los partidos con datos, para no crecer sin límite
    keep = {k: v for k, v in fresh.items() if v.get("events") or v.get("lineups") or not v.get("finished")}
    if len(keep) > MAX_KEEP:
        newest = sorted(keep, key=lambda k: keep[k].get("kickoff") or "")[-MAX_KEEP:]
        keep = {k: keep[k] for k in newest}
    linked = link(espn_matches, [v for v in keep.values() if v.get("events") or v.get("lineups")])
    by_id = {m["id"]: m for m in espn_matches}
    result = {mid: _retag(o, by_id[mid]) for mid, o in linked.items()}
    print(f"OneFootball: {len(found)} partidos vistos, {new} pedidos, {len(result)} enlazados con ESPN")
    return result, {"matches": keep}
