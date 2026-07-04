from __future__ import annotations

from typing import Any, Dict, Optional

from .provider import fetch_marq_market_data


def _empty_marq(
    reason: str = "missing_data",
    event_id: Optional[str] = None,
    outcome_key: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "marq_ai_score": None,
        "marq_ai_signal": "NEUTRAL",
        "marq_ai_direction": "NEUTRAL",
        "marq_ai_strength": 0,
        "marq_ai_consistency": 0,
        "marq_ai_reason": reason,
        "marq_event_id": event_id,
        "marq_outcome_key": outcome_key,
    }


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _opposite_key(outcome_key: str) -> str:
    return "od2" if outcome_key == "od1" else "od1"


def _market_move_pct(opening: Optional[float], latest: Optional[float]) -> Optional[float]:
    opening = _as_float(opening)
    latest = _as_float(latest)
    if opening is None or latest is None or opening <= 0:
        return None
    return ((latest - opening) / opening) * 100.0


def _implied_probability(odds: Optional[float]) -> Optional[float]:
    odds = _as_float(odds)
    if odds is None or odds <= 0:
        return None
    return 1.0 / odds


def _probability_change_pp(opening: Optional[float], latest: Optional[float]) -> Optional[float]:
    p_open = _implied_probability(opening)
    p_latest = _implied_probability(latest)
    if p_open is None or p_latest is None:
        return None
    return (p_latest - p_open) * 100.0


def _score_from_market_data(market_data: Dict[str, Any]) -> Dict[str, Any]:
    outcome_key = market_data.get("pick_outcome_key") or "od1"
    opponent_key = _opposite_key(outcome_key)
    selected = (market_data.get("odds") or {}).get(outcome_key, {})
    opponent = (market_data.get("odds") or {}).get(opponent_key, {})

    opening = _as_float(selected.get("opening"))
    latest = _as_float(selected.get("latest") or selected.get("current"))
    opponent_opening = _as_float(opponent.get("opening"))
    opponent_latest = _as_float(opponent.get("latest") or opponent.get("current"))

    move_pct = _market_move_pct(opening, latest)
    prob_change_pp = _probability_change_pp(opening, latest)
    opponent_move_pct = _market_move_pct(opponent_opening, opponent_latest)

    if opening is None or latest is None:
        return {
            "score": None,
            "signal": "NEUTRAL",
            "direction": "NEUTRAL",
            "strength": 0,
            "consistency": 0,
            "move_pct": move_pct,
            "prob_change_pp": prob_change_pp,
            "opponent_move_pct": opponent_move_pct,
            "opening": opening,
            "latest": latest,
        }

    source = market_data.get("source")

    # Full TennisApi mode: has opening/latest movement if available.
    # Fallback mode: opening == latest, so calculate a stable market-pressure score from current implied probability.
    if source == "fallback_existing_odds":
        p_selected = _implied_probability(latest)
        p_opponent = _implied_probability(opponent_latest)
        if p_selected is not None and p_opponent is not None and (p_selected + p_opponent) > 0:
            fair_market_prob = p_selected / (p_selected + p_opponent)
            score = max(0, min(100, round(fair_market_prob * 100)))
        else:
            score = 50
    else:
        if move_pct is None or prob_change_pp is None:
            score = 50
        else:
            raw_score = 50.0
            raw_score += prob_change_pp * 4.0
            if move_pct <= -12:
                raw_score += 18
            elif move_pct <= -8:
                raw_score += 13
            elif move_pct <= -5:
                raw_score += 9
            elif move_pct <= -3:
                raw_score += 5
            elif move_pct >= 12:
                raw_score -= 18
            elif move_pct >= 8:
                raw_score -= 13
            elif move_pct >= 5:
                raw_score -= 9
            elif move_pct >= 3:
                raw_score -= 5
            if opponent_move_pct is not None:
                if opponent_move_pct >= 8:
                    raw_score += 5
                elif opponent_move_pct >= 4:
                    raw_score += 3
                elif opponent_move_pct <= -8:
                    raw_score -= 5
                elif opponent_move_pct <= -4:
                    raw_score -= 3
            score = max(0, min(100, round(raw_score)))

    if score >= 72:
        signal = "BULLISH"
        direction = "WITH_PICK"
    elif score >= 58:
        signal = "SUPPORT"
        direction = "WITH_PICK"
    elif score <= 28:
        signal = "BEARISH"
        direction = "AGAINST_PICK"
    elif score <= 42:
        signal = "CAUTION"
        direction = "AGAINST_PICK"
    else:
        signal = "NEUTRAL"
        direction = "NEUTRAL"

    strength = max(0, min(100, round(abs(score - 50) * 2)))
    consistency = 50
    if source == "fallback_existing_odds":
        consistency = 55
    elif move_pct is not None and opponent_move_pct is not None:
        selected_support = move_pct < 0
        opponent_support = opponent_move_pct > 0
        selected_against = move_pct > 0
        opponent_against = opponent_move_pct < 0
        if selected_support and opponent_support:
            consistency = 85
        elif selected_against and opponent_against:
            consistency = 85
        elif selected_support or selected_against:
            consistency = 65

    return {
        "score": score,
        "signal": signal,
        "direction": direction,
        "strength": strength,
        "consistency": consistency,
        "move_pct": move_pct,
        "prob_change_pp": prob_change_pp,
        "opponent_move_pct": opponent_move_pct,
        "opening": opening,
        "latest": latest,
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

    result = _score_from_market_data(market_data)
    if result.get("score") is None:
        print(
            "MARQ DEBUG: odds input missing "
            f"event_id={market_data.get('event_id')} pick={pick} outcome={market_data.get('pick_outcome_key')}"
        )
        return _empty_marq(
            reason="odds_input_missing",
            event_id=market_data.get("event_id"),
            outcome_key=market_data.get("pick_outcome_key"),
        )

    print(
        "MARQ DEBUG: score "
        f"source={market_data.get('source')} event_id={market_data.get('event_id')} "
        f"pick={pick} outcome={market_data.get('pick_outcome_key')} "
        f"score={result.get('score')} signal={result.get('signal')} "
        f"opening={result.get('opening')} latest={result.get('latest')} "
        f"move_pct={result.get('move_pct')}"
    )

    return {
        "marq_ai_score": result.get("score"),
        "marq_ai_signal": result.get("signal"),
        "marq_ai_direction": result.get("direction"),
        "marq_ai_strength": result.get("strength"),
        "marq_ai_consistency": result.get("consistency"),
        "marq_ai_reason": "ok",
        "marq_event_id": market_data.get("event_id"),
        "marq_outcome_key": market_data.get("pick_outcome_key"),
        "marq_source": market_data.get("source"),
        "marq_market_name": market_data.get("market_name"),
        "marq_home_name": market_data.get("home_name"),
        "marq_away_name": market_data.get("away_name"),
        "marq_opening": result.get("opening"),
        "marq_latest": result.get("latest"),
        "marq_market_move_pct": result.get("move_pct"),
        "marq_probability_change_pp": result.get("prob_change_pp"),
        "marq_opponent_move_pct": result.get("opponent_move_pct"),
    }
