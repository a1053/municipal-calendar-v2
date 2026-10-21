#!/usr/bin/env python3
"""Genera municipal.ics a partir del calendario de Municipal en ESPN.

Flujo:
  1. Descarga la página de ESPN (o lee un archivo local con --from-file).
  2. Extrae los partidos: primero del JSON embebido (fechas en UTC, lo más
     fiable) y, si no hay, de la tabla HTML.
  3. Mezcla con data/matches.json (la "base de datos" del repo): detecta
     cambios, sube SEQUENCE cuando algo se reprograma y conserva el historial.
  4. Regenera municipal.ics solo si el contenido cambió.

Si no logra extraer ningún partido termina con error y NO toca nada, para no
borrar el calendario por un fallo temporal de la fuente.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "matches.json"
ICS_PATH = ROOT / "municipal.ics"

SOURCE_URL = "https://www.espn.com.gt/futbol/equipo/calendario/_/id/7258/gua.municipal"
API_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{team}/schedule"
# Competencias a consultar en la API de ESPN (slug -> nombre). Un slug que ESPN
# no reconozca (404) se omite; cualquier otro error aborta la corrida para no
# borrar partidos por un fallo temporal.
API_LEAGUES = {
    "gua.1": "Liga Nacional de Guatemala",
    "concacaf.central.american.cup": "Concacaf Central American Cup",
    "concacaf.champions": "Concacaf Champions Cup",
}
TEAM_ID = "7258"
TEAM_NAME = "Municipal"
CAL_NAME = "Municipal (Guatemala)"
# Zona horaria en la que ESPN muestra las horas de la tabla HTML (solo se usa
# en el respaldo HTML; el JSON embebido trae fechas en UTC).
SOURCE_TZ = ZoneInfo("America/Guatemala")
MATCH_DURATION = timedelta(hours=2)

MONTHS = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
          "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}

GAME_ID_RE = re.compile(r"(?:juegoId|gameId)[/=](\d+)")
TEAM_HREF_RE = re.compile(r"/equipo/_/id/(\d+)")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*([AaPp])\.?\s*[Mm]")
UTC = timezone.utc
STAMP = "%Y-%m-%dT%H:%M:%SZ"


# --------------------------------------------------------------------------
# Descarga
# --------------------------------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-GT,es;q=0.9,en;q=0.5",
}


def fetch(url: str) -> str:
    import requests

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_api(slug: str, fixtures: bool = False):
    """JSON del calendario de una competencia, o None si ESPN no la conoce.

    Sin parámetros ESPN entrega los partidos ya jugados; con fixture=true, los
    que faltan por jugar. Hacen falta las dos consultas.
    """
    import requests

    url = API_URL.format(slug=slug, team=TEAM_ID) + ("?fixture=true" if fixtures else "")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------
# Extracción 0: API JSON de ESPN (fuente principal)
# --------------------------------------------------------------------------
def matches_from_api(obj: dict, competition: str) -> dict:
    out: dict[str, dict] = {}
    for ev in (obj or {}).get("events", []):
        gid = str(ev.get("id", ""))
        comps = ev.get("competitions") or []
        if not gid or not comps:
            continue
        comp = comps[0]
        when = ev.get("date") or comp.get("date")
        if not isinstance(when, str) or not ISO_RE.match(when):
            continue
        home = away = None
        for c in comp.get("competitors", []):
            team = c.get("team") or {}
            name = team.get("displayName") or team.get("name")
            if c.get("homeAway") == "home":
                home = name
            elif c.get("homeAway") == "away":
                away = name
        if not home or not away:
            continue
        venue = (comp.get("venue") or {}).get("fullName") or ""
        out[gid] = {
            "id": gid,
            "start": _to_utc(when).strftime(STAMP),
            "all_day": False,
            "home": home,
            "away": away,
            "competition": competition,
            "venue": venue,
            "url": f"https://www.espn.com.gt/futbol/partido/_/juegoId/{gid}",
        }
    return out


# --------------------------------------------------------------------------
# Extracción 1: JSON embebido (window['__espnfitt__'])
# --------------------------------------------------------------------------
def extract_embedded_json(html: str):
    m = re.search(r"window\['__espnfitt__'\]\s*=\s*", html)
    if not m:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(html[m.end():])
        return obj
    except ValueError:
        return None


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _iso_of(value):
    if isinstance(value, str) and ISO_RE.match(value):
        return value
    if isinstance(value, dict):
        for key in ("date", "dateTime"):
            v = value.get(key)
            if isinstance(v, str) and ISO_RE.match(v):
                return v
    return None


def _to_utc(iso: str) -> datetime:
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC)


def matches_from_json(obj) -> dict:
    out: dict[str, dict] = {}
    for d in _walk(obj):
        when = _iso_of(d.get("date"))
        if not when:
            continue
        link = d.get("link") or d.get("href") or ""
        if isinstance(link, dict):
            link = link.get("href", "")
        gid = None
        for key in ("id", "gameId"):
            if re.fullmatch(r"\d{6,}", str(d.get(key, ""))):
                gid = str(d[key])
                break
        if not gid:
            m = GAME_ID_RE.search(str(link))
            gid = m.group(1) if m else None
        opp = d.get("opponent")
        if not gid or not isinstance(opp, dict):
            continue
        opp_name = opp.get("displayName") or opp.get("name")
        if not opp_name:
            continue
        flag = str(d.get("homeAwayFlag") or d.get("atVs") or "").strip().lower()
        i_am_home = flag != "@"
        league = d.get("league")
        comp = (league.get("displayName") or league.get("name")) if isinstance(league, dict) else league
        start = _to_utc(when)
        out[gid] = {
            "id": gid,
            "start": start.strftime(STAMP),
            "all_day": False,
            "home": TEAM_NAME if i_am_home else opp_name,
            "away": opp_name if i_am_home else TEAM_NAME,
            "competition": comp or "",
            "url": f"https://www.espn.com.gt/futbol/partido/_/juegoId/{gid}",
        }
    return out


# --------------------------------------------------------------------------
# Extracción 2: tabla HTML (respaldo)
# --------------------------------------------------------------------------
def matches_from_html(html: str, today: date | None = None) -> dict:
    from bs4 import BeautifulSoup

    today = today or datetime.now(SOURCE_TZ).date()
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, dict] = {}

    for tr in soup.find_all("tr"):
        game_link = tr.find("a", href=GAME_ID_RE)
        if not game_link:
            continue
        gid = GAME_ID_RE.search(game_link["href"]).group(1)

        # Equipos, en orden de aparición: ESPN lista primero al local.
        teams: list[tuple[str, str]] = []
        for a in tr.find_all("a", href=TEAM_HREF_RE):
            text = a.get_text(strip=True)
            if text:
                teams.append((TEAM_HREF_RE.search(a["href"]).group(1), text))
        if len(teams) != 2 or TEAM_ID not in (teams[0][0], teams[1][0]):
            continue
        home, away = teams[0][1], teams[1][1]

        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if not cells:
            continue

        # Fecha: "Mié., Oct. 21"
        dm = re.search(r"([A-Za-zÁ-ú]{3,})\.?\s+(\d{1,2})\s*$", cells[0])
        if not dm or dm.group(1)[:3].lower() not in MONTHS:
            continue
        month, day = MONTHS[dm.group(1)[:3].lower()], int(dm.group(2))

        # Año: del encabezado de mes previo ("Octubre, 2026").
        title = tr.find_previous(string=re.compile(r"^\s*[A-Za-zÁ-ú]+,\s*\d{4}\s*$"))
        if title:
            year = int(re.search(r"\d{4}", title).group(0))
        else:
            year = today.year
            if date(year, month, day) < today - timedelta(days=180):
                year += 1

        # Hora: la celda/enlace con "3:00 PM".
        tm = None
        for text in [game_link.get_text(strip=True)] + cells:
            tm = TIME_RE.search(text)
            if tm:
                break

        if tm:
            hour = int(tm.group(1)) % 12 + (12 if tm.group(3).lower() == "p" else 0)
            local = datetime(year, month, day, hour, int(tm.group(2)), tzinfo=SOURCE_TZ)
            start, all_day = local.astimezone(UTC).strftime(STAMP), False
        else:  # hora por definir
            start, all_day = date(year, month, day).isoformat(), True

        # Competencia: primera celda que no sea fecha, equipos u hora.
        skip = {cells[0], home, away}
        comp = next((c for c in cells[1:] if c and c not in skip and not TIME_RE.search(c)
                     and c.lower() not in {"v", "tv"}), "")

        out[gid] = {
            "id": gid, "start": start, "all_day": all_day,
            "home": home, "away": away, "competition": comp,
            "url": f"https://www.espn.com.gt/futbol/partido/_/juegoId/{gid}",
        }
    return out


def parse_matches(html: str) -> tuple[dict, str]:
    obj = extract_embedded_json(html)
    if obj is not None:
        found = matches_from_json(obj)
        if found:
            return found, "json"
    return matches_from_html(html), "html"


# --------------------------------------------------------------------------
# Base de datos (data/matches.json) y mezcla
# --------------------------------------------------------------------------
TRACKED = ("start", "all_day", "home", "away", "competition", "venue")


def load_db() -> dict:
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text(encoding="utf-8"))
    return {}


def save_db(db: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(db.items(), key=lambda kv: (kv[1]["start"], kv[0])))
    DB_PATH.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def start_dt(m: dict) -> datetime:
    if m.get("all_day"):
        d = date.fromisoformat(m["start"])
        return datetime(d.year, d.month, d.day, tzinfo=UTC)
    return _to_utc(m["start"])


def merge(old: dict, new: dict, now: datetime) -> dict:
    """Partidos nuevos/cambiados reemplazan a los viejos; los ya jugados se
    conservan como historial; los futuros que ESPN ya no lista se eliminan."""
    result: dict[str, dict] = {}
    stamp = now.strftime(STAMP)
    for mid, m in new.items():
        prev = old.get(mid)
        if prev and all((prev.get(k) or "") == (m.get(k) or "") for k in TRACKED):
            result[mid] = prev
        else:
            m = dict(m)
            m["seq"] = prev["seq"] + 1 if prev else 0
            m["updated"] = stamp
            result[mid] = m
    for mid, prev in old.items():
        if mid not in new and start_dt(prev) < now - timedelta(hours=3):
            result[mid] = prev
    return result


# --------------------------------------------------------------------------
# Generación del .ics
# --------------------------------------------------------------------------
def _esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def _fold(line: str) -> str:
    """Pliega líneas a 75 octetos sin partir caracteres UTF-8."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur, size = [], "", 0
    for ch in line:
        n = len(ch.encode("utf-8"))
        limit = 75 if not parts else 74
        if size + n > limit:
            parts.append(cur)
            cur, size = ch, n
        else:
            cur += ch
            size += n
    parts.append(cur)
    return "\r\n ".join(parts)


