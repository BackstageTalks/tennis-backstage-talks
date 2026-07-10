
import os
from typing import Any, Dict, List, Optional, Tuple

from prediction_engine_core import build_all_predictions as build_core_all_predictions

TOP_N = int(os.getenv("TOP_N", "7"))
TOP_MIN_ODDS = float(os.getenv("TOP_MIN_ODDS", "1.40"))
TOP_MAX_ODDS = float(os.getenv("TOP_MAX_ODDS", "5.00"))
TOP_MIN_CORQ_Q = float(os.getenv("TOP_MIN_CORQ_Q", "0.55"))
TOP_MIN_THINQ_Q = float(os.getenv("TOP_MIN_THINQ_Q", "0.55"))
TOP_MAX_MODEL_GAP = float(os.getenv("TOP_MAX_MODEL_GAP", "0.15"))
TOP_MIN_AI_MATCH = float(os.getenv("TOP_MIN_AI_MATCH", "0.0"))


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
    return normalize_probability_decimal(
        prediction.get("bst_ai_probability")
        or prediction.get("thinq_ai_probability")
    )


def get_ai_match(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("ai_match"))


def get_pick_odds(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("odds"))


def has_both_model_outputs(prediction: Dict[str, Any]) -> bool:
    """
    Production TOP rule:
    - Corq probability must exist.
    - Thinq probability must exist.
    - AI Match must exist.

    Historical bst_ai_status is intentionally NOT used as a hard filter.
    """
    if get_corq_probability(prediction) is None:
        return False
    if get_thinq_probability(prediction) is None:
        return False
    if get_ai_match(prediction) is None:
        return False
    return True


def calculate_cross_influence_scores(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)
    ai_match = get_ai_match(prediction)

    if corq is None or thinq is None or ai_match is None:
        return None

    corq_q = 0.80 * corq + 0.20 * thinq
    thinq_q = 0.80 * thinq + 0.20 * corq
    model_gap = abs(corq - thinq)
    consensus_score = (corq_q + thinq_q) / 2.0

    return {
        "corq": corq,
        "thinq": thinq,
        "corq_q": corq_q,
        "thinq_q": thinq_q,
        "model_gap": model_gap,
        "consensus_score": consensus_score,
        "ai_match": ai_match,
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


def has_valid_top_odds(prediction: Dict[str, Any]) -> bool:
    odds = get_pick_odds(prediction)
    return odds is not None and TOP_MIN_ODDS <= odds <= TOP_MAX_ODDS


def eligible_top7(prediction: Dict[str, Any]) -> bool:
    if not has_both_model_outputs(prediction):
        return False
    if not has_valid_top_odds(prediction):
        return False

    scores = calculate_cross_influence_scores(prediction)
    if not scores:
        return False

    if scores["corq_q"] < TOP_MIN_CORQ_Q:
        return False
    if scores["thinq_q"] < TOP_MIN_THINQ_Q:
        return False
    if scores["model_gap"] > TOP_MAX_MODEL_GAP:
        return False
    if scores["ai_match"] < TOP_MIN_AI_MATCH:
        return False

    return True


def top7_score(prediction: Dict[str, Any]) -> Tuple[float, float, float]:
    scores = calculate_cross_influence_scores(prediction)
    if not scores:
        return (0.0, 0.0, 0.0)
    return (
        scores["consensus_score"],
        scores["corq_q"],
        scores["ai_match"],
    )


def apply_top7_metadata(prediction: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(prediction)
    scores = calculate_cross_influence_scores(item)

    if not scores:
        item["top_mode"] = "NO_DUAL_MODEL_OUTPUT"
        item["top_reason"] = "Missing Corq, Thinq or AI Match output"
        return item

    item["corq_raw_probability"] = round(scores["corq"], 4)
    item["thinq_raw_probability"] = round(scores["thinq"], 4)
    item["corq_q_probability"] = round(scores["corq_q"], 4)
    item["thinq_q_probability"] = round(scores["thinq_q"], 4)
    item["model_gap"] = round(scores["model_gap"], 4)
    item["consensus_score"] = round(scores["consensus_score"], 4)
    item["consensus_status"] = consensus_status(scores["model_gap"])
    item["top_mode"] = "TOP7_DUAL_MODEL_CONSENSUS"
    item["top_reason"] = "TOP7: CorqQ/ThinqQ 80/20, odds >= 1.40, model_gap <= 15%, both probabilities required"
    return item


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


def get_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if all_predictions is None:
        all_predictions = build_all_predictions()

    eligible = [
        apply_top7_metadata(prediction)
        for prediction in all_predictions
        if eligible_top7(prediction)
    ]
    eligible = deduplicate_predictions(eligible)
    eligible.sort(key=top7_score, reverse=True)
    selected = eligible[:TOP_N]

    print("TOP7 CONSENSUS COUNT:", len(selected))
    print("TOP7 MIN ODDS:", TOP_MIN_ODDS)
    print("TOP7 MAX MODEL GAP:", TOP_MAX_MODEL_GAP)

    for idx, item in enumerate(selected, start=1):
        print(
            "TOP7 CONSENSUS PICK:",
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "odds=", item.get("odds"),
            "corq_q=", item.get("corq_q_probability"),
            "thinq_q=", item.get("thinq_q_probability"),
            "gap=", item.get("model_gap"),
            "consensus=", item.get("consensus_score"),
            "status=", item.get("consensus_status"),
        )

    return selected


def get_daily_predictions() -> List[Dict[str, Any]]:
    return get_top_predictions()
