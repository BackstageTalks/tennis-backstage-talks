import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tennisapi_client import TennisApiClient, normalize_winning_odds
from tennisapi_cache import get_daily_odds_items, betting_day_datetime, normalize_event_market_odds_payload, provider_id


logger = logging.getLogger(__name__)

_ODDS_CACHE: Optional[List[Dict[str, Any]]] = None


# ----------------------------------------------------------------------
# Public API expected by prediction_engine_core.py
# ----------------------------------------------------------------------


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """
    TennisApi-primary odds fetcher.

    Existing project call pattern:
        odds_matches = fetch_odds()
        odds_data = find_match_odds(odds_list, match)

    Source priority:
        1) TennisApi daily odds batch cache
        2) TennisApi event winning odds fallback inside tennisapi_cache
        3) empty list / no odds
    """
    global _ODDS_CACHE

    if kwargs.get("force_refresh"):
        _ODDS_CACHE = None

    if _ODDS_CACHE is not None:
        return _ODDS_CACHE

    explicit_match_id = _extract_match_id_from_args_kwargs(args, kwargs)
    if explicit_match_id:
        item = get_tennisapi_odds(int(explicit_match_id))
        _ODDS_CACHE = [_to_legacy_odds_item(item)] if item else []
        return _ODDS_CACHE

    odds_items: List[Dict[str, Any]] = []
    days_ahead = _parse_int_env("ODDS_SCAN_DAYS_AHEAD", 1)
    days_back = _parse_int_env("ODDS_SCAN_DAYS_BACK", 0)
    force_refresh = bool(kwargs.get("force_refresh", False))

    today = betting_day_datetime()
    for delta in range(-days_back, days_ahead + 1):
        target_date = today + timedelta(days=delta)
        try:
            daily_items = get_daily_odds_items(
                target_date=target_date,
                force_refresh=force_refresh,
                include_event_fallback=True,
            )
            odds_items.extend(daily_items)
        except Exception as exc:
            logger.warning("TennisApi daily odds items failed date=%s error=%s", target_date.date(), exc)

    # Deduplicate by event id.
    seen = set()
    unique_items = []
    for item in odds_items:
        key = item.get("event_id") or item.get("match_id") or item.get("match")
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)

    _ODDS_CACHE = unique_items
    print("TennisApi odds fetched:", len(_ODDS_CACHE))
    logger.info("TennisApi odds fetched: %s", len(_ODDS_CACHE))
    return _ODDS_CACHE


