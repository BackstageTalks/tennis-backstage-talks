import json
import logging
import os
import unicodedata
from datetime import timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from tennisapi_client import TennisApiClient, normalize_winning_odds
from tennisapi_cache import get_daily_odds_items, betting_day_datetime

logger = logging.getLogger(__name__)

_ODDS_CACHE: Optional[List[Dict[str, Any]]] = None
_NO_ODDS_REPORT: List[Dict[str, Any]] = []
_PLAYER_ALIASES_CACHE: Optional[Dict[str, List[str]]] = None


# ----------------------------------------------------------------------
# Public API expected by prediction_engine_core.py
# ----------------------------------------------------------------------


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """Fetch daily odds list used by prediction_engine_core.

    Source order for daily list:
      1. TennisApi PRO daily cache / event odds fallback from tennisapi_cache.
      2. Direct event fallback is handled by find_match_odds() when match_id exists.

    The heavy direct fallbacks are intentionally not called for every possible match here;
    they are called on demand by find_match_odds() to avoid wasting limited requests.
    """
    global _ODDS_CACHE

    if kwargs.get("force_refresh"):
        _ODDS_CACHE = None

    if _ODDS_CACHE is not None:
        return _ODDS_CACHE

    explicit_match_id = _extract_match_id_from_args_kwargs(args, kwargs)
    if explicit_match_id:
        item = get_event_odds_chain(int(explicit_match_id))
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
            logger.warning("Daily odds items failed date=%s error=%s", target_date.date(), exc)

    # Deduplicate by event id, then by match name.
    seen = set()
    unique_items: List[Dict[str, Any]] = []
    for item in odds_items:
        key = item.get("event_id") or item.get("match_id") or item.get("id") or item.get("match")
        key = str(key) if key is not None else json.dumps(item, sort_keys=True, default=str)[:200]
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(_standardize_legacy_item(item))

    _ODDS_CACHE = unique_items
    print("Tennis odds fetched:", len(_ODDS_CACHE))
    logger.info("Tennis odds fetched: %s", len(_ODDS_CACHE))
    return _ODDS_CACHE


