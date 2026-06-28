import os
import re
import csv
import json
import datetime
import requests
from io import StringIO

TODAY = datetime.date.today().isoformat()

# Jeff Sackmann / mirrors - testujeme viac URL možností
DATA_URLS = [
    "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2026.csv",
    "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2025.csv",
    "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2024.csv",

    "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_2026.csv",
    "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_2025.csv",
    "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_2024.csv",
]


def normalize_name(name):
    if not name:
        return ""

    name = str(name).lower().strip()
    name = re.sub(r"[^a-z\s\-]", "", name)
    name = re.sub(r"\s+", " ", name)

    parts = name.split()

    if not parts:
        return ""

    # používame priezvisko ako rough matching
    return parts[-1]


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


def fetch_csv(url):
    try:
        r = requests.get(url, timeout=25)

        print("FETCH:", url)
        print("HTTP:", r.status_code)

        if r.status_code != 200:
            return []

        text = r.text

        if len(text) < 100:
            return []

        reader = csv.DictReader(StringIO(text))
        rows = list(reader)

        print("ROWS:", len(rows))
        print("COLUMNS SAMPLE:", reader.fieldnames[:20] if reader.fieldnames else [])

        return rows

    except Exception as e:
        print("FETCH ERROR:", url, str(e))
        return []


def parse_sets_from_score(score):
    """
    Very simple parser:
    score like: 6-4 3-6 7-6(5)
    returns approximate sets won by first-listed winner and loser.
    In Sackmann match files, winner_name is winner, loser_name is loser.
    """
    if not score:
        return {"winner_sets": 0, "loser_sets": 0, "sets_total": 0}

    score = str(score)

    # odstráň retirement / walkover flags
    if "RET" in score.upper() or "W/O" in score.upper() or "DEF" in score.upper():
        return {"winner_sets": None, "loser_sets": None, "sets_total": None}

    chunks = score.split()
    winner_sets = 0
    loser_sets = 0

    for chunk in chunks:
        m = re.match(r"(\d+)-(\d+)", chunk)

        if not m:
            continue

        a = int(m.group(1))
        b = int(m.group(2))

        if a > b:
            winner_sets += 1
        elif b > a:
            loser_sets += 1

    return {
        "winner_sets": winner_sets,
        "loser_sets": loser_sets,
        "sets_total": winner_sets + loser_sets
    }


def collect_player_stats(rows, player_name):
    target = normalize_name(player_name)

    stats = {
        "player": player_name,
        "normalized": target,
        "matches_found": 0,
        "ace_values": [],
        "sets_won": 0,
        "sets_lost": 0,
        "matches_with_set_score": 0,
        "won_at_least_one_set_matches": 0,
        "completed_rows_checked": 0
    }

    if not target:
        return stats

    for row in rows:
        winner = row.get("winner_name", "")
        loser = row.get("loser_name", "")

        winner_norm = normalize_name(winner)
        loser_norm = normalize_name(loser)

        if target not in [winner_norm, loser_norm]:
            continue

        stats["matches_found"] += 1

        # Aces
        if target == winner_norm:
            ace = row.get("w_ace")
        else:
            ace = row.get("l_ace")

        try:
            if ace not in [None, "", "NA"]:
                stats["ace_values"].append(float(ace))
        except Exception:
            pass

        # Sets
        score = row.get("score", "")
        parsed = parse_sets_from_score(score)

        if parsed["sets_total"] is not None and parsed["sets_total"] > 0:
            stats["matches_with_set_score"] += 1

            if target == winner_norm:
                player_sets = parsed["winner_sets"]
                opponent_sets = parsed["loser_sets"]
            else:
                player_sets = parsed["loser_sets"]
                opponent_sets = parsed["winner_sets"]

            stats["sets_won"] += player_sets
            stats["sets_lost"] += opponent_sets

            if player_sets >= 1:
                stats["won_at_least_one_set_matches"] += 1

    ace_count = len(stats["ace_values"])

    if ace_count > 0:
        stats["avg_aces"] = round(sum(stats["ace_values"]) / ace_count, 2)
        stats["aces_sample"] = ace_count
    else:
        stats["avg_aces"] = None
        stats["aces_sample"] = 0

    if stats["matches_with_set_score"] > 0:
        stats["set_win_rate"] = round(
            stats["sets_won"] / max(1, stats["sets_won"] + stats["sets_lost"]),
            3
        )
        stats["at_least_one_set_rate"] = round(
            stats["won_at_least_one_set_matches"] / stats["matches_with_set_score"],
            3
        )
    else:
        stats["set_win_rate"] = None
        stats["at_least_one_set_rate"] = None

    # aby JSON nebol obrovský
    stats.pop("ace_values", None)

    return stats


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

    all_rows = []
    source_report = []

    for url in DATA_URLS:
        rows = fetch_csv(url)

        source_report.append({
            "url": url,
            "rows": len(rows),
            "has_w_ace": bool(rows and "w_ace" in rows[0]),
            "has_l_ace": bool(rows and "l_ace" in rows[0]),
            "has_score": bool(rows and "score" in rows[0])
        })

        all_rows.extend(rows)

    print("TOTAL HISTORICAL ROWS:", len(all_rows))

    player_stats = []

    for player in players:
        stats = collect_player_stats(all_rows, player)
        player_stats.append(stats)

    summary = {
        "date": TODAY,
        "predictions_loaded": len(predictions),
        "players_tested": len(players),
        "historical_rows_loaded": len(all_rows),
        "sources": source_report,
        "players_with_aces": sum(1 for p in player_stats if p.get("aces_sample", 0) > 0),
        "players_with_set_data": sum(1 for p in player_stats if p.get("matches_with_set_score", 0) > 0),
    }

    output = {
        "summary": summary,
        "player_stats": player_stats
    }

    print("===== STATS PROBE SUMMARY =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    print("===== PLAYER STATS SAMPLE =====")
    print(json.dumps(player_stats[:20], indent=2, ensure_ascii=False))

    with open("public/stats_probe_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open("public/stats_probe_full.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