def _ics_stamp(iso: str) -> str:
    return _to_utc(iso).strftime("%Y%m%dT%H%M%SZ")


def build_ics(db: dict) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//municipal-calendar//ESPN//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(CAL_NAME)}",
        "X-WR-CALDESC:Partidos de Municipal. Se actualiza automaticamente desde ESPN.",
        "X-WR-TIMEZONE:America/Guatemala",
        "REFRESH-INTERVAL;VALUE=DURATION:PT3H",
        "X-PUBLISHED-TTL:PT3H",
    ]
    for mid, m in sorted(db.items(), key=lambda kv: (kv[1]["start"], kv[0])):
        title = f"{m['home']} vs {m['away']}"
        desc = [f"Competencia: {m['competition']}"] if m.get("competition") else []
        desc += [f"Detalle del partido: {m['url']}", "Fuente: ESPN"]
        lines += [
            "BEGIN:VEVENT",
            f"UID:espn-{mid}@municipal-calendar",
            f"DTSTAMP:{_ics_stamp(m['updated'])}",
            f"SEQUENCE:{m.get('seq', 0)}",
        ]
        if m.get("all_day"):
            d = date.fromisoformat(m["start"])
            lines += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
                      f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}"]
        else:
            s = _to_utc(m["start"])
            lines += [f"DTSTART:{s:%Y%m%dT%H%M%SZ}",
                      f"DTEND:{s + MATCH_DURATION:%Y%m%dT%H%M%SZ}"]
        lines += [
            f"SUMMARY:{_esc(title)}",
            *([f"LOCATION:{_esc(m['venue'])}"] if m.get("venue") else []),
            f"DESCRIPTION:{_esc(chr(10).join(desc))}",
            f"URL:{m['url']}",
            "STATUS:CONFIRMED",
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_esc(title)}",
            "TRIGGER:-PT1H",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


