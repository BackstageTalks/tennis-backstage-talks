
import os
from typing import Any, Dict, List, Optional, Tuple

from prediction_engine_core import build_all_predictions as build_core_all_predictions

TOP_N = 7
DEFAULT_MIN_ODDS = 1.40
DEFAULT_MIN_CORQ_Q = 0.55
DEFAULT_MIN_THINQ_Q = 0.55
DEFAULT_MAX_MODEL_GAP = 0.15


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


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


def has_valid_odds(prediction: Dict[str, Any]) -> bool:
    odds = safe_float(prediction.get("odds"))
    min_odds = env_float("TOP_MIN_ODDS", DEFAULT_MIN_ODDS)
    return odds is not None and odds >= min_odds


def compute_model_metrics(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)
    ai_match = safe_float(prediction.get("ai_match"))

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


def eligible_top7(prediction: Dict[str, Any]) -> bool:
    metrics = compute_model_metrics(prediction)
    if metrics is None:
        return False

    if not has_valid_odds(prediction):
        return False

    min_corq_q = env_float("TOP_MIN_CORQ_Q", DEFAULT_MIN_CORQ_Q)
    min_thinq_q = env_float("TOP_MIN_THINQ_Q", DEFAULT_MIN_THINQ_Q)
    max_gap = env_float("TOP_MAX_MODEL_GAP", DEFAULT_MAX_MODEL_GAP)

    if metrics["corq_q"] < min_corq_q:
        return False
    if metrics["thinq_q"] < min_thinq_q:
        return False
    if metrics["model_gap"] > max_gap:
        return False

    return True


def model_status_from_gap(model_gap: float) -> str:
    if model_gap <= 0.07:
        return "STRONG_CONSENSUS"
    if model_gap <= 0.15:
        return "CONSENSUS"
    if model_gap <= 0.22:
        return "MODEL_GAP"
    return "MODEL_CONFLICT"


def mark_top_metadata(prediction: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(prediction)
    metrics = compute_model_metrics(item)

    if metrics is None:
        item["top_mode"] = "NO_DUAL_MODEL_OUTPUT"
        item["top_reason"] = "Missing Corq, Thinq or AI Match output"
        return item

    item["corq_q_probability"] = round(metrics["corq_q"], 4)
    item["thinq_q_probability"] = round(metrics["thinq_q"], 4)
    item["model_gap"] = round(metrics["model_gap"], 4)
    item["consensus_score"] = round(metrics["consensus_score"], 4)
    item["consensus_status"] = model_status_from_gap(metrics["model_gap"])
    item["top_mode"] = "TOP7_DUAL_MODEL_CONSENSUS"
    item["top_reason"] = "CorqQ/ThinqQ 80-20 dual-model consensus; model_gap <= 15%; odds >= 1.40"
    return item


def top7_sort_key(prediction: Dict[str, Any]) -> Tuple[float, float, float]:
    metrics = compute_model_metrics(prediction)
    if metrics is None:
        return (0.0, 0.0, 0.0)
    return (
        metrics["consensus_score"],
        metrics["corq_q"],
        metrics["ai_match"],
    )


def unique_key(prediction: Dict[str, Any]):
    return (
        str(prediction.get("match_id") or prediction.get("event_id") or prediction.get("match") or ""),
        str(prediction.get("pick") or ""),
    )


def build_all_predictions() -> List[Dict[str, Any]]:
    return build_core_all_predictions()


def get_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if all_predictions is None:
        all_predictions = build_all_predictions()

    required_count = env_int("TOP_N", TOP_N)

    eligible = [
        mark_top_metadata(prediction)
        for prediction in all_predictions
        if eligible_top7(prediction)
    ]

    eligible.sort(key=top7_sort_key, reverse=True)

    selected = []
    seen = set()

    for item in eligible:
        key = unique_key(item)
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= required_count:
            break

    print("TOP7 CONSENSUS COUNT:", len(selected))
    print("TOP7 MIN ODDS:", env_float("TOP_MIN_ODDS", DEFAULT_MIN_ODDS))
    print("TOP7 MAX MODEL GAP:", env_float("TOP_MAX_MODEL_GAP", DEFAULT_MAX_MODEL_GAP))

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
