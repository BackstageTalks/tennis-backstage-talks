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
MIN_ODDS = 1.50


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


def latest_file(pattern):
    files = glob.glob(pattern)

    if not files:
        return None

    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )

    return files[0]


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

        return float(value)

    except Exception:
        return None


def derive_top_from_all(all_predictions):
    """
    Fallback only.

    If public/predictions_YYYY-MM-DD.json is missing or empty,
    derive TOP5 from ALL by current production rule:
    odds > 1.50 + top 5 by Win %.
    """

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

        if odds <= MIN_ODDS:
            continue

        eligible.append(prediction)

    eligible.sort(
        key=lambda item: safe_float(
            item.get("probability")
        ) or 0.0,
        reverse=True,
    )

    return eligible[:TOP_N]


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
        print(
            "WARNING: TOP predictions are empty after fallback. "
            "TOP page will show no picks."
        )


def build_pages():
    ensure_public_dirs()

    top_json = latest_file(
        "public/predictions_*.json",
    )

    all_json = latest_file(
        "public/all_predictions_*.json",
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
