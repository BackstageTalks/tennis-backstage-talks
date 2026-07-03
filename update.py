import json
import os

from play_history import (
    betting_day,
    save_all_snapshot,
    save_top5_snapshot,
)

from prediction_engine_top import (
    build_all_predictions,
    get_top_predictions,
)


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def run():
    today = betting_day()

    print("BETTING DAY:", today)
    print("BUILDING ALL PREDICTIONS...")

    all_predictions = build_all_predictions()

    print("BUILDING TOP5 PREDICTIONS...")

    top_predictions = get_top_predictions(
        all_predictions
    )

    os.makedirs("public", exist_ok=True)

    print("SAVING IMMUTABLE ALL SNAPSHOT...")

    all_snapshot = save_all_snapshot(
        date=today,
        all_predictions=all_predictions,
    )

    print("SAVING IMMUTABLE TOP5 SNAPSHOT...")

    top5_snapshot = save_top5_snapshot(
        date=today,
        top5_predictions=top_predictions,
    )

    top_path = f"public/predictions_{today}.json"
    all_path = f"public/all_predictions_{today}.json"

    save_json(
        top_path,
        top_predictions,
    )

    save_json(
        all_path,
        all_predictions,
    )

    print(
        "SAVED TOP PUBLIC JSON:",
        top_path,
        len(top_predictions),
    )

    print(
        "SAVED ALL PUBLIC JSON:",
        all_path,
        len(all_predictions),
    )

    print(
        "SAVED TOP5 SNAPSHOT:",
        len(top5_snapshot),
    )

    print(
        "SAVED ALL SNAPSHOT:",
        len(all_snapshot),
    )


if __name__ == "__main__":
    run()
