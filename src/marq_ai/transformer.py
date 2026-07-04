from __future__ import annotations

from typing import Any, Dict, Optional


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def resolve_outcome_key(
    player1: str,
    player2: str,
    pick: Optional[str] = None,
) -> str:
    """
    Resolve which RapidAPI odds side belongs to selected pick.

    RapidAPI mapping:
    - od1 = participant1 / player1
    - od2 = participant2 / player2
    """

    p1 = _norm(player1)
    p2 = _norm(player2)
    pk = _norm(pick)

    if not pk:
        return "od1"

    if pk == p1:
        return "od1"

    if pk == p2:
        return "od2"

    if pk in p1 or p1 in pk:
        return "od1"

    if pk in p2 or p2 in pk:
        return "od2"

    p1_parts = set(p1.replace("-", " ").split())
    p2_parts = set(p2.replace("-", " ").split())
    pk_parts = set(pk.replace("-", " ").split())

    if p1_parts and pk_parts and p1_parts.intersection(pk_parts):
        return "od1"

    if p2_parts and pk_parts and p2_parts.intersection(pk_parts):
        return "od2"

    return "od1"


def opposite_outcome_key(outcome_key: str) -> str:
    return "od2" if outcome_key == "od1" else "od1"


def _walk_values(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_values(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_values(item)


def find_event_id(payload: Any) -> Optional[str]:
    """
    Best-effort event id resolver for RapidAPI event/get response.
    """

    if payload is None:
        return None

    candidate_keys = (
        "eventId",
        "event_id",
        "eventID",
        "id",
        "matchId",
        "match_id",
        "fixtureId",
        "fixture_id",
    )

    for item in _walk_values(payload):
        for key in candidate_keys:
            value = item.get(key)
            if value not in (None, "", 0):
                return str(value)

    return None


def _extract_direct_price(
    item: Dict[str, Any],
    outcome_key: str,
) -> Optional[float]:
    """
    Extract selected odds value from one dictionary.
    """

    direct_keys = (
        outcome_key,
        outcome_key.upper(),
        f"{outcome_key}_price",
        f"{outcome_key}Price",
        f"{outcome_key}_odd",
        f"{outcome_key}Odd",
        f"{outcome_key}_odds",
        f"{outcome_key}Odds",
    )

    for key in direct_keys:
        if key in item:
            price = _to_float(item.get(key))
            if price is not None:
                return price

    return None


def _extract_stage_price(
    payload: Any,
    stage: str,
    outcome_key: str,
) -> Optional[float]:
    """
    Extract odds for a stage:
    - start = opening odds
    - kickoff = pre-match odds
    - end = closing/end odds
    """

    if payload is None:
        return None

    stage_norm = _norm(stage)

    for item in _walk_values(payload):
        keys_lower = {_norm(k): k for k in item.keys()}

        # Shape: {"start": {"od1": 1.55, "od2": 2.40}}
        if stage_norm in keys_lower:
            stage_obj = item.get(keys_lower[stage_norm])
            if isinstance(stage_obj, dict):
                price = _extract_direct_price(stage_obj, outcome_key)
                if price is not None:
                    return price

        # Shape: {"period": "start", "od1": 1.55, "od2": 2.40}
        marker_keys = (
            "type",
            "name",
            "period",
            "stage",
            "moment",
            "phase",
            "oddsType",
            "odds_type",
        )

        marker = ""
        for marker_key in marker_keys:
            if marker_key in item:
                marker = _norm(item.get(marker_key))
                break

        if marker == stage_norm:
            price = _extract_direct_price(item, outcome_key)
            if price is not None:
                return price

    return None


def extract_summary_prices(
    summary_payload: Any,
    outcome_key: str,
) -> Dict[str, Optional[float]]:
    return {
        "start": _extract_stage_price(summary_payload, "start", outcome_key),
        "kickoff": _extract_stage_price(summary_payload, "kickoff", outcome_key),
        "end": _extract_stage_price(summary_payload, "end", outcome_key),
    }


def extract_opponent_summary_prices(
    summary_payload: Any,
    outcome_key: str,
) -> Dict[str, Optional[float]]:
    opponent_key = opposite_outcome_key(outcome_key)

    return {
        "start": _extract_stage_price(summary_payload, "start", opponent_key),
        "kickoff": _extract_stage_price(summary_payload, "kickoff", opponent_key),
        "end": _extract_stage_price(summary_payload, "end", opponent_key),
    }


def extract_recent_price(
    recent_payload: Any,
    outcome_key: str,
) -> Optional[float]:
    """
    Extract latest/recent selected odds.
    """

    if recent_payload is None:
        return None

    prices = []

    for item in _walk_values(recent_payload):
        price = _extract_direct_price(item, outcome_key)
        if price is not None:
            prices.append(price)

    if not prices:
        return None

    return prices[-1]


def build_marq_input(
    summary_payload: Any,
    recent_payload: Any,
    outcome_key: str,
) -> Dict[str, Any]:
    """
    Normalize RapidAPI summary/recent odds payloads into Marq AI input.
    """

    selected = extract_summary_prices(summary_payload, outcome_key)
    opponent = extract_opponent_summary_prices(summary_payload, outcome_key)
    recent = extract_recent_price(recent_payload, outcome_key)

    opening = selected.get("start")
    kickoff = selected.get("kickoff")
    closing = selected.get("end")

    latest = recent or closing or kickoff

    return {
        "outcome_key": outcome_key,
        "opening": opening,
        "kickoff": kickoff,
        "closing": closing,
        "recent": recent,
        "latest": latest,
        "opponent_opening": opponent.get("start"),
        "opponent_kickoff": opponent.get("kickoff"),
        "opponent_closing": opponent.get("end"),
    }


def has_usable_marq_input(marq_input: Dict[str, Any]) -> bool:
    if not isinstance(marq_input, dict):
        return False

    opening = marq_input.get("opening")
    latest = marq_input.get("latest")

    return opening is not None and latest is not None


def calculate_market_move_percent(
    opening: Optional[float],
    latest: Optional[float],
) -> Optional[float]:
    """
    Decimal odds move percentage.

    Negative = odds shortened = market support.
    Positive = odds drifted = market against.
    """

    if opening is None or latest is None:
        return None

    if opening <= 0:
        return None

    return ((latest - opening) / opening) * 100.0


def calculate_implied_probability(odds: Optional[float]) -> Optional[float]:
    if odds is None or odds <= 0:
        return None

    return 1.0 / odds


def calculate_probability_change_pp(
    opening: Optional[float],
    latest: Optional[float],
) -> Optional[float]:
    """
    Implied probability change in percentage points.

    Positive = selected player became more likely by market movement.
    """

    p_open = calculate_implied_probability(opening)
    p_latest = calculate_implied_probability(latest)

    if p_open is None or p_latest is None:
        return None

    return (p_latest - p_open) * 100.0


def summarize_movement(marq_input: Dict[str, Any]) -> Dict[str, Any]:
    opening = marq_input.get("opening")
    latest = marq_input.get("latest")

    move_pct = calculate_market_move_percent(opening, latest)
    prob_change_pp = calculate_probability_change_pp(opening, latest)

    opponent_opening = marq_input.get("opponent_opening")
    opponent_latest = (
        marq_input.get("opponent_closing")
        or marq_input.get("opponent_kickoff")
    )

    opponent_move_pct = calculate_market_move_percent(
        opponent_opening,
        opponent_latest,
    )

    return {
        "move_pct": move_pct,
        "prob_change_pp": prob_change_pp,
        "opponent_move_pct": opponent_move_pct,
    }
