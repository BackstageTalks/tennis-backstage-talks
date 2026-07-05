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


# -----------------------------------------------------------------------------
# File helpers
# -----------------------------------------------------------------------------


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

    os.makedirs(
        "public/BsT",
        exist_ok=True,
    )


# -----------------------------------------------------------------------------
# Numeric helpers
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



def get_corq_probability(prediction):
    return safe_float(
        prediction.get("probability")
    )



def get_bst_probability(prediction):
    return safe_float(
        prediction.get("bst_ai_probability")
    )



def get_model_probability(prediction, model_key):
    if model_key == "bst":
        return get_bst_probability(prediction)

    return get_corq_probability(prediction)


# -----------------------------------------------------------------------------
# Sorting helpers
# -----------------------------------------------------------------------------


def prediction_sort_value(prediction):
    probability = get_corq_probability(
        prediction
    )

    if probability is None:
        return 0.0

    return probability



def model_sort_value(prediction, model_key):
    model_probability = get_model_probability(
        prediction,
        model_key,
    )

    corq_probability = get_corq_probability(
        prediction
    )

    bst_probability = get_bst_probability(
        prediction
    )

    ai_match = safe_float(
        prediction.get("ai_match")
    )

    odds = safe_float(
        prediction.get("odds")
    )

    if model_probability is None:
        model_probability = -1.0

    if corq_probability is None:
        corq_probability = 0.0

    if bst_probability is None:
        bst_probability = 0.0

    if ai_match is None:
        ai_match = 0.0

    if odds is None:
        odds = 0.0

    return (
        model_probability,
        ai_match,
        corq_probability,
        bst_probability,
        odds,
    )



def odds_sort_value(prediction):
    odds = safe_float(
        prediction.get("odds")
    )

    probability = get_corq_probability(
        prediction
    )

    if odds is None:
        odds = 0.0

    if probability is None:
        probability = 0.0

    return (
        odds,
        probability,
    )



def model_odds_sort_value(prediction, model_key):
    odds = safe_float(
        prediction.get("odds")
    )

    model_probability = get_model_probability(
        prediction,
        model_key,
    )

    if odds is None:
        odds = 0.0

    if model_probability is None:
        model_probability = 0.0

    return (
        odds,
        model_probability,
    )


# -----------------------------------------------------------------------------
# Prediction mutation helpers
# -----------------------------------------------------------------------------


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
        "BST_MODEL_ONLY",
        "BST_HIGHEST_ODDS_FALLBACK",
    ]:
        updated["bet_tag"] = "INFO ONLY"

        if not updated.get("odds_source") and mode in [
            "MODEL_ONLY",
            "BST_MODEL_ONLY",
        ]:
            updated["odds_source"] = "missing"

    return updated



def mark_bst_view(prediction):
    updated = clone_prediction(
        prediction
    )

    bst_probability = get_bst_probability(
        updated
    )

    # Preserve original Corq-driven probability for audit/debug.
    updated["corq_display_probability"] = updated.get("probability")

    # IMPORTANT:
    # The /BsT/ page is a BsT TOP5-equivalent test page. The renderer uses
    # "probability" for the WIN % column and summary average.
    # Therefore we intentionally set probability to BsT AI probability
    # only in this derived display object, without changing original ALL data.
    if bst_probability is not None:
        updated["probability"] = bst_probability

    return updated


# -----------------------------------------------------------------------------
# Data validity helpers
# -----------------------------------------------------------------------------


def has_basic_model_data(prediction):
    if not prediction.get("pick"):
        return False

    if not prediction.get("opponent"):
        return False

    if not prediction.get("match"):
        return False

    probability = get_corq_probability(
        prediction
    )

    if probability is None:
        return False

    if probability < HIGHEST_ODDS_MIN_PROBABILITY:
        return False

    return True



