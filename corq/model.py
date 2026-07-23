from __future__ import annotations
from typing import Any, Dict
from .schema import clamp, to_float, implied_probability
from .rules import pick_odds

class CorqModel:
    def __init__(self, max_thinq_adjustment: float = 0.06):
        self.max_thinq_adjustment = max_thinq_adjustment

    def raw_probability(self, match: Dict[str, Any]) -> float:
        for key in ["corq_raw_probability", "corq_ai_probability", "probability", "model_probability"]:
            value = to_float(match.get(key))
            if value is not None:
                return value if value <= 1.0 else value / 100.0
        implied = implied_probability(pick_odds(match))
        if implied is not None:
            return clamp(implied + 0.015, 0.35, 0.82)
        return 0.50

    def thinq_adjustment(self, thinq: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        edges = thinq.get("edges") or {}
        confidence = clamp(to_float(thinq.get("confidence"), 0.0) or 0.0, 0.0, 1.0)
        contributions: Dict[str, float] = {}
        for key in ["elo_edge", "h2h_edge", "surface_edge", "history_edge", "opponent_quality_edge"]:
            contributions[key] = (to_float(edges.get(key), 0.0) or 0.0) * confidence
        total = clamp(sum(contributions.values()), -self.max_thinq_adjustment, self.max_thinq_adjustment)
        return total, contributions

    def score(self, match: Dict[str, Any], thinq: Dict[str, Any] | None = None) -> Dict[str, Any]:
        thinq = thinq or {}
        raw = self.raw_probability(match)
        adjustment, contributions = self.thinq_adjustment(thinq)
        probability = clamp(raw + adjustment, 0.01, 0.99)
        implied = implied_probability(pick_odds(match)) or 0.0
        edge = probability - implied if implied else 0.0
        edge_bonus = clamp(edge * 0.25, -0.02, 0.02)
        risk_penalty = 0.0
        risk_flags = []
        odds = pick_odds(match)
        if odds is not None and odds < 1.60 and probability >= 0.75 and edge >= 0.12:
            risk_penalty += 0.06
            risk_flags.append("LOW_ODDS_OVERCONFIDENCE")
        adjusted_score = clamp(probability + edge_bonus - risk_penalty, 0.0, 1.0)
        result = dict(match)
        result.update({
            "corq_raw_probability": raw,
            "thinq_total_adjustment": adjustment,
            "corq_thinq_contributions": contributions,
            "corq_probability": probability,
            "probability": probability,
            "corq_edge": edge,
            "corq_edge_bonus": edge_bonus,
            "corq_risk_penalty": risk_penalty,
            "corq_risk_flags": risk_flags,
            "corq_adjusted_score": adjusted_score,
            "corq_top_score": adjusted_score,
        })
        return result
