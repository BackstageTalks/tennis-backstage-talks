import csv
import re
from io import StringIO
from datetime import datetime
import requests


GITHUB_SOURCES = [
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

TML_FILES_API = "https://stats.tennismylife.org/api/data-files"


def get_text(url, timeout=30):
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.text
    except Exception as e:
        print("GET TEXT ERROR:", url, e)
        return None


def fetch_csv_rows(url):
    text = get_text(url)

    if not text:
        return []

    if "," not in text:
        return []

    try:
        return list(csv.DictReader(StringIO(text)))
    except Exception as e:
        print("CSV READ ERROR:", url, e)
        return []


def normalize_col_name(name):
    if name is None:
        return ""

    value = str(name).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def build_column_map(row):
    column_map = {}

    for key in row.keys():
        column_map[normalize_col_name(key)] = key

    return column_map


def get_first(row, candidates):
    column_map = build_column_map(row)

    for candidate in candidates:
        normalized = normalize_col_name(candidate)
        original_key = column_map.get(normalized)

        if original_key is not None:
            value = row.get(original_key)
            if value not in [None, ""]:
                return value

    return None


def parse_date(value):
    if not value:
        return "0"

    text = str(value).strip()

    # Sackmann: 20240701
    if re.match(r"^\d{8}$", text):
        return text

    # ISO: 2024-07-01
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            return datetime.fromisoformat(text[:10]).strftime("%Y%m%d")
    except Exception:
        pass

    # Tennis-data style: 01/07/2024
    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"]:
        try:
            return datetime.strptime(text[:10], fmt).strftime("%Y%m%d")
        except Exception:
            continue

    numbers = re.findall(r"\d+", text)
    if len(numbers) >= 3:
        joined = "".join(numbers[:3])
        if len(joined) >= 8:
            return joined[:8]

    return "0"


def detect_winner_loser(row):
    # Jeff Sackmann
    winner = get_first(row, [
        "winner_name",
        "winner",
        "Winner",
        "match_winner",
    ])

    loser = get_first(row, [
        "loser_name",
        "loser",
        "Loser",
        "match_loser",
    ])

    if winner and loser:
        return winner, loser

    # Home/Away + winner code formats
    home = get_first(row, [
        "home_player",
        "home_name",
        "home",
        "player_home",
        "player1",
        "player_1",
        "home_team",
    ])

    away = get_first(row, [
        "away_player",
        "away_name",
        "away",
        "player_away",
        "player2",
        "player_2",
        "away_team",
    ])

    winner_code = get_first(row, [
        "winner_code",
        "winner_id",
        "winner",
        "result",
        "match_winner_code",
    ])

    if home and away and winner_code is not None:
        code = str(winner_code).strip().lower()

        if code in ["1", "home", "h", "player1", "player_1"]:
            return home, away

        if code in ["2", "away", "a", "player2", "player_2"]:
            return away, home

    return None, None


def get_surface(row):
    return get_first(row, [
        "surface",
        "Surface",
        "court",
        "Court",
    ]) or "Hard"


def get_tournament(row):
    return get_first(row, [
        "tourney_name",
        "tournament",
        "Tournament",
        "event",
        "Event",
    ]) or ""


def get_level(row):
    return get_first(row, [
        "tourney_level",
        "level",
        "Level",
        "category",
        "Category",
    ]) or ""


def get_date(row):
    return parse_date(get_first(row, [
        "tourney_date",
        "date",
        "Date",
        "match_date",
        "start_date",
    ]))


def parse_rows(rows, source_label):
    parsed = []

    for row in rows:
        try:
            winner, loser = detect_winner_loser(row)

            if not winner or not loser:
                continue

            winner = str(winner).strip()
            loser = str(loser).strip()

            if not winner or not loser:
                continue

            # no doubles
            if "/" in winner or "/" in loser:
                continue

            parsed.append({
                "player1": winner,
                "player2": loser,
                "winner": winner,
                "surface": get_surface(row),
                "date": get_date(row),
                "tournament": get_tournament(row),
                "level": get_level(row),
                "source": source_label,
            })

        except Exception:
            continue

    return parsed


def load_github_source_year(source, year):
    url = source["url"].format(year)
    label = source["label"]

    rows = fetch_csv_rows(url)

    if not rows:
        print(label, year, "rows: 0")
        return []

    parsed = parse_rows(rows, label)

    print(label, year, "rows:", len(rows), "parsed:", len(parsed))

    return parsed


def fetch_tml_file_list():
    try:
        response = requests.get(TML_FILES_API, timeout=30)

        if response.status_code != 200:
            print("TML API ERROR:", response.status_code)
            return []

        data = response.json()
        files = data.get("files", [])

        if not isinstance(files, list):
            return []

        return files

    except Exception as e:
        print("TML API FETCH ERROR:", e)
        return []


def tml_file_matches_year(file_obj, year):
    name = str(file_obj.get("name", "")).lower()
    url = str(file_obj.get("url", "")).lower()

    if not name.endswith(".csv") and not url.endswith(".csv"):
        return False

    if str(year) not in name and str(year) not in url:
        return False

    banned = ["rank", "ranking", "player", "database", "ongoing_tourney"]

    for bad in banned:
        if bad in name:
            return False

    keywords = [
        str(year),
        "challenger",
        "qual",
        "atp",
        "wta",
    ]

    return any(keyword in name for keyword in keywords)


def load_tml_years(start_year, end_year):
    file_list = fetch_tml_file_list()

    if not file_list:
        print("TML FILE LIST EMPTY")
        return []

    all_matches = []

    for year in range(start_year, end_year + 1):
        year_files = [
            f for f in file_list
            if tml_file_matches_year(f, year)
        ]

        print("TML YEAR", year, "FILES:", len(year_files))

        for file_obj in year_files:
            name = file_obj.get("name", "")
            url = file_obj.get("url")

            if not url:
                continue

            rows = fetch_csv_rows(url)

            if not rows:
                print("TML", year, name, "rows: 0")
                continue

            label = f"TML_{name}"

            parsed = parse_rows(rows, label)

            print("TML", year, name, "rows:", len(rows), "parsed:", len(parsed))

            all_matches.extend(parsed)

    return all_matches


def load_all_matches(start_year=2018, end_year=2030):
    all_matches = []
    source_counts = {}

    print("LOADING GITHUB / SACKMANN SOURCES...")

    for year in range(start_year, end_year + 1):
        print("LOADING YEAR:", year)

        for source in GITHUB_SOURCES:
            matches = load_github_source_year(source, year)

            if not matches:
                continue

            label = source["label"]
            source_counts[label] = source_counts.get(label, 0) + len(matches)
            all_matches.extend(matches)

    if len(all_matches) < 1000:
        print("GITHUB SOURCES TOO SMALL, TRYING TENNISMYLIFE FALLBACK...")
        tml_matches = load_tml_years(start_year, end_year)

        for match in tml_matches:
            label = match.get("source", "TML")
            source_counts[label] = source_counts.get(label, 0) + 1

        all_matches.extend(tml_matches)

    # deduplicate
    deduped = {}

    for match in all_matches:
        key = (
            match.get("date"),
            match.get("player1"),
            match.get("player2"),
            match.get("winner"),
            match.get("surface"),
        )
        deduped[key] = match

    output = list(deduped.values())
    output.sort(key=lambda x: x.get("date") or "0")

    print("TOTAL MATCHES:", len(output))
    print("SOURCE COUNTS:", source_counts)

    return output
