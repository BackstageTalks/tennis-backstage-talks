import copy
import glob
import json
import os
import re
from datetime import datetime, timezone

from render_site import (
    write_page,
    write_rss,
)


BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"
SITE_TITLE = "BackstageTalks Statistic Model"

CORQ_MIN_WIN = 0.55
THINQ_MIN_WIN = 0.55
BLEND_MIN_WIN = 0.55
MIN_PAGE_ODDS = 1.33


# -----------------------------------------------------------------------------
# JSON / file helpers
# -----------------------------------------------------------------------------


def extract_date_from_filename(path):
    filename = os.path.basename(path or "")
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)

    if not match:
        return ""

    return match.group(1)


def sorted_files_newest_first(pattern):
    files = glob.glob(pattern)
    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )
    return files


def load_json(path, default):
    try:
        if not path:
            return default

        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as exc:
        print("BUILD PAGES JSON LOAD ERROR:", path, str(exc))
        return default


def load_json_required(path):
    if not path:
        raise FileNotFoundError("Missing JSON path.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"JSON file does not exist: {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"Expected list in JSON file: {path}")

    return data


def find_latest_non_empty_file(pattern, label):
    files = sorted_files_newest_first(pattern)

    print("")
    print(f"=== SEARCHING {label} FILES ===")

    for path in files:
        data = load_json(path, [])
        count = len(data) if isinstance(data, list) else 0

        print(label, "candidate:", path, "count:", count)

        if isinstance(data, list) and count > 0:
            print(label, "selected:", path)
            print(f"=== END SEARCHING {label} FILES ===")
            print("")
            return path

    print(label, "selected:", None)
    print(f"=== END SEARCHING {label} FILES ===")
    print("")
    return None


def ensure_public_dirs():
    os.makedirs("public", exist_ok=True)
    os.makedirs("public/all", exist_ok=True)
    os.makedirs("public/BsT", exist_ok=True)
    os.makedirs("public/Blend", exist_ok=True)


# -----------------------------------------------------------------------------
# Numeric / probability / odds helpers
# -----------------------------------------------------------------------------


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def normalize_probability_decimal(value):
    """
    Returns probability as decimal.

    Accepted inputs:
    - 0.65  -> 0.65
    - 65.0  -> 0.65
    - None  -> None
    """
    number = safe_float(value)

    if number is None:
        return None

    if number > 1.0:
        return number / 100.0

    return number


def get_corq_probability(prediction):
    return normalize_probability_decimal(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )


def get_thinq_probability(prediction):
    return normalize_probability_decimal(
        prediction.get("bst_ai_probability")
    )


def get_prediction_odds(prediction):
    return safe_float(
        prediction.get("odds")
    )


def has_required_page_odds(prediction):
    odds = get_prediction_odds(prediction)

    if odds is None:
        return False

    # Strictly greater than 1.33.
    # This excludes odds 1.33 and lower.
    return odds > MIN_PAGE_ODDS


def is_thinq_ok(prediction):
    return str(prediction.get("bst_ai_status") or "").upper().strip() == "OK"


# -----------------------------------------------------------------------------
# Prediction mutation helpers
# -----------------------------------------------------------------------------


def clone_prediction(prediction):
    return copy.deepcopy(prediction)


def unique_key(prediction):
    return (
        str(
            prediction.get("match_id")
            or prediction.get("event_id")
            or prediction.get("match")
            or ""
        ),
        str(prediction.get("pick") or ""),
    )


def dedupe_predictions(predictions):
    selected = []
    seen = set()

    for prediction in predictions:
        key = unique_key(prediction)

        if key in seen:
            continue

        seen.add(key)
        selected.append(prediction)

    return selected


def mark_corq_view(prediction, corq_probability):
    updated = clone_prediction(prediction)
    updated["probability"] = corq_probability
    updated["corq_display_probability"] = corq_probability
    updated["top_mode"] = "CORQ_THRESHOLD_55_ODDS_GT_1_33"
    updated["top_reason"] = "Corq AI probability >= 55% and odds > 1.33"
    return updated


def mark_thinq_view(prediction, thinq_probability, corq_probability):
    updated = clone_prediction(prediction)
    updated["probability"] = thinq_probability
    updated["corq_display_probability"] = corq_probability
    updated["top_mode"] = "THINQ_THRESHOLD_55_ODDS_GT_1_33"
    updated["top_reason"] = "Thinq AI probability >= 55%, bst_ai_status == OK, and odds > 1.33"
    return updated


def mark_blend_view(prediction, blend_probability, corq_probability, thinq_probability):
    updated = clone_prediction(prediction)
    updated["probability"] = blend_probability
    updated["blend_probability"] = blend_probability
    updated["corq_display_probability"] = corq_probability
    updated["bst_ai_probability"] = thinq_probability
    updated["top_mode"] = "BLEND_50_50_THRESHOLD_55_ODDS_GT_1_33"
    updated["top_reason"] = "50% Corq AI + 50% Thinq AI; Blend probability >= 55%, bst_ai_status == OK, and odds > 1.33"
    return updated


# -----------------------------------------------------------------------------
# Page derivation logic
# -----------------------------------------------------------------------------


def derive_corq_predictions(all_predictions):
    eligible = []

    for prediction in all_predictions or []:
        if not has_required_page_odds(prediction):
            continue

        corq_probability = get_corq_probability(prediction)

        if corq_probability is None:
            continue

        if corq_probability < CORQ_MIN_WIN:
            continue

        eligible.append(
            mark_corq_view(
                prediction,
                corq_probability,
            )
        )

    eligible.sort(
        key=lambda item: get_corq_probability(item) or 0.0,
        reverse=True,
    )

    selected = dedupe_predictions(eligible)

    print("CORQ THRESHOLD COUNT:", len(selected))
    return selected


def derive_thinq_predictions(all_predictions):
    eligible = []

    for prediction in all_predictions or []:
        if not has_required_page_odds(prediction):
            continue

        if not is_thinq_ok(prediction):
            continue

        thinq_probability = get_thinq_probability(prediction)
        corq_probability = get_corq_probability(prediction)

        if thinq_probability is None:
            continue

        if thinq_probability < THINQ_MIN_WIN:
            continue

        eligible.append(
            mark_thinq_view(
                prediction,
                thinq_probability,
                corq_probability,
            )
        )

    eligible.sort(
        key=lambda item: get_thinq_probability(item) or 0.0,
        reverse=True,
    )

    selected = dedupe_predictions(eligible)

    print("THINQ THRESHOLD COUNT:", len(selected))
    return selected


def derive_blend_predictions(all_predictions):
    eligible = []

    for prediction in all_predictions or []:
        if not has_required_page_odds(prediction):
            continue

        if not is_thinq_ok(prediction):
            continue

        corq_probability = get_corq_probability(prediction)
        thinq_probability = get_thinq_probability(prediction)

        if corq_probability is None:
            continue

        if thinq_probability is None:
            continue

        blend_probability = (corq_probability + thinq_probability) / 2.0

        if blend_probability < BLEND_MIN_WIN:
            continue

        eligible.append(
            mark_blend_view(
                prediction,
                blend_probability,
                corq_probability,
                thinq_probability,
            )
        )

    eligible.sort(
        key=lambda item: safe_float(item.get("blend_probability")) or 0.0,
        reverse=True,
    )

    selected = dedupe_predictions(eligible)

    print("BLEND THRESHOLD COUNT:", len(selected))
    return selected


# -----------------------------------------------------------------------------
# Logging / validation
# -----------------------------------------------------------------------------


def print_prediction_sample(label, predictions):
    print("")
    print(f"=== {label} SAMPLE ===")
    print("COUNT:", len(predictions))

    for index, prediction in enumerate(predictions[:10], start=1):
        print(
            json.dumps(
                {
                    "index": index,
                    "match": prediction.get("match"),
                    "pick": prediction.get("pick"),
                    "opponent": prediction.get("opponent"),
                    "probability": prediction.get("probability"),
                    "corq_display_probability": prediction.get("corq_display_probability"),
                    "bst_ai_probability": prediction.get("bst_ai_probability"),
                    "blend_probability": prediction.get("blend_probability"),
                    "ai_match": prediction.get("ai_match"),
                    "bst_ai_status": prediction.get("bst_ai_status"),
                    "odds": prediction.get("odds"),
                    "top_mode": prediction.get("top_mode"),
                    "top_reason": prediction.get("top_reason"),
                },
                ensure_ascii=False,
            )
        )

    print(f"=== END {label} SAMPLE ===")
    print("")


def validate_predictions(all_predictions):
    if not all_predictions:
        raise ValueError("ALL predictions are empty. Refusing to deploy empty ALL page.")

    all_with_pick = [
        prediction
        for prediction in all_predictions
        if prediction.get("pick")
    ]

    if not all_with_pick:
        raise ValueError("ALL predictions exist, but none contain a pick. Refusing deploy.")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def build_pages():
    ensure_public_dirs()

    all_json = find_latest_non_empty_file(
        "public/all_predictions_*.json",
        "ALL",
    )

    print("")
    print("=== BUILD PAGES INPUTS ===")
    print("BUILD TIME UTC:", datetime.now(timezone.utc).isoformat())
    print("BUILD PAGES ALL JSON:", all_json)
    print("MIN PAGE ODDS:", MIN_PAGE_ODDS)
    print("=== END BUILD PAGES INPUTS ===")
    print("")

    all_predictions = load_json_required(all_json)

    validate_predictions(all_predictions)

    corq_predictions = derive_corq_predictions(all_predictions)
    thinq_predictions = derive_thinq_predictions(all_predictions)
    blend_predictions = derive_blend_predictions(all_predictions)

    print_prediction_sample("CORQ PREDICTIONS", corq_predictions)
    print_prediction_sample("THINQ PREDICTIONS", thinq_predictions)
    print_prediction_sample("BLEND PREDICTIONS", blend_predictions)
    print_prediction_sample("ALL PREDICTIONS", all_predictions)

    write_page(
        predictions=corq_predictions,
        title=SITE_TITLE,
        subtitle="Corq AI predictions >= 55% and odds > 1.33",
        destination="public/index.html",
    )

    write_rss(
        predictions=corq_predictions,
        title=f"{SITE_TITLE} - Corq",
        link=f"{BASE_URL}/",
        destination="public/tennis.xml",
    )

    write_page(
        predictions=thinq_predictions,
        title=SITE_TITLE,
        subtitle="Thinq AI predictions >= 55%, OK status and odds > 1.33",
        destination="public/BsT/index.html",
    )

    write_rss(
        predictions=thinq_predictions,
        title=f"{SITE_TITLE} - Thinq",
        link=f"{BASE_URL}/BsT/",
        destination="public/tennis_bst.xml",
    )

    write_page(
        predictions=blend_predictions,
        title=SITE_TITLE,
        subtitle="Blend 50/50 Corq and Thinq predictions >= 55%, OK status and odds > 1.33",
        destination="public/Blend/index.html",
    )

    write_rss(
        predictions=blend_predictions,
        title=f"{SITE_TITLE} - Blend",
        link=f"{BASE_URL}/Blend/",
        destination="public/tennis_blend.xml",
    )

    write_page(
        predictions=all_predictions,
        title=SITE_TITLE,
        subtitle="All available tennis predictions",
        destination="public/all/index.html",
    )

    write_rss(
        predictions=all_predictions,
        title=f"{SITE_TITLE} - ALL",
        link=f"{BASE_URL}/all/",
        destination="public/tennis_all.xml",
    )

    print("")
    print("=== BUILD PAGES WRITTEN ===")
    print("public/index.html")
    print("public/tennis.xml")
    print("public/BsT/index.html")
    print("public/tennis_bst.xml")
    print("public/Blend/index.html")
    print("public/tennis_blend.xml")
    print("public/all/index.html")
    print("public/tennis_all.xml")
    print("CORQ COUNT:", len(corq_predictions))
    print("THINQ COUNT:", len(thinq_predictions))
    print("BLEND COUNT:", len(blend_predictions))
    print("ALL COUNT:", len(all_predictions))
    print("=== END BUILD PAGES WRITTEN ===")
    print("")


if __name__ == "__main__":
    build_pages()
