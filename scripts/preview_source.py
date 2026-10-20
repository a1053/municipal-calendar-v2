import requests

URL = "https://ligagt.org/calendar/calendarioactual/"

HEADERS_TO_TEST = [
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "es-GT,es;q=0.9,en;q=0.8",
    },
    {
        "User-Agent": "MunicipalCalendarV2/1.0",
        "Accept": "text/html,*/*",
    },
]


def main():
    for number, headers in enumerate(HEADERS_TO_TEST, start=1):
        print(f"\nPrueba {number}")

        try:
            response = requests.get(
                URL,
                headers=headers,
                timeout=30,
            )

            print("HTTP:", response.status_code)
            print("Content-Type:", response.headers.get("Content-Type"))
            print("Tamaño:", len(response.content), "bytes")
            print("URL final:", response.url)
            print("Inicio de respuesta:")
            print(response.text[:300].replace("\n", " "))

            if response.status_code == 200:
                print("\nLa página respondió correctamente.")
                return

        except requests.RequestException as exc:
            print("Error de conexión:", str(exc))

    raise SystemExit(
        "\nNo fue posible obtener la página desde GitHub Actions. "
        "No se modificó la base de datos."
    )


if __name__ == "__main__":
    main()
