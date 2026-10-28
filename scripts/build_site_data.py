#!/usr/bin/env python3
"""Genera los JSON que alimentan el sitio web de Municipal (GitHub Pages).

Salida (en --out, por defecto site/data):
  matches.json    partidos de Municipal con marcador y estado (ESPN)
  standings.json  tabla de posiciones de la Liga Nacional (ESPN)
  news.json       noticias de Municipal y de la Liga (ESPN + Google News RSS)
  meta.json       cuándo se generó y qué fuentes funcionaron

Reglas de seguridad (igual que el calendario):
  * Si no se logra leer NINGÚN partido, termina con error y no escribe nada:
    así el workflow no publica un sitio vacío y se queda el anterior.
  * Tabla y noticias son "mejor esfuerzo": si fallan, se reutiliza la última
    versión publicada (--previous) marcada como `stale`, o se publica vacía.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_details as sd  # noqa: E402
import update_calendar as cal  # noqa: E402  (reutiliza API de ESPN y la "base de datos")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "site" / "data"
UTC = timezone.utc

LEAGUE_SLUG = "gua.1"
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/soccer/{slug}/standings"
NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/news?limit=50"
GNEWS_URL = ("https://news.google.com/rss/search?q={q}&hl=es-419&gl=GT&ceid=GT:es-419")
GNEWS_QUERY = '"CSD Municipal" OR "Rojos de Municipal" OR "Municipal" "Liga Nacional" Guatemala'

# Municipal también es un club peruano (y hay otros "Municipal"): se descartan.
NEWS_EXCLUDE = re.compile(
    r"deportivo municipal|\bliga 1\b|per[uú]\b|peruano|municipalidad|municipal de lima",
    re.IGNORECASE,
)
MUNI_WORDS = re.compile(r"\bmunicipal\b|\brojos\b", re.IGNORECASE)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def _num(value):
    """Convierte puntaje/estadística de ESPN (str, número o dict) en número."""
    if isinstance(value, dict):
        value = value.get("value", value.get("displayValue"))
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else f


def _logo(team: dict) -> str:
    if team.get("logo"):
        return team["logo"]
    logos = team.get("logos") or []
    if logos and isinstance(logos[0], dict):
        return logos[0].get("href", "")
    return ""


def _get_json(url: str):
    import requests

    resp = requests.get(url, headers=cal.HEADERS, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------
# Partidos con marcador
# --------------------------------------------------------------------------
def events_from_api(obj: dict, competition: str, slug: str = "") -> dict:
    out: dict[str, dict] = {}
    for ev in (obj or {}).get("events", []):
        gid = str(ev.get("id", ""))
        comps = ev.get("competitions") or []
        if not gid or not comps:
            continue
        comp = comps[0]
        when = ev.get("date") or comp.get("date")
        if not isinstance(when, str) or not cal.ISO_RE.match(when):
            continue

        sides: dict[str, dict] = {}
        for c in comp.get("competitors", []):
            team = c.get("team") or {}
            sides[c.get("homeAway")] = {
                "id": str(team.get("id", "")),
                "name": team.get("displayName") or team.get("name") or "",
                "logo": _logo(team),
                "score": _num(c.get("score")),
                "winner": c.get("winner"),
            }
        home, away = sides.get("home"), sides.get("away")
        if not home or not away or not home["name"] or not away["name"]:
            continue

        status = (comp.get("status") or ev.get("status") or {})
        stype = status.get("type") or {}
        state = stype.get("state") or "pre"
        completed = bool(stype.get("completed")) or state == "post"
        name = (stype.get("name") or "").upper()
        postponed = any(w in name for w in ("POSTPONED", "CANCELED", "CANCELLED", "SUSPENDED", "ABANDONED"))
        if state == "post" and home["score"] is None and away["score"] is None:
            home["score"] = away["score"] = None  # sin marcador conocido

        out[gid] = {
            "id": gid,
            "start": cal._to_utc(when).strftime(cal.STAMP),
            "competition": competition,
            "slug": slug,
            "venue": (comp.get("venue") or {}).get("fullName") or "",
            "state": state,                      # pre | in | post
            "completed": completed,
            "postponed": postponed,
            "status": stype.get("shortDetail") or stype.get("detail") or stype.get("description") or "",
            "clock": status.get("displayClock") or "",
            "home": {k: home[k] for k in ("id", "name", "logo", "score")},
            "away": {k: away[k] for k in ("id", "name", "logo", "score")},
            "url": f"https://www.espn.com.gt/futbol/partido/_/juegoId/{gid}",
        }
    return out


def history_from_db(db: dict, have: set) -> dict:
    """Partidos que ya no devuelve la API pero siguen en data/matches.json."""
    out = {}
    now = datetime.now(UTC)
    for mid, m in db.items():
        if mid in have or m.get("all_day"):
            continue
        past = cal.start_dt(m) < now
        out[mid] = {
            "id": mid, "start": m["start"], "competition": m.get("competition", ""),
            "venue": m.get("venue", ""), "state": "post" if past else "pre",
            "completed": past, "postponed": False, "status": "", "clock": "",
            "home": {"id": "", "name": m["home"], "logo": "", "score": None},
            "away": {"id": "", "name": m["away"], "logo": "", "score": None},
            "url": m.get("url", ""),
        }
    return out


def result_for_municipal(m: dict) -> str | None:
    """'G', 'E' o 'P' según el marcador, desde la perspectiva de Municipal."""
    if m["state"] != "post":
        return None
    h, a = m["home"]["score"], m["away"]["score"]
    if h is None or a is None:
        return None
    mine, theirs = (h, a) if m["home"]["id"] == cal.TEAM_ID or m["home"]["name"] == cal.TEAM_NAME else (a, h)
    return "G" if mine > theirs else "P" if mine < theirs else "E"


# --------------------------------------------------------------------------
# Tabla de posiciones
# --------------------------------------------------------------------------
STAT_KEYS = {
    "gamesPlayed": "pj", "wins": "g", "ties": "e", "losses": "p",
    "pointsFor": "gf", "pointsAgainst": "gc", "pointDifferential": "dg",
    "points": "pts", "rank": "rank",
}


def standings_from_api(obj: dict) -> list[dict]:
    groups = []
    nodes = (obj or {}).get("children") or [obj or {}]
    for child in nodes:
        entries = ((child.get("standings") or {}).get("entries")) or []
        rows = []
        for e in entries:
            team = e.get("team") or {}
            row = {"team_id": str(team.get("id", "")),
                   "name": team.get("displayName") or team.get("name") or "",
                   "logo": _logo(team)}
            stats = {s.get("name"): _num(s) for s in e.get("stats", []) if isinstance(s, dict)}
            for src, dst in STAT_KEYS.items():
                row[dst] = stats.get(src)
            note = e.get("note") or {}
            row["note"] = note.get("description", "") if isinstance(note, dict) else ""
            if row["name"]:
                rows.append(row)
        if not rows:
            continue
        rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 999,
                                 -(r["pts"] or 0), -(r["dg"] or 0)))
        for i, r in enumerate(rows, 1):
            r["pos"] = i
            r["is_municipal"] = r["team_id"] == cal.TEAM_ID or r["name"] == cal.TEAM_NAME
        groups.append({"name": child.get("name") or (child.get("standings") or {}).get("name") or "",
                       "rows": rows})
    return groups


# --------------------------------------------------------------------------
# Noticias
# --------------------------------------------------------------------------
def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime(cal.STAMP)


def espn_news(obj: dict) -> list[dict]:
    items = []
    for a in (obj or {}).get("articles", []):
        link = ((a.get("links") or {}).get("web") or {}).get("href")
        title = a.get("headline")
        if not link or not title:
            continue
        cats = a.get("categories") or []
        about_muni = any(str(c.get("teamId", "")) == cal.TEAM_ID for c in cats if isinstance(c, dict)) \
            or bool(MUNI_WORDS.search(f"{title} {a.get('description', '')}"))
        images = a.get("images") or []
        try:
            when = _iso(cal._to_utc(a["published"])) if a.get("published") else ""
        except ValueError:
            when = ""
        items.append({"title": title, "summary": a.get("description") or "", "url": link,
                      "source": "ESPN", "published": when,
                      "image": images[0].get("url", "") if images and isinstance(images[0], dict) else "",
                      "municipal": about_muni})
    return items


def google_news(xml_text: str) -> list[dict]:
    items = []
    root = ET.fromstring(xml_text)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        if NEWS_EXCLUDE.search(title) or not MUNI_WORDS.search(title):
            continue
        try:
            when = _iso(parsedate_to_datetime(it.findtext("pubDate"))) if it.findtext("pubDate") else ""
        except (TypeError, ValueError):
            when = ""
        items.append({"title": title, "summary": "", "url": link, "source": source or "Google News",
                      "published": when, "image": "", "municipal": True})
    return items


def merge_news(*lists: list[dict], limit: int = 40) -> list[dict]:
    seen, out = set(), []
    for item in sorted((i for l in lists for i in l), key=lambda i: i["published"], reverse=True):
        key = re.sub(r"\W+", " ", item["title"].lower()).strip()[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:limit]


def _previous(prev_dir: Path | None, name: str):
    if prev_dir and (prev_dir / name).exists():
        try:
            return json.loads((prev_dir / name).read_text(encoding="utf-8"))
        except ValueError:
            return None
    return None


MAX_DETAILS = 45


def build_details(matches: list[dict], standings: dict, out_dir: Path, now: datetime, sources: dict) -> list[dict]:
    """Detalle por partido (cronología, alineaciones, estadísticas, rival).

    Devuelve la lista de detalles usados para armar la tabla de jugadores.
    Cualquier fallo se salta: el partido simplemente queda sin página de detalle.
    """
    nxt = next((m for m in matches if m["state"] == "pre" and not m["postponed"]
                and cal._to_utc(m["start"]) > now), None)
    wanted = [m for m in matches if m.get("slug") and (m["state"] in ("in", "post") or m is nxt)]
    wanted = wanted[-MAX_DETAILS:]
    (out_dir / "match").mkdir(parents=True, exist_ok=True)
    used, ok, failed = [], 0, 0
    for m in wanted:
        try:
            detail = sd.parse_summary(_get_json(sd.SUMMARY_URL.format(slug=m["slug"], id=m["id"])), m)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"Aviso: sin detalle del partido {m['id']} ({type(exc).__name__})")
            continue
        rival = None
        if m is nxt and m["slug"] == LEAGUE_SLUG:
            rid = (m["away"] if m["home"]["id"] == cal.TEAM_ID else m["home"])["id"]
            try:
                rival_events = events_from_api(_get_json(cal.API_URL.format(slug=LEAGUE_SLUG, team=rid)) or {}, "", LEAGUE_SLUG)
            except Exception as exc:  # noqa: BLE001
                print(f"Aviso: sin calendario del rival ({type(exc).__name__})")
                rival_events = {}
            rival = sd.build_rival(m, cal.TEAM_ID, standings, rival_events, matches)
        if not detail["has_data"] and not rival:
            continue
        ok += 1
        m["detail"] = True
        used.append(detail)
        payload = {"id": m["id"], "updated": now.strftime(cal.STAMP), "rival": rival,
                   **{k: detail[k] for k in ("events", "lineups", "stats")}}
        (out_dir / "match" / f"{m['id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    sources["details"] = "ok" if ok or not wanted else "error"
    print(f"Detalles: {ok} partidos con detalle, {failed} con error")
    return used


def build(out_dir: Path, prev_dir: Path | None, now: datetime | None = None,
          site_url: str | None = None, index_path: Path | None = None) -> int:
    now = now or datetime.now(UTC).replace(microsecond=0)
    stamp = _iso(now)
    sources: dict[str, str] = {}

    # 1) Partidos (crítico)
    found: dict[str, dict] = {}
    for slug, name in cal.API_LEAGUES.items():
        for fixtures in (False, True):
            try:
                data = cal.fetch_api(slug, fixtures)
            except Exception as exc:  # noqa: BLE001
                print(f"::error title=ESPN partidos::{slug}: {type(exc).__name__} {str(exc)[:160]}")
                return 1
            if data is None:
                break
            found.update(events_from_api(data, name, slug))
    if not found:
        print("::error title=ESPN partidos::sin partidos; no se publica nada")
        return 1
    sources["matches"] = "ok"
    found.update(history_from_db(cal.load_db(), set(found)))
    matches = sorted(found.values(), key=lambda m: (m["start"], m["id"]))
    for m in matches:
        m["result"] = result_for_municipal(m)

    # 2) Tabla (mejor esfuerzo)
    standings = {"groups": [], "stale": False}
    try:
        groups = standings_from_api(_get_json(STANDINGS_URL.format(slug=LEAGUE_SLUG)))
        if not groups:
            raise ValueError("tabla vacía")
        standings, sources["standings"] = {"groups": groups, "stale": False}, "ok"
    except Exception as exc:  # noqa: BLE001
        print(f"Aviso: tabla no disponible ({type(exc).__name__}: {str(exc)[:120]})")
        old = _previous(prev_dir, "standings.json")
        if old and old.get("groups"):
            standings = {**old, "stale": True}
        sources["standings"] = "stale" if standings["groups"] else "error"

    # 3) Noticias (mejor esfuerzo, dos fuentes independientes)
    espn_items, g_items = [], []
    try:
        espn_items = espn_news(_get_json(NEWS_URL.format(slug=LEAGUE_SLUG)))
        sources["news_espn"] = "ok"
    except Exception as exc:  # noqa: BLE001
        print(f"Aviso: noticias ESPN no disponibles ({type(exc).__name__})")
        sources["news_espn"] = "error"
    try:
        import requests
        from urllib.parse import quote

        r = requests.get(GNEWS_URL.format(q=quote(GNEWS_QUERY)), headers=cal.HEADERS, timeout=30)
        r.raise_for_status()
        g_items = google_news(r.text)
        sources["news_google"] = "ok"
    except Exception as exc:  # noqa: BLE001
        print(f"Aviso: Google News no disponible ({type(exc).__name__})")
        sources["news_google"] = "error"

    news = {"municipal": merge_news([i for i in espn_items if i["municipal"]], g_items),
            "liga": merge_news([i for i in espn_items if not i["municipal"]], limit=20),
            "stale": False}
    if not news["municipal"] and not news["liga"]:
        old = _previous(prev_dir, "news.json")
        if old:
            news = {**old, "stale": True}

    out_dir.mkdir(parents=True, exist_ok=True)
    details = build_details(matches, standings, out_dir, now, sources)
    players = sd.build_players(details, cal.TEAM_ID)

    if site_url and index_path and index_path.exists():
        text = sd.share_text(matches, now)
        has_img = False
        try:
            has_img = sd.make_og_png(index_path.parent / "og.png", text)
        except Exception as exc:  # noqa: BLE001
            print(f"Aviso: no se pudo crear og.png ({type(exc).__name__}: {exc})")
        sd.inject_og(index_path, site_url, text, has_img)
        sources["share"] = "ok" if has_img else "sin imagen"

    files = {
        "matches.json": {"updated": stamp, "team_id": cal.TEAM_ID, "team": cal.TEAM_NAME, "matches": matches},
        "standings.json": standings,
        "players.json": {"updated": stamp, "players": players},
        "news.json": news,
        "meta.json": {"updated": stamp, "sources": sources},
    }
    for name, payload in files.items():
        (out_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Sitio: {len(matches)} partidos, tabla={sources['standings']}, "
          f"noticias={len(news['municipal'])}+{len(news['liga'])}  fuentes={sources}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--previous", type=Path, help="carpeta con los JSON publicados antes (respaldo)")
    ap.add_argument("--site-url", help="URL pública del sitio (para la vista previa al compartir)")
    ap.add_argument("--index", type=Path, help="index.html del sitio a publicar (se le agregan metaetiquetas)")
    args = ap.parse_args(argv)
    return build(args.out, args.previous, site_url=args.site_url, index_path=args.index)


if __name__ == "__main__":
    sys.exit(main())
