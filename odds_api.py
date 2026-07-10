
import atexit
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from tennisapi_client import TennisApiClient, normalize_winning_odds
from tennisapi_cache import get_daily_odds_items, betting_day_datetime

logger = logging.getLogger(__name__)

_ODDS_CACHE: Optional[List[Dict[str, Any]]] = None
_NO_ODDS_REPORT: List[Dict[str, Any]] = []
_TENNIS_API_EVENT_CACHE: Dict[str, List[Dict[str, Any]]] = {}

# IMPORTANT CURRENT ODDS FLOW
# 1. Rapid API / TennisApi PRO cache via tennisapi_cache.get_daily_odds_items().
# 2. Tennis API - ATP WTA ITF fallback via TENNIS_API_ATP_WTA_ITF.
#    Do NOT use retired /api/tennis/events/{day}/{month}/{year}.
#    Correct flow:
#       /api/tennis/calendar/{day}/{month}/{year}/categories
#       /api/tennis/category/{categoryId}/events/{day}/{month}/{year}
#       /api/tennis/event/{eventId}/odds
# 3. All Sports API fallback via ALL_SPORTS_API.
#       /api/tennis/event/{event_id}/provider/1/winning-odds
# 4. NO_ODDS.
#
# The old ODDS_API_KEY / The Odds API is intentionally not used.

TENNIS_API_ATP_WTA_ITF_HOST = os.getenv(
    "TENNIS_API_ATP_WTA_ITF_HOST",
    "tennis-api-atp-wta-itf.p.rapidapi.com",
)
TENNIS_API_ATP_WTA_ITF_BASE_URL = os.getenv(
    "TENNIS_API_ATP_WTA_ITF_BASE_URL",
    f"https://{TENNIS_API_ATP_WTA_ITF_HOST}",
).rstrip("/")

ALL_SPORTS_API_HOST = "allsportsapi2.p.rapidapi.com"
ALL_SPORTS_API_BASE_URL = "https://allsportsapi2.p.rapidapi.com"
ALL_SPORTS_PROVIDER_ID = int(os.getenv("ALL_SPORTS_PROVIDER_ID", "1"))
ALL_SPORTS_MAX_REQUESTS_PER_RUN = int(os.getenv("ALL_SPORTS_MAX_REQUESTS_PER_RUN", "80"))
_ALL_SPORTS_REQUESTS = 0


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """
    Public API expected by prediction_engine_core.py.

    Returns a list of normalized/legacy odds rows. Primary source is the existing
    Rapid API / TennisApi cache (`get_daily_odds_items`). Missing event-specific
    odds are additionally handled inside `find_match_odds()` using Tennis API -
    ATP WTA ITF and All Sports API fallbacks.
    """
    global _ODDS_CACHE
    force_refresh = bool(kwargs.get("force_refresh"))

    if _ODDS_CACHE is not None and not force_refresh:
        return _ODDS_CACHE

    items: List[Dict[str, Any]] = []

    try:
        raw_items = get_daily_odds_items(force_refresh=force_refresh)
        if isinstance(raw_items, list):
            for item in raw_items:
                normalized = _to_legacy_odds_item(item)
                if _has_two_prices(normalized):
                    normalized["odds_source"] = normalized.get("odds_source") or "rapid_api"
                    normalized["source"] = normalized.get("source") or normalized.get("odds_source")
                    items.append(normalized)
    except TypeError:
        # Backward compatibility if get_daily_odds_items() does not accept force_refresh.
        try:
            raw_items = get_daily_odds_items()
            if isinstance(raw_items, list):
                for item in raw_items:
                    normalized = _to_legacy_odds_item(item)
                    if _has_two_prices(normalized):
                        normalized["odds_source"] = normalized.get("odds_source") or "rapid_api"
                        normalized["source"] = normalized.get("source") or normalized.get("odds_source")
                        items.append(normalized)
        except Exception as exc:
            logger.info("Rapid API odds cache failed: %s", exc)
    except Exception as exc:
        logger.info("Rapid API odds cache failed: %s", exc)

    _ODDS_CACHE = items
    logger.info("ODDS FLOW: loaded %s primary Rapid API odds rows", len(items))
    return items


