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


def is_bst_ok(prediction: Dict[str, Any]) -> bool:
    return normalize_status(prediction.get("bst_ai_status")) == "OK"


def has_ai_match(prediction: Dict[str, Any]) -> bool:
    return safe_float(prediction.get("ai_match")) is not None


def has_valid_odds(prediction: Dict[str, Any]) -> bool:
    odds = safe_float(prediction.get("odds"))
    return odds is not None and odds > 1.0


def eligible_top5(prediction: Dict[str, Any]) -> bool:
    """
    Main TOP5 eligibility.

    IMPORTANT:
    BsT AI is NOT mandatory here. This keeps candidate coverage wide.
    If BsT exists, it is used only as a soft quality boost in top5_score().
    """
    min_odds = env_float("TOP5_MIN_ODDS", 1.30)
    max_odds = env_float("TOP5_MAX_ODDS", 5.00)
    min_probability = env_float("TOP5_MIN_PROBABILITY", 0.55)

    odds = safe_float(prediction.get("odds"))
    probability = safe_float(prediction.get("probability"))

    if not has_valid_odds(prediction):
        return False
    if odds is None or odds < min_odds or odds > max_odds:
        return False
    if probability is None or probability < min_probability:
        return False

    return True


def top5_score(prediction: Dict[str, Any]) -> float:
    """
    Corq-first TOP5 score with optional BsT support.

    - Corq probability remains the main driver.
    - Odds value is capped, so high prices do not dominate.
    - BsT OK / AI Match adds a soft bonus only when available.
    - Missing BsT does not exclude the pick.
    """
    probability = safe_float(prediction.get("probability")) or 0.0
    odds = safe_float(prediction.get("odds")) or 0.0
    ai_match = safe_float(prediction.get("ai_match"))

    capped_odds = min(odds, env_float("TOP5_SCORE_ODDS_CAP", 3.0))
    value_component = max(capped_odds - 1.0, 0.0) * 0.03

    bst_bonus = 0.0
    if is_bst_ok(prediction) and ai_match is not None:
        # Max bonus approximately +0.10 if AI Match is 100%.
        bst_bonus = (ai_match / 100.0) * env_float("TOP5_BST_SOFT_BONUS", 0.10)

    return probability + value_component + bst_bonus


def mark_top_metadata(prediction: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(prediction)
    if is_bst_ok(item) and has_ai_match(item):
        item["top_mode"] = "CORQ_PRIMARY_BST_SUPPORTED"
        item["top_reason"] = "Corq primary selection; BsT AI available as support signal"
    else:
        item["top_mode"] = "CORQ_PRIMARY_NO_BST"
        item["top_reason"] = "Corq primary selection; BsT AI unavailable, not excluded"
    return item


def unique_key(prediction: Dict[str, Any]):
    return (
        str(prediction.get("match_id") or prediction.get("event_id") or prediction.get("match") or ""),
        str(prediction.get("pick") or ""),
    )


def build_all_predictions() -> List[Dict[str, Any]]:
    return build_core_all_predictions()


def get_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    TOP5 policy:
    - odds required
    - min odds default 1.30
    - max odds default 5.00
    - minimum Corq probability default 55%
    - BsT AI is displayed if available, but NOT mandatory
    """
    if all_predictions is None:
        all_predictions = build_all_predictions()

    required_count = env_int("TOP_N", TOP_N)

    eligible = [mark_top_metadata(p) for p in all_predictions if eligible_top5(p)]
    eligible.sort(key=top5_score, reverse=True)

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

    print("TOP5 SOFT BST COUNT:", len(selected))
    for idx, item in enumerate(selected, start=1):
        print(
            "TOP5 SOFT BST PICK:", idx,
            item.get("pick"), "vs", item.get("opponent"),
            "prob=", item.get("probability"),
            "odds=", item.get("odds"),
            "bst=", item.get("bst_ai_status"),
            "ai_match=", item.get("ai_match"),
            "mode=", item.get("top_mode"),
        )

    return selected


def get_daily_predictions() -> List[Dict[str, Any]]:
    return get_top_predictions()
