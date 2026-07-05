import glob
import json
import os
import re

from play_history import (
    betting_day,
    save_all_snapshot,
    save_top5_snapshot,
)

from prediction_engine_top import (
    build_all_predictions,
    get_top_predictions,
)


ALL_SNAPSHOT_DIR = "data/pick_history/all"
TOP5_SNAPSHOT_DIR = "data/pick_history/top5"


# -----------------------------------------------------------------------------
# Generic JSON helpers
# -----------------------------------------------------------------------------


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



def load_json(path, default):
    try:
        if not path:
            return default

        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as exc:
        print(
            "UPDATE JSON LOAD ERROR:",
            path,
            str(exc),
        )

        return default



def is_non_empty_list(data):
    return isinstance(data, list) and len(data) > 0


# -----------------------------------------------------------------------------
# Snapshot helpers
# -----------------------------------------------------------------------------


def snapshot_path(kind, date):
    if kind == "all":
        return os.path.join(
            ALL_SNAPSHOT_DIR,
            f"{date}.json",
        )

    if kind == "top5":
        return os.path.join(
            TOP5_SNAPSHOT_DIR,
            f"{date}.json",
        )

    raise ValueError(
        f"Unsupported snapshot kind: {kind}"
    )



def extract_date_from_filename(path):
    filename = os.path.basename(path or "")

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})",
        filename,
    )

    if not match:
        return ""

    return match.group(1)



def latest_non_empty_snapshot(kind):
    if kind == "all":
        pattern = os.path.join(
            ALL_SNAPSHOT_DIR,
            "*.json",
        )

    elif kind == "top5":
        pattern = os.path.join(
            TOP5_SNAPSHOT_DIR,
            "*.json",
        )

    else:
        raise ValueError(
            f"Unsupported snapshot kind: {kind}"
        )

    files = glob.glob(pattern)

    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )

    for path in files:
        data = load_json(
            path,
            [],
        )

        if is_non_empty_list(data):
            print(
                "LATEST NON-EMPTY SNAPSHOT:",
                kind,
                path,
                len(data),
            )

            return data

    print(
        "LATEST NON-EMPTY SNAPSHOT:",
        kind,
        None,
    )

    return []



def load_today_snapshot(kind, date):
    path = snapshot_path(
        kind,
        date,
    )

    data = load_json(
        path,
        [],
    )

    if is_non_empty_list(data):
        print(
            "TODAY SNAPSHOT FOUND:",
            kind,
            path,
            len(data),
        )

        return data

    if os.path.exists(path):
        print(
            "TODAY SNAPSHOT EXISTS BUT IS EMPTY - IGNORING:",
            kind,
            path,
        )

    return []



def save_non_empty_all_snapshot(date, all_predictions):
    if not is_non_empty_list(all_predictions):
        print(
            "SKIP ALL SNAPSHOT SAVE:",
            "generated ALL is empty",
        )

        return load_today_snapshot(
            "all",
            date,
        )

    snapshot = save_all_snapshot(
        date=date,
        all_predictions=all_predictions,
    )

    if is_non_empty_list(snapshot):
        return snapshot

    # If an older bug created an empty immutable file for today, treat that empty
    # file as invalid and repair it with the current non-empty generated data.
    path = snapshot_path(
        "all",
        date,
    )

    print(
        "REPAIR EMPTY ALL SNAPSHOT WITH NON-EMPTY GENERATED DATA:",
        path,
        len(all_predictions),
    )

    save_json(
        path,
        all_predictions,
    )

    return all_predictions



def save_non_empty_top5_snapshot(date, top_predictions):
    if not is_non_empty_list(top_predictions):
        print(
            "SKIP TOP5 SNAPSHOT SAVE:",
            "generated TOP5 is empty",
        )

        return load_today_snapshot(
            "top5",
            date,
        )

    snapshot = save_top5_snapshot(
        date=date,
        top5_predictions=top_predictions,
    )

    if is_non_empty_list(snapshot):
        return snapshot

    # If an older bug created an empty immutable file for today, treat that empty
    # file as invalid and repair it with the current non-empty generated data.
    path = snapshot_path(
        "top5",
        date,
    )

    print(
        "REPAIR EMPTY TOP5 SNAPSHOT WITH NON-EMPTY GENERATED DATA:",
        path,
        len(top_predictions),
    )

    save_json(
        path,
        top_predictions,
    )

    return top_predictions


