import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tennisapi_client import TennisApiClient, normalize_winning_odds


logger = logging.getLogger(__name__)

_ODDS_CACHE: Optional[List[Dict[str, Any]]] = None


# ----------------------------------------------------------------------
# Public API expected by the existing prediction engine
# ----------------------------------------------------------------------


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """
    Backward-compatible odds fetcher.

    Supports old engine usage:
        odds = fetch_odds()
        match_odds = find_match_odds(odds, player1, player2)

    New behavior:
        - scans TennisApi fixtures for today and tomorrow
        - fetches TennisApi winning odds by event id
        - returns a legacy-compatible odds list with player names
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

    try:
        client = TennisApiClient()
    except Exception as exc:
        logger.warning("TennisApi odds client init failed: %s", exc)
        _ODDS_CACHE = []
        return _ODDS_CACHE

    category_ids = _parse_category_ids()
    days_ahead = _parse_int_env("ODDS_SCAN_DAYS_AHEAD", 1)
    days_back = _parse_int_env("ODDS_SCAN_DAYS_BACK", 0)

    odds_items: List[Dict[str, Any]] = []
    seen_match_ids = set()

    today = datetime.now()
    for delta in range(-days_back, days_ahead + 1):
        target_date = today + timedelta(days=delta)
        for category_id in category_ids:
            try:
                events = client.get_events_by_category_date(
                    category_id=category_id,
                    day=target_date.day,
                    month=target_date.month,
                    year=target_date.year,
                )
            except Exception as exc:
                logger.info(
                    "Odds event scan failed. category_id=%s date=%s error=%s",
                    category_id,
                    target_date.date(),
                    exc,
                )
                continue

            for event in events:
                if not isinstance(event, dict):
                    continue

                match_id = event.get("id")
                if not match_id or match_id in seen_match_ids:
                    continue
                seen_match_ids.add(match_id)

                home = event.get("homeTeam") or {}
                away = event.get("awayTeam") or {}
                player1 = home.get("name")
                player2 = away.get("name")
                if not player1 or not player2:
                    continue

                odds = get_tennisapi_odds(int(match_id))
                if not odds:
                    continue

                item = _to_legacy_odds_item(odds)
                item["player1"] = player1
                item["player2"] = player2
                item["home_team"] = player1
                item["away_team"] = player2
                item["match"] = f"{player1} vs {player2}"
                item["event_id"] = match_id
                item["match_id"] = match_id
                item["startTimestamp"] = event.get("startTimestamp")
                item["tournament"] = _extract_tournament_name(event)
                odds_items.append(item)

    _ODDS_CACHE = odds_items
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
# TennisApi odds helpers
# ----------------------------------------------------------------------


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    try:
        client = TennisApiClient()
        payload = client.get_match_winning_odds(match_id)
        normalized = normalize_winning_odds(payload)
        if normalized:
            normalized["match_id"] = match_id
            return normalized
    except Exception as exc:
        logger.info("TennisApi odds failed. match_id=%s error=%s", match_id, exc)

    return None


def get_match_odds(match: Dict[str, Any], prefer_tennisapi: bool = True) -> Optional[Dict[str, Any]]:
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
        enriched["odds"] = None
        return enriched

    p1_odds = odds.get("p1_odds") or odds.get("home_odds")
    p2_odds = odds.get("p2_odds") or odds.get("away_odds")

    enriched["odds_status"] = "OK"
    enriched["odds_source"] = odds.get("source")
    enriched["p1_odds"] = p1_odds
    enriched["p2_odds"] = p2_odds
    enriched["home_odds"] = odds.get("home_odds") or p1_odds
    enriched["away_odds"] = odds.get("away_odds") or p2_odds
    enriched["odds"] = p1_odds
    enriched["odds_raw"] = odds.get("raw")
    return enriched


# Compatibility aliases

def get_odds(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_odds_for_match(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_match_odds_for_event(match_id: int) -> Optional[Dict[str, Any]]:
    return get_tennisapi_odds(match_id)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _parse_category_ids() -> List[int]:
    import os

    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3,6,871").strip()
    output: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            output.append(int(part))
        except Exception:
            pass
    return output or [3]


def _parse_int_env(name: str, default: int) -> int:
    import os

    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _extract_tournament_name(event: Dict[str, Any]) -> Optional[str]:
    tournament = event.get("tournament") or {}
    unique = tournament.get("uniqueTournament") or event.get("uniqueTournament") or {}
    return unique.get("name") or tournament.get("name")


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
    p1 = odds.get("p1_odds") or odds.get("home_odds")
    p2 = odds.get("p2_odds") or odds.get("away_odds")
    return {
        "source": odds.get("source", "TennisApi"),
        "match_id": odds.get("match_id"),
        "event_id": odds.get("match_id"),
        "home_odds": p1,
        "away_odds": p2,
        "p1_odds": p1,
        "p2_odds": p2,
        "odds": p1,
        "odds1": p1,
        "odds2": p2,
        "price1": p1,
        "price2": p2,
        "home_expected": odds.get("home_expected"),
        "away_expected": odds.get("away_expected"),
        "home_actual": odds.get("home_actual"),
        "away_actual": odds.get("away_actual"),
        "raw": odds.get("raw", odds),
    }


def _legacy_to_normalized(legacy: Dict[str, Any]) -> Dict[str, Any]:
    p1 = legacy.get("p1_odds") or legacy.get("home_odds") or legacy.get("odds") or legacy.get("odds1") or legacy.get("price1")
    p2 = legacy.get("p2_odds") or legacy.get("away_odds") or legacy.get("odds2") or legacy.get("price2")
    return {
        "source": legacy.get("source", "LegacyOdds"),
        "match_id": legacy.get("match_id") or legacy.get("event_id"),
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

        # Also allow reversed order.
        if p2 in normalized_names and p1 in normalized_names:
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
    odds = fetch_odds(force_refresh=True)
    print(f"Odds found: {len(odds)}")
    for item in odds[:20]:
        print(item.get("match_id"), item.get("player1"), "vs", item.get("player2"), item.get("odds1"), item.get("odds2"))
