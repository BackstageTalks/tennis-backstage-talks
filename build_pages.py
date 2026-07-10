import copy
import glob
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from render_site import write_page, write_rss


BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"
SITE_TITLE = "BackstageTalks Statistic Model"

# -----------------------------------------------------------------------------
# Shared production-selection policy
# -----------------------------------------------------------------------------

TOP_N = int(os.getenv("TOP_N", "7"))

TOP_MIN_ODDS = float(os.getenv("TOP_MIN_ODDS", "1.40"))
TOP_MAX_ODDS = float(os.getenv("TOP_MAX_ODDS", "5.00"))
TOP_MIN_CORQ_Q = float(os.getenv("TOP_MIN_CORQ_Q", "0.55"))
TOP_MIN_THINQ_Q = float(os.getenv("TOP_MIN_THINQ_Q", "0.55"))
TOP_MAX_MODEL_GAP = float(os.getenv("TOP_MAX_MODEL_GAP", "0.15"))
TOP_MIN_AI_MATCH = float(os.getenv("TOP_MIN_AI_MATCH", "0.0"))

# Blenq = close-odds + market-edge + Corq/Thinq consensus model.
BLENQ_MIN_PICK_ODDS = float(os.getenv("BLENQ_MIN_PICK_ODDS", "1.70"))
BLENQ_MAX_PICK_ODDS = float(os.getenv("BLENQ_MAX_PICK_ODDS", "2.65"))
BLENQ_MAX_MARKET_GAP = float(os.getenv("BLENQ_MAX_MARKET_GAP", "0.10"))
BLENQ_MIN_CORQ = float(os.getenv("BLENQ_MIN_CORQ", "0.55"))
BLENQ_MIN_THINQ = float(os.getenv("BLENQ_MIN_THINQ", "0.55"))
BLENQ_MIN_PROBABILITY = float(os.getenv("BLENQ_MIN_PROBABILITY", "0.58"))
BLENQ_MIN_AI_MATCH = float(os.getenv("BLENQ_MIN_AI_MATCH", "88.0"))
BLENQ_MIN_EDGE = float(os.getenv("BLENQ_MIN_EDGE", "0.0"))
BLENQ_MAX_MODEL_GAP = float(os.getenv("BLENQ_MAX_MODEL_GAP", "0.15"))


# -----------------------------------------------------------------------------
# File helpers
# -----------------------------------------------------------------------------


def extract_date_from_filename(path: str) -> str:
    filename = os.path.basename(path or "")
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else ""


def sorted_files_newest_first(pattern: str) -> List[str]:
    files = glob.glob(pattern)
    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )
    return files


def load_json(path: str, default: Any):
    try:
        if not path or not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        print("BUILD PAGES JSON LOAD ERROR:", path, str(exc))
        return default


def save_json(path: str, data: Any) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def find_latest_non_empty_file(pattern: str, label: str) -> Optional[str]:
    for path in sorted_files_newest_first(pattern):
        data = load_json(path, [])
        if isinstance(data, list) and data:
            print("BUILD PAGES SOURCE:", label, path, len(data))
            return path
    print("BUILD PAGES SOURCE MISSING:", label, pattern)
    return None


def ensure_public_dirs() -> None:
    os.makedirs("public", exist_ok=True)
    os.makedirs("public/all", exist_ok=True)
    os.makedirs("public/BsT", exist_ok=True)
    os.makedirs("public/Blend", exist_ok=True)


# -----------------------------------------------------------------------------
# Numeric helpers
# -----------------------------------------------------------------------------


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def normalize_probability_decimal(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number > 1.0:
        return number / 100.0
    return number


def get_corq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )


def get_thinq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(prediction.get("bst_ai_probability"))


def get_ai_match(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("ai_match"))


def get_prediction_odds(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("odds"))


def get_first_float(prediction: Dict[str, Any], keys: List[str]) -> Optional[float]:
    for key in keys:
        value = safe_float(prediction.get(key))
        if value is not None:
            return value
    return None


