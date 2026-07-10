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

# Blenq = close-odds + market-edge + Corq/Thinq consensus model.
BLENQ_MIN_PICK_ODDS = 1.70
BLENQ_MAX_PICK_ODDS = 2.65
BLENQ_MAX_MARKET_GAP = 0.10
BLENQ_MIN_CORQ = 0.55
BLENQ_MIN_THINQ = 0.55
BLENQ_MIN_PROBABILITY = 0.58
BLENQ_MIN_AI_MATCH = 88.0
BLENQ_MIN_EDGE = 0.0


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


def get_first_float(prediction, keys):
    for key in keys:
        value = safe_float(prediction.get(key))
        if value is not None:
            return value
    return None


def get_pick_odds(prediction):
    return get_prediction_odds(prediction)


def get_odds_player1(prediction):
    return get_first_float(prediction, ["odds_player1", "p1_odds", "home_odds", "odds1", "price1"])


def get_odds_player2(prediction):
    return get_first_float(prediction, ["odds_player2", "p2_odds", "away_odds", "odds2", "price2"])


def get_ai_match(prediction):
    return safe_float(prediction.get("ai_match"))


def calculate_market_fair_probabilities(odds_player1, odds_player2):
    if odds_player1 is None or odds_player2 is None:
        return None, None, None
    if odds_player1 <= 1.0 or odds_player2 <= 1.0:
        return None, None, None
    implied_1 = 1.0 / odds_player1
    implied_2 = 1.0 / odds_player2
    total = implied_1 + implied_2
    if total <= 0:
        return None, None, None
    fair_1 = implied_1 / total
    fair_2 = implied_2 / total
    market_gap = abs(fair_1 - fair_2)
    return fair_1, fair_2, market_gap


def calculate_pick_market_fair(prediction, fair_1, fair_2):
    pick = str(prediction.get("pick") or "").strip().lower()
    player1 = str(prediction.get("player1") or "").strip().lower()
    player2 = str(prediction.get("player2") or "").strip().lower()
    if pick and player1 and pick == player1:
        return fair_1
    if pick and player2 and pick == player2:
        return fair_2
    return None


def calculate_blenq_tier(blenq_probability, edge_pp, ai_match, marq_signal):
    signal = str(marq_signal or "").upper().strip()
    negative_market = signal in {"CAUTION", "BEARISH"}
    if blenq_probability >= 0.62 and edge_pp >= 0.05 and ai_match >= 92.0 and not negative_market:
        return "BLENQ_A"
    if blenq_probability >= 0.60 and edge_pp >= 0.03 and ai_match >= 90.0:
        return "BLENQ_B"
    return "BLENQ_WATCH"


