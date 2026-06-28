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

        text = response.text

        reader = csv.DictReader(StringIO(text))
        return list(reader)

    except Exception as e:
        print("Stats csv fetch error:", name, e)
        return []


def empty_player_stats(player):
    return {
        "player": player,
        "matches_found": 0,
        "matches_with_score": 0,
        "sets_won": 0,
        "sets_lost": 0,
        "won_at_least_one_set_matches": 0,
        "aces_total": 0,
        "aces_sample": 0,
        "serve_points_total": 0,
        "serve_points_sample": 0,
        "avg_aces": None,
        "avg_serve_points": None,
        "set_win_rate": None,
        "at_least_one_set_rate": None,
        "ace_profile": "NO_ACE_DATA",
        "set_profile": "NO_SET_DATA"
    }


def update_player_stats(stats, row, player):
    winner = row.get("winner_name", "")
    loser = row.get("loser_name", "")

    is_winner = names_match(player, winner)
    is_loser = names_match(player, loser)

    if not is_winner and not is_loser:
        return

    stats["matches_found"] += 1

    if is_winner:
        aces = safe_float(row.get("w_ace"))
        serve_points = safe_float(row.get("w_svpt"))
    else:
        aces = safe_float(row.get("l_ace"))
        serve_points = safe_float(row.get("l_svpt"))

    if aces is not None:
        stats["aces_total"] += aces
        stats["aces_sample"] += 1

    if serve_points is not None:
        stats["serve_points_total"] += serve_points
        stats["serve_points_sample"] += 1

    parsed = parse_sets_from_score(row.get("score", ""))

    if parsed["sets_total"] is not None:
        stats["matches_with_score"] += 1

        if is_winner:
            player_sets = parsed["winner_sets"]
            opponent_sets = parsed["loser_sets"]
        else:
            player_sets = parsed["loser_sets"]
            opponent_sets = parsed["winner_sets"]

        stats["sets_won"] += player_sets
        stats["sets_lost"] += opponent_sets

        if player_sets >= 1:
            stats["won_at_least_one_set_matches"] += 1


def finalize_player_stats(stats):
    if stats["aces_sample"] > 0:
        stats["avg_aces"] = round(stats["aces_total"] / stats["aces_sample"], 2)

    if stats["serve_points_sample"] > 0:
        stats["avg_serve_points"] = round(
            stats["serve_points_total"] / stats["serve_points_sample"],
            1
        )

    if stats["matches_with_score"] > 0:
        total_sets = stats["sets_won"] + stats["sets_lost"]

        stats["set_win_rate"] = round(
            stats["sets_won"] / max(1, total_sets),
            3
        )

        stats["at_least_one_set_rate"] = round(
            stats["won_at_least_one_set_matches"] / stats["matches_with_score"],
            3
        )

    if stats["avg_aces"] is not None and stats["avg_aces"] >= 5:
        stats["ace_profile"] = "HIGH_ACE_POTENTIAL"
    elif stats["avg_aces"] is not None and stats["avg_aces"] >= 3:
        stats["ace_profile"] = "MEDIUM_ACE_POTENTIAL"
    elif stats["avg_aces"] is not None:
        stats["ace_profile"] = "LOW_ACE_POTENTIAL"

    if stats["at_least_one_set_rate"] is not None and stats["at_least_one_set_rate"] >= 0.75:
        stats["set_profile"] = "STRONG_SET_SAFETY"
    elif stats["at_least_one_set_rate"] is not None and stats["at_least_one_set_rate"] >= 0.60:
        stats["set_profile"] = "MEDIUM_SET_SAFETY"
    elif stats["at_least_one_set_rate"] is not None:
        stats["set_profile"] = "LOW_SET_SAFETY"

    return stats


def get_stats_for_players(players):
    stats_map = {
        player: empty_player_stats(player)
        for player in players
    }

    files = choose_relevant_files(get_data_files())

    print("Stats files selected:", [f.get("name") for f in files])

    for file_info in files:
        rows = fetch_csv_rows(file_info)

        for row in rows:
            for player in players:
                update_player_stats(stats_map[player], row, player)

    for player in players:
        stats_map[player] = finalize_player_stats(stats_map[player])

    return stats_map
