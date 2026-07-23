from __future__ import annotations
from typing import Any, Dict
from .rules import to_float, is_eligible_for_corq, risk_penalty


def clamp(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return max(low, min(high, value))


def implied_probability(odds: Any) -> float | None:
    val = to_float(odds)
    if not val or val <= 1.0:
        return None
    return 1.0 / val


class CorqModel:
    """CORQ CORE output model.

    CORQ builds `corq_raw_probability`, applies THINQ adjustment and risk penalties,
    then produces `corq_adjusted_score` for ranking.
    """

    def score(self, match: Dict[str, Any], thinq: Dict[str, Any] | None = None) -> Dict[str, Any]:
        thinq = thinq or match.get("thinq") or {}
        eligible, reject_reasons = is_eligible_for_corq(match)
        pick_odds = match.get("pick_odds") or match.get("odds")

        raw = to_float(match.get("corq_raw_probability"))
        if raw is None:
            raw = to_float(match.get("corq_ai_probability"))
        if raw is None:
            raw = to_float(match.get("probability"))
        if raw is not None and raw > 1.0:
            raw = raw / 100.0

        # Odds-only fallback must not make huge underdogs look like 35% picks.
        # Use implied probability with a small conservative margin adjustment.
        if raw is None:
            implied = implied_probability(pick_odds)
            raw = implied - 0.015 if implied is not None else 0.50
            raw = clamp(raw, 0.03, 0.92)

        edges = thinq.get("edges") or match.get("thinq_edges") or {}
        thinq_adjustment = 0.0
        contributions = {}
        for key, weight in [
            ("elo_edge", 1.00),
            ("h2h_edge", 0.80),
            ("surface_form_edge", 0.60),
            ("recent_form_edge", 0.50),
        ]:
            edge = to_float(edges.get(key), 0.0) or 0.0
            if edge:
                value = edge * weight
                contributions[key] = round(value, 4)
                thinq_adjustment += value
        thinq_adjustment = clamp(thinq_adjustment, -0.06, 0.06)

        probability_before_risk = clamp(raw + thinq_adjustment, 0.01, 0.99)
        penalty, risk_flags = risk_penalty(match, probability_before_risk)
        corq_probability = clamp(probability_before_risk - penalty, 0.01, 0.99)

        odds = to_float(pick_odds)
        market_edge = None
        if odds and odds > 1:
            market_edge = corq_probability - (1.0 / odds)
        edge_bonus = min(max((market_edge or 0.0) * 0.25, 0.0), 0.02)
        corq_adjusted_score = clamp(corq_probability + edge_bonus - penalty, 0.01, 0.99)

        output = dict(match)
        output.update({
            "corq_raw_probability": round(raw, 4),
            "thinq_total_adjustment": round(thinq_adjustment, 4),
            "corq_thinq_contributions": contributions,
            "corq_probability": round(corq_probability, 4),
            "probability": round(corq_probability, 4),
            "corq_edge": round(market_edge, 4) if market_edge is not None else None,
            "corq_edge_bonus": round(edge_bonus, 4),
            "corq_risk_penalty": round(penalty, 4),
            "corq_risk_flags": risk_flags,
            "corq_adjusted_score": round(corq_adjusted_score, 4),
            "corq_reject_reasons": reject_reasons,
            "corq_eligible": eligible,
            "thinq": thinq,
        })
        return output
