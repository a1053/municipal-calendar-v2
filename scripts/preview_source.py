import re
import requests
from bs4 import BeautifulSoup

URL = "https://ligagt.org/calendar/calendarioactual/"


def main():
    response = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "MunicipalCalendarV2/1.0"}
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    found = 0

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td", recursive=False)

            if len(cells) < 6:
                continue

            date_text = cells[0].get_text(" ", strip=True)
            match_text = cells[1].get_text(" ", strip=True)
            time_text = cells[2].get_text(" ", strip=True)
            season = cells[3].get_text(" ", strip=True)
            venue = cells[4].get_text(" ", strip=True)
            matchday = cells[5].get_text(" ", strip=True)

            if "municipal" not in match_text.lower():
                continue

            date_match = re.search(
                r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})",
                date_text
            )

            teams = re.split(
                r"\s+vs\.?\s+",
                match_text,
                maxsplit=1,
                flags=re.IGNORECASE
            )

            if not date_match or len(teams) != 2:
                print("REVISAR:", match_text, "|", date_text)
                continue

            kickoff = f"{date_match.group(1)}T{date_match.group(2)}"

            print(
                f"{kickoff} | {teams[0]} vs. {teams[1]} | "
                f"{season} | {matchday} | "
                f"Hora/resultado: {time_text} | Estadio: {venue}"
            )
            found += 1

    if found == 0:
        raise SystemExit(
            "ERROR: No se encontraron partidos de Municipal. "
            "La estructura de la página puede haber cambiado."
        )

    print(f"\nTotal de filas de Municipal encontradas: {found}")


if __name__ == "__main__":
    main()
