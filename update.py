
import glob
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from play_history import betting_day, save_all_snapshot, save_top5_snapshot
from prediction_engine_top import build_all_predictions, get_top_predictions
from src.bst_ai.service import build_bst_ai_comparison
from src.marq_ai import build_marq_from_match

ALL_SNAPSHOT_DIR = "data/pick_history/all"
TOP5_SNAPSHOT_DIR = "data/pick_history/top5"
LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def save_json(path, data):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_json(path, default):
    try:
        if not path or not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def is_non_empty_list(data):
    return isinstance(data, list) and len(data) > 0


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def snapshot_path(kind, date):
    if kind == "all":
        return os.path.join(ALL_SNAPSHOT_DIR, f"{date}.json")
    return os.path.join(TOP5_SNAPSHOT_DIR, f"{date}.json")


def extract_date_from_filename(path):
    filename = os.path.basename(path or "")
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else ""


def latest_non_empty_snapshot(kind):
    if kind == "all":
        pattern = os.path.join(ALL_SNAPSHOT_DIR, "*.json")
    else:
        pattern = os.path.join(TOP5_SNAPSHOT_DIR, "*.json")
    files = glob.glob(pattern)
    files.sort(key=lambda path: (extract_date_from_filename(path), os.path.getmtime(path)), reverse=True)
    for path in files:
        data = load_json(path, [])
        if is_non_empty_list(data):
            return data
    return []


def load_today_snapshot(kind, date):
    return load_json(snapshot_path(kind, date), [])


def save_non_empty_all_snapshot(date, all_predictions):
    if not is_non_empty_list(all_predictions):
        print("SKIP ALL SNAPSHOT SAVE:", "generated ALL is empty")
        return
    os.makedirs(ALL_SNAPSHOT_DIR, exist_ok=True)
    save_json(snapshot_path("all", date), all_predictions)
    try:
        save_all_snapshot(date, all_predictions)
    except Exception as exc:
        print("PLAY HISTORY ALL SNAPSHOT SAVE WARNING:", exc)


def save_non_empty_top5_snapshot(date, top_predictions):
    if not is_non_empty_list(top_predictions):
        print("SKIP TOP SNAPSHOT SAVE:", "generated TOP is empty")
        return
    os.makedirs(TOP5_SNAPSHOT_DIR, exist_ok=True)
    save_json(snapshot_path("top", date), top_predictions)
    try:
        save_top5_snapshot(date, top_predictions)
    except Exception as exc:
        print("PLAY HISTORY TOP SNAPSHOT SAVE WARNING:", exc)


def choose_public_all_predictions(generated_all_predictions, all_snapshot):
    if is_non_empty_list(generated_all_predictions):
        print("PUBLIC ALL SOURCE: generated")
        return generated_all_predictions
    if is_non_empty_list(all_snapshot):
        print("PUBLIC ALL SOURCE: snapshot fallback")
        return all_snapshot
    print("PUBLIC ALL SOURCE: empty")
    return []


def choose_public_top_predictions(generated_top_predictions, top5_snapshot, public_all_predictions):
    if is_non_empty_list(generated_top_predictions):
        print("PUBLIC TOP SOURCE: generated")
        return generated_top_predictions
    if is_non_empty_list(top5_snapshot):
        print("PUBLIC TOP SOURCE: snapshot fallback")
        return top5_snapshot
    print("PUBLIC TOP SOURCE: empty")
    return []


def run():
    today = betting_day()
    print("UPDATE BETTING DAY:", today)

    all_predictions = build_all_predictions()
    top_predictions = get_top_predictions(all_predictions)

    print("GENERATED ALL COUNT:", len(all_predictions))
    print("GENERATED TOP7 COUNT:", len(top_predictions))

    save_non_empty_all_snapshot(today, all_predictions)
    save_non_empty_top5_snapshot(today, top_predictions)

    all_snapshot = load_today_snapshot("all", today) or latest_non_empty_snapshot("all")
    top_snapshot = load_today_snapshot("top", today) or latest_non_empty_snapshot("top")

    public_all = choose_public_all_predictions(all_predictions, all_snapshot)
    public_top = choose_public_top_predictions(top_predictions, top_snapshot, public_all)

    os.makedirs("public", exist_ok=True)
    save_json(f"public/all_predictions_{today}.json", public_all)
    save_json("public/all_predictions_latest.json", public_all)
    save_json(f"public/top_predictions_{today}.json", public_top)
    save_json("public/top_predictions_latest.json", public_top)

    print("PUBLIC ALL COUNT:", len(public_all))
    print("PUBLIC TOP7 COUNT:", len(public_top))


if __name__ == "__main__":
    run()
