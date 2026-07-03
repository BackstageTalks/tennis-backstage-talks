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

TOP_N = 5

PRIMARY_MIN_ODDS = 1.50
SECONDARY_MIN_ODDS = 1.35
SECONDARY_MIN_PROBABILITY = 0.70

HIGHEST_ODDS_MIN_PROBABILITY = 0.01


def extract_date_from_filename(path):
    if not path:
        return ""

    filename = os.path.basename(path)

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})",
        filename,
    )

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

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception as exc:
        print(
            "BUILD PAGES JSON LOAD ERROR:",
            path,
            str(exc),
        )

        return default


def load_json_required(path):
    if not path:
        raise FileNotFoundError(
            "Missing JSON path."
        )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"JSON file does not exist: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"Expected list in JSON file: {path}"
        )

    return data


def find_latest_non_empty_file(pattern, label):
    files = sorted_files_newest_first(
        pattern,
    )

    print("")
    print(f"=== SEARCHING {label} FILES ===")

    for path in files:
        data = load_json(
            path,
            [],
        )

        count = len(data) if isinstance(data, list) else 0

        print(
            label,
            "candidate:",
            path,
            "count:",
            count,
        )

        if isinstance(data, list) and count > 0:
            print(
                label,
                "selected:",
                path,
            )

            print(f"=== END SEARCHING {label} FILES ===")
            print("")

            return path

    print(
        label,
        "selected:",
        None,
    )

    print(f"=== END SEARCHING {label} FILES ===")
    print("")

    return None


def ensure_public_dirs():
    os.makedirs(
        "public",
        exist_ok=True,
    )

    os.makedirs(
        "public/all",
        exist_ok=True,
    )


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def prediction_sort_value(prediction):
    probability = safe_float(
        prediction.get("probability")
    )

    if probability is None:
        return 0.0

    return probability


def odds_sort_value(prediction):
    odds = safe_float(
        prediction.get("odds")
    )

    probability = safe_float(
        prediction.get("probability")
    )

    if odds is None:
        odds = 0.0

    if probability is None:
        probability = 0.0

    return (
        odds,
        probability,
    )


def clone_prediction(prediction):
    return copy.deepcopy(
        prediction
    )


def mark_top_mode(prediction, mode, reason):
    updated = clone_prediction(
        prediction
    )

    updated["top_mode"] = mode
    updated["top_reason"] = reason

    if mode in [
        "MODEL_ONLY",
        "HIGHEST_ODDS_FALLBACK",
    ]:
        updated["bet_tag"] = "INFO ONLY"

        if not updated.get("odds_source") and mode == "MODEL_ONLY":
            updated["odds_source"] = "missing"

    return updated


def has_basic_model_data(prediction):
    if not prediction.get("pick"):
        return False

    if not prediction.get("opponent"):
        return False

    if not prediction.get("match"):
        return False

    probability = safe_float(
        prediction.get("probability")
    )

    if probability is None:
        return False

    if probability < HIGHEST_ODDS_MIN_PROBABILITY:
        return False

    return True


def usable_odds_predictions(all_predictions):
    usable = []

    for prediction in all_predictions:
        odds = safe_float(
            prediction.get("odds")
        )

        if odds is None:
            continue

        if odds <= 1.0:
            continue

        if not has_basic_model_data(prediction):
            continue

        usable.append(prediction)

    return usable


def derive_primary_top(all_predictions):
    eligible = []

    for prediction in all_predictions:
        odds = safe_float(
            prediction.get("odds")
        )

        probability = safe_float(
            prediction.get("probability")
        )

        if odds is None:
            continue

        if probability is None:
            continue

        if odds < PRIMARY_MIN_ODDS:
            continue

        eligible.append(
            mark_top_mode(
                prediction,
                "ODDS_PRIMARY",
                "odds >= 1.50",
            )
        )

    eligible.sort(
        key=prediction_sort_value,
        reverse=True,
    )

    return eligible[:TOP_N]


def derive_secondary_top(all_predictions):
    eligible = []

    for prediction in all_predictions:
        odds = safe_float(
            prediction.get("odds")
        )

        probability = safe_float(
            prediction.get("probability")
        )

        if odds is None:
            continue

        if probability is None:
            continue

        if odds < SECONDARY_MIN_ODDS:
            continue

        if probability < SECONDARY_MIN_PROBABILITY:
            continue

        eligible.append(
            mark_top_mode(
                prediction,
                "ODDS_SECONDARY",
                "odds >= 1.35 and probability >= 70%",
            )
        )

    eligible.sort(
        key=prediction_sort_value,
        reverse=True,
    )

    return eligible[:TOP_N]


def derive_model_only_top(all_predictions):
    eligible = []

    for prediction in all_predictions:
        if not has_basic_model_data(prediction):
            continue

        eligible.append(
            mark_top_mode(
                prediction,
                "MODEL_ONLY",
                "no usable matched odds available; model-only fallback",
            )
        )

    eligible.sort(
        key=prediction_sort_value,
        reverse=True,
    )

    return eligible[:TOP_N]


def derive_highest_odds_fallback_top(all_predictions):
    eligible = []

    for prediction in all_predictions:
        if not has_basic_model_data(prediction):
            continue

        odds = safe_float(
            prediction.get("odds")
        )

        if odds is None:
            continue

        if odds <= 1.0:
            continue

        eligible.append(
            mark_top_mode(
                prediction,
                "HIGHEST_ODDS_FALLBACK",
                "no primary or secondary picks available; selected by highest available odds",
            )
        )

    eligible.sort(
        key=odds_sort_value,
        reverse=True,
    )

    return eligible[:TOP_N]


