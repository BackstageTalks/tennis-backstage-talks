import json
import os
from datetime import datetime, timezone

try:
    import requests
except Exception:
    requests = None


MIN_ODDS = 1.50
MIN_PLAY_PROBABILITY = 0.60

DATA_HISTORY_PATH = "data/play_candidates_history.jsonl"
PUBLIC_HISTORY_PATH = "public/play_candidates_history.jsonl"

PREVIOUS_PUBLIC_HISTORY_URL = (
    "https://backstagetalks.github.io/tennis-backstage-talks/"
    "play_candidates_history.jsonl"
)


def ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs("public", exist_ok=True)


def play_candidate_filter(prediction):
    try:
        odds = prediction.get("odds")
        probability = prediction.get("probability")

        if odds is None or probability is None:
            return False

        return (
            float(odds) >= MIN_ODDS
            and float(probability) >= MIN_PLAY_PROBABILITY
            and prediction.get("elo_found_player1")
            and prediction.get("elo_found_player2")
        )
    except Exception:
        return False


def compact_candidate(prediction, date, rank):
    adjustment = prediction.get("form_adjustment") or {}

    return {
        "date": date,
        "rank": rank,

        "pick": prediction.get("pick"),
        "opponent": prediction.get("opponent"),
        "match": prediction.get("match"),
        "player1": prediction.get("player1"),
        "player2": prediction.get("player2"),
        "tournament": prediction.get("tournament"),
        "surface": prediction.get("surface"),
        "time": prediction.get("time"),
        "match_start": prediction.get("match_start"),

        "base_probability": prediction.get("base_probability"),
        "probability": prediction.get("probability"),
        "confidence": prediction.get("confidence"),

        "form_adjustment": adjustment.get("total_adjustment"),
        "recent_adjustment": adjustment.get("recent_adjustment"),
        "surface_adjustment": adjustment.get("surface_adjustment"),

        "odds": prediction.get("odds"),
        "odds_player1": prediction.get("odds_player1"),
        "odds_player2": prediction.get("odds_player2"),
        "odds_source": prediction.get("odds_source"),

        "market_probability": prediction.get("market_probability"),

        "elo_player": prediction.get("elo_player"),
        "elo_opponent": prediction.get("elo_opponent"),
        "elo_player1": prediction.get("elo_player1"),
        "elo_player2": prediction.get("elo_player2"),

        "elo_found_player1": prediction.get("elo_found_player1"),
        "elo_found_player2": prediction.get("elo_found_player2"),
        "elo_reliability_player1": prediction.get("elo_reliability_player1"),
        "elo_reliability_player2": prediction.get("elo_reliability_player2"),
        "elo_matches_player1": prediction.get("elo_matches_player1"),
        "elo_matches_player2": prediction.get("elo_matches_player2"),

        "model_source": prediction.get("model_source"),
        "model_version": prediction.get("model_version"),

        "result": "PENDING",
        "winner": None,
        "score_result": None,
        "profit_1u": None,

        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_play_candidates(all_predictions, date):
    candidates = [
        p for p in all_predictions
        if play_candidate_filter(p)
    ]

    candidates.sort(
        key=lambda x: (
            float(x.get("probability") or 0),
            min(
                float(x.get("elo_reliability_player1") or 0),
                float(x.get("elo_reliability_player2") or 0),
            ),
        ),
        reverse=True,
    )

    return [
        compact_candidate(prediction, date, index + 1)
        for index, prediction in enumerate(candidates)
    ]


def load_jsonl(path):
    rows = []

    if not os.path.exists(path):
        return rows

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except Exception:
                continue

    return rows


def fetch_previous_public_history():
    if requests is None:
        return []

    try:
        response = requests.get(PREVIOUS_PUBLIC_HISTORY_URL, timeout=20)

        if response.status_code != 200:
            return []

        rows = []

        for line in response.text.splitlines():
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except Exception:
                continue

        return rows

    except Exception as e:
        print("PREVIOUS HISTORY FETCH ERROR:", e)
        return []


def row_key(row):
    return "::".join([
        str(row.get("date") or ""),
        str(row.get("match") or ""),
        str(row.get("pick") or ""),
        str(row.get("opponent") or ""),
    ])


def merge_history(existing_rows, new_rows):
    merged = {}

    for row in existing_rows:
        merged[row_key(row)] = row

    for row in new_rows:
        merged[row_key(row)] = row

    output = list(merged.values())

    output.sort(
        key=lambda x: (
            str(x.get("date") or ""),
            int(x.get("rank") or 9999),
            str(x.get("match") or ""),
        )
    )

    return output


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_play_candidates(date, all_predictions):
    ensure_dirs()

    daily_candidates = build_play_candidates(all_predictions, date)

    daily_path = f"public/play_candidates_{date}.json"

    with open(daily_path, "w", encoding="utf-8") as f:
        json.dump(daily_candidates, f, ensure_ascii=False, indent=2)

    local_history = load_jsonl(DATA_HISTORY_PATH)

    if not local_history:
        previous_public_history = fetch_previous_public_history()
    else:
        previous_public_history = []

    existing_history = local_history or previous_public_history

    merged_history = merge_history(existing_history, daily_candidates)

    write_jsonl(DATA_HISTORY_PATH, merged_history)
    write_jsonl(PUBLIC_HISTORY_PATH, merged_history)

    print("SAVED PLAY CANDIDATES:", daily_path, len(daily_candidates))
    print("PLAY HISTORY TOTAL:", len(merged_history))

    return {
        "daily_path": daily_path,
        "daily_count": len(daily_candidates),
        "history_count": len(merged_history),
        "daily_candidates": daily_candidates,
    }
