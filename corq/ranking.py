from __future__ import annotations
from typing import Any, Dict, Iterable, List
from .schema import to_float
from .rules import eligible_for_corq

def rank_key(prediction: Dict[str, Any]):
    return (
        to_float(prediction.get("corq_adjusted_score"), -1.0) or -1.0,
        to_float(prediction.get("corq_probability"), -1.0) or -1.0,
        to_float(prediction.get("corq_edge"), -99.0) or -99.0,
    )

def rank_predictions(predictions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = []
    for item in predictions:
        item = dict(item)
        ok, reasons = eligible_for_corq(item)
        item["corq_eligible"] = ok
        item["corq_rejected_reasons"] = reasons
        if ok:
            eligible.append(item)
    ranked = sorted(eligible, key=rank_key, reverse=True)
    for idx, item in enumerate(ranked, start=1):
        item["corq_rank"] = idx
    return ranked

def top_n_from_ranked(ranked: List[Dict[str, Any]], n: int = 7) -> List[Dict[str, Any]]:
    return list(ranked[:n])
