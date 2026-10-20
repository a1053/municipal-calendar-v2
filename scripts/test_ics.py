import sqlite3
from pathlib import Path

from icalendar import Calendar

DB_PATH = Path("data/municipal.sqlite3")
ICS_PATH = Path("public/municipal.ics")
UID_SUFFIX = "@municipal-calendar-v2"


def main():
    if not DB_PATH.exists():
        raise SystemExit("ERROR: No existe la base de datos.")

    if not ICS_PATH.exists():
        raise SystemExit("ERROR: No existe el archivo ICS.")

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT match_id
            FROM matches
            ORDER BY match_id
        """).fetchall()

    expected_ids = [row[0] for row in rows]

    if not expected_ids:
        raise SystemExit("ERROR: La base de datos está vacía.")

    if len(expected_ids) != len(set(expected_ids)):
        raise SystemExit("ERROR: Hay IDs duplicados en la base.")

    try:
        calendar = Calendar.from_ical(ICS_PATH.read_bytes())
    except Exception as exc:
        raise SystemExit(f"ERROR: ICS ilegible: {exc}")

    events = calendar.walk("VEVENT")
    actual_ids = []
    actual_uids = []

    for event in events:
        match_id = event.get("X-MATCH-ID")
        uid = event.get("UID")

        if match_id is None or uid is None:
            raise SystemExit(
                "ERROR: Evento sin X-MATCH-ID o UID."
            )

        actual_ids.append(str(match_id))
        actual_uids.append(str(uid))

        expected_uid = f"{match_id}{UID_SUFFIX}"

        if str(uid) != expected_uid:
            raise SystemExit(
                f"ERROR: UID inesperado para {match_id}: {uid}"
            )

        if event.get("DTSTART") is None:
            raise SystemExit(
                f"ERROR: Evento sin fecha: {match_id}"
            )

    if len(actual_ids) != len(set(actual_ids)):
        raise SystemExit("ERROR: Hay partidos duplicados en el ICS.")

    if len(actual_uids) != len(set(actual_uids)):
        raise SystemExit("ERROR: Hay UID duplicados en el ICS.")

    if set(expected_ids) != set(actual_ids):
        missing = set(expected_ids) - set(actual_ids)
        unexpected = set(actual_ids) - set(expected_ids)

        raise SystemExit(
            f"ERROR: Diferencias entre base e ICS. "
            f"Faltantes: {sorted(missing)}; "
            f"inesperados: {sorted(unexpected)}"
        )

    print(
        f"OK: {len(events)} eventos coinciden con la base de datos. "
        "Sin partidos ni UID duplicados."
    )


if __name__ == "__main__":
    main()
