import json
import os
from datetime import datetime, timezone

from elo_engine import load as load_elo_store
from form_engine import load_form_store
from play_history import save_play_candidates

from prediction_engine_top import (
    build_all_predictions,
    get_top_predictions,
    MIN_TOP_PROBABILITY,
    MIN_ODDS,
)


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def run():
    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    print("BUILDING ALL PREDICTIONS...")
    all_predictions = build_all_predictions()

    print("BUILDING TOP PREDICTIONS...")
    top_predictions = get_top_predictions(
        all_predictions
    )

    os.makedirs(
        "public",
        exist_ok=True,
    )

    print("SAVING PLAY CANDIDATES...")
    save_play_candidates(
        today,
        all_predictions,
    )

    top_path = (
        f"public/predictions_{today}.json"
    )

    all_path = (
        f"public/all_predictions_{today}.json"
    )

    save_json(
        top_path,
        top_predictions,
    )

    save_json(
        all_path,
        all_predictions,
    )

    print(
        "SAVED TOP:",
        top_path,
        len(top_predictions),
    )

    print(
        "SAVED ALL:",
        all_path,
        len(all_predictions),
    )


if __name__ == "__main__":
    run()
