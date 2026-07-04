import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tennisapi_client import TennisApiClient, normalize_winning_odds


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# TennisApi / REcodeX odds
# ----------------------------------------------------------------------


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    """
    Primary odds datasource pre tenis.

    Očakávaný TennisApi tvar:
    {
        "home": {"fractionalValue": "73/100", "expected": 58, "actual": 53},
        "away": {"fractionalValue": "11/10", "expected": 48, "actual": 60}
    }
    """
    try:
        client = TennisApiClient()
        payload = client.get_match_winning_odds(match_id)
        normalized = normalize_winning_odds(payload)

        if normalized:
            normalized["match_id"] = match_id
            return normalized

    except Exception as exc:
        logger.warning("TennisApi odds failed. match_id=%s error=%s", match_id, exc)

    return None


# ----------------------------------------------------------------------
# Backward-compatible API used by prediction_engine_core.py
# ----------------------------------------------------------------------


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """
    Backward-compatible replacement for the original fetch_odds function.

    Existing code imports:
        from odds_api import fetch_odds, find_match_odds

    This function intentionally accepts any args/kwargs so old calls do not crash.
    If a match_id/event_id/id is provided, TennisApi odds are fetched and returned
    as a one-item odds list. If no match_id is available, returns an empty list.
    """
    match_id = _extract_match_id_from_args_kwargs(args, kwargs)

    if match_id:
        odds = get_tennisapi_odds(int(match_id))
        if odds:
            return [_to_legacy_odds_item(odds)]

    return []