def get_odds_player1(prediction: Dict[str, Any]) -> Optional[float]:
    return get_first_float(
        prediction,
        ["odds_player1", "p1_odds", "home_odds", "odds1", "price1"],
    )


def get_odds_player2(prediction: Dict[str, Any]) -> Optional[float]:
    return get_first_float(
        prediction,
        ["odds_player2", "p2_odds", "away_odds", "odds2", "price2"],
    )


def is_thinq_ok(prediction: Dict[str, Any]) -> bool:
    return str(prediction.get("bst_ai_status") or "").upper().strip() == "OK"


def has_both_model_outputs(prediction: Dict[str, Any]) -> bool:
    if not is_thinq_ok(prediction):
        return False
    if get_corq_probability(prediction) is None:
        return False
    if get_thinq_probability(prediction) is None:
        return False
    if get_ai_match(prediction) is None:
        return False
    return True


def calculate_quality_scores(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)
    if corq is None or thinq is None:
        return None

    corq_q = (0.80 * corq) + (0.20 * thinq)
    thinq_q = (0.80 * thinq) + (0.20 * corq)
    model_gap = abs(corq - thinq)
    consensus_score = (corq_q + thinq_q) / 2.0

    return {
        "corq_raw_probability": corq,
        "thinq_raw_probability": thinq,
        "corq_q_probability": corq_q,
        "thinq_q_probability": thinq_q,
        "model_gap": model_gap,
        "consensus_score": consensus_score,
    }


def consensus_status(model_gap: Optional[float]) -> str:
    if model_gap is None:
        return "NO_CONSENSUS_DATA"
    if model_gap <= 0.07:
        return "STRONG_CONSENSUS"
    if model_gap <= 0.15:
        return "CONSENSUS"
    if model_gap <= 0.22:
        return "MODEL_GAP"
    return "MODEL_CONFLICT"


def has_required_top_odds(prediction: Dict[str, Any]) -> bool:
    odds = get_prediction_odds(prediction)
    return odds is not None and TOP_MIN_ODDS <= odds <= TOP_MAX_ODDS


