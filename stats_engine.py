import re
import csv
import requests
from io import StringIO

DATA_FILES_ENDPOINT = "https://stats.tennismylife.org/api/data-files"


def normalize_name(name):
    if not name:
        return ""

    name = str(name).lower().strip()
    name = re.sub(r"[^a-zA-ZÀ-ž\s\-']", "", name)
    name = re.sub(r"\s+", " ", name)

    return name


def loose_keys(name):
    name = normalize_name(name)
    parts = name.split()

    keys = set()

    if name:
        keys.add(name)

    if parts:
        keys.add(parts[-1])

    if len(parts) >= 2:
        keys.add(" ".join(parts[-2:]))

    return keys


def names_match(a, b):
    a_keys = loose_keys(a)
    b_keys = loose_keys(b)

    if not a_keys or not b_keys:
        return False

    return bool(a_keys.intersection(b_keys))


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None
        return float(value)
    except Exception:
        return None


def parse_date(value):
    try:
        value = str(value).strip()

        if len(value) == 8 and value.isdigit():
            return int(value)

        digits = re.sub(r"\D", "", value)

        if len(digits) >= 8:
            return int(digits[:8])
    except Exception:
        pass

    return 0


def parse_sets_from_score(score):
    if not score:
        return {"winner_sets": None, "loser_sets": None, "sets_total": None}

    score = str(score)

    if any(x in score.upper() for x in ["RET", "W/O", "WO", "DEF", "ABN"]):
        return {"winner_sets": None, "loser_sets": None, "sets_total": None}

    chunks = score.split()

    winner_sets = 0
    loser_sets = 0

    for chunk in chunks:
        match = re.match(r"(\d+)-(\d+)", chunk)

        if not match:
            continue

        a = int(match.group(1))
        b = int(match.group(2))

        if a > b:
            winner_sets += 1
        elif b > a:
            loser_sets += 1

    total = winner_sets + loser_sets

    if total == 0:
        return {"winner_sets": None, "loser_sets": None, "sets_total": None}

    return {
        "winner_sets": winner_sets,
        "loser_sets": loser_sets,
        "sets_total": total
    }


def get_data_files():
    try:
        response = requests.get(DATA_FILES_ENDPOINT, timeout=30)

        if response.status_code != 200:
            print("Stats data files error:", response.status_code)
            return []

        data = response.json()
        return data.get("files", [])

    except Exception as e:
        print("Stats data list error:", e)
        return []


def file_priority(file_info):
    name = str(file_info.get("name", "")).lower()

    if "ongoing" in name:
        return 1000

    if "2026" in name and "challenger" in name:
        return 950

    if "2026" in name:
        return 900

    if "2025" in name and "challenger" in name:
        return 850

    if "2025" in name:
        return 800

    if "2024" in name and "challenger" in name:
        return 750

    if "2024" in name:
        return 700

    if "2023" in name and "challenger" in name:
        return 650

    if "2023" in name:
        return 600

    return 0


def choose_relevant_files(files):
    candidates = []

    for f in files:
        name = str(f.get("name", "")).lower()
        url = f.get("url")

        if not url:
            continue

        if not name.endswith(".csv"):
            continue

        prio = file_priority(f)

        if prio > 0:
            candidates.append((prio, f))

    candidates.sort(key=lambda x: x[0], reverse=True)

    return [f for _, f in candidates[:12]]


def fetch_csv_rows(file_info):
    url = file_info.get("url")
    name = file_info.get("name", "unknown.csv")

    try:
        print("Stats fetch:", name)

        response = requests.get(url, timeout=45)

        if response.status_code != 200:
            print("Stats csv error:", response.status_code, name)
            return []

        reader = csv.DictReader(StringIO(response.text))
        return list(reader)

    except Exception as e:
        print("Stats csv fetch error:", name, e)
        return []


def build_player_record(row, player):
    winner = row.get("winner_name", "")
    loser = row.get("loser_name", "")

    is_winner = names_match(player, winner)
    is_loser = names_match(player, loser)

    if not is_winner and not is_loser:
        return None

    parsed = parse_sets_from_score(row.get("score", ""))

    if is_winner:
        aces = safe_float(row.get("w_ace"))
        serve_points = safe_float(row.get("w_svpt"))
        sets_won = parsed["winner_sets"]
        sets_lost = parsed["loser_sets"]
        won_match = True
    else:
        aces = safe_float(row.get("l_ace"))
        serve_points = safe_float(row.get("l_svpt"))
        sets_won = parsed["loser_sets"]
        sets_lost = parsed["winner_sets"]
        won_match = False

    won_set = None

    if sets_won is not None:
        won_set = sets_won >= 1

    return {
        "date": parse_date(row.get("tourney_date")),
        "surface": row.get("surface") or "Unknown",
        "won_match": won_match,
        "aces": aces,
        "serve_points": serve_points,
        "sets_won": sets_won,
        "sets_lost": sets_lost,
        "won_set": won_set
    }


