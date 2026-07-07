import os
from typing import Any, Dict, List, Optional

from prediction_engine_core import build_all_predictions as build_core_all_predictions


DEFAULT_MIN_WIN = 0.55


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


def get_corq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )


def unique_key(prediction: Dict[str, Any]):
    return (
        str(
            prediction.get("match_id")
            or prediction.get("event_id")
            or prediction.get("match")
            or ""
        ),
        str(prediction.get("pick") or ""),
    )


def mark_corq_metadata(prediction: Dict[str, Any], probability: float) -> Dict[str, Any]:
    item = dict(prediction)
    item["probability"] = probability
    item["corq_display_probability"] = probability
    item["top_mode"] = "CORQ_THRESHOLD_55"
    item["top_reason"] = "Corq AI probability >= 55%"
    return item


def build_all_predictions() -> List[Dict[str, Any]]:
    return build_core_all_predictions()


def get_top_predictions(
    all_predictions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Corq public-pick policy.

    Current behavior:
    - no forced TOP5 limit by default;
    - all current Corq picks with Corq WIN >= TOP5_MIN_PROBABILITY are returned;
    - default threshold is 0.55 = 55%;
    - sorting is pure Corq WIN % descending;
    - Thinq/BsT is display/support only and is not mandatory here;
    - optional cap can be set with TOP_MAX_PICKS if needed later.
    """
    if all_predictions is None:
        all_predictions = build_all_predictions()

    min_probability = env_float("TOP5_MIN_PROBABILITY", DEFAULT_MIN_WIN)
    max_picks = env_int("TOP_MAX_PICKS", 9999)

    eligible = []

    for prediction in all_predictions or []:
        probability = get_corq_probability(prediction)

        if probability is None:
            continue

        if probability < min_probability:
            continue

        eligible.append(
            mark_corq_metadata(
                prediction,
                probability,
            )
        )

    eligible.sort(
        key=lambda item: get_corq_probability(item) or 0.0,
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

        if len(selected) >= max_picks:
            break

    print("CORQ THRESHOLD PUBLIC COUNT:", len(selected))

    for idx, item in enumerate(selected, start=1):
        print(
            "CORQ THRESHOLD PICK:",
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "prob=",
            item.get("probability"),
            "odds=",
            item.get("odds"),
            "thinq_status=",
            item.get("bst_ai_status"),
            "ai_match=",
            item.get("ai_match"),
            "mode=",
            item.get("top_mode"),
        )

    return selected


def get_daily_predictions() -> List[Dict[str, Any]]:
    return get_top_predictions()
