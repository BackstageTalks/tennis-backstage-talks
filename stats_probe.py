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

    parts = name.split()

    if not parts:
        return ""

    # rough matching podľa priezviska
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


def get_data_files():
    print("FETCH DATA FILE LIST:", DATA_FILES_ENDPOINT)

    try:
        r = requests.get(DATA_FILES_ENDPOINT, timeout=30)
        print("DATA FILES HTTP:", r.status_code)

        if r.status_code != 200:
            print("RAW ERROR:", r.text[:1000])
            return []

        data = r.json()

        files = data.get("files", [])

        print("DATA FILES FOUND:", len(files))

        for f in files[:20]:
            print("FILE SAMPLE:", f)

        return files

    except Exception as e:
        print("DATA FILE LIST ERROR:", str(e))
        return []


def choose_relevant_files(files):
    selected = []

    priority_keywords = [
        "ongoing",
        "2026",
        "2025",
        "2024",
        "challenger",
        "quali"
    ]

    for f in files:
        name = str(f.get("name", "")).lower()
        url = f.get("url")

        if not url:
            continue

        if not name.endswith(".csv"):
            continue

        if any(k in name for k in priority_keywords):
            selected.append(f)

    # limit, aby workflow neťahal úplne všetko
    selected = selected[:20]

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

        r = requests.get(url, timeout=45)

        print("HTTP:", r.status_code)

        if r.status_code != 200:
            print("RAW ERROR:", r.text[:500])
            return [], []

        text = r.text

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


def find_col(columns, candidates):
    lower_map = {c.lower(): c for c in columns}

    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]

    # fuzzy fallback
    for col in columns:
        low = col.lower()
        for cand in candidates:
            if cand.lower() in low:
                return col

    return None


def parse_sets_from_score(score):
    if not score:
        return {
            "p1_sets": None,
            "p2_sets": None,
            "sets_total": None
        }

    score = str(score)

    if any(x in score.upper() for x in ["RET", "W/O", "WO", "DEF", "ABN"]):
        return {
            "p1_sets": None,
            "p2_sets": None,
            "sets_total": None
        }

    chunks = score.split()

    p1_sets = 0
    p2_sets = 0

    for chunk in chunks:
        m = re.match(r"(\d+)-(\d+)", chunk)

        if not m:
            continue

        a = int(m.group(1))
        b = int(m.group(2))

        if a > b:
            p1_sets += 1
        elif b > a:
            p2_sets += 1

    total = p1_sets + p2_sets

    if total == 0:
        return {
            "p1_sets": None,
            "p2_sets": None,
            "sets_total": None
        }

    return {
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
        "sets_total": total
    }


def collect_stats_from_rows(rows, columns, player):
    player_norm = normalize_name(player)

    stats = {
        "player": player,
        "normalized": player_norm,
        "matches_found": 0,
        "matches_with_score": 0,
        "sets_won": 0,
        "sets_lost": 0,
        "won_at_least_one_set_matches": 0,
        "aces_values": [],
        "ace_columns_used": []
    }

    if not player_norm:
        return stats

    # možné názvy stĺpcov
    p1_col = find_col(columns, [
        "Player_1", "player_1", "player1", "player1_name",
        "winner_name", "Winner", "winner"
    ])

    p2_col = find_col(columns, [
        "Player_2", "player_2", "player2", "player2_name",
        "loser_name", "Loser", "loser"
    ])

    winner_col = find_col(columns, [
        "Winner", "winner", "winner_name"
    ])

    score_col = find_col(columns, [
        "Score", "score"
    ])

    # ace stĺpce - viac možností
    p1_ace_col = find_col(columns, [
        "w_ace", "player1_aces", "p1_aces", "Player_1_Aces",
        "player_1_aces", "aces_1", "Ace1", "Aces1"
    ])

    p2_ace_col = find_col(columns, [
        "l_ace", "player2_aces", "p2_aces", "Player_2_Aces",
        "player_2_aces", "aces_2", "Ace2", "Aces2"
    ])

    for row in rows:
        p1 = row.get(p1_col, "") if p1_col else ""
        p2 = row.get(p2_col, "") if p2_col else ""
        winner = row.get(winner_col, "") if winner_col else ""

        p1_norm = normalize_name(p1)
        p2_norm = normalize_name(p2)
        winner_norm = normalize_name(winner)

        if player_norm not in [p1_norm, p2_norm]:
            continue

        stats["matches_found"] += 1

        # setové dáta
        if score_col:
            parsed = parse_sets_from_score(row.get(score_col))

            if parsed["sets_total"] is not None:
                stats["matches_with_score"] += 1

                # ak formát je Winner/Loser dataset:
                # p1 môže byť winner_name, p2 loser_name
                if winner_col and winner_norm == player_norm:
                    player_sets = max(parsed["p1_sets"], parsed["p2_sets"])
                    opp_sets = min(parsed["p1_sets"], parsed["p2_sets"])
                elif winner_col and winner_norm != player_norm:
                    player_sets = min(parsed["p1_sets"], parsed["p2_sets"])
                    opp_sets = max(parsed["p1_sets"], parsed["p2_sets"])
                else:
                    # ak je Player_1 / Player_2 dataset
                    if player_norm == p1_norm:
                        player_sets = parsed["p1_sets"]
                        opp_sets = parsed["p2_sets"]
                    else:
                        player_sets = parsed["p2_sets"]
                        opp_sets = parsed["p1_sets"]

                stats["sets_won"] += player_sets
                stats["sets_lost"] += opp_sets

                if player_sets >= 1:
                    stats["won_at_least_one_set_matches"] += 1

        # ace dáta
        try:
            if player_norm == p1_norm and p1_ace_col:
                value = row.get(p1_ace_col)
                if value not in [None, "", "NA", "NaN"]:
                    stats["aces_values"].append(float(value))
                    stats["ace_columns_used"].append(p1_ace_col)

            elif player_norm == p2_norm and p2_ace_col:
                value = row.get(p2_ace_col)
                if value not in [None, "", "NA", "NaN"]:
                    stats["aces_values"].append(float(value))
                    stats["ace_columns_used"].append(p2_ace_col)
        except Exception:
            pass

    aces_count = len(stats["aces_values"])

    if aces_count > 0:
        stats["avg_aces"] = round(sum(stats["aces_values"]) / aces_count, 2)
        stats["aces_sample"] = aces_count
    else:
        stats["avg_aces"] = None
        stats["aces_sample"] = 0

    if stats["matches_with_score"] > 0:
        total_sets = stats["sets_won"] + stats["sets_lost"]

        stats["set_win_rate"] = round(stats["sets_won"] / max(1, total_sets), 3)

        stats["at_least_one_set_rate"] = round(
            stats["won_at_least_one_set_matches"] / stats["matches_with_score"],
            3
        )
    else:
        stats["set_win_rate"] = None
        stats["at_least_one_set_rate"] = None

    # cleanup
    stats["ace_columns_used"] = sorted(list(set(stats["ace_columns_used"])))
    stats.pop("aces_values", None)

    return stats


