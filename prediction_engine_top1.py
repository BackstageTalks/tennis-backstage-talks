import os
from typing import Any, Dict, List, Optional

from prediction_engine_core import build_all_predictions as build_core_all_predictions


TOP_N = 5


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


def normalize_status(value: Any) -> str:
    return str(value or "").upper().strip()


def has_odds(prediction: Dict[str, Any]) -> bool:
    odds = safe_float(prediction.get("odds"))
    return odds is not None and odds > 1.0


def is_bst_ok(prediction: Dict[str, Any]) -> bool:
    return normalize_status(prediction.get("bst_ai_status")) == "OK"


def has_ai_match(prediction: Dict[str, Any]) -> bool:
    return safe_float(prediction.get("ai_match")) is not None


def apply_top_metadata(prediction: Dict[str, Any], mode: str, reason: str) -> Dict[str, Any]:
    item = dict(prediction)
    item["top_mode"] = mode
    item["top_reason"] = reason
    return item


def top5_score(prediction: Dict[str, Any]) -> float:
    """
    Conservative TOP5 score.

    This intentionally avoids selecting very high odds purely because of market price.
    BsT AI must be OK before a pick can enter TOP5.
    """
    probability = safe_float(prediction.get("probability")) or 0.0
    ai_match = safe_float(prediction.get("ai_match")) or 0.0
    odds = safe_float(prediction.get("odds")) or 0.0

    # Value is useful, but capped so odds 8.00 cannot dominate the list.
    capped_odds = min(odds, env_float("TOP5_SCORE_ODDS_CAP", 3.0))
    value_component = max(capped_odds - 1.0, 0.0) * 0.03

    return probability + (ai_match / 100.0) * 0.15 + value_component


def eligible_primary(prediction: Dict[str, Any]) -> bool:
    min_odds = env_float("TOP5_MIN_ODDS", 1.30)
    max_odds = env_float("TOP5_MAX_ODDS", 5.00)
    min_probability = env_float("TOP5_MIN_PROBABILITY", 0.55)
    min_ai_match = env_float("TOP5_MIN_AI_MATCH", 0.0)

    odds = safe_float(prediction.get("odds"))
    probability = safe_float(prediction.get("probability"))
    ai_match = safe_float(prediction.get("ai_match"))

    if not has_odds(prediction):
        return False
    if not is_bst_ok(prediction):
        return False
    if not has_ai_match(prediction):
        return False
    if odds is None or odds < min_odds or odds > max_odds:
        return False
    if probability is None or probability < min_probability:
        return False
    if ai_match is None or ai_match < min_ai_match:
        return False

    return True


def eligible_bst_relaxed(prediction: Dict[str, Any]) -> bool:
    """
    Secondary safety tier if strict filters return fewer than TOP_N.
    Still requires BsT OK and odds; only relaxes probability/odds thresholds a bit.
    """
    min_odds = env_float("TOP5_RELAXED_MIN_ODDS", 1.15)
    max_odds = env_float("TOP5_RELAXED_MAX_ODDS", 6.00)

    odds = safe_float(prediction.get("odds"))

    if not has_odds(prediction):
        return False
    if not is_bst_ok(prediction):
        return False
    if not has_ai_match(prediction):
        return False
    if odds is None or odds < min_odds or odds > max_odds:
        return False

    return True


def deduplicate_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []

    for prediction in predictions:
        key = (
            str(prediction.get("match_id") or prediction.get("event_id") or ""),
            str(prediction.get("match") or ""),
            str(prediction.get("pick") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(prediction)

    return output


def build_all_predictions() -> List[Dict[str, Any]]:
    return build_core_all_predictions()


def get_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Current TOP5 policy:
    - BsT AI must be OK.
    - AI Match must be available.
    - Odds must be available.
    - Very high odds are capped/filtered so odds 8.00 does not enter TOP5 only because of price.

    The old behavior allowed picks with missing BsT AI and very high odds to enter TOP5.
    This file prevents that while keeping the rest of the Corq AI model unchanged.
    """
    if all_predictions is None:
        all_predictions = build_all_predictions()

    required_count = env_int("TOP_N", TOP_N)

    primary = [
        apply_top_metadata(
            prediction,
            "BST_REQUIRED_PRIMARY",
            "BsT AI OK + AI Match available + usable odds",
        )
        for prediction in all_predictions
        if eligible_primary(prediction)
    ]
    primary.sort(key=top5_score, reverse=True)

    selected = primary[:required_count]

    if len(selected) < required_count:
        selected_keys = {
            (
                item.get("match_id") or item.get("event_id") or item.get("match"),
                item.get("pick"),
            )
            for item in selected
        }

        relaxed = []
        for prediction in all_predictions:
            key = (
                prediction.get("match_id") or prediction.get("event_id") or prediction.get("match"),
                prediction.get("pick"),
            )
            if key in selected_keys:
                continue
            if eligible_bst_relaxed(prediction):
                relaxed.append(
                    apply_top_metadata(
                        prediction,
                        "BST_REQUIRED_RELAXED",
                        "BsT AI OK required; relaxed odds/probability fallback",
                    )
                )

        relaxed.sort(key=top5_score, reverse=True)
        selected.extend(relaxed[: max(required_count - len(selected), 0)])

    selected = deduplicate_predictions(selected)

    print("TOP5 BST REQUIRED COUNT:", len(selected))
    for idx, item in enumerate(selected[:required_count], start=1):
        print(
            "TOP5 BST REQUIRED PICK:",
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "prob=",
            item.get("probability"),
            "odds=",
            item.get("odds"),
            "bst=",
            item.get("bst_ai_status"),
            "ai_match=",
            item.get("ai_match"),
            "mode=",
            item.get("top_mode"),
        )

    return selected[:required_count]


def get_daily_predictions() -> List[Dict[str, Any]]:
    return get_top_predictions()
