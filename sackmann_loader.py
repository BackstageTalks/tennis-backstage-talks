import csv
from io import StringIO
import requests


SOURCES = [
    {
        "label": "ATP_MAIN",
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv",
    },
    {
        "label": "ATP_QUAL_CHALL",
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_qual_chall_{}.csv",
    },
    {
        "label": "WTA_MAIN",
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv",
    },
]


def fetch_csv(url):
    try:
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            return []

        text = response.text

        if not text or "winner_name" not in text or "loser_name" not in text:
            return []

        return list(csv.DictReader(StringIO(text)))

    except Exception as e:
        print("FETCH CSV ERROR:", url, e)
        return []


def parse_rows(rows, source_label):
    parsed = []

    for row in rows:
        try:
            winner = row.get("winner_name")
            loser = row.get("loser_name")

            if not winner or not loser:
                continue

            if "/" in winner or "/" in loser:
                continue

            surface = row.get("surface") or "Hard"
            date = row.get("tourney_date") or "0"
            tournament = row.get("tourney_name") or ""
            level = row.get("tourney_level") or ""

            parsed.append({
                "player1": winner.strip(),
                "player2": loser.strip(),
                "winner": winner.strip(),
                "surface": surface,
                "date": date,
                "tournament": tournament,
                "level": level,
                "source": source_label,
            })

        except Exception:
            continue

    return parsed


def load_source_year(source, year):
    url = source["url"].format(year)
    label = source["label"]

    rows = fetch_csv(url)

    if not rows:
        print(label, year, "rows: 0")
        return []

    parsed = parse_rows(rows, label)

    print(label, year, "rows:", len(rows), "parsed:", len(parsed))

    return parsed


def load_all_matches(start_year=2018, end_year=2030):
    all_matches = []
    source_counts = {}

    for year in range(start_year, end_year + 1):
        print("LOADING YEAR:", year)

        for source in SOURCES:
            matches = load_source_year(source, year)

            if not matches:
                continue

            label = source["label"]
            source_counts[label] = source_counts.get(label, 0) + len(matches)
            all_matches.extend(matches)

    all_matches.sort(key=lambda x: x.get("date") or "0")

    print("TOTAL MATCHES:", len(all_matches))
    print("SOURCE COUNTS:", source_counts)

    return all_matches
