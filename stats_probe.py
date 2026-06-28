import os
import re
import csv
import json
import datetime
import requests
from io import StringIO

TODAY = datetime.date.today().isoformat()

DATA_FILES_ENDPOINT = "https://stats.tennismylife.org/api/data-files"


def normalize_name(name):
    if not name:
        return ""

    name = str(name).lower().strip()
    name = re.sub(r"[^a-zA-ZÀ-ž\s\-']", "", name)
    name = re.sub(r"\s+", " ", name)

    return name


def surname_key(name):
    name = normalize_name(name)

    if not name:
        return ""

    parts = name.split()

    if len(parts) >= 2:
        # kvôli menám typu Dalla Valle, Sanchez Quilez
        return " ".join(parts[-2:])

    return parts[-1]


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


def load_latest_predictions():
    if not os.path.exists("public"):
        return []

    files = [
        f for f in os.listdir("public")
        if f.startswith("predictions_") and f.endswith(".json")
    ]

    if not files:
        print("No predictions file found.")
        return []

    latest = sorted(files)[-1]
    path = os.path.join("public", latest)

    print("Using predictions file:", path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_data_files():
    print("FETCH DATA FILE LIST:", DATA_FILES_ENDPOINT)

    try:
        response = requests.get(DATA_FILES_ENDPOINT, timeout=30)

        print("DATA FILES HTTP:", response.status_code)

        if response.status_code != 200:
            print("RAW ERROR:", response.text[:1000])
            return []

        data = response.json()
        files = data.get("files", [])

        print("DATA FILES FOUND:", len(files))

        return files

    except Exception as e:
        print("DATA FILE LIST ERROR:", str(e))
        return []


def file_priority(file_info):
    name = str(file_info.get("name", "")).lower()

    # najvyššia priorita: ongoing a aktuálne roky
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

    if "2022" in name and "challenger" in name:
        return 550

    if "2022" in name:
        return 500

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

    selected = [f for _, f in candidates[:16]]

    print("SELECTED FILES:", len(selected))

    for f in selected:
        print("SELECTED:", f.get("name"), f.get("url"))

    return selected


def fetch_csv_file(file_info):
    url = file_info.get("url")
    name = file_info.get("name", "unknown.csv")

    try:
        print("\nFETCH CSV:", name)
        print("URL:", url)

        response = requests.get(url, timeout=45)

        print("HTTP:", response.status_code)

        if response.status_code != 200:
            print("RAW ERROR:", response.text[:500])
            return [], []

        text = response.text

        if len(text) < 50:
            print("CSV too small")
            return [], []

        reader = csv.DictReader(StringIO(text))
        rows = list(reader)
        columns = reader.fieldnames or []

        print("ROWS:", len(rows))
        print("COLUMNS:", columns[:80])

        return rows, columns

    except Exception as e:
        print("CSV FETCH ERROR:", str(e))
        return [], []


def parse_sets_from_score(score):
    if not score:
        return {
            "winner_sets": None,
            "loser_sets": None,
            "sets_total": None
        }

    score = str(score)

    if any(x in score.upper() for x in ["RET", "W/O", "WO", "DEF", "ABN"]):
        return {
            "winner_sets": None,
            "loser_sets": None,
            "sets_total": None
        }

    chunks = score.split()

    winner_sets = 0
    loser_sets = 0

    for chunk in chunks:
        match = re.match(r"(\d+)-(\d+)", chunk)

        if not match:
            continue

        a = int(match.group(1))
        b = int(match.group(2))

        # v tomto datasete winner_name je víťaz zápasu
        if a > b:
            winner_sets += 1
        elif b > a:
            loser_sets += 1

    total = winner_sets + loser_sets

    if total == 0:
        return {
            "winner_sets": None,
            "loser_sets": None,
            "sets_total": None
        }

    return {
        "winner_sets": winner_sets,
        "loser_sets": loser_sets,
        "sets_total": total
    }


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None
        return float(value)
    except Exception:
        return None


def collect_player_stats(rows, player):
    stats = {
        "player": player,
        "matches_found": 0,
        "matches_with_score": 0,
        "sets_won": 0,
        "sets_lost": 0,
        "won_at_least_one_set_matches": 0,
        "aces_total": 0,
        "aces_sample": 0,
        "serve_points_total": 0,
        "serve_points_sample": 0
    }

    for row in rows:
        winner = row.get("winner_name", "")
        loser = row.get("loser_name", "")

        is_winner = names_match(player, winner)
        is_loser = names_match(player, loser)

        if not is_winner and not is_loser:
            continue

        stats["matches_found"] += 1

        # esá
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

        # sety
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

    if stats["aces_sample"] > 0:
        stats["avg_aces"] = round(stats["aces_total"] / stats["aces_sample"], 2)
    else:
        stats["avg_aces"] = None

    if stats["serve_points_sample"] > 0:
        stats["avg_serve_points"] = round(
            stats["serve_points_total"] / stats["serve_points_sample"],
            1
        )
    else:
        stats["avg_serve_points"] = None

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
    else:
        stats["set_win_rate"] = None
        stats["at_least_one_set_rate"] = None

    return stats


def merge_stats(stats_by_player):
    merged = {}

    for player, stat_list in stats_by_player.items():
        base = {
            "player": player,
            "matches_found": 0,
            "matches_with_score": 0,
            "sets_won": 0,
            "sets_lost": 0,
            "won_at_least_one_set_matches": 0,
            "aces_total": 0,
            "aces_sample": 0,
            "serve_points_total": 0,
            "serve_points_sample": 0
        }

        for s in stat_list:
            base["matches_found"] += s.get("matches_found", 0)
            base["matches_with_score"] += s.get("matches_with_score", 0)
            base["sets_won"] += s.get("sets_won", 0)
            base["sets_lost"] += s.get("sets_lost", 0)
            base["won_at_least_one_set_matches"] += s.get("won_at_least_one_set_matches", 0)
            base["aces_total"] += s.get("aces_total", 0)
            base["aces_sample"] += s.get("aces_sample", 0)
            base["serve_points_total"] += s.get("serve_points_total", 0)
            base["serve_points_sample"] += s.get("serve_points_sample", 0)

        if base["aces_sample"] > 0:
            base["avg_aces"] = round(base["aces_total"] / base["aces_sample"], 2)
        else:
            base["avg_aces"] = None

        if base["serve_points_sample"] > 0:
            base["avg_serve_points"] = round(
                base["serve_points_total"] / base["serve_points_sample"],
                1
            )
        else:
            base["avg_serve_points"] = None

        if base["matches_with_score"] > 0:
            total_sets = base["sets_won"] + base["sets_lost"]

            base["set_win_rate"] = round(
                base["sets_won"] / max(1, total_sets),
                3
            )

            base["at_least_one_set_rate"] = round(
                base["won_at_least_one_set_matches"] / base["matches_with_score"],
                3
            )
        else:
            base["set_win_rate"] = None
            base["at_least_one_set_rate"] = None

        # pomocné skóre pre možné alternatívne trhy
        if base["avg_aces"] is not None and base["avg_aces"] >= 5:
            base["ace_profile"] = "HIGH_ACE_POTENTIAL"
        elif base["avg_aces"] is not None and base["avg_aces"] >= 3:
            base["ace_profile"] = "MEDIUM_ACE_POTENTIAL"
        elif base["avg_aces"] is not None:
            base["ace_profile"] = "LOW_ACE_POTENTIAL"
        else:
            base["ace_profile"] = "NO_ACE_DATA"

        if base["at_least_one_set_rate"] is not None and base["at_least_one_set_rate"] >= 0.75:
            base["set_profile"] = "STRONG_SET_SAFETY"
        elif base["at_least_one_set_rate"] is not None and base["at_least_one_set_rate"] >= 0.6:
            base["set_profile"] = "MEDIUM_SET_SAFETY"
        elif base["at_least_one_set_rate"] is not None:
            base["set_profile"] = "LOW_SET_SAFETY"
        else:
            base["set_profile"] = "NO_SET_DATA"

        merged[player] = base

    return list(merged.values())


def main():
    os.makedirs("public", exist_ok=True)

    predictions = load_latest_predictions()

    players = []

    for p in predictions:
        for key in ["player1", "player2", "pick", "opponent"]:
            value = p.get(key)

            if value and value not in players:
                players.append(value)

    print("PLAYERS TO TEST:", players)

    data_files = get_data_files()
    selected_files = choose_relevant_files(data_files)

    source_reports = []
    stats_by_player = {player: [] for player in players}

    for file_info in selected_files:
        rows, columns = fetch_csv_file(file_info)

        source_reports.append({
            "name": file_info.get("name"),
            "url": file_info.get("url"),
            "rows": len(rows),
            "has_score": "score" in columns,
            "has_w_ace": "w_ace" in columns,
            "has_l_ace": "l_ace" in columns,
            "has_serve_stats": "w_svpt" in columns and "l_svpt" in columns
        })

        if not rows:
            continue

        for player in players:
            stats_by_player[player].append(
                collect_player_stats(rows, player)
            )

    player_stats = merge_stats(stats_by_player)

    summary = {
        "date": TODAY,
        "predictions_loaded": len(predictions),
        "players_tested": len(players),
        "files_found": len(data_files),
        "files_selected": len(selected_files),
        "players_with_matches": sum(1 for p in player_stats if p["matches_found"] > 0),
        "players_with_aces": sum(1 for p in player_stats if p["aces_sample"] > 0),
        "players_with_set_data": sum(1 for p in player_stats if p["matches_with_score"] > 0)
    }

    output = {
        "summary": summary,
        "sources": source_reports,
        "player_stats": player_stats
    }

    print("===== STATS PROBE SUMMARY =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    print("===== PLAYER STATS =====")
    print(json.dumps(player_stats, indent=2, ensure_ascii=False))

    with open("public/stats_probe_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open("public/stats_probe_full.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
