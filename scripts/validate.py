import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar

ICS_FILE = Path("public/municipal.ics")
DUPLICATE_WINDOW_SECONDS = 24 * 60 * 60


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def event_start(event):
    value = event.get("DTSTART")
    if value is None:
        return None
    dt = value.dt
    if not isinstance(dt, datetime):
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fixture_pair(summary):
    # Recognize the common formats used by this calendar.
    parts = re.split(r"\s+vs\.?\s+|\s+v\s+", str(summary or ""), maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    home, away = normalize(parts[0]), normalize(parts[1])
    if not home or not away:
        return None
    return home, away


def main():
    if not ICS_FILE.exists():
        raise SystemExit(f"ERROR: No existe el archivo {ICS_FILE}")

    try:
        calendar = Calendar.from_ical(ICS_FILE.read_bytes())
    except Exception as exc:
        raise SystemExit(f"ERROR: El archivo ICS no es válido: {exc}")

    if str(calendar.get("VERSION", "")) != "2.0":
        raise SystemExit("ERROR: Falta VERSION:2.0")

    events = calendar.walk("VEVENT")
    if not events:
        raise SystemExit("ERROR: El calendario no contiene eventos.")

    uids, match_ids = set(), set()
    fixtures = []

    for event in events:
        uid = str(event.get("UID", "")).strip()
        summary = str(event.get("SUMMARY", "")).strip()
        start = event_start(event)
        if not uid:
            raise SystemExit("ERROR: Evento sin UID.")
        if uid in uids:
            raise SystemExit(f"ERROR: UID duplicado: {uid}")
        uids.add(uid)

        if not summary or start is None:
            raise SystemExit(f"ERROR: Evento incompleto: {uid}")

        match_id = str(event.get("X-MATCH-ID", "")).strip()
        if not match_id:
            raise SystemExit(f"ERROR: Evento sin X-MATCH-ID: {uid}")
        if match_id in match_ids:
            raise SystemExit(f"ERROR: X-MATCH-ID duplicado: {match_id}")
        match_ids.add(match_id)

        pair = fixture_pair(summary)
        if pair:
            # Include season/competition where available in DESCRIPTION so
            # fixtures from separate seasons/competitions are not conflated.
            description = normalize(event.get("DESCRIPTION", ""))
            context = tuple(
                token for token in ("apertura 2026", "clausura 2026", "apertura 2027", "clausura 2027")
                if token in description
            )
            fixtures.append((pair, context, start, match_id, summary))

    for index, current in enumerate(fixtures):
        pair, context, start, match_id, summary = current
        for other in fixtures[index + 1:]:
            other_pair, other_context, other_start, other_id, other_summary = other
            # Same home/away order and same competition context, with kickoff
            # timestamps within 24 hours, is a likely duplicated fixture.
            if pair == other_pair and context == other_context:
                seconds = abs((start - other_start).total_seconds())
                if seconds <= DUPLICATE_WINDOW_SECONDS:
                    raise SystemExit(
                        "ERROR: Posible partido duplicado aunque los IDs difieran: "
                        f"'{summary}' ({match_id}) y '{other_summary}' ({other_id}); "
                        f"diferencia de inicio: {int(seconds)} segundos."
                    )

    print(
        f"OK: {len(events)} eventos validados; UID e IDs únicos; "
        "sin duplicados semánticos detectados."
    )


if __name__ == "__main__":
    main()
