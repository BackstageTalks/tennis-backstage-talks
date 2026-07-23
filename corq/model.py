"""CORQ scoring model.

CORQ creates its own raw probability and then applies THINQ intelligence adjustment.
"""

from __future__ import annotations

from typing import Any, Dict

from .rules import normalize_probability, safe_float

MAX_THINQ_ADJUSTMENT = 0.06


def _clamp(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return max(low, min(high, value))


def _extract_thinq_adjustment(thinq: Dict[str, Any] | None, prediction: Dict[str, Any]) -> float:
    if prediction.get("thinq_total_adjustment") is not None:
        val = safe_float(prediction.get("thinq_total_adjustment"), 0.0) or 0.0
        return max(-MAX_THINQ_ADJUSTMENT, min(MAX_THINQ_ADJUSTMENT, val))

    if not isinstance(thinq, dict):
        thinq = prediction.get("thinq") if isinstance(prediction.get("thinq"), dict) else {}

    edges = thinq.get("edges") if isinstance(thinq.get("edges"), dict) else {}
    total = 0.0
    for key in ("elo_edge", "surface_edge", "history_edge", "h2h_edge", "form_edge"):
        total += safe_float(edges.get(key), 0.0) or 0.0
    return max(-MAX_THINQ_ADJUSTMENT, min(MAX_THINQ_ADJUSTMENT, total))


def score_prediction(match: Dict[str, Any], thinq: Dict[str, Any] | None = None) -> Dict[str, Any]:
    prediction = dict(match)

    raw_probability = normalize_probability(
        prediction.get("corq_raw_probability")
        or prediction.get("corq_probability")
        or prediction.get("corq_ai_probability")
        or prediction.get("probability")
    )

    if raw_probability is None:
        # Conservative fallback until full model is calibrated.
        pick_odds = safe_float(prediction.get("pick_odds") or prediction.get("odds"))
        if pick_odds and pick_odds > 1.0:
            raw_probability = _clamp(1.0 / pick_odds)
        else:
            raw_probability = 0.50

    thinq_adjustment = _extract_thinq_adjustment(thinq, prediction)
    final_probability = _clamp(raw_probability + thinq_adjustment)

    edge = 0.0
    pick_odds = safe_float(prediction.get("pick_odds") or prediction.get("odds"))
    if pick_odds and pick_odds > 1.0:
        implied = 1.0 / pick_odds
        edge = final_probability - implied

    edge_bonus = min(max(edge, 0.0) * 0.25, 0.02)
    risk_penalty = safe_float(prediction.get("corq_risk_penalty"), 0.0) or 0.0
    adjusted_score = final_probability + edge_bonus - risk_penalty

    prediction.update({
        "corq_raw_probability": raw_probability,
        "thinq_total_adjustment": thinq_adjustment,
        "corq_probability": final_probability,
        "probability": final_probability,
        "corq_edge": edge,
        "corq_edge_bonus": edge_bonus,
        "corq_risk_penalty": risk_penalty,
        "corq_adjusted_score": adjusted_score,
    })
    return prediction


def score_predictions(matches, thinq_by_key=None):
    out = []
    thinq_by_key = thinq_by_key or {}
    for match in matches:
        key = match.get("match_id") or match.get("event_id") or match.get("eventId") or match.get("match")
        out.append(score_prediction(match, thinq_by_key.get(key)))
    return out
