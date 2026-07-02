import json
import os
import re
from datetime import datetime, timezone


PLAY_HISTORY_DIR = "data/play_history"
LATEST_PUBLIC_PATH = "public/play_history_latest.json"


def ensure_dirs():
    os.makedirs(
        PLAY_HISTORY_DIR,
        exist_ok=True,
    )

    os.makedirs(
        "public",
        exist_ok=True,
    )


def normalize_text(value):
    if value is None:
        return ""

    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9à-ž\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_pick_id(date, prediction):
    match = normalize_text(
        prediction.get("match")
    )

    pick = normalize_text(
        prediction.get("pick")
    )

    opponent = normalize_text(
        prediction.get("opponent")
    )

    base = f"{date}::{match}::{pick}::{opponent}"

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        base,
    ).strip("_")


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None

        return float(value)

    except Exception:
        return None


def today_utc():
    return datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")


def history_path(date):
    return os.path.join(
        PLAY_HISTORY_DIR,
        f"{date}.json",
    )


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception:
        return default


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def build_snapshot_record(date, prediction, rank):
    pick_id = make_pick_id(
        date,
        prediction,
    )

    odds = safe_float(
        prediction.get("odds")
    )

    probability = safe_float(
        prediction.get("probability")
    )

    return {
        "id": pick_id,
        "date": date,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "rank": rank,

        "match": prediction.get("match"),
        "pick": prediction.get("pick"),
        "opponent": prediction.get("opponent"),

        "probability": probability,
        "odds": odds,

        "time": prediction.get("time"),

        "bookmaker": prediction.get("bookmaker"),
        "odds_source": prediction.get("odds_source"),

        "tournament": prediction.get("tournament"),
        "gender": prediction.get("gender"),
        "surface": prediction.get("surface"),
        "best_of": prediction.get("best_of"),

        "expected_sets": prediction.get("expected_sets"),
        "sets_probability": prediction.get("sets_probability"),
        "sets_probability_label": prediction.get("sets_probability_label"),
        "most_likely_score": prediction.get("most_likely_score"),
        "score_probabilities": prediction.get("score_probabilities"),

        "bet_tag": prediction.get("bet_tag"),

        "result_status": "PENDING",
        "winner": None,
        "score": None,
        "units": 0.0,
        "resolved_at": None,
        "result_source": None,
        "result_match_score": None,
    }


def merge_existing_record(existing, new_record):
    """
    Denný pick je snapshot.

    Pri opakovanom rune nechceme prepísať:
    - pick
    - odds
    - probability
    - tournament
    - modelové dáta

    Zachováme však výsledkové polia, ak už existujú.
    """

    result_fields = [
        "result_status",
        "winner",
        "score",
        "units",
        "resolved_at",
        "result_source",
        "result_match_score",
    ]

    merged = dict(existing)

    for field in result_fields:
        if field in existing:
            merged[field] = existing.get(field)

    return merged


def save_play_candidates(date=None, predictions=None):
    """
    Volané z update.py.

    Očakávané volanie:
        save_play_candidates(today, all_predictions)

    Funkcia uloží snapshot pickov do:
        data/play_history/YYYY-MM-DD.json

    Pri ďalšom rune v ten istý deň sa existujúce picky neprepíšu.
    Nové picky sa doplnia.
    """

    ensure_dirs()

    if predictions is None:
        predictions = []

    if date is None:
        date = today_utc()

    path = history_path(date)

    existing_data = load_json(
        path,
        [],
    )

    existing_by_id = {
        item.get("id"): item
        for item in existing_data
        if item.get("id")
    }

    output = []

    for rank, prediction in enumerate(
        predictions,
        start=1,
    ):
        if not prediction.get("pick"):
            continue

        if not prediction.get("match"):
            continue

        new_record = build_snapshot_record(
            date,
            prediction,
            rank,
        )

        pick_id = new_record["id"]

        if pick_id in existing_by_id:
            output.append(
                merge_existing_record(
                    existing_by_id[pick_id],
                    new_record,
                )
            )

        else:
            output.append(new_record)

    existing_ids = {
        item.get("id")
        for item in output
    }

    for item in existing_data:
        item_id = item.get("id")

        if item_id and item_id not in existing_ids:
            output.append(item)

    output.sort(
        key=lambda item: (
            item.get("rank") or 9999,
            item.get("match") or "",
        )
    )

    save_json(
        path,
        output,
    )

    save_json(
        LATEST_PUBLIC_PATH,
        {
            "date": date,
            "count": len(output),
            "items": output,
        },
    )

    print(
        "PLAY HISTORY SAVED:",
        path,
        len(output),
    )

    return output


def load_play_history_for_date(date):
    return load_json(
        history_path(date),
        [],
    )


def load_all_play_history():
    ensure_dirs()

    items = []

    for filename in sorted(os.listdir(PLAY_HISTORY_DIR)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(
            PLAY_HISTORY_DIR,
            filename,
        )

        data = load_json(
            path,
            [],
        )

        if isinstance(data, list):
            items.extend(data)

    return items
