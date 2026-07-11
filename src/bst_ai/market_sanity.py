from typing import Any, Dict, Optional


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        text = str(value).replace(",", ".").strip()
        if not text or text in {"-", "--", "n/a", "N/A", "None", "none", "null"}:
            return None
        number = float(text)
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
    require_market: bool = True,
    high_conflict_gap: float = 0.45,
) -> Dict[str, Any]:
    """Defensive market/model sanity guard for Corq/Thinq/Douq pipelines.

    Intended usage:
    - ALL/debug may keep blocked rows for audit.
    - TOP/Telegram must exclude rows where returned block == True.

    This function does not decide the model probability. It only flags/blocks outputs
    that are too contradictory to the selected market price or missing market data.
    """
    odds = _float_or_none(selected_odds)
    probability = _float_or_none(model_probability)

    if probability is not None and probability > 1.0:
        probability = probability / 100.0

    if odds is None:
        return {
            "status": "BLOCK_NO_MARKET_DATA" if require_market else "NO_MARKET_DATA",
            "reason": "Missing selected odds / market data.",
            "selected_odds": None,
            "model_probability": round(probability, 4) if probability is not None else None,
            "market_implied_probability": None,
            "market_model_gap": None,
            "cap_probability": None,
            "block": bool(require_market),
        }

    if probability is None:
        return {
            "status": "BLOCK_NO_MODEL_PROBABILITY",
            "reason": "Missing model probability.",
            "selected_odds": round(odds, 4),
            "model_probability": None,
            "market_implied_probability": round(1.0 / odds, 4),
            "market_model_gap": None,
            "cap_probability": None,
            "block": True,
        }

    implied = 1.0 / odds
    gap = probability - implied

    status = "OK"
    reason = "OK"
    block = False
    cap_probability = None

    # Extreme contradictions: model says strong favourite, market says big outsider.
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


def apply_market_sanity_to_pick(
    pick: Dict[str, Any],
    *,
    probability_key: str = "corq_ai_probability",
    odds_key: str = "odds",
    require_market: bool = True,
) -> Dict[str, Any]:
    """Attach market sanity fields to one prediction/pick dict.

    The input dict is copied, not mutated. The caller should use sanity_block to
    exclude rows from TOP/Telegram while keeping the row in ALL/debug.
    """
    item = dict(pick or {})
    sanity = market_model_sanity(
        selected_odds=item.get(odds_key) or item.get("selected_odds") or item.get("pick_odds"),
        model_probability=item.get(probability_key) or item.get("probability") or item.get("model_probability"),
        pick_rating_missing=bool(item.get("pick_rating_missing") or item.get("pick_missing_rating")),
        opponent_rating_available=bool(item.get("opponent_rating_available") or item.get("opponent_has_rank") or item.get("opponent_has_rating")),
        require_market=require_market,
    )
    item["sanity_status"] = sanity.get("status")
    item["sanity_reason"] = sanity.get("reason")
    item["sanity_block"] = sanity.get("block")
    item["market_implied_probability"] = sanity.get("market_implied_probability")
    item["market_model_gap"] = sanity.get("market_model_gap")
    item["market_sanity"] = sanity
    return item
