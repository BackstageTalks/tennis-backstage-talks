import json
import glob
import os
import re
from datetime import datetime, timezone


DATA_DIR = "data"
PUBLIC_DIR = "public"
HISTORY_PATH = os.path.join(DATA_DIR, "bet_history.jsonl")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)


def latest_file(pattern):
    files = sorted(glob.glob(pattern))

    if not files:
        return None

    return files[-1]


def load_json(path):
    if not path or not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("ERROR reading JSON:", path, e)
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["results", "predictions", "items", "data", "matches"]:
            if isinstance(data.get(key), list):
                return data[key]

    return []


def extract_date_from_filename(path):
    if not path:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    name = os.path.basename(path)

    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if m:
        return m.group(1)

    m = re.search(r"(\d{8})", name)
    if m:
        raw = m.group(1)
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def safe(value, default=""):
    if value is None:
        return default

    return str(value)


def normalize_name(value):
    return safe(value).strip().lower()


def normalize_status(value):
    if value is None:
        return None

    text = safe(value).strip().upper()

    if text in ["WON", "WIN", "WINNER", "SUCCESS", "HIT", "✅ WON"]:
        return "WON"

    if text in ["LOST", "LOSS", "LOSE", "FAILED", "MISS", "❌ LOST"]:
        return "LOST"

    if text in ["VOID", "CANCELLED", "CANCELED", "WALKOVER", "RET", "RETIRED"]:
        return "VOID"

    if text in ["PENDING", "OPEN", "SCHEDULED", "NOT_STARTED", "LIVE"]:
        return "PENDING"

    if text in ["UNKNOWN", "NOT_FOUND", "NO_RESULT"]:
        return "UNKNOWN"

    return None


def detect_status(item):
    """
    Robustné čítanie výsledkov z rôznych možných štruktúr results_checker.py.
    """
    for key in [
        "pick_result",
        "bet_result",
        "result",
        "status",
        "match_status",
        "outcome",
        "prediction_result",
    ]:
        status = normalize_status(item.get(key))
        if status:
            return status

    won_value = item.get("won")

    if isinstance(won_value, bool):
        return "WON" if won_value else "LOST"

    success_value = item.get("success")

    if isinstance(success_value, bool):
        return "WON" if success_value else "LOST"

    pick = normalize_name(item.get("pick"))
    opponent = normalize_name(item.get("opponent"))

    winner = normalize_name(
        item.get("winner")
        or item.get("match_winner")
        or item.get("actual_winner")
        or item.get("result_winner")
    )

    if winner:
        if winner == pick:
            return "WON"

        if winner == opponent:
            return "LOST"

    return "PENDING"


def extract_score(item):
    for key in [
        "score",
        "final_score",
        "match_score",
        "result_score",
        "sets_score",
    ]:
        value = item.get(key)
        if value:
            return safe(value)

    return ""


def make_bet_id(date, feed, item):
    pick = safe(item.get("pick")).strip()
    opponent = safe(item.get("opponent")).strip()
    tournament = safe(item.get("tournament")).strip()
    match_time = safe(item.get("match_time_raw") or item.get("match_start")).strip()

    raw = "|".join([
        date,
        feed,
        pick.lower(),
        opponent.lower(),
        tournament.lower(),
        match_time.lower(),
    ])

    raw = re.sub(r"\s+", " ", raw)

    return raw


def base_record(date, feed, item):
    alt = item.get("alternative_market_info") or {}

    status = detect_status(item)

    return {
        "bet_id": make_bet_id(date, feed, item),
        "date": date,
        "feed": feed,

        "pick": item.get("pick"),
        "opponent": item.get("opponent"),
        "player1": item.get("player1"),
        "player2": item.get("player2"),
        "tournament": item.get("tournament"),

        "probability": item.get("probability"),
        "odds": item.get("odds"),

        "match_start": item.get("match_start"),
        "match_time_raw": item.get("match_time_raw"),

        "result": status,
        "score": extract_score(item),

        "model_source": item.get("model_source"),
        "bet_tag": item.get("bet_tag"),

        "sets_most_likely": alt.get("most_likely_sets"),
        "sets_probability": alt.get("sets_probability"),
        "expected_games": alt.get("expected_games"),
        "games_lean": alt.get("games_lean"),

        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {}

    records = {}

    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
            except Exception:
                continue

            bet_id = item.get("bet_id")

            if bet_id:
                records[bet_id] = item

    return records


def save_history(records):
    ordered = sorted(
        records.values(),
        key=lambda x: (
            x.get("date", ""),
            x.get("feed", ""),
            x.get("pick", ""),
            x.get("opponent", ""),
        )
    )

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        for item in ordered:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def merge_record(records, new_record):
    bet_id = new_record["bet_id"]

    old_record = records.get(bet_id)

    if not old_record:
        records[bet_id] = new_record
        return

    old_status = old_record.get("result")
    new_status = new_record.get("result")

    # PENDING môže byť prepísaný WON/LOST/VOID/UNKNOWN.
    # WON/LOST neprepíšeme späť na PENDING.
    if old_status in ["WON", "LOST", "VOID"] and new_status == "PENDING":
        new_record["result"] = old_status
        new_record["score"] = old_record.get("score", new_record.get("score"))

    merged = old_record.copy()
    merged.update(new_record)

    records[bet_id] = merged


def import_feed(records, feed, predictions_path, results_path):
    prediction_items = load_json(predictions_path)
    result_items = load_json(results_path)

    date = extract_date_from_filename(predictions_path or results_path)

    print(f"Import feed={feed}")
    print("Predictions path:", predictions_path)
    print("Results path:", results_path)
    print("Prediction items:", len(prediction_items))
    print("Result items:", len(result_items))

    # Najprv vložíme predikcie ako PENDING.
    for item in prediction_items:
        record = base_record(date, feed, item)

        # Ak predikčný JSON nemá výsledok, nech je PENDING.
        if record["result"] not in ["WON", "LOST", "VOID", "UNKNOWN"]:
            record["result"] = "PENDING"

        merge_record(records, record)

    # Potom overlayneme výsledky, ak už existujú.
    for item in result_items:
        record = base_record(date, feed, item)
        merge_record(records, record)


def main():
    ensure_dirs()

    records = load_history()

    top_predictions = latest_file(os.path.join(PUBLIC_DIR, "predictions_*.json"))
    all_predictions = latest_file(os.path.join(PUBLIC_DIR, "all_predictions_*.json"))

    top_results = latest_file(os.path.join(PUBLIC_DIR, "results_*.json"))
    all_results = latest_file(os.path.join(PUBLIC_DIR, "all_results_*.json"))

    import_feed(
        records=records,
        feed="TOP",
        predictions_path=top_predictions,
        results_path=top_results,
    )

    import_feed(
        records=records,
        feed="ALL",
        predictions_path=all_predictions,
        results_path=all_results,
    )

    save_history(records)

    print("History saved:", HISTORY_PATH)
    print("Total history records:", len(records))


if __name__ == "__main__":
    main()