def calc_metrics(records, label):
    records = sorted(records, key=lambda x: x.get("date", 0), reverse=True)

    n = len(records)

    if n == 0:
        return {
            "label": label,
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "at_least_one_set_rate": None,
            "set_win_rate": None,
            "avg_aces": None,
            "avg_serve_points": None,
            "ace_rate": None
        }

    wins = sum(1 for r in records if r["won_match"])
    losses = n - wins

    score_records = [r for r in records if r.get("won_set") is not None]

    set_rate = None

    if score_records:
        set_rate = sum(1 for r in score_records if r["won_set"]) / len(score_records)

    total_sets_won = sum(
        r["sets_won"] for r in score_records
        if r["sets_won"] is not None
    )

    total_sets_lost = sum(
        r["sets_lost"] for r in score_records
        if r["sets_lost"] is not None
    )

    set_win_rate = None

    if total_sets_won + total_sets_lost > 0:
        set_win_rate = total_sets_won / (total_sets_won + total_sets_lost)

    ace_values = [r["aces"] for r in records if r.get("aces") is not None]
    serve_values = [r["serve_points"] for r in records if r.get("serve_points") is not None]

    avg_aces = None

    if ace_values:
        avg_aces = sum(ace_values) / len(ace_values)

    avg_serve_points = None

    if serve_values:
        avg_serve_points = sum(serve_values) / len(serve_values)

    ace_rate = None

    if avg_aces is not None and avg_serve_points:
        ace_rate = avg_aces / avg_serve_points

    return {
        "label": label,
        "sample": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / n, 3),
        "at_least_one_set_rate": round(set_rate, 3) if set_rate is not None else None,
        "set_win_rate": round(set_win_rate, 3) if set_win_rate is not None else None,
        "avg_aces": round(avg_aces, 2) if avg_aces is not None else None,
        "avg_serve_points": round(avg_serve_points, 1) if avg_serve_points is not None else None,
        "ace_rate": round(ace_rate, 4) if ace_rate is not None else None
    }


def empty_player_stats(player):
    return {
        "player": player,
        "records_total": 0,
        "career": calc_metrics([], "career"),
        "last10": calc_metrics([], "last10"),
        "surface": {}
    }


def infer_match_surface(match, all_rows):
    p1 = match.get("player1")
    p2 = match.get("player2")

    candidates = []

    for row in all_rows:
        winner = row.get("winner_name", "")
        loser = row.get("loser_name", "")

        both_match = (
            (names_match(p1, winner) and names_match(p2, loser)) or
            (names_match(p1, loser) and names_match(p2, winner))
        )

        if both_match:
            surface = row.get("surface")
            date = parse_date(row.get("tourney_date"))

            if surface:
                candidates.append((date, surface))

    if not candidates:
        return "Unknown"

    candidates.sort(key=lambda x: x[0], reverse=True)

    return candidates[0][1]


def get_stats_context(players, matches):
    stats_map = {
        player: empty_player_stats(player)
        for player in players
    }

    files = choose_relevant_files(get_data_files())

    print("Stats files selected:", [f.get("name") for f in files])

    all_rows = []

    for file_info in files:
        rows = fetch_csv_rows(file_info)
        all_rows.extend(rows)

    player_records = {player: [] for player in players}

    for row in all_rows:
        for player in players:
            rec = build_player_record(row, player)

            if rec:
                player_records[player].append(rec)

    for player in players:
        records = sorted(
            player_records[player],
            key=lambda x: x.get("date", 0),
            reverse=True
        )

        stats_map[player]["records_total"] = len(records)
        stats_map[player]["career"] = calc_metrics(records, "career")
        stats_map[player]["last10"] = calc_metrics(records[:10], "last10")

        surfaces = sorted(set(r.get("surface", "Unknown") for r in records))

        for surface in surfaces:
            s_records = [
                r for r in records
                if r.get("surface") == surface
            ]

            stats_map[player]["surface"][surface] = calc_metrics(
                s_records[:10],
                f"last10_{surface}"
            )

    surface_map = {}

    for match in matches:
        key = f"{match.get('player1')}::{match.get('player2')}"
        surface_map[key] = infer_match_surface(match, all_rows)

    return stats_map, surface_map
