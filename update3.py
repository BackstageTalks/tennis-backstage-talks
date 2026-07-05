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


def is_non_empty_list(data):
    return isinstance(data, list) and len(data) > 0


def choose_public_all_predictions(
    generated_all_predictions,
    all_snapshot,
):
    if is_non_empty_list(generated_all_predictions):
        print(
            "PUBLIC ALL SOURCE:",
            "generated predictions",
            len(generated_all_predictions),
        )

        return generated_all_predictions

    if is_non_empty_list(all_snapshot):
        print(
            "PUBLIC ALL SOURCE:",
            "existing immutable snapshot",
            len(all_snapshot),
        )

        return all_snapshot

    raise RuntimeError(
        "No ALL predictions available. "
        "Generated ALL is empty and no immutable ALL snapshot exists. "
        "Refusing to write empty public ALL JSON."
    )


def choose_public_top_predictions(
    generated_top_predictions,
    top5_snapshot,
    public_all_predictions,
):
    if is_non_empty_list(generated_top_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "generated predictions",
            len(generated_top_predictions),
        )

        return generated_top_predictions

    if is_non_empty_list(top5_snapshot):
        print(
            "PUBLIC TOP5 SOURCE:",
            "existing immutable snapshot",
            len(top5_snapshot),
        )

        return top5_snapshot

    if is_non_empty_list(public_all_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "derived from restored ALL predictions",
        )

        derived_top = get_top_predictions(
            public_all_predictions,
        )

        if is_non_empty_list(derived_top):
            print(
                "PUBLIC TOP5 DERIVED COUNT:",
                len(derived_top),
            )

            return derived_top

    print(
        "PUBLIC TOP5 WARNING:",
        "No generated TOP5, no TOP5 snapshot, and no derived TOP5. "
        "Writing empty TOP5 public JSON. build_pages.py can derive TOP5 from ALL."
    )

    return []


def run():
    today = betting_day()

    print("BETTING DAY:", today)
    print("BUILDING ALL PREDICTIONS...")

    all_predictions = build_all_predictions()

    print(
        "GENERATED ALL COUNT:",
        len(all_predictions)
        if isinstance(all_predictions, list)
        else "invalid",
    )

    print("BUILDING TOP5 PREDICTIONS...")

    if is_non_empty_list(all_predictions):
        top_predictions = get_top_predictions(
            all_predictions
        )
    else:
        top_predictions = []

    print(
        "GENERATED TOP5 COUNT:",
        len(top_predictions)
        if isinstance(top_predictions, list)
        else "invalid",
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

    print(
        "IMMUTABLE ALL SNAPSHOT COUNT:",
        len(all_snapshot)
        if isinstance(all_snapshot, list)
        else "invalid",
    )

    print(
        "IMMUTABLE TOP5 SNAPSHOT COUNT:",
        len(top5_snapshot)
        if isinstance(top5_snapshot, list)
        else "invalid",
    )

    public_all_predictions = choose_public_all_predictions(
        generated_all_predictions=all_predictions,
        all_snapshot=all_snapshot,
    )

    public_top_predictions = choose_public_top_predictions(
        generated_top_predictions=top_predictions,
        top5_snapshot=top5_snapshot,
        public_all_predictions=public_all_predictions,
    )

    top_path = f"public/predictions_{today}.json"
    all_path = f"public/all_predictions_{today}.json"

    save_json(
        top_path,
        public_top_predictions,
    )

    save_json(
        all_path,
        public_all_predictions,
    )

    print(
        "SAVED TOP PUBLIC JSON:",
        top_path,
        len(public_top_predictions),
    )

    print(
        "SAVED ALL PUBLIC JSON:",
        all_path,
        len(public_all_predictions),
    )

    print(
        "SAVED TOP5 SNAPSHOT:",
        len(top5_snapshot)
        if isinstance(top5_snapshot, list)
        else "invalid",
    )

    print(
        "SAVED ALL SNAPSHOT:",
        len(all_snapshot)
        if isinstance(all_snapshot, list)
        else "invalid",
    )


if __name__ == "__main__":
    run()
