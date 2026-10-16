import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

DB_PATH = Path("data/municipal.sqlite3")
ICS_PATH = Path("public/municipal.ics")
GUATEMALA = ZoneInfo("America/Guatemala")


def parse_kickoff(value):
    dt = datetime.fromisoformat(value)

    # Si no trae zona horaria, asumimos hora de Guatemala.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=GUATEMALA)

    return dt


def main():
    if not DB_PATH.exists():
        raise SystemExit(
            "ERROR: No existe la base de datos. "
            "Ejecuta primero scripts/init_db.py."
        )

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        matches = conn.execute("""
            SELECT *
            FROM matches
            ORDER BY kickoff_local, match_id
        """).fetchall()

    if not matches:
        raise SystemExit(
            "ERROR: No hay partidos cargados. "
            "No se publicará un calendario vacío."
        )

    calendar = Calendar()
    calendar.add("prodid", "-//CSD Municipal//Calendario V2//ES")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", "CSD Municipal")
    calendar.add("x-wr-timezone", "America/Guatemala")

    seen_ids = set()

    for match in matches:
        match_id = match["match_id"]

        if not match_id or match_id in seen_ids:
            raise SystemExit(
                f"ERROR: ID de partido vacío o duplicado: {match_id}"
            )
        seen_ids.add(match_id)

        if not match["kickoff_local"]:
            raise SystemExit(
                f"ERROR: Falta fecha/hora para {match_id}"
            )

        kickoff = parse_kickoff(match["kickoff_local"])

        event = Event()
        event.add("uid", f"{match_id}@municipal-calendar-v2")
        event.add("sequence", int(match["sequence"]))
        event.add("dtstamp", datetime.now(timezone.utc))
        event.add("dtstart", kickoff)

        event.add(
            "summary",
            f'{match["home_team"]} vs. {match["away_team"]}'
        )

        details = [
            f'Competición: {match["competition"]}',
            f'Temporada: {match["season"]}',
        ]

        if match["matchday"]:
            details.append(f'Jornada: {match["matchday"]}')

        if match["venue"]:
            details.append(f'Estadio: {match["venue"]}')

        details.append(f'ID del partido: {match_id}')

        if match["source_url"]:
            details.append(f'Fuente: {match["source_url"]}')

        event.add("description", "\n".join(details))
        event.add("X-MATCH-ID", match_id)
        event.add("X-LOCAL-TIMEZONE", "America/Guatemala")

        if match["venue"]:
            event.add("location", match["venue"])

        status = match["status"]

        if status == "cancelled":
            event.add("status", "CANCELLED")
        elif status == "completed":
            event.add("status", "CONFIRMED")
            if match["home_score"] is not None:
                event.add(
                    "description",
                    "\n".join(details)
                    + f'\nResultado: {match["home_score"]}'
                    + f' - {match["away_score"]}'
                )
        elif status == "postponed":
            event.add("status", "TENTATIVE")
            details.append(
                "Partido aplazado; horario pendiente de confirmación."
            )
            event["description"] = "\n".join(details)
        else:
            event.add("status", "CONFIRMED")

        calendar.add_component(event)

    ICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ICS_PATH.write_bytes(calendar.to_ical())

    print(
        f"OK: generado {ICS_PATH} con "
        f"{len(matches)} partidos."
    )


if __name__ == "__main__":
    main()
