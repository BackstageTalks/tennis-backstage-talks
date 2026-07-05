from __future__ import annotations

from statistics import median
from typing import Any, Dict, List, Optional

from .provider import fetch_marq_market_data


def _empty_marq(
    reason: str = "missing_data",
    event_id: Optional[str] = None,
    outcome_key: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "marq_ai_score": None,
        "marq_ai_signal": "NO MARKET DATA",
        "marq_ai_direction": "NO_MARKET_DATA",
        "marq_ai_strength": 0,
        "marq_ai_consistency": 0,
        "marq_ai_reason": reason,
        "marq_event_id": event_id,
        "marq_outcome_key": outcome_key,
        "marq_source": None,
        "marq_provider_count": 0,
        "marq_market_spread_pct": None,
        "marq_market_median_odds": None,
        "marq_outlier_count": 0,
    }


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
        return number if number > 1 else None
    except Exception:
        return None


def _quote_pick_odds(quote: Dict[str, Any], outcome_key: str, match_direction: str) -> Optional[float]:
    if match_direction == "direct":
        value = quote.get("odds_1") if outcome_key == "od1" else quote.get("odds_2")
    else:
        value = quote.get("odds_2") if outcome_key == "od1" else quote.get("odds_1")
    return _as_float(value)


def _market_quality_from_odds(pick_odds_values: List[float]) -> Dict[str, Any]:
    values = [float(v) for v in pick_odds_values if _as_float(v) is not None]
    count = len(values)

    if count == 0:
        return {
            "signal": "NO MARKET DATA",
            "score": None,
            "direction": "NO_MARKET_DATA",
            "strength": 0,
            "consistency": 0,
            "provider_count": 0,
            "median_odds": None,
            "spread_pct": None,
            "outlier_count": 0,
        }

    med = float(median(values))
    minimum = min(values)
    maximum = max(values)
    spread_pct = ((maximum - minimum) / med) * 100 if med > 0 else None

    outliers = [v for v in values if med > 0 and abs(v - med) / med >= 0.12]
    outlier_count = len(outliers)

    if count <= 2:
        signal = "THIN MARKET"
        score = 35
        direction = "LIMITED_MARKET_SAMPLE"
        strength = 25
        consistency = 35
    else:
        non_outliers = [v for v in values if v not in outliers]
        non_outlier_spread = None
        if len(non_outliers) >= 2:
            non_med = float(median(non_outliers))
            non_outlier_spread = ((max(non_outliers) - min(non_outliers)) / non_med) * 100 if non_med > 0 else None

        if outlier_count >= 1 and len(non_outliers) >= 3 and (non_outlier_spread is not None and non_outlier_spread <= 6.0):
            signal = "OUTLIER"
            score = 60
            direction = "MARKET_HAS_OUTLIER"
            strength = 55
            consistency = 55
        elif spread_pct is not None and spread_pct <= 6.0:
            signal = "CONSENSUS"
            score = 80
            direction = "MARKET_CONSENSUS"
            strength = 80
            consistency = 85
        elif spread_pct is not None and spread_pct <= 12.0:
            signal = "CONSENSUS"
            score = 70
            direction = "MARKET_SOFT_CONSENSUS"
            strength = 65
            consistency = 70
        else:
            signal = "MIXED MARKET"
            score = 45
            direction = "MARKET_DISAGREEMENT"
            strength = 55
            consistency = 40

    return {
        "signal": signal,
        "score": score,
        "direction": direction,
        "strength": strength,
        "consistency": consistency,
        "provider_count": count,
        "median_odds": round(med, 4),
        "spread_pct": round(spread_pct, 2) if spread_pct is not None else None,
        "outlier_count": outlier_count,
    }


def build_marq_from_match(
    player1: str,
    player2: str,
    date_only: str,
    pick: Optional[str] = None,
    odds_player1: Optional[float] = None,
    odds_player2: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Marq AI = market quality / market agreement layer.

    Signals:
    - CONSENSUS
    - MIXED MARKET
    - OUTLIER
    - THIN MARKET
    - NO MARKET DATA
    """

    try:
        market_data = fetch_marq_market_data(
            player1=player1,
            player2=player2,
            date_only=date_only,
            pick=pick,
            odds_player1=odds_player1,
            odds_player2=odds_player2,
        )
    except Exception as exc:
        print(f"MARQ AI ERROR: provider failed {player1} vs {player2} {date_only}: {exc}")
        return _empty_marq(reason="provider_error")

    if not market_data:
        print(f"MARQ DEBUG: market_data missing {player1} vs {player2} {date_only}")
        return _empty_marq(reason="market_data_missing")

    outcome_key = market_data.get("pick_outcome_key") or "od1"
    match_direction = market_data.get("match_direction") or "direct"
    quotes = market_data.get("market_quotes") or []

    pick_odds_values = []
    for quote in quotes:
        if isinstance(quote, dict):
            value = _quote_pick_odds(quote, outcome_key, match_direction)
            if value is not None:
                pick_odds_values.append(value)

    quality = _market_quality_from_odds(pick_odds_values)

    print(
        "MARQ DEBUG: market quality "
        f"source={market_data.get('source')} event_id={market_data.get('event_id')} "
        f"pick={pick} providers={quality.get('provider_count')} "
        f"median_odds={quality.get('median_odds')} spread_pct={quality.get('spread_pct')} "
        f"outliers={quality.get('outlier_count')} signal={quality.get('signal')}"
    )

    if quality.get("signal") == "NO MARKET DATA":
        return _empty_marq(
            reason="market_quality_unavailable",
            event_id=market_data.get("event_id"),
            outcome_key=outcome_key,
        )

    return {
        "marq_ai_score": quality.get("score"),
        "marq_ai_signal": quality.get("signal"),
        "marq_ai_direction": quality.get("direction"),
        "marq_ai_strength": quality.get("strength"),
        "marq_ai_consistency": quality.get("consistency"),
        "marq_ai_reason": "ok",
        "marq_event_id": market_data.get("event_id"),
        "marq_outcome_key": outcome_key,
        "marq_source": market_data.get("source"),
        "marq_market_name": "market_quality",
        "marq_provider_count": quality.get("provider_count"),
        "marq_market_spread_pct": quality.get("spread_pct"),
        "marq_market_median_odds": quality.get("median_odds"),
        "marq_outlier_count": quality.get("outlier_count"),
        # Backward-compatible fields used by old logs/render/debug.
        "marq_opening": quality.get("median_odds"),
        "marq_latest": quality.get("median_odds"),
        "marq_market_move_pct": None,
        "marq_probability_change_pp": None,
        "marq_opponent_move_pct": None,
    }
