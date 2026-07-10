import os
from typing import Any, Dict, List, Optional, Tuple

from prediction_engine_core import build_all_predictions as build_core_all_predictions


TOP_N = 7


# -----------------------------------------------------------------------------
# Basic helpers
# -----------------------------------------------------------------------------


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def normalize_probability_decimal(value: Any) -> Optional[float]:
    number = safe_float(value)

    if number is None:
        return None

    # Some upstream layers may store probabilities as 62.5 instead of 0.625.
    if number > 1.0:
        return number / 100.0

    return number


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def normalize_status(value: Any) -> str:
    return str(value or "").upper().strip()


def is_bst_ok(prediction: Dict[str, Any]) -> bool:
    return normalize_status(prediction.get("bst_ai_status")) == "OK"


def has_ai_match(prediction: Dict[str, Any]) -> bool:
    return safe_float(prediction.get("ai_match")) is not None


def get_pick_odds(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("odds"))


def get_corq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )


def get_thinq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("bst_ai_probability")
    )


# -----------------------------------------------------------------------------
# Consensus / cross-influence model
# -----------------------------------------------------------------------------


def calculate_cross_influence_scores(
    prediction: Dict[str, Any],
) -> Optional[Dict[str, float]]:
    """
    TOP7 consensus layer.

    Corq raw and Thinq raw are preserved, but TOP selection uses lightly
    cross-influenced values:

    - CorqQ  = 80% Corq  + 20% Thinq
    - ThinqQ = 80% Thinq + 20% Corq

    This reduces conflict picks where one model is very high and the other one
    strongly disagrees, while still keeping each model as the dominant signal in
    its own adjusted view.
    """

    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)

    if corq is None or thinq is None:
        return None

    corq_weight = env_float("TOP7_CORQ_SELF_WEIGHT", 0.80)
    thinq_cross_weight = env_float("TOP7_CORQ_THINQ_WEIGHT", 0.20)

    thinq_weight = env_float("TOP7_THINQ_SELF_WEIGHT", 0.80)
    corq_cross_weight = env_float("TOP7_THINQ_CORQ_WEIGHT", 0.20)

    corq_q = (corq_weight * corq) + (thinq_cross_weight * thinq)
    thinq_q = (thinq_weight * thinq) + (corq_cross_weight * corq)

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


# -----------------------------------------------------------------------------
# TOP7 eligibility and scoring
# -----------------------------------------------------------------------------


def eligible_top7(prediction: Dict[str, Any]) -> bool:
    """
    TOP7 test policy:

    - valid odds required
    - odds >= 1.40 by default
    - bst_ai_status == OK required
    - AI Match must exist
    - CorqQ >= 55% by default
    - ThinqQ >= 55% by default
    - model_gap <= 15 percentage points by default

    No relaxed filler tier is used. If only 3 picks pass, only 3 picks are
    returned. This avoids forcing lower-quality picks into the shortlist.
    """

    min_odds = env_float("TOP7_MIN_ODDS", 1.40)
    max_odds = env_float("TOP7_MAX_ODDS", 5.00)
    min_corq_q = env_float("TOP7_MIN_CORQ_Q", 0.55)
    min_thinq_q = env_float("TOP7_MIN_THINQ_Q", 0.55)
    max_model_gap = env_float("TOP7_MAX_MODEL_GAP", 0.15)
    min_ai_match = env_float("TOP7_MIN_AI_MATCH", 0.0)

    odds = get_pick_odds(prediction)
    ai_match = safe_float(prediction.get("ai_match"))

    if odds is None:
        return False

    if odds < min_odds or odds > max_odds:
        return False

    if not is_bst_ok(prediction):
        return False

    if ai_match is None:
        return False

    if ai_match < min_ai_match:
        return False

    scores = calculate_cross_influence_scores(prediction)

    if not scores:
        return False

    if scores["model_gap"] > max_model_gap:
        return False

    if scores["corq_q_probability"] < min_corq_q:
        return False

    if scores["thinq_q_probability"] < min_thinq_q:
        return False

    return True


