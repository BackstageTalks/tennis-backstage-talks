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


def parse_matches(rows):
    parsed = []

    for r in rows:
        try:
            winner = r.get("winner_name")
            loser = r.get("loser_name")

            if not winner or not loser:
                continue

            surface = r.get("surface") or "Hard"

            parsed.append({
                "player1": winner.strip(),
                "player2": loser.strip(),
                "winner": winner.strip(),
                "surface": surface,
                "date": r.get("tourney_date")
            })

        except:
            continue

    return parsed


def load_all_matches(start_year=2018, end_year=2030):
    all_matches = []

    for year in range(start_year, end_year + 1):

        # ✅ ATP
        atp_url = BASE_ATP_URL.format(year)
        atp_data = fetch_csv(atp_url)

        if atp_data:
            print(f"ATP {year}: {len(atp_data)}")
            all_matches.extend(parse_matches(atp_data))

        # ✅ WTA