async def fetch_odds_async(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return fetch_odds(*args, **kwargs)


def find_match_odds(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Backward-compatible matcher.

    Supported patterns:
        find_match_odds(match)
        find_match_odds(odds_list, match)
        find_match_odds(player1, player2)
        find_match_odds(player1, player2, odds_list)
        find_match_odds(odds_list, player1, player2)
    """
    odds_list, match, player1, player2 = _parse_find_match_odds_args(args, kwargs)

    if not odds_list:
        odds_list = fetch_odds()

    match_id = None
    if isinstance(match, dict):
        match_id = match.get("match_id") or match.get("event_id") or match.get("id")
        player1 = player1 or match.get("player1") or match.get("pick") or match.get("home") or match.get("home_team")
        player2 = player2 or match.get("player2") or match.get("opponent") or match.get("away") or match.get("away_team")

    if match_id:
        for item in odds_list:
            item_id = item.get("match_id") or item.get("event_id") or item.get("id")
            if str(item_id) == str(match_id):
                return dict(item)

        direct = get_tennisapi_odds(int(match_id))
        if direct:
            item = _to_legacy_odds_item(direct)
            if player1:
                item["player1"] = player1
            if player2:
                item["player2"] = player2
            return item

    return _find_in_legacy_odds_list(odds_list, player1, player2)


# ----------------------------------------------------------------------
# TennisApi event odds fallback
# ----------------------------------------------------------------------


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    """Try all TennisApi PRO event-level odds endpoints for a match/event id."""
    try:
        client = TennisApiClient()
    except Exception as exc:
        logger.info("TennisApi client init failed. match_id=%s error=%s", match_id, exc)
        return None
    attempts = [
        ("TennisApiMatchWinningOdds", lambda: client.get_match_winning_odds(match_id, provider_id()), normalize_winning_odds),
        ("TennisApiMatchBettingOdds", lambda: client.get_match_betting_odds(match_id), normalize_event_market_odds_payload),
        ("TennisApiAllOddsForEvent", lambda: client.get_all_odds_for_event(match_id, provider_id()), normalize_event_market_odds_payload),
        ("TennisApiMatchFeaturedOdds", lambda: client.get_match_featured_odds(match_id), normalize_event_market_odds_payload),
    ]
    for source_name, fetcher, normalizer in attempts:
        try:
            payload = fetcher()
            normalized = normalizer(payload)
            if normalized:
                normalized["source"] = source_name
                normalized["odds_source"] = source_name
                normalized["match_id"] = match_id
                normalized["event_id"] = match_id
                normalized["bookmaker"] = normalized.get("bookmaker") or "TennisApi"
                return normalized
        except Exception as exc:
            logger.debug("TennisApi event odds candidate failed source=%s match_id=%s error=%s", source_name, match_id, exc)
    logger.info("TennisApi PRO event odds unavailable. match_id=%s", match_id)
    return None


# Compatibility aliases

def get_match_odds(match: Dict[str, Any], prefer_tennisapi: bool = True) -> Optional[Dict[str, Any]]:
    legacy = find_match_odds(match)
    if legacy:
        return _legacy_to_normalized(legacy)
    return None


def enrich_match_with_odds(match: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(match)
    odds = get_match_odds(match)
    if not odds:
        enriched["odds_status"] = "NO_ODDS"
        enriched["odds_source"] = None
        enriched["p1_odds"] = None
        enriched["p2_odds"] = None
        enriched["odds"] = None
        return enriched

    p1 = odds.get("odds_player1") or odds.get("p1_odds") or odds.get("home_odds")
    p2 = odds.get("odds_player2") or odds.get("p2_odds") or odds.get("away_odds")
    enriched["odds_status"] = "OK"
    enriched["odds_source"] = odds.get("odds_source") or odds.get("source")
    enriched["odds_player1"] = p1
    enriched["odds_player2"] = p2
    enriched["p1_odds"] = p1
    enriched["p2_odds"] = p2
    enriched["home_odds"] = p1
    enriched["away_odds"] = p2
    enriched["odds"] = p1
    enriched["bookmaker"] = odds.get("bookmaker")
    enriched["odds_raw"] = odds.get("raw")
    return enriched


def get_odds(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_odds_for_match(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_match_odds_for_event(match_id: int) -> Optional[Dict[str, Any]]:
    return get_tennisapi_odds(match_id)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _parse_int_env(name: str, default: int) -> int:
    import os
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


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

    non_list_positional: List[Any] = []
    for arg in args:
        if isinstance(arg, list):
            odds_list = arg
        else:
            non_list_positional.append(arg)

    positional = non_list_positional
    if positional and isinstance(positional[0], dict):
        match = positional.pop(0)
    if positional and player1 is None:
        player1 = str(positional.pop(0))
    if positional and player2 is None:
        player2 = str(positional.pop(0))
    return odds_list, match, player1, player2


def _to_legacy_odds_item(odds: Dict[str, Any]) -> Dict[str, Any]:
    p1 = odds.get("p1_odds") or odds.get("home_odds") or odds.get("odds_player1")
    p2 = odds.get("p2_odds") or odds.get("away_odds") or odds.get("odds_player2")
    return {
        "source": odds.get("source") or odds.get("odds_source") or "TennisApi",
        "odds_source": odds.get("odds_source") or odds.get("source") or "TennisApi",
        "bookmaker": odds.get("bookmaker") or "TennisApi",
        "match_id": odds.get("match_id"),
        "event_id": odds.get("match_id"),
        "home_odds": p1,
        "away_odds": p2,
        "p1_odds": p1,
        "p2_odds": p2,
        "odds_player1": p1,
        "odds_player2": p2,
        "odds": p1,
        "odds1": p1,
        "odds2": p2,
        "price1": p1,
        "price2": p2,
        "raw": odds.get("raw", odds),
    }


def _legacy_to_normalized(legacy: Dict[str, Any]) -> Dict[str, Any]:
    p1 = legacy.get("odds_player1") or legacy.get("p1_odds") or legacy.get("home_odds") or legacy.get("odds") or legacy.get("odds1") or legacy.get("price1")
    p2 = legacy.get("odds_player2") or legacy.get("p2_odds") or legacy.get("away_odds") or legacy.get("odds2") or legacy.get("price2")
    return {
        "source": legacy.get("source") or legacy.get("odds_source") or "LegacyOdds",
        "odds_source": legacy.get("odds_source") or legacy.get("source") or "LegacyOdds",
        "match_id": legacy.get("match_id") or legacy.get("event_id"),
        "home_odds": _to_float_or_none(p1),
        "away_odds": _to_float_or_none(p2),
        "p1_odds": _to_float_or_none(p1),
        "p2_odds": _to_float_or_none(p2),
        "odds_player1": _to_float_or_none(p1),
        "odds_player2": _to_float_or_none(p2),
        "bookmaker": legacy.get("bookmaker"),
        "raw": legacy.get("raw", legacy),
    }


def _find_in_legacy_odds_list(
    odds_list: List[Dict[str, Any]],
    player1: Optional[str],
    player2: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not player1 or not player2:
        return None
    requested_p1 = _normalize_name(player1)
    requested_p2 = _normalize_name(player2)
    for item in odds_list:
        item_p1 = item.get("player1") or item.get("home_team") or item.get("home")
        item_p2 = item.get("player2") or item.get("away_team") or item.get("away")
        norm_item_p1 = _normalize_name(item_p1)
        norm_item_p2 = _normalize_name(item_p2)
        direct = _names_match_normalized(requested_p1, norm_item_p1) and _names_match_normalized(requested_p2, norm_item_p2)
        reversed_match = _names_match_normalized(requested_p1, norm_item_p2) and _names_match_normalized(requested_p2, norm_item_p1)
        if direct:
            return dict(item)
        if reversed_match:
            swapped = dict(item)
            p1 = item.get("odds_player2") or item.get("p2_odds") or item.get("away_odds") or item.get("odds2") or item.get("price2")
            p2 = item.get("odds_player1") or item.get("p1_odds") or item.get("home_odds") or item.get("odds1") or item.get("price1")
            swapped["player1"] = player1
            swapped["player2"] = player2
            swapped["odds_player1"] = p1
            swapped["odds_player2"] = p2
            swapped["p1_odds"] = p1
            swapped["p2_odds"] = p2
            swapped["home_odds"] = p1
            swapped["away_odds"] = p2
            swapped["odds"] = p1
            swapped["odds1"] = p1
            swapped["odds2"] = p2
            return swapped
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


def _name_keys(normalized: str) -> set:
    parts = normalized.split()
    keys = set()
    if normalized:
        keys.add(normalized)
    if parts:
        keys.add(parts[-1])
    if len(parts) >= 2:
        keys.add(" ".join(parts[-2:]))
        keys.add(f"{parts[0][0]} {parts[-1]}")
    return keys


def _names_match_normalized(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return bool(_name_keys(a).intersection(_name_keys(b)))


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    odds = fetch_odds(force_refresh=True)
    print(f"Odds found: {len(odds)}")
    for item in odds[:20]:
        print(item.get("match_id"), item.get("player1"), "vs", item.get("player2"), item.get("odds_player1"), item.get("odds_player2"))
