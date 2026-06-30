import requests
import csv
from io import StringIO

BASE_ATP_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv"
BASE_WTA_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv"


def fetch_csv(url):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None

        return list(csv.DictReader(StringIO(r.text)))
    except:
        return None


def load_all_matches(start_year=2000, end_year=2030):
    """
    dynamicky načíta všetky existujúce roky
    """

    all_matches = []

    for year in range(start_year, end_year + 1):

        # ATP
        atp_url = BASE_ATP_URL.format(year)
        atp_data = fetch_csv(atp_url)

        if atp_data:
            print(f"ATP {year} loaded:", len(atp_data))
            all_matches.extend(parse_matches(atp_data))

        # WTA
        wta_url = BASE_WTA_URL.format(year)
        wta_data = fetch_csv(wta_url)

        if wta_data:
            print(f"WTA {year} loaded:", len(wta_data))
            all_matches.extend(parse_matches(wta_data))

    print("TOTAL MATCHES:", len(all_matches))

    return all_matches


def parse_matches(rows):
    parsed = []

    for r in rows:
        try:
            p1 = r.get("winner_name")
            p2 = r.get("loser_name")

            if not p1 or not p2:
                continue

            surface = r.get("surface") or "Hard"

            parsed.append({
                "player1": p1.strip(),
                "player2": p2.strip(),
                "winner": p1.strip(),
                "surface": surface,
                "date": r.get("tourney_date")
            })

        except:
            continue

    return parsed
