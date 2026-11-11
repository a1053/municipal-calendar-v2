"""Alineaciones cargadas a mano (data/lineups.json), para partidos donde ninguna fuente automática trae formación.

Cada entrada dice fecha (día en Guatemala), rival, formación y los 11 titulares en orden: portero, luego cada
fila de izquierda a derecha, de la defensa al ataque. Reemplaza la alineación de Municipal de ese partido.
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import site_details as sd

PATH = Path(__file__).resolve().parent.parent / "data" / "lineups.json"
GT = timedelta(hours=-6)


def load(path: Path = PATH) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [e for e in data if isinstance(e, dict) and len(e.get("starters") or []) == 11] if isinstance(data, list) else []


def find(entries: list[dict], match: dict, start_utc, team_id: str) -> dict | None:
    """Entrada que corresponde a este partido: mismo día (±1) en Guatemala y el rival en el nombre del otro equipo."""
    day = (start_utc + GT).date()
    rival = match["away"] if match["home"]["id"] == team_id else match["home"]
    rname = sd._norm(rival.get("name", ""))
    for e in entries:
        try:
            d = type(day).fromisoformat(e["date"])
        except (KeyError, ValueError):
            continue
        if abs((day - d).days) <= 1 and sd._norm(e.get("rival", "")) and sd._norm(e["rival"]) in rname:
            return e
    return None


def to_lineup(entry: dict, team_id: str, team: str, home_away: str, prefix: str = "") -> dict:
    players = []
    for i, p in enumerate(entry[prefix + "starters"], 1):
        players.append({"id": "", "name": p["name"], "jersey": str(p.get("jersey", "")), "pos": p.get("pos", ""),
                        "starter": True, "place": i, "played": True, "marks": list(p.get("marks", []))})
    for p in entry.get(prefix + "bench") or []:
        marks = list(p.get("marks", []))
        players.append({"id": "", "name": p["name"], "jersey": str(p.get("jersey", "")), "pos": p.get("pos", ""),
                        "starter": False, "place": 0, "played": "in" in marks, "marks": marks})
    return {"team_id": team_id, "team": team, "home_away": home_away, "formation": entry.get(prefix + "formation", ""),
            "coach": entry.get(prefix + "coach", ""), "source": entry.get("source", ""), "manual": True, "players": players}


def apply(lineups: list[dict], entry: dict, match: dict, team_id: str) -> list[dict]:
    """Cambia la alineación de Municipal por la manual (y la del rival si la entrada la trae)."""
    mine = match["home"] if match["home"]["id"] == team_id else match["away"]
    ha = "home" if mine is match["home"] else "away"
    other = match["away"] if mine is match["home"] else match["home"]
    out = [lu for lu in lineups if lu.get("team_id") != team_id] + [to_lineup(entry, team_id, mine["name"], ha)]
    if len(entry.get("rival_starters") or []) == 11:      # la alineación del rival, si también se cargó
        out = [lu for lu in out if lu.get("team_id") != other["id"]] + [
            to_lineup(entry, other["id"], other["name"], "away" if ha == "home" else "home", "rival_")]
    return out
