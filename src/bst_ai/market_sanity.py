from typing import Any, Dict, Optional


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(str(value).replace(",", ".").strip())
        if number <= 0:
            return None
        return number
    except Exception:
        return None


def market_model_sanity(
    selected_odds: Any,
    model_probability: Any,
    *,
    pick_rating_missing: bool = False,
    opponent_rating_available: bool = False,
    high_conflict_gap: float = 0.45,
) -> Dict[str, Any]:
    """Defensive market/model sanity guard for Corq/Thinq/Douq pipelines.

    This does not decide the model probability. It only flags or blocks outputs that
    are too contradictory to the selected market price, especially no-rating outsider
    cases such as odds 8.00 with 75% model probability.
    """
    odds = _float_or_none(selected_odds)
    probability = _float_or_none(model_probability)

    if odds is None or probability is None:
        return {
            "status": "UNKNOWN",
            "reason": "Missing odds or model probability",
            "selected_odds": odds,
            "model_probability": probability,
            "market_implied_probability": None,
            "market_model_gap": None,
            "block": False,
        }

    # Accept both 0.757 and 75.7 style inputs.
    if probability > 1.0:
        probability = probability / 100.0

    implied = 1.0 / odds
    gap = probability - implied

    status = "OK"
    reason = "OK"
    block = False
    cap_probability = None

    if odds >= 7.0 and probability >= 0.60:
        status = "BLOCK_EXTREME_MARKET_CONFLICT"
        reason = "Selected odds >= 7.00 but model probability >= 60%."
        block = True
    elif odds >= 5.0 and probability >= 0.65:
        status = "BLOCK_MARKET_CONFLICT"
        reason = "Selected odds >= 5.00 but model probability >= 65%."
        block = True
    elif abs(gap) >= high_conflict_gap:
        status = "FLAG_MARKET_MODEL_GAP"
        reason = "Large gap between model probability and market implied probability."

    # Additional protection: no-rating pick vs rated/ranked opponent should not get
    # a high-probability pass when the market prices the pick as a big outsider.
    if pick_rating_missing and opponent_rating_available and odds >= 7.0:
        cap_probability = 0.30
        if probability > cap_probability:
            status = "BLOCK_NO_RATING_OUTSIDER"
            reason = "No-rating pick is a large market outsider against a rated/ranked opponent."
            block = True
    elif pick_rating_missing and opponent_rating_available and odds >= 4.0:
        cap_probability = 0.40
        if probability > cap_probability and not block:
            status = "CAP_NO_RATING_OUTSIDER"
            reason = "No-rating pick is a market outsider against a rated/ranked opponent."

    return {
        "status": status,
        "reason": reason,
        "selected_odds": round(odds, 4),
        "model_probability": round(probability, 4),
        "market_implied_probability": round(implied, 4),
        "market_model_gap": round(gap, 4),
        "cap_probability": cap_probability,
        "block": block,
    }
