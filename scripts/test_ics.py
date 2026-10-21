import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar

DB_PATH = Path("data/municipal.sqlite3")
ICS_PATH = Path("public/municipal.ics")
UID_SUFFIX = "@municipal-calendar-v2"
DUPLICATE_WINDOW_SECONDS = 24 * 60 * 60


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def start_utc(event):
    value = event.get("DTSTART")
    if value is None:
        return None
    dt = value.dt
    if not isinstance(dt, datetime):
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def pair(summary):
    parts = re.split(r"\s+vs\.?\s+|\s+v\s+", str(summary or ""), maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    return normalize(parts[0]), normalize(parts[1])


def main():
    if not DB_PATH.exists():
        raise SystemExit("ERROR: No existe la base de datos.")
    if not ICS_PATH.exists():
        raise SystemExit("ERROR: No existe el archivo ICS.")

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT match_id FROM matches ORDER BY match_id").fetchall()
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
    actual_ids, actual_uids, fixtures = [], [], []

    for event in events:
        match_id = event.get("X-MATCH-ID")
        uid = event.get("UID")
        if match_id is None or uid is None or event.get("DTSTART") is None:
            raise SystemExit("ERROR: Evento sin X-MATCH-ID, UID o DTSTART.")
        match_id, uid = str(match_id).strip(), str(uid).strip()
        actual_ids.append(match_id)
        actual_uids.append(uid)

        expected_uid = f"{match_id}{UID_SUFFIX}"
        if uid != expected_uid:
            raise SystemExit(f"ERROR: UID inesperado para {match_id}: {uid}")

        team_pair = pair(event.get("SUMMARY", ""))
        kickoff = start_utc(event)
        if team_pair and kickoff:
            fixtures.append((team_pair, kickoff, match_id, str(event.get("SUMMARY", ""))))

    if len(actual_ids) != len(set(actual_ids)):
        raise SystemExit("ERROR: Hay X-MATCH-ID duplicados en el ICS.")
    if len(actual_uids) != len(set(actual_uids)):
        raise SystemExit("ERROR: Hay UID duplicados en el ICS.")
    if set(expected_ids) != set(actual_ids):
        missing = set(expected_ids) - set(actual_ids)
        unexpected = set(actual_ids) - set(expected_ids)
        raise SystemExit(
            f"ERROR: Diferencias entre base e ICS. "
            f"Faltantes: {sorted(missing)}; inesperados: {sorted(unexpected)}"
        )

    for i, current in enumerate(fixtures):
        p1, t1, id1, s1 = current
        for p2, t2, id2, s2 in fixtures[i + 1:]:
            if p1 == p2 and abs((t1 - t2).total_seconds()) <= DUPLICATE_WINDOW_SECONDS:
                raise SystemExit(
                    "ERROR: Posible partido duplicado con IDs distintos: "
                    f"'{s1}' ({id1}) y '{s2}' ({id2})."
                )

    print(f"OK: {len(events)} eventos coinciden con la base; sin duplicados detectados.")


if __name__ == "__main__":
    main()
