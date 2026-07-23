from __future__ import annotations
from typing import Any, Dict, List
from .rules import to_float


def rank_key(prediction: Dict[str, Any]) -> tuple:
    return (
        to_float(prediction.get("corq_adjusted_score"), 0.0) or 0.0,
        to_float(prediction.get("corq_probability"), 0.0) or 0.0,
        to_float(prediction.get("corq_edge"), -9.0) or -9.0,
    )


def rank_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = [p for p in predictions if p.get("corq_eligible")]
    ranked = sorted(eligible, key=rank_key, reverse=True)
    for idx, item in enumerate(ranked, 1):
        item["corq_rank"] = idx
    return ranked


def top_n_from_ranked(ranked: List[Dict[str, Any]], n: int = 7) -> List[Dict[str, Any]]:
    return ranked[:n]