async def fetch_odds_async(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """Async-safe wrapper, in case some code imports/uses an async odds fetcher."""
    return fetch_odds(*args, **kwargs)


def find_match_odds(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Backward-compatible replacement for the original find_match_odds function.

    Supported usage patterns:
        find_match_odds(match)
        find_match_odds(odds_list, match)
        find_match_odds(player1, player2)
        find_match_odds(odds_list, player1, player2)

    Primary path:
        - if match contains match_id/event_id/id -> TennisApi by event id

    Secondary path:
        - tries to match inside provided odds_list by player names
    """
    odds_list, match, player1, player2 = _parse_find_match_odds_args(args, kwargs)

    match_id = None
    if isinstance(match, dict):
        match_id = match.get("match_id") or match.get("event_id") or match.get("id")
        player1 = player1 or match.get("player1") or match.get("home") or match.get("home_team")
        player2 = player2 or match.get("player2") or match.get("away") or match.get("away_team")

    if match_id:
        odds = get_tennisapi_odds(int(match_id))
        if odds:
            return _to_legacy_odds_item(odds)

    if odds_list:
        matched = _find_in_legacy_odds_list(odds_list, player1, player2)
        if matched:
            return matched

    return None


def get_match_odds(match: Dict[str, Any], prefer_tennisapi: bool = True) -> Optional[Dict[str, Any]]:
    """
    Main normalized odds helper.

    Current order:
        TennisApi / REcodeX
        -> old/list fallback if caller provides data elsewhere
        -> None
    """
    match_id = match.get("match_id") or match.get("event_id") or match.get("id")

    if prefer_tennisapi and match_id:
        odds = get_tennisapi_odds(int(match_id))
        if odds:
            return odds

    legacy = find_match_odds(match)
    if legacy:
        return _legacy_to_normalized(legacy)

    if not prefer_tennisapi and match_id:
        odds = get_tennisapi_odds(int(match_id))
        if odds:
            return odds

    return None


def enrich_match_with_odds(match: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(match)
    odds = get_match_odds(match)

    if not odds:
        enriched["odds_status"] = "NO_ODDS"
        enriched["odds_source"] = None
        enriched["p1_odds"] = None
        enriched["p2_odds"] = None
        return enriched

    enriched["odds_status"] = "OK"
    enriched["odds_source"] = odds.get("source")
    enriched["p1_odds"] = odds.get("p1_odds") or odds.get("home_odds")
    enriched["p2_odds"] = odds.get("p2_odds") or odds.get("away_odds")
    enriched["home_odds"] = odds.get("home_odds") or odds.get("p1_odds")
    enriched["away_odds"] = odds.get("away_odds") or odds.get("p2_odds")
    enriched["odds_raw"] = odds.get("raw")
    enriched["home_expected"] = odds.get("home_expected")
    enriched["away_expected"] = odds.get("away_expected")
    enriched["home_actual"] = odds.get("home_actual")
    enriched["away_actual"] = odds.get("away_actual")
    return enriched


# ----------------------------------------------------------------------
# Compatibility aliases often used in older code
# ----------------------------------------------------------------------


def get_odds(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_odds_for_match(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_match_odds_for_event(match_id: int) -> Optional[Dict[str, Any]]:
    return get_tennisapi_odds(match_id)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _extract_match_id_from_args_kwargs(args: Sequence[Any], kwargs: Dict[str, Any]) -> Optional[int]:
    for key in ("match_id", "event_id", "id"):
        value = kwargs.get(key)
        if value:
            return int(value)

    for arg in args:
        if isinstance(arg, dict):
            value = arg.get("match_id") or arg.get("event_id") or arg.get("id")
            if value:
                return int(value)
        elif isinstance(arg, int):
            return int(arg)
        elif isinstance(arg, str) and arg.isdigit():
            return int(arg)

    return None


def _parse_find_match_odds_args(
    args: Sequence[Any],
    kwargs: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    odds_list: List[Dict[str, Any]] = []
    match: Optional[Dict[str, Any]] = None
    player1: Optional[str] = kwargs.get("player1") or kwargs.get("home_player")
    player2: Optional[str] = kwargs.get("player2") or kwargs.get("away_player")

    if isinstance(kwargs.get("match"), dict):
        match = kwargs["match"]

    if isinstance(kwargs.get("odds_list"), list):
        odds_list = kwargs["odds_list"]
    elif isinstance(kwargs.get("odds"), list):
        odds_list = kwargs["odds"]

    positional = list(args)

    if positional and isinstance(positional[0], list):
        odds_list = positional.pop(0)

    if positional and isinstance(positional[0], dict):
        match = positional.pop(0)

    if positional and player1 is None:
        player1 = str(positional.pop(0))

    if positional and player2 is None:
        player2 = str(positional.pop(0))

    return odds_list, match, player1, player2


def _to_legacy_odds_item(odds: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": odds.get("source", "TennisApi"),
        "match_id": odds.get("match_id"),
        "home_odds": odds.get("home_odds") or odds.get("p1_odds"),
        "away_odds": odds.get("away_odds") or odds.get("p2_odds"),
        "p1_odds": odds.get("p1_odds") or odds.get("home_odds"),
        "p2_odds": odds.get("p2_odds") or odds.get("away_odds"),
        "odds1": odds.get("p1_odds") or odds.get("home_odds"),
        "odds2": odds.get("p2_odds") or odds.get("away_odds"),
        "home_expected": odds.get("home_expected"),
        "away_expected": odds.get("away_expected"),
        "home_actual": odds.get("home_actual"),
        "away_actual": odds.get("away_actual"),
        "raw": odds.get("raw", odds),
    }


def _legacy_to_normalized(legacy: Dict[str, Any]) -> Dict[str, Any]:
    p1 = (
        legacy.get("p1_odds")
        or legacy.get("home_odds")
        or legacy.get("odds1")
        or legacy.get("price1")
    )
    p2 = (
        legacy.get("p2_odds")
        or legacy.get("away_odds")
        or legacy.get("odds2")
        or legacy.get("price2")
    )

    return {
        "source": legacy.get("source", "LegacyOdds"),
        "match_id": legacy.get("match_id"),
        "home_odds": _to_float_or_none(p1),
        "away_odds": _to_float_or_none(p2),
        "p1_odds": _to_float_or_none(p1),
        "p2_odds": _to_float_or_none(p2),
        "raw": legacy.get("raw", legacy),
    }


def _find_in_legacy_odds_list(
    odds_list: List[Dict[str, Any]],
    player1: Optional[str],
    player2: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not player1 or not player2:
        return None

    p1 = _normalize_name(player1)
    p2 = _normalize_name(player2)

    for item in odds_list:
        names = [
            item.get("player1"),
            item.get("player2"),
            item.get("home_team"),
            item.get("away_team"),
            item.get("home"),
            item.get("away"),
        ]
        normalized_names = {_normalize_name(name) for name in names if name}

        if p1 in normalized_names and p2 in normalized_names:
            return item

    return None


def _normalize_name(name: Any) -> str:
    return (
        str(name or "")
        .lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_match = {
        "match_id": 189477,
        "player1": "Home Player",
        "player2": "Away Player",
    }

    print(enrich_match_with_odds(test_match))