# --------------------------------------------------------------------------
def _annotate(message: str) -> None:
    """Error visible en el resumen de GitHub Actions y en stderr."""
    print(f"::error title=Fallo al leer ESPN::{message}")
    print(message, file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-file", help="leer HTML de un archivo en vez de descargar")
    ap.add_argument("--dry-run", action="store_true", help="mostrar partidos sin escribir")
    args = ap.parse_args(argv)

    found: dict[str, dict] = {}
    notes: list[str] = []
    how = "api"

    if args.from_file:
        found, how = parse_matches(Path(args.from_file).read_text(encoding="utf-8"))
    else:
        for slug, name in API_LEAGUES.items():
            counts = []
            for fixtures in (False, True):  # jugados y por jugar
                try:
                    data = fetch_api(slug, fixtures)
                except Exception as exc:  # noqa: BLE001
                    status = getattr(getattr(exc, "response", None), "status_code", "-")
                    _annotate(f"API de ESPN falló para {slug}"
                              f"{' (por jugar)' if fixtures else ''}: {type(exc).__name__} "
                              f"(HTTP {status}); se aborta para no borrar partidos. "
                              + str(exc)[:160])
                    return 1
                if data is None:
                    counts.append("no existe")
                    break
                part = matches_from_api(data, name)
                counts.append(str(len(part)))
                found.update(part)
            notes.append(f"{slug}: {'/'.join(counts)}")

        if not found:  # respaldo: página HTML
            try:
                html = fetch(SOURCE_URL)
            except Exception as exc:  # noqa: BLE001
                status = getattr(getattr(exc, "response", None), "status_code", "-")
                _annotate(f"Sin datos de la API ({'; '.join(notes)}) y falló la página: "
                          f"{type(exc).__name__} (HTTP {status})")
                return 1
            found, how = parse_matches(html)
            if not found:
                _annotate(
                    f"No se extrajo ningún partido; no se modifica nada. API: {'; '.join(notes)}. "
                    f"Página: bytes={len(html)}, filas_tr={html.count('<tr')}, "
                    f"juegoId={html.count('juegoId')}, fitt={'__espnfitt__' in html}"
                )
                return 1

    print(f"Partidos extraídos: {len(found)} (método: {how}) {'; '.join(notes)}")
    if not found:
        _annotate("No se extrajo ningún partido; no se modifica nada.")
        return 1

    now = datetime.now(UTC).replace(microsecond=0)
    db = merge(load_db(), found, now)

    if args.dry_run:
        for m in sorted(db.values(), key=lambda x: x["start"]):
            print(m["start"], m["home"], "vs", m["away"], "|", m["competition"])
        return 0

    save_db(db)
    ics = build_ics(db)
    current = ICS_PATH.read_bytes().decode("utf-8") if ICS_PATH.exists() else ""
    if ics != current:
        ICS_PATH.write_bytes(ics.encode("utf-8"))
        print(f"municipal.ics actualizado ({len(db)} partidos).")
    else:
        print("Sin cambios.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
