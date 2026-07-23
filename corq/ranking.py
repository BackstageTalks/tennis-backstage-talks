"""CORQ ranking utilities.

Critical production rule:
- TOP7 is not a model.
- TOP7 is only the first N records from CORQ ranking.
- CORQ ranking must contain at most one selected pick per real match/event.

Why this exists:
Candidate expansion creates one candidate for player1 and one candidate for player2.
That is useful for CORQ side selection, but both sides of the same match must never
enter TOP7 together.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple
import re

from .rules import apply_corq_eligibility, normalize_probability, safe_float

TOP_N = 7


def _clean_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def match_identity(prediction: Dict[str, Any]) -> str:
    """Stable identity for one real match.

    Prefer provider ids. Fall back to sorted player names + tournament/date.
    This prevents both sides of the same event from entering CORQ ranking.
    """
    for key in ("event_id", "eventId", "match_id", "matchId", "id"):
        value = prediction.get(key)
        if value not in (None, ""):
            return f"event:{value}"

    p1 = _clean_name(prediction.get("player1"))
    p2 = _clean_name(prediction.get("player2"))
    players = "__".join(sorted([p1, p2]))
    tournament = _clean_name(prediction.get("tournament"))
    time_key = str(prediction.get("time") or prediction.get("match_time") or prediction.get("start_time") or "")[:10]
    return f"pair:{players}:{tournament}:{time_key}"


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


def _dedupe_one_pick_per_match(eligible: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only the strongest CORQ candidate for each real match/event."""
    best_by_match: Dict[str, Dict[str, Any]] = {}
    dropped_count = 0

    for prediction in eligible:
        key = match_identity(prediction)
        current = best_by_match.get(key)
        if current is None or corq_rank_tuple(prediction) > corq_rank_tuple(current):
            if current is not None:
                dropped_count += 1
            chosen = dict(prediction)
            chosen["corq_match_identity"] = key
            chosen["corq_candidate_selected"] = True
            best_by_match[key] = chosen
        else:
            dropped_count += 1

    if dropped_count:
        print("CORQ DEDUPE SUMMARY:", {"dropped_opposite_side_candidates": dropped_count})

    return list(best_by_match.values())


def rank_corq_predictions(predictions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible: List[Dict[str, Any]] = []
    rejected_count = 0
    rejected_by_reason: Dict[str, int] = {}

    for raw in predictions:
        prediction = apply_corq_eligibility(dict(raw))
        if prediction.get("eligible_for_corq"):
            eligible.append(prediction)
        else:
            rejected_count += 1
            for reason in prediction.get("corq_reject_reasons", []):
                rejected_by_reason[reason] = rejected_by_reason.get(reason, 0) + 1

    one_per_match = _dedupe_one_pick_per_match(eligible)
    ranked = sorted(one_per_match, key=corq_rank_tuple, reverse=True)

    for idx, prediction in enumerate(ranked, start=1):
        prediction["corq_rank"] = idx
        prediction["corq_rank_score"] = score_value(prediction)

    print("CORQ RANKING SUMMARY:", {
        "eligible_candidates": len(eligible),
        "eligible_matches_after_dedupe": len(ranked),
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


# Backward-compatible aliases used by corq.engine and earlier files.
rank_predictions = rank_corq_predictions
get_top_predictions = select_top7_from_corq_ranking
top_n_from_ranked = select_top7_from_corq_ranking