# -----------------------------------------------------------------------------
# Public output selection
# -----------------------------------------------------------------------------


def choose_public_all_predictions(
    today,
    generated_all_predictions,
    all_snapshot,
):
    # Production rule:
    # 1. Prefer today's immutable non-empty snapshot.
    # 2. If there is no such snapshot, use today's non-empty generated output.
    # 3. If today is empty, fall back to the latest historical non-empty snapshot.
    # 4. Only fail if the project has no usable data at all.

    if is_non_empty_list(all_snapshot):
        print(
            "PUBLIC ALL SOURCE:",
            "today immutable snapshot",
            len(all_snapshot),
        )

        return all_snapshot

    if is_non_empty_list(generated_all_predictions):
        print(
            "PUBLIC ALL SOURCE:",
            "generated predictions",
            len(generated_all_predictions),
        )

        return generated_all_predictions

    restored_all = latest_non_empty_snapshot(
        "all"
    )

    if is_non_empty_list(restored_all):
        print(
            "PUBLIC ALL SOURCE:",
            "latest non-empty snapshot fallback",
            len(restored_all),
        )

        return restored_all

    raise RuntimeError(
        "No ALL predictions available. "
        "Generated ALL is empty and no non-empty immutable ALL snapshot exists. "
        "Refusing to write empty public ALL JSON."
    )



def choose_public_top_predictions(
    today,
    generated_top_predictions,
    top5_snapshot,
    public_all_predictions,
):
    # Production rule:
    # 1. Prefer today's immutable non-empty TOP5 snapshot.
    # 2. If there is no TOP5 snapshot, use today's non-empty generated TOP5.
    # 3. If TOP5 is empty, restore latest historical non-empty TOP5 snapshot.
    # 4. If no TOP5 snapshot exists, derive TOP5 from restored ALL.
    # 5. Only write empty TOP5 if ALL exists and build_pages.py can derive TOP5.

    if is_non_empty_list(top5_snapshot):
        print(
            "PUBLIC TOP5 SOURCE:",
            "today immutable snapshot",
            len(top5_snapshot),
        )

        return top5_snapshot

    if is_non_empty_list(generated_top_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "generated predictions",
            len(generated_top_predictions),
        )

        return generated_top_predictions

    restored_top5 = latest_non_empty_snapshot(
        "top5"
    )

    if is_non_empty_list(restored_top5):
        print(
            "PUBLIC TOP5 SOURCE:",
            "latest non-empty snapshot fallback",
            len(restored_top5),
        )

        return restored_top5

    if is_non_empty_list(public_all_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "derived from public ALL predictions",
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
        "No generated TOP5, no TOP5 snapshot, no historical TOP5, "
        "and no derived TOP5. Writing empty TOP5 public JSON. "
        "build_pages.py can derive TOP5 from ALL."
    )

    return []


# -----------------------------------------------------------------------------
# Main workflow entry
# -----------------------------------------------------------------------------


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
    os.makedirs(ALL_SNAPSHOT_DIR, exist_ok=True)
    os.makedirs(TOP5_SNAPSHOT_DIR, exist_ok=True)

    print("LOADING TODAY IMMUTABLE SNAPSHOTS...")

    existing_all_snapshot = load_today_snapshot(
        "all",
        today,
    )

    existing_top5_snapshot = load_today_snapshot(
        "top5",
        today,
    )

    print("SAVING IMMUTABLE ALL SNAPSHOT IF NON-EMPTY...")

    if is_non_empty_list(existing_all_snapshot):
        all_snapshot = existing_all_snapshot
        print(
            "KEEPING EXISTING NON-EMPTY ALL SNAPSHOT:",
            len(all_snapshot),
        )
    else:
        all_snapshot = save_non_empty_all_snapshot(
            date=today,
            all_predictions=all_predictions,
        )

    print("SAVING IMMUTABLE TOP5 SNAPSHOT IF NON-EMPTY...")

    if is_non_empty_list(existing_top5_snapshot):
        top5_snapshot = existing_top5_snapshot
        print(
            "KEEPING EXISTING NON-EMPTY TOP5 SNAPSHOT:",
            len(top5_snapshot),
        )
    else:
        top5_snapshot = save_non_empty_top5_snapshot(
            date=today,
            top_predictions=top_predictions,
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
        today=today,
        generated_all_predictions=all_predictions,
        all_snapshot=all_snapshot,
    )

    public_top_predictions = choose_public_top_predictions(
        today=today,
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
