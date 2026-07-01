import json
import os
from datetime import datetime, timezone

from elo_engine import load as load_elo_store
from prediction_engine import build_all_predictions, get_top_predictions


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def probability_buckets(all_predictions):
    buckets = {
        "50_55": 0,
        "55_60": 0,
        "60_65": 0,
        "65_70": 0,
        "70_75": 0,
        "75_80": 0,
        "80_85": 0,
        "85_plus": 0,
    }

    for prediction in all_predictions:
        p = prediction.get("probability")

        if p is None:
            continue

        if p < 0.55:
            buckets["50_55"] += 1
        elif p < 0.60:
            buckets["55_60"] += 1
        elif p < 0.65:
            buckets["60_65"] += 1
        elif p < 0.70:
            buckets["65_70"] += 1
        elif p < 0.75:
            buckets["70_75"] += 1
        elif p < 0.80:
            buckets["75_80"] += 1
        elif p < 0.85:
            buckets["80_85"] += 1
        else:
            buckets["85_plus"] += 1

    return buckets


def average_probability(all_predictions):
    values = [
        p.get("probability")
        for p in all_predictions
        if p.get("probability") is not None
    ]

    if not values:
        return 0

    return round(sum(values) / len(values), 3)


def min_probability(all_predictions):
    values = [
        p.get("probability")
        for p in all_predictions
        if p.get("probability") is not None
    ]

    if not values:
        return 0

    return min(values)


def max_probability(all_predictions):
    values = [
        p.get("probability")
        for p in all_predictions
        if p.get("probability") is not None
    ]

    if not values:
        return 0

    return max(values)


def build_debug(all_predictions, top_predictions):
    with_odds = [
        p for p in all_predictions
        if p.get("odds") is not None
    ]

    eligible = [
        p for p in all_predictions
        if p.get("odds") is not None and p.get("odds") >= 1.50
    ]

    elo_found_both = [
        p for p in all_predictions
        if p.get("elo_found_player1") and p.get("elo_found_player2")
    ]

    elo_missing = [
        p for p in all_predictions
        if not (p.get("elo_found_player1") and p.get("elo_found_player2"))
    ]

    elo_store = load_elo_store()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "all_count": len(all_predictions),
        "top_count": len(top_predictions),

        "with_odds_count": len(with_odds),
        "eligible_odds_1_50_count": len(eligible),

        "elo_store_players": len(elo_store),
        "elo_found_both_count": len(elo_found_both),
        "elo_missing_count": len(elo_missing),

        "min_probability": round(min_probability(all_predictions), 3),
        "avg_probability": average_probability(all_predictions),
        "max_probability": round(max_probability(all_predictions), 3),
        "probability_buckets": probability_buckets(all_predictions),

        "sample_all": all_predictions[:5],
        "sample_top": top_predictions[:5],
        "sample_elo_found": elo_found_both[:10],
        "sample_elo_missing": elo_missing[:10],
    }


def run():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("BUILDING ALL PREDICTIONS...")
    all_predictions = build_all_predictions()

    print("BUILDING TOP PREDICTIONS...")
    top_predictions = get_top_predictions(all_predictions)

    os.makedirs("public", exist_ok=True)

    top_path = f"public/predictions_{today}.json"
    all_path = f"public/all_predictions_{today}.json"
    debug_path = "public/debug_counts.json"

    debug_data = build_debug(all_predictions, top_predictions)

    save_json(top_path, top_predictions)
    save_json(all_path, all_predictions)
    save_json(debug_path, debug_data)

    print("SAVED TOP:", top_path, len(top_predictions))
    print("SAVED ALL:", all_path, len(all_predictions))
    print("SAVED DEBUG:", debug_path)
    print("DEBUG:", debug_data)


if __name__ == "__main__":
    run()
