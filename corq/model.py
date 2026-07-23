"""CORQ scoring model.

CORQ creates its own raw probability and then applies THINQ intelligence adjustment.
This file intentionally exposes both:
- score_prediction(...)
- CorqModel.score(...)

Reason: corq/engine.py imports CorqModel.
"""

from __future__ import annotations

from typing import Any, Dict

from .rules import safe_float, normalize_probability

MAX_THINQ_ADJUSTMENT = 0.06


def _clamp(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return max(low, min(high, value))


def implied_probability(odds: Any) -> float | None:
    val = safe_float(odds)
    if val is None or val <= 1.0:
        return None
    return 1.0 / val


def _extract_thinq_adjustment(thinq: Dict[str, Any] | None, prediction: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
    if prediction.get("thinq_total_adjustment") is not None:
        val = safe_float(prediction.get("thinq_total_adjustment"), 0.0) or 0.0
        val = max(-MAX_THINQ_ADJUSTMENT, min(MAX_THINQ_ADJUSTMENT, val))
        return val, {"legacy_thinq_total_adjustment": val}

    if not isinstance(thinq, dict):
        thinq = prediction.get("thinq") if isinstance(prediction.get("thinq"), dict) else {}

    edges = thinq.get("edges") if isinstance(thinq.get("edges"), dict) else {}
    contributions: Dict[str, float] = {}
    total = 0.0
    for key, weight in (
        ("elo_edge", 1.00),
        ("surface_edge", 0.60),
        ("history_edge", 0.55),
        ("h2h_edge", 0.80),
        ("form_edge", 0.50),
        ("recent_form_edge", 0.50),
        ("surface_form_edge", 0.60),
    ):
        edge = safe_float(edges.get(key), 0.0) or 0.0
        if edge:
            value = edge * weight
            contributions[key] = round(value, 4)
            total += value

    total = max(-MAX_THINQ_ADJUSTMENT, min(MAX_THINQ_ADJUSTMENT, total))
    return total, contributions


def _raw_probability_from_prediction(prediction: Dict[str, Any]) -> float:
    raw_probability = normalize_probability(
        prediction.get("corq_raw_probability")
        or prediction.get("corq_probability")
        or prediction.get("corq_ai_probability")
        or prediction.get("model_probability")
        or prediction.get("probability")
    )
    if raw_probability is not None:
        return raw_probability

    # Odds-only fallback. Keep it realistic: implied probability, not artificial 35% for huge underdogs.
    pick_odds = safe_float(prediction.get("pick_odds") or prediction.get("odds"))
    implied = implied_probability(pick_odds)
    if implied is not None:
        return _clamp(implied - 0.015, 0.03, 0.92)
    return 0.50


def score_prediction(match: Dict[str, Any], thinq: Dict[str, Any] | None = None) -> Dict[str, Any]:
    prediction = dict(match)
    raw_probability = _raw_probability_from_prediction(prediction)
    thinq_adjustment, contributions = _extract_thinq_adjustment(thinq, prediction)
    probability_before_risk = _clamp(raw_probability + thinq_adjustment)

    edge = 0.0
    pick_odds = safe_float(prediction.get("pick_odds") or prediction.get("odds"))
    if pick_odds and pick_odds > 1.0:
        edge = probability_before_risk - (1.0 / pick_odds)

    edge_bonus = min(max(edge, 0.0) * 0.25, 0.02)

    # Risk penalty may already be calculated elsewhere; keep default 0.
    risk_penalty = safe_float(prediction.get("corq_risk_penalty"), 0.0) or 0.0
    corq_probability = _clamp(probability_before_risk - risk_penalty)
    adjusted_score = _clamp(corq_probability + edge_bonus - risk_penalty)

    prediction.update({
        "corq_raw_probability": round(raw_probability, 4),
        "thinq_total_adjustment": round(thinq_adjustment, 4),
        "corq_thinq_contributions": contributions,
        "corq_probability": round(corq_probability, 4),
        "probability": round(corq_probability, 4),
        "corq_edge": round(edge, 4),
        "corq_edge_bonus": round(edge_bonus, 4),
        "corq_risk_penalty": round(risk_penalty, 4),
        "corq_adjusted_score": round(adjusted_score, 4),
    })
    return prediction


class CorqModel:
    """Small class wrapper used by corq.engine."""

    def score(self, match: Dict[str, Any], thinq: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return score_prediction(match, thinq)


def score_predictions(matches, thinq_by_key=None):
    out = []
    thinq_by_key = thinq_by_key or {}
    for match in matches:
        key = match.get("match_id") or match.get("event_id") or match.get("eventId") or match.get("match")
        out.append(score_prediction(match, thinq_by_key.get(key)))
    return out