def calculate_market_fair_probabilities(
    odds_player1: Optional[float],
    odds_player2: Optional[float],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
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


def calculate_pick_market_fair(
    prediction: Dict[str, Any],
    fair_1: Optional[float],
    fair_2: Optional[float],
) -> Optional[float]:
    pick = str(prediction.get("pick") or "").strip().lower()
    player1 = str(prediction.get("player1") or "").strip().lower()
    player2 = str(prediction.get("player2") or "").strip().lower()

    if pick and player1 and pick == player1:
        return fair_1
    if pick and player2 and pick == player2:
        return fair_2
    return None


def calculate_blenq_tier(
    blenq_probability: float,
    edge_pp: float,
    ai_match: float,
    marq_signal: Any,
) -> str:
    signal = str(marq_signal or "").upper().strip()
    negative_market = signal in {"CAUTION", "BEARISH"}

    if blenq_probability >= 0.62 and edge_pp >= 0.05 and ai_match >= 92.0 and not negative_market:
        return "BLENQ_A"
    if blenq_probability >= 0.60 and edge_pp >= 0.03 and ai_match >= 90.0:
        return "BLENQ_B"
    return "BLENQ_WATCH"


def calculate_blenq_risk(
    prediction: Dict[str, Any],
    market_gap: Optional[float],
    edge_pp: Optional[float],
    ai_match: Optional[float],
    model_gap: Optional[float],
) -> str:
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
    if model_gap is not None and model_gap > 0.15:
        notes.append("MODEL_GAP")

    return "OK" if not notes else ",".join(notes)


# -----------------------------------------------------------------------------
# Prediction mutation helpers
# -----------------------------------------------------------------------------


def clone_prediction(prediction: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(prediction)


def unique_key(prediction: Dict[str, Any]) -> Tuple[str, str]:
    return (
        str(prediction.get("match_id") or prediction.get("event_id") or prediction.get("match") or ""),
        str(prediction.get("pick") or ""),
    )


def dedupe_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected = []
    seen = set()
    for prediction in predictions:
        key = unique_key(prediction)
        if key in seen:
            continue
        seen.add(key)
        selected.append(prediction)
    return selected


def apply_consensus_metadata(
    prediction: Dict[str, Any],
    display_probability: float,
    view_name: str,
    reason: str,
) -> Dict[str, Any]:
    updated = clone_prediction(prediction)
    scores = calculate_quality_scores(updated) or {}
    model_gap = scores.get("model_gap")

    updated["corq_raw_probability"] = scores.get("corq_raw_probability")
    updated["thinq_raw_probability"] = scores.get("thinq_raw_probability")
    updated["corq_q_probability"] = scores.get("corq_q_probability")
    updated["thinq_q_probability"] = scores.get("thinq_q_probability")
    updated["model_gap"] = model_gap
    updated["consensus_score"] = scores.get("consensus_score")
    updated["consensus_status"] = consensus_status(model_gap)

    updated["probability"] = round(display_probability, 4)
    updated["corq_display_probability"] = scores.get("corq_q_probability")
    updated["top_mode"] = view_name
    updated["top_reason"] = reason
    return updated


def mark_blenq_view(
    prediction: Dict[str, Any],
    blenq_probability: float,
    scores: Dict[str, float],
) -> Dict[str, Any]:
    updated = apply_consensus_metadata(
        prediction,
        blenq_probability,
        "BLENQ_CLOSE_ODDS_EDGE",
        "Blenq close-odds market-edge model with both Corq and Thinq outputs required.",
    )

    pick_odds = get_prediction_odds(prediction)
    odds_player1 = get_odds_player1(prediction)
    odds_player2 = get_odds_player2(prediction)
    fair_1, fair_2, market_gap = calculate_market_fair_probabilities(odds_player1, odds_player2)
    market_implied_pick = 1.0 / pick_odds if pick_odds and pick_odds > 1.0 else None
    market_fair_pick = calculate_pick_market_fair(prediction, fair_1, fair_2)
    edge_pp = blenq_probability - market_implied_pick if market_implied_pick is not None else None
    ai_match = get_ai_match(prediction) or 0.0
    model_gap = scores.get("model_gap")

    updated["probability"] = round(blenq_probability, 4)
    updated["blend_probability"] = round(blenq_probability, 4)
    updated["blenq_probability"] = round(blenq_probability, 4)
    updated["odds_player1"] = odds_player1
    updated["odds_player2"] = odds_player2
    updated["market_fair_player1"] = fair_1
    updated["market_fair_player2"] = fair_2
    updated["market_fair_pick"] = market_fair_pick
    updated["market_gap"] = market_gap
    updated["market_implied_pick"] = market_implied_pick
    updated["edge_pp"] = edge_pp
    updated["blenq_score"] = edge_pp

    updated["blenq_tier"] = calculate_blenq_tier(
        blenq_probability,
        edge_pp if edge_pp is not None else -999.0,
        ai_match,
        prediction.get("marq_ai_signal"),
    )
    updated["blenq_risk"] = calculate_blenq_risk(
        prediction,
        market_gap,
        edge_pp,
        ai_match,
        model_gap,
    )

    return updated


# -----------------------------------------------------------------------------
# Page derivation logic
# -----------------------------------------------------------------------------


def eligible_common_top(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not has_both_model_outputs(prediction):
        return None
    if not has_required_top_odds(prediction):
        return None

    scores = calculate_quality_scores(prediction)
    if not scores:
        return None

    if scores["model_gap"] > TOP_MAX_MODEL_GAP:
        return None
    if scores["corq_q_probability"] < TOP_MIN_CORQ_Q:
        return None
    if scores["thinq_q_probability"] < TOP_MIN_THINQ_Q:
        return None

    ai_match = get_ai_match(prediction)
    if ai_match is None or ai_match < TOP_MIN_AI_MATCH:
        return None

    return scores


def derive_corq_predictions(all_predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = []
    for prediction in all_predictions:
        scores = eligible_common_top(prediction)
        if not scores:
            continue
        eligible.append(
            apply_consensus_metadata(
                prediction,
                scores["corq_q_probability"],
                "CORQ_TOP7_CONSENSUS",
                "CorqQ = 80% Corq + 20% Thinq; both models required; model_gap <= 15%; odds >= 1.40.",
            )
        )

    eligible = dedupe_predictions(eligible)
    eligible.sort(
        key=lambda item: (
            safe_float(item.get("consensus_score")) or 0.0,
            safe_float(item.get("corq_q_probability")) or 0.0,
            safe_float(item.get("ai_match")) or 0.0,
        ),
        reverse=True,
    )
    return eligible[:TOP_N]


def derive_thinq_predictions(all_predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = []
    for prediction in all_predictions:
        scores = eligible_common_top(prediction)
        if not scores:
            continue
        updated = apply_consensus_metadata(
            prediction,
            scores["thinq_q_probability"],
            "THINQ_TOP7_CONSENSUS",
            "ThinqQ = 80% Thinq + 20% Corq; both models required; model_gap <= 15%; odds >= 1.40.",
        )
        updated["bst_ai_probability"] = scores["thinq_q_probability"]
        eligible.append(updated)

    eligible = dedupe_predictions(eligible)
    eligible.sort(
        key=lambda item: (
            safe_float(item.get("consensus_score")) or 0.0,
            safe_float(item.get("thinq_q_probability")) or 0.0,
            safe_float(item.get("ai_match")) or 0.0,
        ),
        reverse=True,
    )
    return eligible[:TOP_N]


def eligible_blenq(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not has_both_model_outputs(prediction):
        return None

    scores = calculate_quality_scores(prediction)
    if not scores:
        return None

    if scores["model_gap"] > BLENQ_MAX_MODEL_GAP:
        return None
    if scores["corq_raw_probability"] < BLENQ_MIN_CORQ:
        return None
    if scores["thinq_raw_probability"] < BLENQ_MIN_THINQ:
        return None

    pick_odds = get_prediction_odds(prediction)
    if pick_odds is None or pick_odds < BLENQ_MIN_PICK_ODDS or pick_odds > BLENQ_MAX_PICK_ODDS:
        return None

    odds_player1 = get_odds_player1(prediction)
    odds_player2 = get_odds_player2(prediction)
    _, _, market_gap = calculate_market_fair_probabilities(odds_player1, odds_player2)
    if market_gap is None or market_gap > BLENQ_MAX_MARKET_GAP:
        return None

    blenq_probability = scores["consensus_score"]
    if blenq_probability < BLENQ_MIN_PROBABILITY:
        return None

    ai_match = get_ai_match(prediction)
    if ai_match is None or ai_match < BLENQ_MIN_AI_MATCH:
        return None

    market_implied_pick = 1.0 / pick_odds if pick_odds and pick_odds > 1.0 else None
    edge_pp = blenq_probability - market_implied_pick if market_implied_pick is not None else None
    if edge_pp is None or edge_pp < BLENQ_MIN_EDGE:
        return None

    return scores


def derive_blenq_predictions(all_predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = []
    for prediction in all_predictions:
        scores = eligible_blenq(prediction)
        if not scores:
            continue
        eligible.append(mark_blenq_view(prediction, scores["consensus_score"], scores))

    eligible = dedupe_predictions(eligible)
    eligible.sort(
        key=lambda item: (
            safe_float(item.get("edge_pp")) or -999.0,
            safe_float(item.get("blenq_probability")) or 0.0,
            safe_float(item.get("ai_match")) or 0.0,
        ),
        reverse=True,
    )
    return eligible[:TOP_N]


# -----------------------------------------------------------------------------
# Logging / validation
# -----------------------------------------------------------------------------


def print_prediction_sample(label: str, predictions: List[Dict[str, Any]]) -> None:
    print("")
    print(f"=== {label} SAMPLE ===")
    print("COUNT:", len(predictions))
    for idx, item in enumerate(predictions[:10], start=1):
        print(
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "prob=",
            item.get("probability"),
            "odds=",
            item.get("odds"),
            "corq_q=",
            item.get("corq_q_probability"),
            "thinq_q=",
            item.get("thinq_q_probability"),
            "gap=",
            item.get("model_gap"),
            "consensus=",
            item.get("consensus_score"),
            "mode=",
            item.get("top_mode"),
        )


def validate_predictions(all_predictions: List[Dict[str, Any]]) -> None:
    if not all_predictions:
        raise ValueError("ALL predictions are empty. Refusing to deploy empty ALL page.")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def load_all_predictions_for_pages() -> List[Dict[str, Any]]:
    source = find_latest_non_empty_file("public/all_predictions_*.json", "public all predictions")
    if not source:
        source = find_latest_non_empty_file("data/pick_history/all/*.json", "all snapshot")
    if not source:
        raise FileNotFoundError("No non-empty ALL predictions JSON found.")
    data = load_json(source, [])
    if not isinstance(data, list):
        raise ValueError(f"ALL predictions source is not a list: {source}")
    return data


def build_pages() -> None:
    ensure_public_dirs()

    all_predictions = load_all_predictions_for_pages()
    validate_predictions(all_predictions)

    corq_predictions = derive_corq_predictions(all_predictions)
    thinq_predictions = derive_thinq_predictions(all_predictions)
    blenq_predictions = derive_blenq_predictions(all_predictions)

    print("TOP_N:", TOP_N)
    print("TOP MIN ODDS:", TOP_MIN_ODDS)
    print("TOP MAX MODEL GAP:", TOP_MAX_MODEL_GAP)
    print("BLENQ MIN PICK ODDS:", BLENQ_MIN_PICK_ODDS)
    print("BLENQ MAX PICK ODDS:", BLENQ_MAX_PICK_ODDS)
    print("BLENQ MARKET GAP MAX:", BLENQ_MAX_MARKET_GAP)
    print("CORQ TOP7 COUNT:", len(corq_predictions))
    print("THINQ TOP7 COUNT:", len(thinq_predictions))
    print("BLENQ COUNT:", len(blenq_predictions))

    print_prediction_sample("CORQ TOP7", corq_predictions)
    print_prediction_sample("THINQ TOP7", thinq_predictions)
    print_prediction_sample("BLENQ", blenq_predictions)

    write_page(
        predictions=corq_predictions,
        title=SITE_TITLE,
        subtitle="Corq TOP7 consensus picks",
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
        subtitle="Thinq TOP7 consensus picks",
        destination="public/BsT/index.html",
    )
    write_rss(
        predictions=thinq_predictions,
        title=f"{SITE_TITLE} - Thinq",
        link=f"{BASE_URL}/BsT/",
        destination="public/tennis_bst.xml",
    )

    write_page(
        predictions=blenq_predictions,
        title=SITE_TITLE,
        subtitle="Blenq close-odds market-edge picks",
        destination="public/Blend/index.html",
    )
    write_rss(
        predictions=blenq_predictions,
        title=f"{SITE_TITLE} - Blenq",
        link=f"{BASE_URL}/Blend/",
        destination="public/tennis_blend.xml",
    )

    write_page(
        predictions=all_predictions,
        title=SITE_TITLE,
        subtitle="ALL audit predictions",
        destination="public/all/index.html",
    )
    write_rss(
        predictions=all_predictions,
        title=f"{SITE_TITLE} - ALL",
        link=f"{BASE_URL}/all/",
        destination="public/tennis_all.xml",
    )

    save_json("public/page_build_summary.json", {
        "top_n": TOP_N,
        "top_min_odds": TOP_MIN_ODDS,
        "top_max_model_gap": TOP_MAX_MODEL_GAP,
        "corq_count": len(corq_predictions),
        "thinq_count": len(thinq_predictions),
        "blenq_count": len(blenq_predictions),
    })

    print("")
    print("BUILD PAGES DONE")
    print("public/index.html")
    print("public/BsT/index.html")
    print("public/Blend/index.html")
    print("public/all/index.html")
    print("public/tennis.xml")
    print("public/tennis_bst.xml")
    print("public/tennis_blend.xml")
    print("public/tennis_all.xml")


if __name__ == "__main__":
    build_pages()
