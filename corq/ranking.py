"""CORQ ranking utilities.

TOP7 is not a model. TOP7 is only the first N records from CORQ ranking.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from .rules import apply_corq_eligibility, normalize_probability, safe_float

TOP_N = 7


def score_value(prediction: Dict[str, Any]) -> float:
    for key in (
        "corq_adjusted_score",
        "corq_top_score",
        "corq_q_probability",
        "corq_thinq_adjusted_probability",
        "corq_probability",
        "corq_ai_probability",
        "probability",
    ):
        val = prediction.get(key)
        if key.endswith("probability") or key in {"corq_ai_probability", "probability"}:
            prob = normalize_probability(val)
            if prob is not None:
                return prob
        else:
            number = safe_float(val)
            if number is not None:
                return number
    return 0.0


def corq_rank_tuple(prediction: Dict[str, Any]) -> Tuple[float, float, float]:
    score = score_value(prediction)
    prob = normalize_probability(prediction.get("corq_probability") or prediction.get("probability")) or 0.0
    odds = safe_float(prediction.get("pick_odds") or prediction.get("odds")) or 0.0
    # Higher score first, then higher probability, then slightly higher odds.
    return (score, prob, odds)


def rank_corq_predictions(predictions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    rejected_count = 0
    rejected_by_reason: Dict[str, int] = {}

    for raw in predictions:
        prediction = apply_corq_eligibility(dict(raw))
        if prediction.get("eligible_for_corq"):
            enriched.append(prediction)
        else:
            rejected_count += 1
            for reason in prediction.get("corq_reject_reasons", []):
                rejected_by_reason[reason] = rejected_by_reason.get(reason, 0) + 1

    ranked = sorted(enriched, key=corq_rank_tuple, reverse=True)
    for idx, prediction in enumerate(ranked, start=1):
        prediction["corq_rank"] = idx
        prediction["corq_rank_score"] = score_value(prediction)

    print("CORQ RANKING SUMMARY:", {
        "eligible": len(ranked),
        "rejected": rejected_count,
        "rejected_by_reason": rejected_by_reason,
    })
    return ranked


def select_top7_from_corq_ranking(ranked_predictions: Iterable[Dict[str, Any]], top_n: int = TOP_N) -> List[Dict[str, Any]]:
    top = list(ranked_predictions)[:top_n]
    for idx, prediction in enumerate(top, start=1):
        prediction["top7_rank"] = idx
        prediction["top7_source"] = "CORQ_RANKING"
    return top

# Backward-compatible aliases
rank_predictions = rank_corq_predictions
get_top_predictions = select_top7_from_corq_ranking