def derive_top_from_all(all_predictions):
    primary = derive_primary_top(
        all_predictions
    )

    if primary:
        print(
            "TOP5 derived from PRIMARY odds tier:",
            len(primary),
        )

        return primary

    secondary = derive_secondary_top(
        all_predictions
    )

    if secondary:
        print(
            "TOP5 derived from SECONDARY odds tier:",
            len(secondary),
        )

        return secondary

    odds_available = usable_odds_predictions(
        all_predictions
    )

    if not odds_available:
        model_only = derive_model_only_top(
            all_predictions
        )

        print(
            "TOP5 derived from MODEL_ONLY fallback:",
            len(model_only),
        )

        return model_only

    highest_odds = derive_highest_odds_fallback_top(
        all_predictions
    )

    print(
        "TOP5 derived from HIGHEST_ODDS_FALLBACK:",
        len(highest_odds),
    )

    if highest_odds:
        return highest_odds

    model_only = derive_model_only_top(
        all_predictions
    )

    print(
        "TOP5 derived from FINAL MODEL_ONLY fallback:",
        len(model_only),
    )

    return model_only


def print_prediction_sample(label, predictions):
    print("")
    print(f"=== {label} SAMPLE ===")
    print("COUNT:", len(predictions))

    for index, prediction in enumerate(
        predictions[:5],
        start=1,
    ):
        print(
            json.dumps(
                {
                    "index": index,
                    "match": prediction.get("match"),
                    "pick": prediction.get("pick"),
                    "opponent": prediction.get("opponent"),
                    "probability": prediction.get("probability"),
                    "corq_ai_probability": prediction.get("corq_ai_probability"),
                    "bst_ai_probability": prediction.get("bst_ai_probability"),
                    "ai_match": prediction.get("ai_match"),
                    "ai_lean": prediction.get("ai_lean"),
                    "ai_match_color": prediction.get("ai_match_color"),
                    "bst_ai_status": prediction.get("bst_ai_status"),
                    "odds": prediction.get("odds"),
                    "time": prediction.get("time"),
                    "tournament": prediction.get("tournament"),
                    "gender": prediction.get("gender"),
                    "best_of": prediction.get("best_of"),
                    "surface": prediction.get("surface"),
                    "expected_sets": prediction.get("expected_sets"),
                    "sets_probability": prediction.get("sets_probability"),
                    "sets_probability_label": prediction.get("sets_probability_label"),
                    "most_likely_score": prediction.get("most_likely_score"),
                    "bet_tag": prediction.get("bet_tag"),
                    "top_mode": prediction.get("top_mode"),
                    "top_reason": prediction.get("top_reason"),
                    "odds_source": prediction.get("odds_source"),
                },
                ensure_ascii=False,
            )
        )

    print(f"=== END {label} SAMPLE ===")
    print("")


def validate_predictions(top_predictions, all_predictions):
    if not all_predictions:
        raise ValueError(
            "ALL predictions are empty. Refusing to deploy empty ALL page."
        )

    all_with_pick = [
        prediction
        for prediction in all_predictions
        if prediction.get("pick")
    ]

    if not all_with_pick:
        raise ValueError(
            "ALL predictions exist, but none contain a pick. Refusing deploy."
        )

    if not top_predictions:
        raise ValueError(
            "TOP predictions are empty even after all fallback tiers. Refusing deploy."
        )


def build_pages():
    ensure_public_dirs()

    all_json = find_latest_non_empty_file(
        "public/all_predictions_*.json",
        "ALL",
    )

    top_json = find_latest_non_empty_file(
        "public/predictions_*.json",
        "TOP",
    )

    print("")
    print("=== BUILD PAGES INPUTS ===")
    print("BUILD TIME UTC:", datetime.now(timezone.utc).isoformat())
    print("BUILD PAGES TOP JSON:", top_json)
    print("BUILD PAGES ALL JSON:", all_json)
    print("=== END BUILD PAGES INPUTS ===")
    print("")

    all_predictions = load_json_required(
        all_json,
    )

    top_predictions = []

    if top_json:
        try:
            top_predictions = load_json_required(
                top_json,
            )

        except Exception as exc:
            print(
                "BUILD PAGES TOP JSON LOAD WARNING:",
                str(exc),
            )

            top_predictions = []

    if not top_predictions:
        print(
            "TOP predictions missing or empty. "
            "Deriving TOP5 from ALL predictions."
        )

        top_predictions = derive_top_from_all(
            all_predictions,
        )

    validate_predictions(
        top_predictions,
        all_predictions,
    )

    print_prediction_sample(
        "TOP PREDICTIONS",
        top_predictions,
    )

    print_prediction_sample(
        "ALL PREDICTIONS",
        all_predictions,
    )

    write_page(
        predictions=top_predictions,
        title=SITE_TITLE,
        subtitle="Top tennis picks",
        destination="public/index.html",
    )

    write_rss(
        predictions=top_predictions,
        title=SITE_TITLE,
        link=f"{BASE_URL}/",
        destination="public/tennis.xml",
    )

    write_page(
        predictions=all_predictions,
        title=SITE_TITLE,
        subtitle="All available tennis predictions",
        destination="public/all/index.html",
    )

    write_rss(
        predictions=all_predictions,
        title=SITE_TITLE,
        link=f"{BASE_URL}/all/",
        destination="public/tennis_all.xml",
    )

    print("")
    print("=== BUILD PAGES WRITTEN ===")
    print("public/index.html")
    print("public/tennis.xml")
    print("public/all/index.html")
    print("public/tennis_all.xml")
    print("TOP COUNT:", len(top_predictions))
    print("ALL COUNT:", len(all_predictions))
    print("=== END BUILD PAGES WRITTEN ===")
    print("")


if __name__ == "__main__":
    build_pages()