async def fetch_odds_async(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return fetch_odds(*args, **kwargs)


def find_match_odds(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Backward-compatible matcher used by prediction_engine_core.py.

    Supported call styles:
      find_match_odds(odds_list, match)
      find_match_odds(match)
      find_match_odds(player1=..., player2=..., event_id=...)

    Lookup order:
      1. Already fetched Rapid API odds list by id/name.
      2. Tennis API - ATP WTA ITF event odds by event id or discovered category event id.
      3. All Sports API provider winning odds by event id.
      4. None, while adding entry to public/no_odds_report.json.
    """
    odds_list, match, player1, player2 = _parse_find_match_odds_args(args, kwargs)

    if match:
        player1 = player1 or match.get("player1")
        player2 = player2 or match.get("player2")

    match_id = _extract_match_id_from_args_kwargs(args, kwargs)
    if match and not match_id:
        match_id = _safe_int(match.get("event_id") or match.get("match_id") or match.get("id"))

    # 1. Primary list lookup: event id first, then names.
    if odds_list:
        by_id = _find_in_legacy_odds_list_by_id(odds_list, match_id)
        if by_id:
            return by_id

        by_names = _find_in_legacy_odds_list(odds_list, player1, player2)
        if by_names:
            return by_names

    # 2. Tennis API - ATP WTA ITF fallback.
    tennis_odds = None
    tennis_event_id = match_id

    if tennis_event_id:
        tennis_odds = get_tennis_api_atp_wta_itf_odds(tennis_event_id)

    if not tennis_odds and match:
        discovered_event = discover_tennis_api_atp_wta_itf_event(match)
        if discovered_event:
            tennis_event_id = _safe_int(discovered_event.get("event_id") or discovered_event.get("id"))
            if tennis_event_id:
                tennis_odds = get_tennis_api_atp_wta_itf_odds(tennis_event_id)
                if tennis_odds:
                    tennis_odds["tennis_api_discovered_event"] = discovered_event

    if tennis_odds:
        tennis_odds = _to_legacy_odds_item(tennis_odds)
        tennis_odds["odds_source"] = "tennis_api_atp_wta_itf"
        tennis_odds["source"] = "tennis_api_atp_wta_itf"
        return _align_odds_to_match_players(tennis_odds, player1, player2)

    # 3. All Sports API fallback.
    all_sports_event_id = tennis_event_id or match_id
    all_sports_odds = None
    if all_sports_event_id:
        all_sports_odds = get_all_sports_api_winning_odds(all_sports_event_id)

    if all_sports_odds:
        all_sports_odds = _to_legacy_odds_item(all_sports_odds)
        all_sports_odds["odds_source"] = "all_sports_api"
        all_sports_odds["source"] = "all_sports_api"
        return _align_odds_to_match_players(all_sports_odds, player1, player2)

    _record_no_odds(match=match, player1=player1, player2=player2, event_id=match_id, reason="no_odds_after_all_sources")
    return None


# ----------------------------------------------------------------------
# Existing TennisApi / Rapid API compatibility helpers
# ----------------------------------------------------------------------


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    """Compatibility alias for the existing TennisApiClient odds call."""
    try:
        client = TennisApiClient()
        payload = client.get_match_winning_odds(match_id)
        normalized = normalize_winning_odds(payload)
        if normalized:
            normalized["match_id"] = match_id
            normalized["event_id"] = match_id
            normalized["odds_source"] = normalized.get("odds_source") or "rapid_api"
            return normalized
    except Exception as exc:
        logger.info("TennisApi odds failed. match_id=%s error=%s", match_id, exc)
    return None


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
        enriched["no_odds_reason"] = "no_odds_after_all_sources"
        return enriched

    enriched.update(
        {
            "odds_status": "OK",
            "odds_source": odds.get("odds_source") or odds.get("source"),
            "p1_odds": odds.get("p1_odds") or odds.get("home_odds"),
            "p2_odds": odds.get("p2_odds") or odds.get("away_odds"),
            "odds_player1": odds.get("odds_player1") or odds.get("p1_odds"),
            "odds_player2": odds.get("odds_player2") or odds.get("p2_odds"),
            "odds": odds.get("odds_player1") or odds.get("p1_odds"),
            "bookmaker": odds.get("bookmaker"),
            "no_odds_reason": None,
        }
    )
    return enriched


def get_odds(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_odds_for_match(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_match_odds_for_event(match_id: int) -> Optional[Dict[str, Any]]:
    return get_tennisapi_odds(match_id)


# ----------------------------------------------------------------------
# Tennis API - ATP WTA ITF fallback
# ----------------------------------------------------------------------


def _tennis_api_atp_wta_itf_headers() -> Optional[Dict[str, str]]:
    key = os.getenv("TENNIS_API_ATP_WTA_ITF")
    if not key:
        return None
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": TENNIS_API_ATP_WTA_ITF_HOST,
        "Content-Type": "application/json",
    }


def _tennis_api_atp_wta_itf_get(path: str) -> Optional[Dict[str, Any]]:
    headers = _tennis_api_atp_wta_itf_headers()
    if not headers:
        return None

    url = f"{TENNIS_API_ATP_WTA_ITF_BASE_URL}{path}"
    try:
        response = requests.get(url, headers=headers, timeout=25)
        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            logger.info("Tennis API - ATP WTA ITF HTTP %s: %s", response.status_code, path)
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) else {"data": payload}
    except Exception as exc:
        logger.info("Tennis API - ATP WTA ITF request failed: %s path=%s", exc, path)
        return None


def get_tennis_api_atp_wta_itf_categories(day: int, month: int, year: int) -> List[Dict[str, Any]]:
    payload = _tennis_api_atp_wta_itf_get(f"/api/tennis/calendar/{day}/{month}/{year}/categories")
    categories = _extract_collection(payload, keys=("categories", "data", "result", "events"))
    return [item for item in categories if isinstance(item, dict)]


def get_tennis_api_atp_wta_itf_category_events(category_id: Any, day: int, month: int, year: int) -> List[Dict[str, Any]]:
    payload = _tennis_api_atp_wta_itf_get(f"/api/tennis/category/{category_id}/events/{day}/{month}/{year}")
    events = _extract_collection(payload, keys=("events", "data", "result"))
    return [_normalize_tennis_api_event(item) for item in events if isinstance(item, dict)]


def get_tennis_api_atp_wta_itf_events_for_date(day: int, month: int, year: int) -> List[Dict[str, Any]]:
    cache_key = f"{year:04d}-{month:02d}-{day:02d}"
    if cache_key in _TENNIS_API_EVENT_CACHE:
        return _TENNIS_API_EVENT_CACHE[cache_key]

    events: List[Dict[str, Any]] = []
    categories = get_tennis_api_atp_wta_itf_categories(day, month, year)

    for category in categories:
        category_id = category.get("id") or category.get("categoryId") or category.get("cid")
        if not category_id:
            continue
        category_name = category.get("name") or category.get("categoryName") or category.get("slug")
        for event in get_tennis_api_atp_wta_itf_category_events(category_id, day, month, year):
            event["tennis_api_category_id"] = category_id
            event["tennis_api_category_name"] = category_name
            events.append(event)

    _TENNIS_API_EVENT_CACHE[cache_key] = events
    return events


def discover_tennis_api_atp_wta_itf_event(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    player1 = match.get("player1")
    player2 = match.get("player2")
    if not player1 or not player2:
        return None

    dt = _extract_match_date(match)
    if not dt:
        try:
            dt = betting_day_datetime()
        except Exception:
            dt = datetime.now(timezone.utc)

    day = int(dt.day)
    month = int(dt.month)
    year = int(dt.year)

    requested_p1 = _normalize_name(player1)
    requested_p2 = _normalize_name(player2)

    for event in get_tennis_api_atp_wta_itf_events_for_date(day, month, year):
        event_p1 = _normalize_name(event.get("player1") or event.get("homeTeam") or event.get("home"))
        event_p2 = _normalize_name(event.get("player2") or event.get("awayTeam") or event.get("away"))

        direct = _names_match_normalized(requested_p1, event_p1) and _names_match_normalized(requested_p2, event_p2)
        reversed_match = _names_match_normalized(requested_p1, event_p2) and _names_match_normalized(requested_p2, event_p1)

        if direct:
            result = dict(event)
            result["orientation"] = "direct"
            return result

        if reversed_match:
            result = dict(event)
            result["orientation"] = "reversed"
            return result

    return None


def get_tennis_api_atp_wta_itf_odds(event_id: Any) -> Optional[Dict[str, Any]]:
    if not event_id:
        return None

    payload = _tennis_api_atp_wta_itf_get(f"/api/tennis/event/{event_id}/odds")
    normalized = _parse_tennis_api_atp_wta_itf_odds_payload(payload)
    if not normalized:
        return None

    normalized["match_id"] = event_id
    normalized["event_id"] = event_id
    normalized["odds_event_id"] = event_id
    normalized["odds_source"] = "tennis_api_atp_wta_itf"
    normalized["source"] = "tennis_api_atp_wta_itf"
    normalized["bookmaker"] = normalized.get("bookmaker") or "Tennis API - ATP WTA ITF"
    normalized["raw"] = payload
    return normalized


def _parse_tennis_api_atp_wta_itf_odds_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None

    # Generic extraction from nested structures. We only accept a two-way market
    # with two decimal/fractional prices.
    candidates: List[Dict[str, Any]] = []
    _collect_dicts(payload, candidates)

    for item in candidates:
        p1 = _first_float(
            item,
            keys=("odds_player1", "home_odds", "homeOdds", "p1_odds", "odds1", "price1", "home", "od1"),
        )
        p2 = _first_float(
            item,
            keys=("odds_player2", "away_odds", "awayOdds", "p2_odds", "odds2", "price2", "away", "od2"),
        )

        if p1 and p2 and p1 > 1.0 and p2 > 1.0:
            return {
                "odds_player1": p1,
                "odds_player2": p2,
                "p1_odds": p1,
                "p2_odds": p2,
                "home_odds": p1,
                "away_odds": p2,
                "bookmaker": item.get("bookmaker") or item.get("provider") or item.get("providerName"),
            }

    return None


# ----------------------------------------------------------------------
# All Sports API fallback
# ----------------------------------------------------------------------


def _all_sports_headers() -> Optional[Dict[str, str]]:
    key = os.getenv("ALL_SPORTS_API")
    if not key:
        return None
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": ALL_SPORTS_API_HOST,
        "Content-Type": "application/json",
    }


def get_all_sports_api_winning_odds(event_id: Any) -> Optional[Dict[str, Any]]:
    global _ALL_SPORTS_REQUESTS

    if not event_id:
        return None

    headers = _all_sports_headers()
    if not headers:
        return None

    if _ALL_SPORTS_REQUESTS >= ALL_SPORTS_MAX_REQUESTS_PER_RUN:
        logger.info("All Sports API fallback skipped: per-run limit reached")
        return None

    url = f"{ALL_SPORTS_API_BASE_URL}/api/tennis/event/{event_id}/provider/{ALL_SPORTS_PROVIDER_ID}/winning-odds"

    try:
        _ALL_SPORTS_REQUESTS += 1
        response = requests.get(url, headers=headers, timeout=25)
        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            logger.info("All Sports API HTTP %s for event_id=%s", response.status_code, event_id)
            return None
        payload = response.json()
    except Exception as exc:
        logger.info("All Sports API fallback failed. event_id=%s error=%s", event_id, exc)
        return None

    home = payload.get("home") if isinstance(payload, dict) else None
    away = payload.get("away") if isinstance(payload, dict) else None

    if not isinstance(home, dict) or not isinstance(away, dict):
        return None

    p1 = fractional_to_decimal(home.get("fractionalValue"))
    p2 = fractional_to_decimal(away.get("fractionalValue"))

    if not p1 or not p2 or p1 <= 1.0 or p2 <= 1.0:
        return None

    return {
        "match_id": event_id,
        "event_id": event_id,
        "odds_event_id": event_id,
        "odds_player1": round(float(p1), 3),
        "odds_player2": round(float(p2), 3),
        "p1_odds": round(float(p1), 3),
        "p2_odds": round(float(p2), 3),
        "home_odds": round(float(p1), 3),
        "away_odds": round(float(p2), 3),
        "bookmaker": f"AllSports provider {ALL_SPORTS_PROVIDER_ID}",
        "odds_provider": str(ALL_SPORTS_PROVIDER_ID),
        "odds_source": "all_sports_api",
        "source": "all_sports_api",
        "raw": payload,
    }


# ----------------------------------------------------------------------
# Internal normalization helpers
# ----------------------------------------------------------------------


def _parse_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _extract_match_id_from_args_kwargs(args: Sequence[Any], kwargs: Dict[str, Any]) -> Optional[int]:
    for key in ("match_id", "event_id", "id"):
        value = kwargs.get(key)
        if value:
            return _safe_int(value)

    for arg in args:
        if isinstance(arg, dict):
            value = arg.get("match_id") or arg.get("event_id") or arg.get("id")
            if value:
                return _safe_int(value)
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

    for arg in args:
        if isinstance(arg, list):
            odds_list = arg
        elif isinstance(arg, dict):
            match = arg
        elif isinstance(arg, str):
            if not player1:
                player1 = arg
            elif not player2:
                player2 = arg

    if isinstance(kwargs.get("odds_list"), list):
        odds_list = kwargs["odds_list"]

    if isinstance(kwargs.get("match"), dict):
        match = kwargs["match"]

    if match:
        player1 = player1 or match.get("player1") or match.get("home") or match.get("home_team")
        player2 = player2 or match.get("player2") or match.get("away") or match.get("away_team")

    return odds_list, match, player1, player2


def _to_legacy_odds_item(odds: Dict[str, Any]) -> Dict[str, Any]:
    p1 = odds.get("p1_odds") or odds.get("home_odds") or odds.get("odds_player1") or odds.get("odds1") or odds.get("price1")
    p2 = odds.get("p2_odds") or odds.get("away_odds") or odds.get("odds_player2") or odds.get("odds2") or odds.get("price2")
    p1 = _to_float_or_none(p1)
    p2 = _to_float_or_none(p2)

    return {
        "source": odds.get("source") or odds.get("odds_source") or "rapid_api",
        "odds_source": odds.get("odds_source") or odds.get("source") or "rapid_api",
        "bookmaker": odds.get("bookmaker") or odds.get("odds_provider") or "Rapid API",
        "odds_provider": odds.get("odds_provider") or odds.get("provider"),
        "match_id": odds.get("match_id") or odds.get("event_id") or odds.get("id"),
        "event_id": odds.get("event_id") or odds.get("match_id") or odds.get("id"),
        "odds_event_id": odds.get("odds_event_id") or odds.get("event_id") or odds.get("match_id") or odds.get("id"),
        "player1": odds.get("player1") or odds.get("homeTeam") or odds.get("home_team") or odds.get("home"),
        "player2": odds.get("player2") or odds.get("awayTeam") or odds.get("away_team") or odds.get("away"),
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
        "no_odds_reason": None,
        "raw": odds.get("raw", odds),
    }


def _legacy_to_normalized(legacy: Dict[str, Any]) -> Dict[str, Any]:
    p1 = legacy.get("odds_player1") or legacy.get("p1_odds") or legacy.get("home_odds") or legacy.get("odds") or legacy.get("odds1") or legacy.get("price1")
    p2 = legacy.get("odds_player2") or legacy.get("p2_odds") or legacy.get("away_odds") or legacy.get("odds2") or legacy.get("price2")
    return {
        "source": legacy.get("source") or legacy.get("odds_source") or "LegacyOdds",
        "odds_source": legacy.get("odds_source") or legacy.get("source") or "LegacyOdds",
        "match_id": legacy.get("match_id") or legacy.get("event_id"),
        "event_id": legacy.get("event_id") or legacy.get("match_id"),
        "odds_event_id": legacy.get("odds_event_id") or legacy.get("event_id") or legacy.get("match_id"),
        "home_odds": _to_float_or_none(p1),
        "away_odds": _to_float_or_none(p2),
        "p1_odds": _to_float_or_none(p1),
        "p2_odds": _to_float_or_none(p2),
        "odds_player1": _to_float_or_none(p1),
        "odds_player2": _to_float_or_none(p2),
        "bookmaker": legacy.get("bookmaker"),
        "odds_provider": legacy.get("odds_provider"),
        "raw": legacy.get("raw", legacy),
    }


def _find_in_legacy_odds_list_by_id(odds_list: List[Dict[str, Any]], match_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not match_id:
        return None

    match_id_text = str(match_id)
    for item in odds_list:
        for key in ("match_id", "event_id", "id", "odds_event_id"):
            if item.get(key) is not None and str(item.get(key)) == match_id_text:
                normalized = dict(item)
                if _has_two_prices(normalized):
                    return normalized
    return None


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
        item_p1 = item.get("player1") or item.get("home_team") or item.get("home") or item.get("homeTeam")
        item_p2 = item.get("player2") or item.get("away_team") or item.get("away") or item.get("awayTeam")
        norm_item_p1 = _normalize_name(item_p1)
        norm_item_p2 = _normalize_name(item_p2)

        direct = _names_match_normalized(requested_p1, norm_item_p1) and _names_match_normalized(requested_p2, norm_item_p2)
        reversed_match = _names_match_normalized(requested_p1, norm_item_p2) and _names_match_normalized(requested_p2, norm_item_p1)

        if direct and _has_two_prices(item):
            return dict(item)

        if reversed_match and _has_two_prices(item):
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


def _align_odds_to_match_players(odds: Dict[str, Any], player1: Optional[str], player2: Optional[str]) -> Dict[str, Any]:
    if not player1 or not player2:
        return odds

    odds_p1_name = odds.get("player1") or odds.get("homeTeam") or odds.get("home_team")
    odds_p2_name = odds.get("player2") or odds.get("awayTeam") or odds.get("away_team")

    if not odds_p1_name or not odds_p2_name:
        odds["player1"] = player1
        odds["player2"] = player2
        return odds

    requested_p1 = _normalize_name(player1)
    requested_p2 = _normalize_name(player2)
    norm_odds_p1 = _normalize_name(odds_p1_name)
    norm_odds_p2 = _normalize_name(odds_p2_name)

    reversed_match = _names_match_normalized(requested_p1, norm_odds_p2) and _names_match_normalized(requested_p2, norm_odds_p1)

    if reversed_match:
        p1 = odds.get("odds_player2") or odds.get("p2_odds") or odds.get("away_odds")
        p2 = odds.get("odds_player1") or odds.get("p1_odds") or odds.get("home_odds")
        odds = dict(odds)
        odds["player1"] = player1
        odds["player2"] = player2
        odds["odds_player1"] = p1
        odds["odds_player2"] = p2
        odds["p1_odds"] = p1
        odds["p2_odds"] = p2
        odds["home_odds"] = p1
        odds["away_odds"] = p2
        odds["odds"] = p1
        odds["odds1"] = p1
        odds["odds2"] = p2
        return odds

    odds["player1"] = player1
    odds["player2"] = player2
    return odds


def _normalize_tennis_api_event(event: Dict[str, Any]) -> Dict[str, Any]:
    home = event.get("homeTeam") or event.get("home") or event.get("homePlayer") or {}
    away = event.get("awayTeam") or event.get("away") or event.get("awayPlayer") or {}

    if isinstance(home, dict):
        player1 = home.get("name") or home.get("shortName") or home.get("slug")
    else:
        player1 = str(home) if home else None

    if isinstance(away, dict):
        player2 = away.get("name") or away.get("shortName") or away.get("slug")
    else:
        player2 = str(away) if away else None

    event_id = event.get("id") or event.get("eventId") or event.get("matchId")

    return {
        "id": event_id,
        "event_id": event_id,
        "match_id": event_id,
        "player1": player1,
        "player2": player2,
        "homeTeam": player1,
        "awayTeam": player2,
        "startTimestamp": event.get("startTimestamp"),
        "status": event.get("status"),
        "raw": event,
    }


def _extract_collection(payload: Optional[Dict[str, Any]], keys: Sequence[str]) -> List[Any]:
    if payload is None:
        return []

    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _extract_collection(value, keys)
            if nested:
                return nested

    # Some APIs return a dict keyed by ids.
    if all(isinstance(value, dict) for value in payload.values()):
        return list(payload.values())

    return []


def _collect_dicts(value: Any, output: List[Dict[str, Any]]) -> None:
    if isinstance(value, dict):
        output.append(value)
        for nested in value.values():
            _collect_dicts(nested, output)
    elif isinstance(value, list):
        for item in value:
            _collect_dicts(item, output)


def _first_float(item: Dict[str, Any], keys: Sequence[str]) -> Optional[float]:
    for key in keys:
        value = item.get(key)
        if isinstance(value, dict):
            # All Sports-like dicts can have fractionalValue.
            value = value.get("decimal") or value.get("value") or value.get("fractionalValue")
        price = parse_any_odds_value(value)
        if price is not None:
            return price
    return None


def parse_any_odds_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if "/" in text:
        return fractional_to_decimal(text)
    try:
        return float(text)
    except Exception:
        return None


def fractional_to_decimal(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or "/" not in text:
        return parse_any_odds_value(text) if "/" not in text else None
    try:
        numerator, denominator = text.split("/", 1)
        numerator_f = float(numerator)
        denominator_f = float(denominator)
        if denominator_f == 0:
            return None
        return 1.0 + numerator_f / denominator_f
    except Exception:
        return None


def _normalize_name(name: Any) -> str:
    return (
        str(name or "")
        .lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
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
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def _has_two_prices(item: Dict[str, Any]) -> bool:
    p1 = _to_float_or_none(item.get("odds_player1") or item.get("p1_odds") or item.get("home_odds") or item.get("odds1") or item.get("price1"))
    p2 = _to_float_or_none(item.get("odds_player2") or item.get("p2_odds") or item.get("away_odds") or item.get("odds2") or item.get("price2"))
    return p1 is not None and p2 is not None and p1 > 1.0 and p2 > 1.0


def _extract_match_date(match: Dict[str, Any]) -> Optional[datetime]:
    for key in ("match_start", "start_time", "commence_time", "date"):
        value = match.get(key)
        if not value:
            continue
        try:
            text = str(value)
            if text.endswith("Z"):
                text = text.replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _record_no_odds(match: Optional[Dict[str, Any]], player1: Optional[str], player2: Optional[str], event_id: Optional[int], reason: str) -> None:
    item = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}" if player1 and player2 else None,
    }
    if isinstance(match, dict):
        item.update(
            {
                "tournament": match.get("tournament"),
                "category": match.get("category"),
                "match_start": match.get("match_start") or match.get("start_time") or match.get("commence_time"),
                "match_id": match.get("match_id") or match.get("event_id") or match.get("id"),
            }
        )
    _NO_ODDS_REPORT.append(item)


def write_no_odds_report(path: str = "public/no_odds_report.json") -> None:
    if not _NO_ODDS_REPORT:
        return
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(_NO_ODDS_REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.info("Could not write no odds report: %s", exc)


atexit.register(write_no_odds_report)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    odds = fetch_odds(force_refresh=True)
    print(f"Odds found: {len(odds)}")
    for item in odds[:20]:
        print(
            item.get("match_id"),
            item.get("player1"),
            "vs",
            item.get("player2"),
            item.get("odds_player1"),
            item.get("odds_player2"),
            item.get("odds_source"),
        )
