import json
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

LEGACY_PLAY_HISTORY_DIR = "data/play_history"

PICK_HISTORY_ROOT = "data/pick_history"
ALL_PICK_HISTORY_DIR = "data/pick_history/all"
TOP5_PICK_HISTORY_DIR = "data/pick_history/top5"

LATEST_ALL_PUBLIC_PATH = "public/play_history_all_latest.json"
LATEST_TOP5_PUBLIC_PATH = "public/play_history_top5_latest.json"
LATEST_LEGACY_PUBLIC_PATH = "public/play_history_latest.json"


def ensure_dirs():
    os.makedirs(LEGACY_PLAY_HISTORY_DIR, exist_ok=True)
    os.makedirs(ALL_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs(TOP5_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs("public", exist_ok=True)


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def betting_day(date_time=None):
    """
    Betting day window:
    Europe/Bratislava 06:00 -> next day 06:00

    If local time is before 06:00, the betting day is previous calendar day.
    """
    if date_time is None:
        date_time = datetime.now(BRATISLAVA_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=BRATISLAVA_TZ)
    else:
        date_time = date_time.astimezone(BRATISLAVA_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time.strftime("%Y-%m-%d")


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def normalize_text(value):
    if value is None:
        return ""

    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9à-ž\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_pick_id(date, prediction):
    match = normalize_text(prediction.get("match"))
    pick = normalize_text(prediction.get("pick"))
    opponent = normalize_text(prediction.get("opponent"))

    base = f"{date}::{match}::{pick}::{opponent}"

    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None

        return float(value)

    except Exception:
        return None


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return default


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def all_snapshot_path(date):
    return os.path.join(ALL_PICK_HISTORY_DIR, f"{date}.json")


def top5_snapshot_path(date):
    return os.path.join(TOP5_PICK_HISTORY_DIR, f"{date}.json")


def legacy_history_path(date):
    return os.path.join(LEGACY_PLAY_HISTORY_DIR, f"{date}.json")


def build_snapshot_record(date, prediction, rank, dataset):
    pick_id = make_pick_id(date, prediction)

    odds = safe_float(prediction.get("odds"))
    probability = safe_float(prediction.get("probability"))

    return {
        "id": pick_id,
        "dataset": dataset,
        "date": date,
        "created_at": now_utc_iso(),

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
        "set_win_probability": prediction.get("set_win_probability"),
        "most_likely_score": prediction.get("most_likely_score"),
        "most_likely_score_probability": prediction.get("most_likely_score_probability"),
        "score_probabilities": prediction.get("score_probabilities"),

        "bet_tag": prediction.get("bet_tag"),
        "top_mode": prediction.get("top_mode"),
        "top_reason": prediction.get("top_reason"),

        "result_status": prediction.get("result_status") or "PENDING",
        "winner": prediction.get("winner"),
        "score": prediction.get("score"),
        "units": safe_float(prediction.get("units")) or 0.0,
        "resolved_at": prediction.get("resolved_at"),
        "result_source": prediction.get("result_source"),
        "result_match_score": prediction.get("result_match_score"),
    }


def build_snapshot(date, predictions, dataset):
    if predictions is None:
        predictions = []

    output = []

    for rank, prediction in enumerate(predictions, start=1):
        if not isinstance(prediction, dict):
            continue

        if not prediction.get("pick"):
            continue

        if not prediction.get("match"):
            continue

        output.append(
            build_snapshot_record(
                date=date,
                prediction=prediction,
                rank=rank,
                dataset=dataset,
            )
        )

    output.sort(
        key=lambda item: (
            item.get("rank") or 9999,
            item.get("match") or "",
        )
    )

    return output


def save_snapshot(date, predictions, dataset, path, latest_public_path, overwrite=False):
    """
    Daily snapshot is immutable.

    Default behavior:
    - if snapshot file already exists and is non-empty, keep it unchanged
    - do not overwrite odds, probability, rank, pick, model fields during the day

    overwrite=True is intentionally available only for manual recovery.
    """
    ensure_dirs()

    if date is None:
        date = betting_day()

    existing = load_json(path, None)

    if (
        existing is not None
        and isinstance(existing, list)
        and len(existing) > 0
        and not overwrite
    ):
        save_json(
            latest_public_path,
            {
                "date": date,
                "dataset": dataset,
                "count": len(existing),
                "immutable_snapshot": True,
                "items": existing,
            },
        )

        print(
            "SNAPSHOT EXISTS - KEEPING IMMUTABLE:",
            dataset,
            path,
            len(existing),
        )

        return existing

    output = build_snapshot(
        date=date,
        predictions=predictions,
        dataset=dataset,
    )

    save_json(path, output)

    save_json(
        latest_public_path,
        {
            "date": date,
            "dataset": dataset,
            "count": len(output),
            "immutable_snapshot": True,
            "items": output,
        },
    )

    print(
        "SNAPSHOT SAVED:",
        dataset,
        path,
        len(output),
    )

    return output


def save_all_snapshot(date=None, all_predictions=None, overwrite=False):
    if date is None:
        date = betting_day()

    return save_snapshot(
        date=date,
        predictions=all_predictions or [],
        dataset="all",
        path=all_snapshot_path(date),
        latest_public_path=LATEST_ALL_PUBLIC_PATH,
        overwrite=overwrite,
    )


def save_top5_snapshot(date=None, top5_predictions=None, overwrite=False):
    if date is None:
        date = betting_day()

    return save_snapshot(
        date=date,
        predictions=top5_predictions or [],
        dataset="top5",
        path=top5_snapshot_path(date),
        latest_public_path=LATEST_TOP5_PUBLIC_PATH,
        overwrite=overwrite,
    )


def save_play_candidates(date=None, predictions=None, overwrite=False):
    """
    Backward-compatible wrapper.

    Old code called:
        save_play_candidates(today, all_predictions)

    New architecture stores this as ALL snapshot:
        data/pick_history/all/YYYY-MM-DD.json

    It also writes legacy data/play_history/YYYY-MM-DD.json only if missing,
    so older local scripts do not immediately break.
    """
    if date is None:
        date = betting_day()

    output = save_all_snapshot(
        date=date,
        all_predictions=predictions or [],
        overwrite=overwrite,
    )

    legacy_path = legacy_history_path(date)

    if not os.path.exists(legacy_path):
        save_json(legacy_path, output)

    save_json(
        LATEST_LEGACY_PUBLIC_PATH,
        {
            "date": date,
            "dataset": "all",
            "count": len(output),
            "items": output,
        },
    )

    return output


def load_all_snapshot_for_date(date):
    return load_json(all_snapshot_path(date), [])


def load_top5_snapshot_for_date(date):
    return load_json(top5_snapshot_path(date), [])


def load_play_history_for_date(date):
    data = load_all_snapshot_for_date(date)

    if data:
        return data

    return load_json(legacy_history_path(date), [])


def load_history_dir(directory):
    ensure_dirs()

    items = []

    if not os.path.exists(directory):
        return items

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(directory, filename)
        data = load_json(path, [])

        if isinstance(data, list):
            items.extend(data)

    return items


def load_all_pick_history():
    return load_history_dir(ALL_PICK_HISTORY_DIR)


def load_top5_pick_history():
    return load_history_dir(TOP5_PICK_HISTORY_DIR)


def load_all_play_history():
    """
    Backward-compatible loader.

    Prefer new ALL pick history.
    Fall back to old data/play_history if new folder is empty.
    """
    items = load_all_pick_history()

    if items:
        return items

    return load_history_dir(LEGACY_PLAY_HISTORY_DIR)
