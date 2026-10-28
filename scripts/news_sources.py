"""Noticias de Municipal desde muchas fuentes públicas, sin claves ni cuentas.

Fuentes (todas opcionales; si una falla se sigue con las demás):
  * Google Noticias (RSS) con varias búsquedas
  * Bing Noticias (RSS) con varias búsquedas
  * GDELT (índice mundial de noticias, API gratuita)
  * RSS de medios guatemaltecos (secciones de deportes y búsquedas internas)

Como "Municipal" también es un club de Perú, El Salvador y Costa Rica, y una
palabra de política local, cada nota pasa por `is_relevant`.
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, quote_plus, urlparse

UTC = timezone.utc
STAMP = "%Y-%m-%dT%H:%M:%SZ"

# --------------------------------------------------------------------------
# Fuentes
# --------------------------------------------------------------------------
GOOGLE = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=GT&ceid=GT:es-419"
BING = "https://www.bing.com/news/search?q={q}&format=rss&mkt=es-GT&setlang=es"
GDELT = ("https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode=artlist&format=json"
         "&maxrecords=75&sort=datedesc&timespan=3months")

QUERIES = [
    '"CSD Municipal"',
    '"Municipal" "Liga Nacional" Guatemala',
    '"Rojos" Municipal Guatemala fútbol',
    '"Municipal" Bantrab',
    '"Municipal" Concacaf Guatemala',
]
GDELT_QUERY = '("CSD Municipal" OR "Club Social y Deportivo Municipal" OR "Rojos de Municipal") sourcelang:spanish'

# Búsqueda interna de sitios WordPress (si el sitio no la ofrece, simplemente falla)
WP_SEARCH = {
    "Prensa Libre": "https://www.prensalibre.com/?s=municipal&feed=rss2",
    "Emisoras Unidas": "https://emisorasunidas.com/?s=municipal&feed=rss2",
    "La Hora": "https://lahora.gt/?s=municipal&feed=rss2",
    "Público GT": "https://publicogt.com/?s=municipal&feed=rss2",
}
SPORTS_FEEDS = {
    "Prensa Libre": [
        "https://www.prensalibre.com/deportes/futbol-nacional/feed/",
        "https://www.prensalibre.com/deportes/deporte-nacional/feed/",
        "https://www.prensalibre.com/deportes/feed/",
    ],
    "Emisoras Unidas": ["https://emisorasunidas.com/deportes/feed/", "https://emisorasunidas.com/feed/"],
}


def build_sources() -> list[dict]:
    out = []
    for q in QUERIES:
        out.append({"id": f"google: {q}", "kind": "rss", "url": GOOGLE.format(q=quote_plus(q + " when:90d")), "name": ""})
    for q in QUERIES[:3]:
        out.append({"id": f"bing: {q}", "kind": "rss", "url": BING.format(q=quote_plus(q)), "name": ""})
    out.append({"id": "gdelt", "kind": "gdelt", "url": GDELT.format(q=quote_plus(GDELT_QUERY)), "name": ""})
    for name, urls in SPORTS_FEEDS.items():
        for u in urls:
            out.append({"id": f"rss: {u}", "kind": "rss", "url": u, "name": name, "sports": True})
    for name, u in WP_SEARCH.items():
        out.append({"id": f"búsqueda: {name}", "kind": "rss", "url": u, "name": name})
    return out


# --------------------------------------------------------------------------
# Relevancia
# --------------------------------------------------------------------------
EXCLUDE = re.compile(
    r"deportivo municipal|municipal lime[nñ]o|municipal p[eé]rez zeled[oó]n|p[eé]rez zeled[oó]n|municipal grecia|"
    r"municipal liberia|municipal puntarenas|municipal de lima|\bliga 1\b|per[uú]\b|peruano|"
    r"municipalidad|concejo municipal|elecciones municipales|polic[ií]a municipal|alcald[ií]a|alcalde",
    re.IGNORECASE,
)
CLUB = re.compile(r"\bc\.?s\.?d\.? municipal\b|club social y deportivo municipal|rojos de municipal", re.IGNORECASE)
MUNI = re.compile(r"\bmunicipal\b", re.IGNORECASE)
SPORT = re.compile(
    r"f[uú]tbol|partido|\bgol(es)?\b|liga|rojos|t[eé]cnico|entrenador|jugador|refuerzo|concacaf|cancha|estadio|"
    r"tr[eé]bol|bantrab|apertura|clausura|fecha \d|delantero|portero|volante|defensa|campe[oó]n|cl[aá]sico|"
    r"fichaje|plantel|directiva|afici[oó]n|goleada|victoria|derrota|empate|marcador|tabla",
    re.IGNORECASE,
)
GT_CONTEXT = re.compile(
    r"guatemala|chap[ií]n|liga nacional|bantrab|tr[eé]bol|comunicaciones|xelaj[uú]|antigua|cob[aá]n|mixco|"
    r"malacateco|marquense|guastatoya|aurora|suchitep[eé]quez|zacapa|achuapa|san pedro|motagua|fas\b",
    re.IGNORECASE,
)
TRUSTED = {
    "prensa libre", "soy502", "publinews", "nuestro diario", "emisoras unidas", "la hora", "república",
    "republica.gt", "diario de centro américa", "crónica", "futbolgt", "deportes guatemala", "tigo sports",
    "tn23", "tvn", "canal antigua", "radio sonora", "agn", "guatevision", "guatemala.com", "público gt",
    "publicogt", "liga nacional", "csd municipal", "espn", "prensa comunitaria",
}
TRUSTED_DOMAINS = (".gt", "prensalibre.com", "emisorasunidas.com", "soy502.com", "nuestro.diario", "espn.com.gt",
                   "publicogt.com", "guatemala.com")


def is_relevant(item: dict, sports_feed: bool = False) -> bool:
    """¿Habla del C.S.D. Municipal de Guatemala y no de otro 'municipal'?"""
    text = f"{item['title']} {item.get('summary', '')}"
    title = item["title"]
    if not (CLUB.search(text) or MUNI.search(text)):
        return False
    gt = bool(GT_CONTEXT.search(text)) or _trusted(item)
    # "Club Social y Deportivo Municipal" contiene "deportivo municipal" (club de Perú): se quita antes de excluir.
    if EXCLUDE.search(CLUB.sub(" ", text)) and not (CLUB.search(text) and "guatemala" in text.lower()):
        return False
    if CLUB.search(text):
        return gt or bool(SPORT.search(text))
    # Solo "Municipal": debe estar en el titular (o venir de sección de deportes) y verse deportivo y chapín.
    if not (MUNI.search(title) or sports_feed):
        return False
    return gt and (bool(SPORT.search(text)) or sports_feed)


def _trusted(item: dict) -> bool:
    src = (item.get("source") or "").lower()
    host = urlparse(item.get("url", "")).netloc.lower()
    return src in TRUSTED or any(d in host for d in TRUSTED_DOMAINS) or any(d in src for d in TRUSTED_DOMAINS)


# --------------------------------------------------------------------------
# Lectura de feeds
# --------------------------------------------------------------------------
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _clean(text: str, limit: int = 240) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _iso(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        d = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return ""
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC).strftime(STAMP)


def real_url(url: str) -> str:
    """Bing envía el enlace real dentro de apiclick.aspx?url=..."""
    p = urlparse(url)
    if p.netloc.endswith("bing.com") and "url" in parse_qs(p.query):
        return parse_qs(p.query)["url"][0]
    return url


def parse_feed(xml_text: str, default_source: str = "") -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter():
        if _local(it.tag) not in ("item", "entry"):
            continue
        fields: dict[str, str] = {}
        image = ""
        for ch in it:
            name = _local(ch.tag)
            if name == "link":
                fields.setdefault("link", (ch.attrib.get("href") or ch.text or "").strip())
            elif name in ("title", "pubdate", "published", "updated", "description", "summary"):
                fields.setdefault(name, (ch.text or "").strip())
            elif name == "source":
                fields.setdefault("source", (ch.text or "").strip())
            elif name in ("content", "thumbnail", "enclosure", "image") and not image:
                cand = ch.attrib.get("url") or (ch.text or "").strip()
                if cand.startswith("http") and re.search(r"\.(jpe?g|png|webp)|image", cand + ch.attrib.get("type", ""), re.I):
                    image = cand
        title, link = fields.get("title", ""), fields.get("link", "")
        if not title or not link:
            continue
        source = fields.get("source", "") or default_source
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        items.append({
            "title": _clean(title, 200), "summary": _clean(fields.get("description") or fields.get("summary", "")),
            "url": real_url(link), "source": source,
            "published": _iso(fields.get("pubdate") or fields.get("published") or fields.get("updated")),
            "image": image, "municipal": True,
        })
    return items


def parse_gdelt(text: str) -> list[dict]:
    data = json.loads(text)
    items = []
    for a in data.get("articles", []) or []:
        title, url = (a.get("title") or "").strip(), a.get("url") or ""
        if not title or not url:
            continue
        try:
            when = datetime.strptime(a.get("seendate", ""), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).strftime(STAMP)
        except ValueError:
            when = ""
        items.append({"title": _clean(title, 200), "summary": "", "url": url, "source": a.get("domain", ""),
                      "published": when, "image": a.get("socialimage") or "", "municipal": True})
    return items


# --------------------------------------------------------------------------
# Recolección
# --------------------------------------------------------------------------
def collect(fetch, sources: list[dict] | None = None, workers: int = 8) -> tuple[list[dict], dict]:
    """Lee todas las fuentes en paralelo. `fetch(url) -> texto`. Devuelve (notas, estado por fuente)."""
    sources = sources if sources is not None else build_sources()

    def run(src):
        text = fetch(src["url"])
        items = parse_gdelt(text) if src["kind"] == "gdelt" else parse_feed(text, src.get("name", ""))
        return [i for i in items if is_relevant(i, bool(src.get("sports")))]

    items, status = [], {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [(s, ex.submit(run, s)) for s in sources]
        for src, fut in futures:
            try:
                got = fut.result()
                status[src["id"]] = f"ok ({len(got)})"
                items += got
            except Exception as exc:  # noqa: BLE001
                status[src["id"]] = f"error: {type(exc).__name__}"
    return items, status


def drop_old(items: list[dict], now: datetime, days: int = 150) -> list[dict]:
    out = []
    for i in items:
        if i.get("published"):
            try:
                age = now - datetime.strptime(i["published"], STAMP).replace(tzinfo=UTC)
                if age.days > days:
                    continue
            except ValueError:
                pass
        out.append(i)
    return out
