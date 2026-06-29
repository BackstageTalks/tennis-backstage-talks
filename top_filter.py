import os
import json
import datetime


MIN_TOP_ODDS = float(os.getenv("MIN_TOP_ODDS", "1.50"))
MAX_TOP_ITEMS = int(os.getenv("MAX_TOP_ITEMS", "7"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def list_json_files(prefix):
    if not os.path.exists("public"):
        return []

    files = [
        os.path.join("public", f)
        for f in os.listdir("public")
        if f.startswith(prefix) and f.endswith(".json")
    ]

    return sorted(files)


def latest_file(prefix):
    files = list_json_files(prefix)

    if not files:
        return None

    return files[-1]


def to_float(value):
    try:
        if value in [None, "", "-", "None"]:
            return None
        return float(value)
    except Exception:
        return None


def normalize_name(value):
    return str(value or "").strip().lower()


def get_pick_odds(item):
    odds = to_float(item.get("odds"))

    if odds is not None:
        return odds

    pick = normalize_name(item.get("pick"))
    player1 = normalize_name(item.get("player1"))
    player2 = normalize_name(item.get("player2"))

    if pick and pick == player1:
        return to_float(item.get("odds_player1"))

    if pick and pick == player2:
        return to_float(item.get("odds_player2"))

    return None


def get_probability(item):
    value = item.get("probability")

    try:
        return float(value)
    except Exception:
        return 0.0


def unique_key(item):
    pick = normalize_name(item.get("pick"))
    opponent = normalize_name(item.get("opponent"))
    player1 = normalize_name(item.get("player1"))
    player2 = normalize_name(item.get("player2"))
    match_start = str(item.get("match_start", ""))

    return "::".join([pick, opponent, player1, player2, match_start])


def enrich_item(item, odds):
    item = dict(item)

    item["odds"] = odds
    item["top_filter_min_odds"] = MIN_TOP_ODDS
    item["top_filter_passed"] = True

    return item


def filter_top_from_all(all_predictions):
    eligible = []

    for item in all_predictions:
        odds = get_pick_odds(item)

        if odds is None:
            continue

        if odds < MIN_TOP_ODDS:
            continue

        enriched = enrich_item(item, odds)
        eligible.append(enriched)

    eligible = sorted(
        eligible,
        key=lambda x: (
            get_probability(x),
            get_pick_odds(x) or 0,
        ),
        reverse=True,
    )

    selected = []
    seen = set()

    for item in eligible:
        key = unique_key(item)

        if key in seen:
            continue

        seen.add(key)
        selected.append(item)

        if len(selected) >= MAX_TOP_ITEMS:
            break

    return selected


def run():
    os.makedirs("public", exist_ok=True)

    top_path = latest_file("predictions_")
    all_path = latest_file("all_predictions_")

    print("TOP FILTER MIN_TOP_ODDS:", MIN_TOP_ODDS)
    print("TOP FILTER MAX_TOP_ITEMS:", MAX_TOP_ITEMS)
    print("TOP FILTER top_path:", top_path)
    print("TOP FILTER all_path:", all_path)

    if all_path is None:
        raise RuntimeError("Cannot apply TOP odds filter: all_predictions_*.json missing")

    all_predictions = load_json(all_path)

    if not isinstance(all_predictions, list):
        raise RuntimeError("ALL predictions JSON is not a list")

    filtered_top = filter_top_from_all(all_predictions)

    print("TOP FILTER eligible selected:", len(filtered_top))

    if len(filtered_top) == 0:
        raise RuntimeError(
            f"TOP odds filter selected 0 picks with odds >= {MIN_TOP_ODDS}. Refusing to create empty TOP."
        )

    if top_path is None:
        today = datetime.date.today().isoformat()
        top_path = f"public/predictions_{today}.json"

    save_json(top_path, filtered_top)

    print("TOP FILTER saved:", top_path)
    print("TOP FILTER sample:", filtered_top[:3])


if __name__ == "__main__":
    run()
