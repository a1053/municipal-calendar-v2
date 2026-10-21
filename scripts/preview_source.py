import requests

# Liga Bantrab is the sole source of truth. Check both the public calendar
# page and the public SportsPress REST endpoint; this script only diagnoses
# access and never alters the database or publishes an ICS.
URLS = [
    "https://ligagt.org/calendario/",
    "https://ligagt.org/wp-json/sportspress/v2/events?per_page=5&page=1",
    "https://ligagt.org/wp-json/sportspress/v2/calendars?per_page=5&page=1",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MunicipalCalendarV2/1.0)",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-GT,es;q=0.9,en;q=0.8",
}


def main():
    failed = []
    for url in URLS:
        print(f"\nURL: {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=25)
            print("HTTP:", response.status_code)
            print("Content-Type:", response.headers.get("Content-Type", ""))
            print("Bytes:", len(response.content))
            print("Preview:", response.text[:220].replace("\n", " "))
            if response.status_code != 200:
                failed.append((url, response.status_code))
        except requests.RequestException as exc:
            print("Error:", exc)
            failed.append((url, str(exc)))

    if failed:
        print("\nRESULTADO: No todos los endpoints son accesibles desde este entorno.")
        print("No se modificó la base de datos y no se debe generar/publicar el ICS automáticamente.")
        for url, reason in failed:
            print(f"- {url}: {reason}")
        raise SystemExit(1)

    print("\nRESULTADO: Los endpoints respondieron HTTP 200. Esto confirma acceso, no que la extracción esté validada.")


if __name__ == "__main__":
    main()
