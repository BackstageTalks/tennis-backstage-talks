import json
import os
from datetime import datetime, timezone

from prediction_engine import build_all_predictions, get_top_predictions


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_count": len(all_predictions),
        "top_count": len(top_predictions),
        "with_odds_count": len(with_odds),
        "eligible_odds_1_50_count": len(eligible),
        "elo_found_both_count": len(elo_found_both),
        "elo_missing_count": len(elo_missing),
        "max_probability": max(
            [p.get("probability") or 0 for p in all_predictions],
            default=0
        ),
        "sample_all": all_predictions[:5],
        "sample_top": top_predictions[:5],
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
