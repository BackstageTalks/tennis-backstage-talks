import json
import glob
import os
import re
from datetime import datetime, timezone


DATA_DIR = "data"
PUBLIC_DIR = "public"
HISTORY_PATH = os.path.join(DATA_DIR, "bet_history.jsonl")

MODEL_VERSION = "ELO_PLUS_TOP5_ODDS_GT_150_V1"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


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


def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)
    except Exception:
        return None


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

    if text in [
        "VOID",
        "CANCELLED",
        "CANCELED",
        "WALKOVER",
        "RET",
        "RETIRED",
        "ABANDONED",
        "WITHDRAWN",
    ]:
        return "VOID"

    if text in ["PENDING", "OPEN", "SCHEDULED", "NOT_STARTED", "LIVE"]:
        return "PENDING"

    if text in ["UNKNOWN", "NOT_FOUND", "NO_RESULT"]:
        return "UNKNOWN"

    return None


def detect_status(item):
    """
    Robustné čítanie výsledkov z rôznych možných štruktúr results_checker.py.
    Ak výsledok nevieme zistiť, použijeme PENDING.
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
    """
    Stabilný identifikátor jedného picku.
    Cieľ: zabrániť duplicitám aj pri opakovanom results refresh.
    """
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


def get_model_version(item):
    return (
        item.get("model_version")
        or item.get("model_source_version")
        or MODEL_VERSION
    )


def base_record(date, feed, item):
    alt = item.get("alternative_market_info") or {}

    status = detect_status(item)

    probability = safe_float(item.get("probability"))
    odds = safe_float(item.get("odds"))

    record = {
        "bet_id": make_bet_id(date, feed, item),

        # identity
        "date": date,
        "feed": feed,
        "model_version": get_model_version(item),
        "model_source": item.get("model_source"),

        # match
        "pick": item.get("pick"),
        "opponent": item.get("opponent"),
        "player1": item.get("player1"),
        "player2": item.get("player2"),
        "tournament": item.get("tournament"),
        "surface": item.get("surface"),

        # prediction snapshot
        "probability": probability,
        "opponent_probability": safe_float(item.get("opponent_probability")),
        "confidence": safe_float(item.get("confidence")),
        "winner_rank_score": safe_float(item.get("winner_rank_score") or item.get("score")),
        "base_elo_probability": safe_float(item.get("base_elo_probability")),
        "elo_stats_adjustment": safe_float(item.get("elo_stats_adjustment")),

        # odds snapshot
        "odds": odds,
        "odds_player1": safe_float(item.get("odds_player1")),
        "odds_player2": safe_float(item.get("odds_player2")),
        "odds_source": item.get("odds_source"),

        # timing
        "match_start": item.get("match_start"),
        "match_time_raw": item.get("match_time_raw"),

        # result
        "result": status,
        "score": extract_score(item),

        # classification
        "bet_tag": item.get("bet_tag"),
        "short_reason": item.get("short_reason"),

        # INFO ONLY markets
        "sets_most_likely": alt.get("most_likely_sets"),
        "sets_probability": safe_float(alt.get("sets_probability")),
        "sets_fair_odds": safe_float(alt.get("sets_fair_odds")),
        "over_2_5_sets_probability": safe_float(alt.get("over_2_5_sets_probability")),
        "under_2_5_sets_probability": safe_float(alt.get("under_2_5_sets_probability")),
        "over_3_5_sets_probability": safe_float(alt.get("over_3_5_sets_probability")),
        "under_3_5_sets_probability": safe_float(alt.get("under_3_5_sets_probability")),
        "over_4_5_sets_probability": safe_float(alt.get("over_4_5_sets_probability")),
        "under_4_5_sets_probability": safe_float(alt.get("under_4_5_sets_probability")),
        "expected_games": safe_float(alt.get("expected_games")),
        "games_lean": alt.get("games_lean"),

        # future learning fields
        "learning_bucket_probability": probability_bucket(probability),
        "learning_bucket_odds": odds_bucket(odds),
        "is_top_feed": feed == "TOP",

        # timestamps
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    return record


def probability_bucket(probability):
    if probability is None:
        return "unknown"

    if probability < 0.50:
        return "<50"

    if probability < 0.55:
        return "50-55"

    if probability < 0.60:
        return "55-60"

    if probability < 0.65:
        return "60-65"

    if probability < 0.70:
        return "65-70"

    if probability < 0.75:
        return "70-75"

    return "75+"


def odds_bucket(odds):
    if odds is None:
        return "unknown"

    if odds < 1.30:
        return "<1.30"

    if odds < 1.50:
        return "1.30-1.50"

    if odds < 1.80:
        return "1.50-1.80"

    if odds < 2.20:
        return "1.80-2.20"

    if odds < 3.00:
        return "2.20-3.00"

    return "3.00+"


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
            x.get("pick", "") or "",
            x.get("opponent", "") or "",
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

    # Ak už máme definitívny výsledok, neprepíšeme ho späť na PENDING.
    if old_status in ["WON", "LOST", "VOID"] and new_status == "PENDING":
        new_record["result"] = old_status
        new_record["score"] = old_record.get("score", new_record.get("score"))

    # Zachovaj pôvodný created_at.
    if old_record.get("created_at"):
        new_record["created_at"] = old_record.get("created_at")

    new_record["updated_at"] = utc_now()

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

    # 1. Najprv uložíme predikcie ako historický snapshot.
    for item in prediction_items:
        record = base_record(date, feed, item)

        if record["result"] not in ["WON", "LOST", "VOID", "UNKNOWN"]:
            record["result"] = "PENDING"

        merge_record(records, record)

    # 2. Potom prelepíme výsledkami, ak už existujú.
    for item in result_items:
        record = base_record(date, feed, item)
        merge_record(records, record)


def export_learning_snapshot(records):
    """
    Exportuje kompletný JSON vhodný pre budúce učenie.
    JSONL ostáva hlavná DB, toto je pohodlný full export.
    """
    path = os.path.join(DATA_DIR, "bet_history_learning_snapshot.json")

    ordered = sorted(
        records.values(),
        key=lambda x: (
            x.get("date", ""),
            x.get("feed", ""),
            x.get("pick", "") or "",
            x.get("opponent", "") or "",
        )
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)

    print("Learning snapshot saved:", path)


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
    export_learning_snapshot(records)

    print("History saved:", HISTORY_PATH)
    print("Total history records:", len(records))


if __name__ == "__main__":
    main()