def merge_player_stats(stats_list):
    merged = {}

    for s in stats_list:
        player = s["player"]

        if player not in merged:
            merged[player] = {
                "player": player,
                "normalized": s["normalized"],
                "matches_found": 0,
                "matches_with_score": 0,
                "sets_won": 0,
                "sets_lost": 0,
                "won_at_least_one_set_matches": 0,
                "aces_total": 0,
                "aces_sample": 0,
                "ace_columns_used": set()
            }

        m = merged[player]

        m["matches_found"] += s.get("matches_found", 0)
        m["matches_with_score"] += s.get("matches_with_score", 0)
        m["sets_won"] += s.get("sets_won", 0)
        m["sets_lost"] += s.get("sets_lost", 0)
        m["won_at_least_one_set_matches"] += s.get("won_at_least_one_set_matches", 0)

        if s.get("avg_aces") is not None and s.get("aces_sample", 0) > 0:
            m["aces_total"] += s["avg_aces"] * s["aces_sample"]
            m["aces_sample"] += s["aces_sample"]

        for col in s.get("ace_columns_used", []):
            m["ace_columns_used"].add(col)

    output = []

    for player, m in merged.items():
        if m["aces_sample"] > 0:
            avg_aces = round(m["aces_total"] / m["aces_sample"], 2)
        else:
            avg_aces = None

        if m["matches_with_score"] > 0:
            total_sets = m["sets_won"] + m["sets_lost"]
            set_win_rate = round(m["sets_won"] / max(1, total_sets), 3)
            at_least_one_set_rate = round(
                m["won_at_least_one_set_matches"] / m["matches_with_score"],
                3
            )
        else:
            set_win_rate = None
            at_least_one_set_rate = None

        output.append({
            "player": player,
            "normalized": m["normalized"],
            "matches_found": m["matches_found"],
            "matches_with_score": m["matches_with_score"],
            "avg_aces": avg_aces,
            "aces_sample": m["aces_sample"],
            "ace_columns_used": sorted(list(m["ace_columns_used"])),
            "set_win_rate": set_win_rate,
            "at_least_one_set_rate": at_least_one_set_rate,
        })

    return output


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
    all_player_stats = []

    for file_info in selected_files:
        rows, columns = fetch_csv_file(file_info)

        if not rows:
            source_reports.append({
                "name": file_info.get("name"),
                "url": file_info.get("url"),
                "rows": 0,
                "columns": [],
                "has_score": False,
                "has_aces_candidate": False
            })
            continue

        has_score = any("score" in c.lower() for c in columns)
        has_aces_candidate = any(
            "ace" in c.lower() or "aces" in c.lower()
            for c in columns
        )

        source_reports.append({
            "name": file_info.get("name"),
            "url": file_info.get("url"),
            "rows": len(rows),
            "columns": columns,
            "has_score": has_score,
            "has_aces_candidate": has_aces_candidate
        })

        for player in players:
            s = collect_stats_from_rows(rows, columns, player)
            s["source_file"] = file_info.get("name")
            all_player_stats.append(s)

    merged_stats = merge_player_stats(all_player_stats)

    summary = {
        "date": TODAY,
        "predictions_loaded": len(predictions),
        "players_tested": len(players),
        "files_found": len(data_files),
        "files_selected": len(selected_files),
        "players_with_matches": sum(1 for p in merged_stats if p["matches_found"] > 0),
        "players_with_aces": sum(1 for p in merged_stats if p["aces_sample"] > 0),
        "players_with_set_data": sum(1 for p in merged_stats if p["matches_with_score"] > 0),
    }

    output = {
        "summary": summary,
        "sources": source_reports,
        "player_stats": merged_stats,
        "raw_player_stats_by_file": all_player_stats
    }

    print("===== STATS PROBE SUMMARY =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    print("===== PLAYER STATS =====")
    print(json.dumps(merged_stats, indent=2, ensure_ascii=False))

    with open("public/stats_probe_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open("public/stats_probe_full.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