def has_model_data(prediction, model_key):
    if not prediction.get("pick"):
        return False

    if not prediction.get("opponent"):
        return False

    if not prediction.get("match"):
        return False

    if model_key == "bst":
        if prediction.get("bst_ai_status") != "OK":
            return False

    probability = get_model_probability(
        prediction,
        model_key,
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



def usable_model_odds_predictions(all_predictions, model_key):
    usable = []

    for prediction in all_predictions:
        odds = safe_float(
            prediction.get("odds")
        )

        if odds is None:
            continue

        if odds <= 1.0:
            continue

        if not has_model_data(prediction, model_key):
            continue

        usable.append(prediction)

    return usable


# -----------------------------------------------------------------------------
# Corq TOP5 logic - production logic
# -----------------------------------------------------------------------------


def derive_primary_top(all_predictions):
    eligible = []

    for prediction in all_predictions:
        odds = safe_float(
            prediction.get("odds")
        )

        probability = get_corq_probability(
            prediction
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

        probability = get_corq_probability(
            prediction
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


# -----------------------------------------------------------------------------
# BsT TOP5 logic - 1:1 equivalent of Corq TOP5 logic
# Difference: model confidence = bst_ai_probability instead of probability.
# -----------------------------------------------------------------------------


def derive_model_primary_top(all_predictions, model_key, mode_prefix):
    eligible = []

    for prediction in all_predictions:
        odds = safe_float(
            prediction.get("odds")
        )

        probability = get_model_probability(
            prediction,
            model_key,
        )

        if odds is None:
            continue

        if probability is None:
            continue

        if odds < PRIMARY_MIN_ODDS:
            continue

        if not has_model_data(prediction, model_key):
            continue

        eligible.append(
            mark_top_mode(
                prediction,
                f"{mode_prefix}_ODDS_PRIMARY",
                "odds >= 1.50",
            )
        )

    eligible.sort(
        key=lambda item: model_sort_value(item, model_key),
        reverse=True,
    )

    return eligible[:TOP_N]



def derive_model_secondary_top(all_predictions, model_key, mode_prefix):
    eligible = []

    for prediction in all_predictions:
        odds = safe_float(
            prediction.get("odds")
        )

        probability = get_model_probability(
            prediction,
            model_key,
        )

        if odds is None:
            continue

        if probability is None:
            continue

        if odds < SECONDARY_MIN_ODDS:
            continue

        if probability < SECONDARY_MIN_PROBABILITY:
            continue

        if not has_model_data(prediction, model_key):
            continue

        eligible.append(
            mark_top_mode(
                prediction,
                f"{mode_prefix}_ODDS_SECONDARY",
                "odds >= 1.35 and model probability >= 70%",
            )
        )

    eligible.sort(
        key=lambda item: model_sort_value(item, model_key),
        reverse=True,
    )

    return eligible[:TOP_N]



def derive_model_model_only_top(all_predictions, model_key, mode_prefix):
    eligible = []

    for prediction in all_predictions:
        if not has_model_data(prediction, model_key):
            continue

        eligible.append(
            mark_top_mode(
                prediction,
                f"{mode_prefix}_MODEL_ONLY",
                "no usable matched odds available; model-only fallback",
            )
        )

    eligible.sort(
        key=lambda item: model_sort_value(item, model_key),
        reverse=True,
    )

    return eligible[:TOP_N]



def derive_model_highest_odds_fallback_top(all_predictions, model_key, mode_prefix):
    eligible = []

    for prediction in all_predictions:
        if not has_model_data(prediction, model_key):
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
                f"{mode_prefix}_HIGHEST_ODDS_FALLBACK",
                "no primary or secondary picks available; selected by highest available odds",
            )
        )

    eligible.sort(
        key=lambda item: model_odds_sort_value(item, model_key),
        reverse=True,
    )

    return eligible[:TOP_N]



def derive_model_top_from_all(all_predictions, model_key, mode_prefix, label):
    primary = derive_model_primary_top(
        all_predictions,
        model_key,
        mode_prefix,
    )

    if primary:
        print(
            f"{label} derived from PRIMARY odds tier:",
            len(primary),
        )

        return primary

    secondary = derive_model_secondary_top(
        all_predictions,
        model_key,
        mode_prefix,
    )

    if secondary:
        print(
            f"{label} derived from SECONDARY odds tier:",
            len(secondary),
        )

        return secondary

    odds_available = usable_model_odds_predictions(
        all_predictions,
        model_key,
    )

    if not odds_available:
        model_only = derive_model_model_only_top(
            all_predictions,
            model_key,
            mode_prefix,
        )

        print(
            f"{label} derived from MODEL_ONLY fallback:",
            len(model_only),
        )

        return model_only

    highest_odds = derive_model_highest_odds_fallback_top(
        all_predictions,
        model_key,
        mode_prefix,
    )

    print(
        f"{label} derived from HIGHEST_ODDS_FALLBACK:",
        len(highest_odds),
    )

    if highest_odds:
        return highest_odds

    model_only = derive_model_model_only_top(
        all_predictions,
        model_key,
        mode_prefix,
    )

    print(
        f"{label} derived from FINAL MODEL_ONLY fallback:",
        len(model_only),
    )

    return model_only



def derive_bst_top_from_all(all_predictions):
    bst_top = derive_model_top_from_all(
        all_predictions=all_predictions,
        model_key="bst",
        mode_prefix="BST",
        label="BST TOP5",
    )

    return [
        mark_bst_view(prediction)
        for prediction in bst_top
    ]


# -----------------------------------------------------------------------------
# Logging / validation
# -----------------------------------------------------------------------------


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
                    "corq_display_probability": prediction.get("corq_display_probability"),
                    "corq_ai_probability": prediction.get("corq_ai_probability"),
                    "bst_ai_probability": prediction.get("bst_ai_probability"),
                    "marq_ai_score": prediction.get("marq_ai_score"),
                    "marq_ai_signal": prediction.get("marq_ai_signal"),
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


# -----------------------------------------------------------------------------
# Main page builder
# -----------------------------------------------------------------------------


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

    bst_predictions = derive_bst_top_from_all(
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

    print_prediction_sample(
        "BST TOP5 PREDICTIONS",
        bst_predictions,
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

    write_page(
        predictions=bst_predictions,
        title=SITE_TITLE,
        subtitle="BsT AI TOP5 equivalent",
        destination="public/BsT/index.html",
    )

    write_rss(
        predictions=bst_predictions,
        title=f"{SITE_TITLE} - BsT AI",
        link=f"{BASE_URL}/BsT/",
        destination="public/tennis_bst.xml",
    )

    print("")
    print("=== BUILD PAGES WRITTEN ===")
    print("public/index.html")
    print("public/tennis.xml")
    print("public/all/index.html")
    print("public/tennis_all.xml")
    print("public/BsT/index.html")
    print("public/tennis_bst.xml")
    print("TOP COUNT:", len(top_predictions))
    print("ALL COUNT:", len(all_predictions))
    print("BST TOP5 COUNT:", len(bst_predictions))
    print("=== END BUILD PAGES WRITTEN ===")
    print("")


if __name__ == "__main__":
    build_pages()