def top7_score(prediction: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Ranking order:

    1. consensus_score DESC
    2. CorqQ DESC
    3. AI Match DESC

    Odds do not directly boost rank. Odds are a strict eligibility filter,
    not a score booster. This prevents higher odds from pulling weaker model
    picks upward.
    """

    scores = calculate_cross_influence_scores(prediction) or {}
    consensus = safe_float(scores.get("consensus_score")) or 0.0
    corq_q = safe_float(scores.get("corq_q_probability")) or 0.0
    ai_match = safe_float(prediction.get("ai_match")) or 0.0

    return consensus, corq_q, ai_match


def apply_top7_metadata(prediction: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(prediction)
    scores = calculate_cross_influence_scores(item) or {}

    corq_raw = scores.get("corq_raw_probability")
    thinq_raw = scores.get("thinq_raw_probability")
    corq_q = scores.get("corq_q_probability")
    thinq_q = scores.get("thinq_q_probability")
    model_gap = scores.get("model_gap")
    consensus = scores.get("consensus_score")

    # Preserve raw model values under explicit names.
    item["corq_raw_probability"] = corq_raw
    item["thinq_raw_probability"] = thinq_raw

    # Add TOP7 adjusted values.
    item["corq_q_probability"] = corq_q
    item["thinq_q_probability"] = thinq_q
    item["model_gap"] = model_gap
    item["consensus_score"] = consensus
    item["consensus_status"] = consensus_status(model_gap)

    # For the Corq/TOP public page, show the lightly adjusted CorqQ as the
    # displayed WIN probability while retaining raw Corq above.
    if corq_q is not None:
        item["probability"] = round(corq_q, 4)
        item["corq_display_probability"] = round(corq_q, 4)

    item["top_mode"] = "TOP7_CORQ_THINQ_CONSENSUS"
    item["top_reason"] = (
        "TOP7 test: odds >= 1.40, bst_ai_status OK, AI Match available, "
        "CorqQ/ThinqQ 80/20 cross influence, model_gap <= 15%."
    )

    return item


# -----------------------------------------------------------------------------
# Dedupe and public API
# -----------------------------------------------------------------------------


def unique_key(prediction: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(prediction.get("match_id") or prediction.get("event_id") or ""),
        str(prediction.get("match") or ""),
        str(prediction.get("pick") or ""),
    )


def deduplicate_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []

    for prediction in predictions:
        key = unique_key(prediction)

        if key in seen:
            continue

        seen.add(key)
        output.append(prediction)

    return output


def build_all_predictions() -> List[Dict[str, Any]]:
    return build_core_all_predictions()


def get_top_predictions(
    all_predictions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    TOP7 policy:

    - No relaxed filler tier.
    - No snapshot fill to reach TOP7.
    - If fewer than 7 picks pass, return fewer than 7.
    - Ranking is consensus-driven, not odds-boosted.
    """

    if all_predictions is None:
        all_predictions = build_all_predictions()

    required_count = env_int("TOP_N", TOP_N)

    eligible = [
        apply_top7_metadata(prediction)
        for prediction in all_predictions
        if eligible_top7(prediction)
    ]

    eligible = deduplicate_predictions(eligible)
    eligible.sort(key=top7_score, reverse=True)

    selected = eligible[:required_count]

    print("TOP7 CONSENSUS COUNT:", len(selected))
    print("TOP7 MIN ODDS:", env_float("TOP7_MIN_ODDS", 1.40))
    print("TOP7 MAX MODEL GAP:", env_float("TOP7_MAX_MODEL_GAP", 0.15))

    for idx, item in enumerate(selected, start=1):
        print(
            "TOP7 CONSENSUS PICK:",
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "corq_raw=",
            item.get("corq_raw_probability"),
            "thinq_raw=",
            item.get("thinq_raw_probability"),
            "corq_q=",
            item.get("corq_q_probability"),
            "thinq_q=",
            item.get("thinq_q_probability"),
            "gap=",
            item.get("model_gap"),
            "consensus=",
            item.get("consensus_score"),
            "odds=",
            item.get("odds"),
            "status=",
            item.get("consensus_status"),
        )

    return selected


def get_daily_predictions() -> List[Dict[str, Any]]:
    return get_top_predictions()