def calculate_blenq_risk(prediction, market_gap, edge_pp, ai_match):
    notes = []
    signal = str(prediction.get("marq_ai_signal") or "").upper().strip()
    if signal in {"CAUTION", "BEARISH"}:
        notes.append("NEGATIVE_MARKET")
    elif signal == "THIN MARKET":
        notes.append("THIN_MARKET")
    elif signal in {"", "NO MARKET DATA"}:
        notes.append("NO_MARKET_DATA")
    if market_gap is not None and market_gap > 0.08:
        notes.append("WIDER_CLOSE_MARKET")
    if edge_pp is not None and edge_pp < 0.03:
        notes.append("LOW_EDGE")
    if ai_match is not None and ai_match < 90.0:
        notes.append("LOW_AI_MATCH")
    return "OK" if not notes else ",".join(notes)


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
    pick_odds = get_pick_odds(prediction)
    odds_player1 = get_odds_player1(prediction)
    odds_player2 = get_odds_player2(prediction)
    market_fair_player1, market_fair_player2, market_gap = calculate_market_fair_probabilities(odds_player1, odds_player2)
    market_implied_pick = 1.0 / pick_odds if pick_odds and pick_odds > 1.0 else None
    market_fair_pick = calculate_pick_market_fair(prediction, market_fair_player1, market_fair_player2)
    edge_pp = blend_probability - market_implied_pick if market_implied_pick is not None else None
    ai_match = get_ai_match(prediction) or 0.0
    updated["probability"] = blend_probability
    updated["blend_probability"] = blend_probability
    updated["blenq_probability"] = blend_probability
    updated["corq_display_probability"] = corq_probability
    updated["bst_ai_probability"] = thinq_probability
    updated["odds_player1"] = odds_player1
    updated["odds_player2"] = odds_player2
    updated["market_fair_player1"] = market_fair_player1
    updated["market_fair_player2"] = market_fair_player2
    updated["market_fair_pick"] = market_fair_pick
    updated["market_gap"] = market_gap
    updated["market_implied_pick"] = market_implied_pick
    updated["edge_pp"] = edge_pp
    updated["blenq_score"] = edge_pp
    updated["blenq_tier"] = calculate_blenq_tier(blend_probability, edge_pp or -999.0, ai_match, prediction.get("marq_ai_signal"))
    updated["blenq_risk"] = calculate_blenq_risk(prediction, market_gap, edge_pp, ai_match)
    updated["top_mode"] = "BLENQ_CLOSE_ODDS_EDGE"
    updated["top_reason"] = "Blenq close-odds market-edge model: odds 1.70-2.65, market gap <= 10%, consensus >= 58%, AI Match >= 88%, edge >= 0"
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
        if not is_thinq_ok(prediction):
            continue
        pick_odds = get_pick_odds(prediction)
        odds_player1 = get_odds_player1(prediction)
        odds_player2 = get_odds_player2(prediction)
        corq_probability = get_corq_probability(prediction)
        thinq_probability = get_thinq_probability(prediction)
        ai_match = get_ai_match(prediction)
        if pick_odds is None or odds_player1 is None or odds_player2 is None:
            continue
        if corq_probability is None or thinq_probability is None or ai_match is None:
            continue
        if pick_odds < BLENQ_MIN_PICK_ODDS or pick_odds > BLENQ_MAX_PICK_ODDS:
            continue
        market_fair_player1, market_fair_player2, market_gap = calculate_market_fair_probabilities(odds_player1, odds_player2)
        if market_gap is None or market_gap > BLENQ_MAX_MARKET_GAP:
            continue
        market_implied_pick = 1.0 / pick_odds if pick_odds > 1.0 else None
        if market_implied_pick is None:
            continue
        blend_probability = (corq_probability + thinq_probability) / 2.0
        edge_pp = blend_probability - market_implied_pick
        if corq_probability < BLENQ_MIN_CORQ or thinq_probability < BLENQ_MIN_THINQ:
            continue
        if blend_probability < BLENQ_MIN_PROBABILITY or ai_match < BLENQ_MIN_AI_MATCH or edge_pp < BLENQ_MIN_EDGE:
            continue
        eligible.append(mark_blend_view(prediction, blend_probability, corq_probability, thinq_probability))

    eligible.sort(key=lambda item: (safe_float(item.get("edge_pp")) or -999.0, safe_float(item.get("blenq_probability")) or 0.0, safe_float(item.get("ai_match")) or 0.0), reverse=True)
    selected = dedupe_predictions(eligible)
    print("BLENQ COUNT:", len(selected))
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
                    "blenq_probability": prediction.get("blenq_probability") or prediction.get("blend_probability"),
                    "market_gap": prediction.get("market_gap"),
                    "edge_pp": prediction.get("edge_pp"),
                    "blenq_tier": prediction.get("blenq_tier"),
                    "blenq_risk": prediction.get("blenq_risk"),
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
    print("BLENQ MIN PICK ODDS:", BLENQ_MIN_PICK_ODDS)
    print("BLENQ MAX PICK ODDS:", BLENQ_MAX_PICK_ODDS)
    print("BLENQ MARKET GAP MAX:", BLENQ_MAX_MARKET_GAP)
    print("=== END BUILD PAGES INPUTS ===")
    print("")

    all_predictions = load_json_required(all_json)

    validate_predictions(all_predictions)

    corq_predictions = derive_corq_predictions(all_predictions)
    thinq_predictions = derive_thinq_predictions(all_predictions)
    blend_predictions = derive_blend_predictions(all_predictions)

    print_prediction_sample("CORQ PREDICTIONS", corq_predictions)
    print_prediction_sample("THINQ PREDICTIONS", thinq_predictions)
    print_prediction_sample("BLENQ PREDICTIONS", blend_predictions)
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
        subtitle="Blenq close-odds market-edge predictions",
        destination="public/Blend/index.html",
    )

    write_rss(
        predictions=blend_predictions,
        title=f"{SITE_TITLE} - Blenq",
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
    print("BLENQ COUNT:", len(blend_predictions))
    print("ALL COUNT:", len(all_predictions))
    print("=== END BUILD PAGES WRITTEN ===")
    print("")


if __name__ == "__main__":
    build_pages()
