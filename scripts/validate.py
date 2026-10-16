from pathlib import Path
from icalendar import Calendar

ICS_FILE = Path("public/municipal.ics")


def main():
    if not ICS_FILE.exists():
        raise SystemExit(
            f"ERROR: No existe el archivo {ICS_FILE}"
        )

    try:
        calendar = Calendar.from_ical(
            ICS_FILE.read_bytes()
        )
    except Exception as exc:
        raise SystemExit(
            f"ERROR: El archivo ICS no es válido: {exc}"
        )

    if calendar.get("VERSION") != "2.0":
        raise SystemExit("ERROR: Falta VERSION:2.0")

    events = calendar.walk("VEVENT")

    if not events:
        raise SystemExit(
            "ERROR: El calendario no contiene eventos."
        )

    uids = set()
    match_ids = set()

    for event in events:
        uid = str(event.get("UID", "")).strip()
        summary = str(event.get("SUMMARY", "")).strip()
        start = event.get("DTSTART")

        if not uid:
            raise SystemExit("ERROR: Evento sin UID.")

        if uid in uids:
            raise SystemExit(
                f"ERROR: UID duplicado: {uid}"
            )
        uids.add(uid)

        if not summary or start is None:
            raise SystemExit(
                f"ERROR: Evento incompleto: {uid}"
            )

        match_id = event.get("X-MATCH-ID")

        if match_id:
            match_id = str(match_id).strip()

            if match_id in match_ids:
                raise SystemExit(
                    f"ERROR: Partido duplicado: {match_id}"
                )

            match_ids.add(match_id)

    print(
        f"OK: {len(events)} eventos validados; "
        "sin UID duplicados ni partidos repetidos "
        "con el mismo X-MATCH-ID."
    )


if __name__ == "__main__":
    main()
