"""Plantel de Municipal según ESPN (número, posición, edad, nacionalidad) unido con las estadísticas del sitio.

Mejor esfuerzo: si ESPN no responde o cambia el formato, el sitio sigue con el último plantel publicado
(o sin la vista de plantel). Los datos que ESPN no trae (foto, edad) simplemente no se muestran.
"""
from __future__ import annotations

import site_details as sd

URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{team}/roster"

POSITIONS = {  # abreviatura ESPN -> (singular, plural, orden)
    "G": ("Portero", "Porteros", 0),
    "D": ("Defensa", "Defensas", 1),
    "M": ("Mediocampista", "Mediocampistas", 2),
    "F": ("Delantero", "Delanteros", 3),
}
COUNTRIES = {
    "Guatemala": "Guatemala", "Costa Rica": "Costa Rica", "Argentina": "Argentina", "Uruguay": "Uruguay", "Cuba": "Cuba",
    "Ecuador": "Ecuador", "Colombia": "Colombia", "Honduras": "Honduras", "El Salvador": "El Salvador", "Panama": "Panamá",
    "Mexico": "México", "Brazil": "Brasil", "Chile": "Chile", "Peru": "Perú", "Venezuela": "Venezuela", "Paraguay": "Paraguay",
    "Nicaragua": "Nicaragua", "Jamaica": "Jamaica", "Trinidad and Tobago": "Trinidad y Tobago", "Haiti": "Haití",
    "Spain": "España", "United States": "Estados Unidos", "Canada": "Canadá", "Dominican Republic": "República Dominicana",
    "Belize": "Belice", "Bolivia": "Bolivia", "Nigeria": "Nigeria", "Ghana": "Ghana",
}
STAT_KEYS = ("pj", "starts", "goals", "assists", "yellow", "red")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _flat(obj: dict) -> list[dict]:
    out = []
    for a in (obj or {}).get("athletes") or []:
        if isinstance(a, dict) and isinstance(a.get("items"), list):   # algunos deportes agrupan por posición
            out += [x for x in a["items"] if isinstance(x, dict)]
        elif isinstance(a, dict):
            out.append(a)
    return out


def _injury(a: dict) -> str:
    """Texto corto de la lesión si ESPN reporta alguna (cadena vacía si no)."""
    for inj in a.get("injuries") or []:
        if not isinstance(inj, dict):
            continue
        for key in ("shortComment", "longComment", "status", "detail", "type"):
            v = inj.get(key)
            if isinstance(v, dict):
                v = v.get("description") or v.get("name") or v.get("text")
            if isinstance(v, str) and v.strip():
                return v.strip()
        return "Lesionado"
    return ""


def parse_roster(obj: dict) -> list[dict]:
    """Jugadores del plantel, ordenados por posición y número. [] si no hay datos."""
    out = []
    for a in _flat(obj):
        name = (a.get("displayName") or a.get("fullName") or "").strip()
        if not name:
            continue
        pos = (a.get("position") or {}).get("abbreviation") or ""
        pos = pos.upper()[:1] if pos else ""
        singular, plural, order = POSITIONS.get(pos, ("", "Otros", 9))
        jersey = str(a.get("jersey") or "").strip()
        age = a.get("age")
        country = a.get("citizenship") or ((a.get("flag") or {}).get("alt")) or ""
        cm, kg = _num(a.get("height")), _num(a.get("weight"))
        head = (a.get("headshot") or {}).get("href") if isinstance(a.get("headshot"), dict) else ""
        flag = (a.get("flag") or {}).get("href") if isinstance(a.get("flag"), dict) else ""
        out.append({
            "id": str(a.get("id") or ""), "name": name, "short": a.get("shortName") or name,
            "jersey": jersey, "pos": singular, "pos_group": plural, "pos_order": order,
            "age": age if isinstance(age, int) and 14 <= age <= 50 else None,
            "country": COUNTRIES.get(country, country), "flag": flag or "",
            "height_cm": int(cm * 2.54 + 0.5) if cm else None, "weight_kg": int(kg * 0.4536 + 0.5) if kg else None,   # ESPN da pulgadas y libras
            "photo": head or "", "injury": _injury(a), "status": ((a.get("status") or {}).get("type") or "active"),
        })
    out.sort(key=lambda p: (p["pos_order"], int(p["jersey"]) if p["jersey"].isdigit() else 999, p["name"]))
    return out


def attach_stats(roster: list[dict], players: list[dict]) -> list[dict]:
    """Agrega a cada jugador sus estadísticas (de players.json) emparejando por nombre.

    Usa el mismo emparejamiento que las estadísticas (sin acentos, nombres más largos, errores de tipeo);
    si hay duda no une, para no darle a un jugador los goles de otro.
    """
    by_norm = {sd._norm(p["name"]): p for p in players}
    used: set[int] = set()
    for r in roster:
        n = sd._norm(r["name"])
        hit = by_norm.get(n)
        if hit is None:
            near = {id(p): p for k, p in by_norm.items() if sd._close(k, n)}
            hit = next(iter(near.values())) if len(near) == 1 else None
        if hit is not None and id(hit) in used:
            hit = None   # un jugador de las estadísticas no se reparte entre dos del plantel
        if hit is not None:
            used.add(id(hit))
            r["stats"] = {k: hit.get(k, 0) for k in STAT_KEYS}
            r["comps"] = {c: {k: v.get(k, 0) for k in STAT_KEYS} for c, v in (hit.get("comps") or {}).items()}
        else:
            r["stats"] = dict.fromkeys(STAT_KEYS, 0)
            r["comps"] = {}
    return roster