async def fetch_odds_async(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return fetch_odds(*args, **kwargs)


def find_match_odds(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """Find odds for a match using id-first and robust name matching.

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
        for key in ("odds_event_id", "tennis_api_event_id", "rapid_event_id", "match_id", "event_id", "id"):
            value = match.get(key)
            if value:
                match_id = value
                break
        player1 = player1 or match.get("player1") or match.get("home") or match.get("home_team") or match.get("pick")
        player2 = player2 or match.get("player2") or match.get("away") or match.get("away_team") or match.get("opponent")

    # 1) Exact id matching against fetched daily odds.
    if match_id:
        for item in odds_list:
            for key in ("odds_event_id", "match_id", "event_id", "id"):
                item_id = item.get(key)
                if item_id is not None and str(item_id) == str(match_id):
                    found = _standardize_legacy_item(dict(item))
                    found["matching_direction"] = "event_id"
                    found["matching_score"] = 1.0
                    return found

        # 2) On-demand direct fallback chain for this id.
        direct = None
        try:
            direct = get_event_odds_chain(int(match_id))
        except Exception as exc:
            logger.debug("Direct event odds chain failed match_id=%s error=%s", match_id, exc)

        if direct:
            item = _to_legacy_odds_item(direct)
            if player1:
                item["player1"] = player1
            if player2:
                item["player2"] = player2
            item["matching_direction"] = "direct_event_api"
            item["matching_score"] = 1.0
            return item

    # 3) Robust name matching against fetched odds list.
    matched = _find_in_legacy_odds_list(odds_list, player1, player2)
    if matched:
        return matched

    _append_no_odds_report(match, player1, player2, "event_id_and_name_matching_failed")
    return None


# ----------------------------------------------------------------------
# Three-source direct event odds chain
# ----------------------------------------------------------------------


def get_event_odds_chain(event_id: int) -> Optional[Dict[str, Any]]:
    """Try all direct event odds sources in project-agreed order."""
    # 1) Primary: Rapid API / TennisApi PRO.
    primary = get_tennisapi_pro_odds(event_id)
    if primary:
        return primary

    # 2) Second fallback: Tennis API - ATP WTA ITF.
    second = get_tennis_api_atp_wta_itf_odds(event_id)
    if second:
        return second

    # 3) Last fallback: All Sports API.
    third = get_all_sports_odds(event_id)
    if third:
        return third

    return None


def get_tennisapi_pro_odds(event_id: int) -> Optional[Dict[str, Any]]:
    try:
        client = TennisApiClient()
        payload = client.get_match_winning_odds(event_id)
        normalized = normalize_winning_odds(payload)
        if normalized:
            normalized["source"] = normalized.get("source") or "TennisApiPro"
            normalized["odds_source"] = normalized.get("odds_source") or "TennisApiPro"
            normalized["bookmaker"] = normalized.get("bookmaker") or "TennisApi PRO"
            normalized["match_id"] = event_id
            normalized["event_id"] = event_id
            return normalized
    except Exception as exc:
        logger.info("TennisApi PRO odds failed event_id=%s error=%s", event_id, exc)
    return None


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    """Backward-compatible alias used elsewhere in the project."""
    return get_event_odds_chain(match_id)


def get_tennis_api_atp_wta_itf_odds(event_id: int) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("TENNIS_API_ATP_WTA_ITF", "").strip()
    if not api_key or requests is None:
        return None

    host = "tennis-api-atp-wta-itf.p.rapidapi.com"
    # Known endpoint from your RapidAPI snippet.
    url = f"https://{host}/tennis/v2/extend/api/odds/arbitrage/{event_id}"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": host,
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code >= 400:
            logger.info("Tennis API ATP/WTA/ITF odds HTTP %s event_id=%s", response.status_code, event_id)
            return None
        payload = response.json()
        found = _recursive_find_odds_pair(payload)
        if not found:
            return None
        first, second, raw_node = found
        return {
            "source": "TennisApiAtpWtaItf",
            "odds_source": "TennisApiAtpWtaItf",
            "bookmaker": _extract_provider_name(raw_node) or "Tennis API - ATP WTA ITF",
            "match_id": event_id,
            "event_id": event_id,
            "home_odds": first,
            "away_odds": second,
            "p1_odds": first,
            "p2_odds": second,
            "odds_player1": first,
            "odds_player2": second,
            "raw": payload,
            "raw_odds_node": raw_node,
        }
    except Exception as exc:
        logger.info("Tennis API ATP/WTA/ITF odds failed event_id=%s error=%s", event_id, exc)
        return None


def get_all_sports_odds(event_id: int) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("ALL_SPORTS_API", "").strip()
    if not api_key or requests is None:
        return None

    url = f"https://allsportsapi2.p.rapidapi.com/api/tennis/event/{event_id}/provider/1/winning-odds"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "allsportsapi2.p.rapidapi.com",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code >= 400:
            logger.info("All Sports odds HTTP %s event_id=%s", response.status_code, event_id)
            return None
        payload = response.json()
        normalized = normalize_winning_odds(payload)
        if not normalized:
            found = _recursive_find_odds_pair(payload)
            if not found:
                return None
            first, second, raw_node = found
            normalized = {
                "home_odds": first,
                "away_odds": second,
                "p1_odds": first,
                "p2_odds": second,
                "raw": payload,
                "raw_odds_node": raw_node,
            }
        normalized["source"] = "AllSportsApi"
        normalized["odds_source"] = "AllSportsApi"
        normalized["bookmaker"] = normalized.get("bookmaker") or "AllSportsApi provider 1"
        normalized["match_id"] = event_id
        normalized["event_id"] = event_id
        return normalized
    except Exception as exc:
        logger.info("All Sports odds failed event_id=%s error=%s", event_id, exc)
        return None


# ----------------------------------------------------------------------
# Compatibility aliases
# ----------------------------------------------------------------------


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
    return get_event_odds_chain(match_id)


# ----------------------------------------------------------------------
# Internal helpers
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

    positional: List[Any] = []
    for arg in args:
        if isinstance(arg, list):
            odds_list = arg
        else:
            positional.append(arg)

    if positional and isinstance(positional[0], dict):
        match = positional.pop(0)
    if positional and player1 is None:
        player1 = str(positional.pop(0))
    if positional and player2 is None:
        player2 = str(positional.pop(0))
    return odds_list, match, player1, player2


def _standardize_legacy_item(item: Dict[str, Any]) -> Dict[str, Any]:
    p1 = item.get("odds_player1") or item.get("p1_odds") or item.get("home_odds") or item.get("odds1") or item.get("price1")
    p2 = item.get("odds_player2") or item.get("p2_odds") or item.get("away_odds") or item.get("odds2") or item.get("price2")
    if p1 is not None:
        item["odds_player1"] = _to_float_or_none(p1)
        item["p1_odds"] = item["odds_player1"]
        item["home_odds"] = item["odds_player1"]
        item["odds1"] = item["odds_player1"]
        item["price1"] = item["odds_player1"]
        item["odds"] = item["odds_player1"]
    if p2 is not None:
        item["odds_player2"] = _to_float_or_none(p2)
        item["p2_odds"] = item["odds_player2"]
        item["away_odds"] = item["odds_player2"]
        item["odds2"] = item["odds_player2"]
        item["price2"] = item["odds_player2"]
    item["odds_source"] = item.get("odds_source") or item.get("source") or "UnknownOdds"
    item["source"] = item.get("source") or item.get("odds_source")
    return item


def _to_legacy_odds_item(odds: Dict[str, Any]) -> Dict[str, Any]:
    odds = _standardize_legacy_item(dict(odds))
    p1 = odds.get("p1_odds") or odds.get("home_odds") or odds.get("odds_player1")
    p2 = odds.get("p2_odds") or odds.get("away_odds") or odds.get("odds_player2")
    return {
        "source": odds.get("source") or odds.get("odds_source") or "TennisOdds",
        "odds_source": odds.get("odds_source") or odds.get("source") or "TennisOdds",
        "bookmaker": odds.get("bookmaker") or odds.get("odds_provider") or odds.get("source") or "TennisOdds",
        "match_id": odds.get("match_id") or odds.get("event_id"),
        "event_id": odds.get("event_id") or odds.get("match_id"),
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
    legacy = _standardize_legacy_item(dict(legacy))
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


def _valid_legacy_odds_item(item: Dict[str, Any]) -> bool:
    p1 = item.get("odds_player1") or item.get("p1_odds") or item.get("home_odds") or item.get("odds1") or item.get("price1")
    p2 = item.get("odds_player2") or item.get("p2_odds") or item.get("away_odds") or item.get("odds2") or item.get("price2")
    return _to_float_or_none(p1) is not None and _to_float_or_none(p2) is not None


def _find_in_legacy_odds_list(
    odds_list: List[Dict[str, Any]],
    player1: Optional[str],
    player2: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not player1 or not player2:
        return None

    best_item: Optional[Dict[str, Any]] = None
    best_score = 0.0
    best_reversed = False

    for item in odds_list:
        if not _valid_legacy_odds_item(item):
            continue
        item_p1 = item.get("player1") or item.get("home_team") or item.get("home") or item.get("homePlayer")
        item_p2 = item.get("player2") or item.get("away_team") or item.get("away") or item.get("awayPlayer")
        if not item_p1 or not item_p2:
            continue

        direct_score = _match_pair_score(player1, player2, item_p1, item_p2)
        reversed_score = _match_pair_score(player1, player2, item_p2, item_p1)

        if direct_score >= 0.90 and direct_score >= reversed_score:
            found = _standardize_legacy_item(dict(item))
            found["matching_direction"] = "direct"
            found["matching_score"] = round(direct_score, 4)
            return found
        if reversed_score >= 0.90:
            found = _swap_legacy_item(item, player1, player2)
            found["matching_score"] = round(reversed_score, 4)
            return found

        if direct_score > best_score:
            best_item = dict(item)
            best_score = direct_score
            best_reversed = False
        if reversed_score > best_score:
            best_item = dict(item)
            best_score = reversed_score
            best_reversed = True

    if best_item and best_score >= 0.86:
        found = _swap_legacy_item(best_item, player1, player2) if best_reversed else _standardize_legacy_item(dict(best_item))
        found["matching_direction"] = "fuzzy_reversed" if best_reversed else "fuzzy_direct"
        found["matching_score"] = round(best_score, 4)
        return found
    return None


def _swap_legacy_item(item: Dict[str, Any], player1: Optional[str], player2: Optional[str]) -> Dict[str, Any]:
    swapped = _standardize_legacy_item(dict(item))
    p1 = item.get("odds_player2") or item.get("p2_odds") or item.get("away_odds") or item.get("odds2") or item.get("price2")
    p2 = item.get("odds_player1") or item.get("p1_odds") or item.get("home_odds") or item.get("odds1") or item.get("price1")
    swapped["player1"] = player1 or item.get("player2")
    swapped["player2"] = player2 or item.get("player1")
    swapped["odds_player1"] = _to_float_or_none(p1)
    swapped["odds_player2"] = _to_float_or_none(p2)
    swapped["p1_odds"] = swapped["odds_player1"]
    swapped["p2_odds"] = swapped["odds_player2"]
    swapped["home_odds"] = swapped["odds_player1"]
    swapped["away_odds"] = swapped["odds_player2"]
    swapped["odds"] = swapped["odds_player1"]
    swapped["odds1"] = swapped["odds_player1"]
    swapped["odds2"] = swapped["odds_player2"]
    swapped["matching_direction"] = "reversed"
    return swapped


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_name(name: Any) -> str:
    text = _strip_accents(str(name or "").lower())
    for token in [".", ",", "'", "`", "’", "´", "-", "_", "(", ")", "[", "]"]:
        text = text.replace(token, " ")
    return " ".join(text.split())


def _load_player_aliases() -> Dict[str, List[str]]:
    global _PLAYER_ALIASES_CACHE
    if _PLAYER_ALIASES_CACHE is not None:
        return _PLAYER_ALIASES_CACHE
    path = Path("data/player_aliases.json")
    aliases: Dict[str, List[str]] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for canonical, values in raw.items():
                    key = _normalize_name(canonical)
                    if isinstance(values, list):
                        aliases[key] = [_normalize_name(item) for item in values if item]
                    elif values:
                        aliases[key] = [_normalize_name(values)]
        except Exception as exc:
            logger.warning("Failed to load player aliases path=%s error=%s", path, exc)
    _PLAYER_ALIASES_CACHE = aliases
    return aliases


def _name_variants(name: Any) -> set:
    normalized = _normalize_name(name)
    parts = normalized.split()
    variants = set()
    if normalized:
        variants.add(normalized)
    if parts:
        variants.add(parts[-1])
    if len(parts) >= 2:
        variants.add(" ".join(parts[-2:]))
        variants.add(f"{parts[0][0]} {parts[-1]}")
        variants.add(f"{parts[-1]} {parts[0]}")
        variants.add(" ".join(reversed(parts)))

    aliases = _load_player_aliases()
    if normalized in aliases:
        variants.update(aliases[normalized])
    for canonical, alias_values in aliases.items():
        if normalized in alias_values:
            variants.add(canonical)
            variants.update(alias_values)
    return {variant for variant in variants if variant}


def _names_match_normalized(a: str, b: str) -> bool:
    if not a or not b:
        return False
    variants_a = _name_variants(a)
    variants_b = _name_variants(b)
    if variants_a.intersection(variants_b):
        return True
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio() >= 0.90


def _match_pair_score(req1: str, req2: str, item1: str, item2: str) -> float:
    r1 = _normalize_name(req1)
    r2 = _normalize_name(req2)
    i1 = _normalize_name(item1)
    i2 = _normalize_name(item2)
    s1 = 1.0 if _names_match_normalized(r1, i1) else SequenceMatcher(None, r1, i1).ratio()
    s2 = 1.0 if _names_match_normalized(r2, i2) else SequenceMatcher(None, r2, i2).ratio()
    return min(s1, s2)


def _extract_decimal(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, str) and "/" in value:
            left, right = value.split("/", 1)
            denominator = float(right)
            if denominator == 0:
                return None
            return round(1.0 + float(left) / denominator, 4)
        number = float(value)
        if number > 1.0:
            return round(number, 4)
    except Exception:
        return None
    return None


def _recursive_find_odds_pair(payload: Any) -> Optional[Tuple[float, float, Any]]:
    if isinstance(payload, dict):
        first = _extract_decimal(payload.get("od1") or payload.get("odds1") or payload.get("price1") or payload.get("home_odds"))
        second = _extract_decimal(payload.get("od2") or payload.get("odds2") or payload.get("price2") or payload.get("away_odds"))
        if first and second:
            return first, second, payload

        home = payload.get("home")
        away = payload.get("away")
        if isinstance(home, dict) and isinstance(away, dict):
            first = _extract_decimal(home.get("fractionalValue") or home.get("decimalValue") or home.get("value") or home.get("odds") or home.get("price"))
            second = _extract_decimal(away.get("fractionalValue") or away.get("decimalValue") or away.get("value") or away.get("odds") or away.get("price"))
            if first and second:
                return first, second, payload

        for key in ("choices", "options", "outcomes", "selections"):
            choices = payload.get(key)
            if isinstance(choices, list) and len(choices) >= 2 and isinstance(choices[0], dict) and isinstance(choices[1], dict):
                first = _extract_decimal(choices[0].get("fractionalValue") or choices[0].get("decimalValue") or choices[0].get("value") or choices[0].get("odds") or choices[0].get("price"))
                second = _extract_decimal(choices[1].get("fractionalValue") or choices[1].get("decimalValue") or choices[1].get("value") or choices[1].get("odds") or choices[1].get("price"))
                if first and second:
                    return first, second, payload

        for value in payload.values():
            found = _recursive_find_odds_pair(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _recursive_find_odds_pair(item)
            if found:
                return found
    return None


def _extract_provider_name(raw_node: Any) -> Optional[str]:
    if not isinstance(raw_node, dict):
        return None
    for key in ("bookmaker", "provider", "source", "sourceName", "name"):
        value = raw_node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict) and value.get("name"):
            return str(value.get("name"))
    return None


def _append_no_odds_report(match: Optional[Dict[str, Any]], player1: Optional[str], player2: Optional[str], reason: str) -> None:
    record = {
        "match": (match or {}).get("match") if isinstance(match, dict) else None,
        "player1": player1,
        "player2": player2,
        "event_id": (match or {}).get("event_id") if isinstance(match, dict) else None,
        "match_id": (match or {}).get("match_id") if isinstance(match, dict) else None,
        "id": (match or {}).get("id") if isinstance(match, dict) else None,
        "tournament": (match or {}).get("tournament") if isinstance(match, dict) else None,
        "start_time": ((match or {}).get("start_time") or (match or {}).get("time")) if isinstance(match, dict) else None,
        "no_odds_reason": reason,
    }
    _NO_ODDS_REPORT.append(record)
    try:
        path = Path("public/no_odds_report.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_NO_ODDS_REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


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
        print(
            item.get("match_id"),
            item.get("player1"),
            "vs",
            item.get("player2"),
            item.get("odds_player1"),
            item.get("odds_player2"),
            item.get("odds_source"),
        )
