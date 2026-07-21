import logging
import os
import re
import unicodedata
from datetime import timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tennisapi_client import TennisApiClient, normalize_winning_odds
from tennisapi_cache import (
    betting_day_datetime,
    get_daily_odds_items,
    normalize_event_market_odds_payload,
    provider_id,
)

logger = logging.getLogger(__name__)

_ODDS_CACHE: Optional[List[Dict[str, Any]]] = None
_EVENT_ODDS_CACHE: Dict[int, Optional[Dict[str, Any]]] = {}

# Extra transliteration for characters not always decomposed by NFKD.
_TRANSLATE = str.maketrans(
    {
        "ł": "l", "Ł": "L",
        "đ": "d", "Đ": "D",
        "ð": "d", "Ð": "D",
        "þ": "th", "Þ": "Th",
        "ß": "ss",
        "ø": "o", "Ø": "O",
        "æ": "ae", "Æ": "Ae",
        "œ": "oe", "Œ": "Oe",
    }
)


# ----------------------------------------------------------------------
# Public API expected by prediction_engine_core.py
# ----------------------------------------------------------------------


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """TennisApi PRO-primary odds fetcher.

    This function intentionally does NOT call limited fallback APIs such as
    AllSportsApi or Tennis API - ATP WTA ITF. Those should be called only later,
    if needed, for a small TOP/TG shortlist after TennisApi PRO has failed.

    Source priority here:
        1) TennisApi PRO daily odds batch cache
        2) TennisApi PRO event winning odds fallback inside tennisapi_cache
        3) TennisApi PRO event-level endpoints when explicit event_id is requested
    """
    global _ODDS_CACHE

    if kwargs.get("force_refresh"):
        _ODDS_CACHE = None
        _EVENT_ODDS_CACHE.clear()

    explicit_match_id = _extract_match_id_from_args_kwargs(args, kwargs)
    if explicit_match_id:
        item = get_tennisapi_odds(int(explicit_match_id))
        return [_to_legacy_odds_item(item)] if item else []

    if _ODDS_CACHE is not None:
        return _ODDS_CACHE

    odds_items: List[Dict[str, Any]] = []
    days_ahead = _parse_int_env("ODDS_SCAN_DAYS_AHEAD", 1)
    days_back = _parse_int_env("ODDS_SCAN_DAYS_BACK", 0)
    force_refresh = bool(kwargs.get("force_refresh", False))
    include_event_fallback = _bool_env("TENNISAPI_INCLUDE_EVENT_FALLBACK", True)

    today = betting_day_datetime()
    for delta in range(-days_back, days_ahead + 1):
        target_date = today + timedelta(days=delta)
        try:
            daily_items = get_daily_odds_items(
                target_date=target_date,
                force_refresh=force_refresh,
                include_event_fallback=include_event_fallback,
            )
            odds_items.extend(daily_items)
        except Exception as exc:
            logger.warning(
                "TennisApi daily odds items failed date=%s error=%s",
                target_date.date(),
                exc,
            )

    # Deduplicate by preferred event id first; if missing, use pair key.
    seen = set()
    unique_items: List[Dict[str, Any]] = []
    for item in odds_items:
        key = _odds_item_identity_key(item)
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
    """Backward-compatible paid TennisApi matcher.

    Supported call patterns:
        find_match_odds(match)
        find_match_odds(odds_list, match)
        find_match_odds(player1, player2)
        find_match_odds(player1, player2, odds_list)
        find_match_odds(odds_list, player1, player2)

    Matching order:
        1) event_id / match_id in current TennisApi PRO odds list
        2) normalized, order-insensitive player-pair match in current odds list
        3) TennisApi PRO event-level endpoints for explicit event_id

    The player-pair matcher is intentionally robust for:
        - diacritics: Garcia == García, Poljicak == Poljičak
        - initials: E. Avanesyan == Elina Avanesyan
        - surname-first: Avanesyan E. == Elina Avanesyan
        - reversed home/away order
        - punctuation/hyphen/underscore differences
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
            if item_id and str(item_id) == str(match_id):
                matched = _orient_odds_to_requested_players(dict(item), player1, player2)
                matched["odds_match_method"] = "EVENT_ID_LIST"
                matched["odds_match_score"] = 2.0
                return matched

    # Before spending a per-event PRO call, try pair matching against the paid batch.
    # This fixes stale/different event ids and most name-order issues.
    pair_match = _find_in_legacy_odds_list(odds_list, player1, player2)
    if pair_match:
        return pair_match

    if match_id:
        direct = get_tennisapi_odds(int(match_id))
        if direct:
            item = _to_legacy_odds_item(direct)
            item = _orient_odds_to_requested_players(item, player1, player2)
            if player1:
                item["player1"] = player1
            if player2:
                item["player2"] = player2
            item["odds_match_method"] = "EVENT_ID_DETAIL"
            item["odds_match_score"] = 2.0
            return item

    return None


# ----------------------------------------------------------------------
# TennisApi PRO event odds endpoints
# ----------------------------------------------------------------------


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    """Try all paid TennisApi PRO event-level odds endpoints for an event id."""
    if match_id in _EVENT_ODDS_CACHE:
        return _EVENT_ODDS_CACHE[match_id]

    try:
        client = TennisApiClient()
    except Exception as exc:
        logger.info("TennisApi client init failed. match_id=%s error=%s", match_id, exc)
        _EVENT_ODDS_CACHE[match_id] = None
        return None

    attempts = [
        (
            "TennisApiMatchWinningOdds",
            lambda: client.get_match_winning_odds(match_id, provider_id()),
            normalize_winning_odds,
        ),
        (
            "TennisApiMatchBettingOdds",
            lambda: client.get_match_betting_odds(match_id),
            normalize_event_market_odds_payload,
        ),
        (
            "TennisApiAllOddsForEvent",
            lambda: client.get_all_odds_for_event(match_id, provider_id()),
            normalize_event_market_odds_payload,
        ),
        (
            "TennisApiMatchFeaturedOdds",
            lambda: client.get_match_featured_odds(match_id),
            normalize_event_market_odds_payload,
        ),
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
                _EVENT_ODDS_CACHE[match_id] = normalized
                return normalized
        except Exception as exc:
            logger.debug(
                "TennisApi event odds candidate failed source=%s match_id=%s error=%s",
                source_name,
                match_id,
                exc,
            )

    logger.info("TennisApi PRO event odds unavailable. match_id=%s", match_id)
    _EVENT_ODDS_CACHE[match_id] = None
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

    p1, p2 = _extract_odds_pair(odds)
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
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


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


def _first_present(item: Dict[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None and value != "":
            return value
    return None


def _extract_odds_pair(item: Dict[str, Any]) -> Tuple[Any, Any]:
    """Extract both sides of a win market odds pair from normalized or legacy payloads."""
    p1 = _first_present(
        item,
        (
            "odds_player1",
            "p1_odds",
            "home_odds",
            "odds1",
            "price1",
            "home_price",
            "player1_odds",
            "homeDecimalOdds",
            "home_decimal_odds",
        ),
    )
    p2 = _first_present(
        item,
        (
            "odds_player2",
            "p2_odds",
            "away_odds",
            "odds2",
            "price2",
            "away_price",
            "player2_odds",
            "awayDecimalOdds",
            "away_decimal_odds",
        ),
    )

    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    if p1 is None and raw:
        p1 = _first_present(raw, ("odds_player1", "p1_odds", "home_odds", "odds1", "price1", "home_price"))
    if p2 is None and raw:
        p2 = _first_present(raw, ("odds_player2", "p2_odds", "away_odds", "odds2", "price2", "away_price"))

    return p1, p2


def _apply_odds_pair_aliases(item: Dict[str, Any], p1: Any, p2: Any) -> Dict[str, Any]:
    updated = dict(item)
    updated["home_odds"] = p1
    updated["away_odds"] = p2
    updated["p1_odds"] = p1
    updated["p2_odds"] = p2
    updated["odds_player1"] = p1
    updated["odds_player2"] = p2
    updated["odds1"] = p1
    updated["odds2"] = p2
    updated["price1"] = p1
    updated["price2"] = p2
    return updated


def _orient_odds_to_requested_players(
    odds: Dict[str, Any],
    requested_player1: Optional[str],
    requested_player2: Optional[str],
) -> Dict[str, Any]:
    """Orient odds_player1/odds_player2 to match prediction player1/player2.

    TennisApi odds may have the same event id but reversed home/away order.
    Corq/Cloq need odds_player1 and odds_player2 aligned to prediction player1/player2.
    """
    if not requested_player1 or not requested_player2:
        return odds

    item_p1 = _item_player1(odds)
    item_p2 = _item_player2(odds)
    if not item_p1 or not item_p2:
        return odds

    req1 = _normalize_name(requested_player1)
    req2 = _normalize_name(requested_player2)
    item1 = _normalize_name(item_p1)
    item2 = _normalize_name(item_p2)

    direct = _name_match_score(req1, item1) + _name_match_score(req2, item2)
    reverse = _name_match_score(req1, item2) + _name_match_score(req2, item1)

    if reverse <= direct:
        return odds

    p1, p2 = _extract_odds_pair(odds)
    oriented = _apply_odds_pair_aliases(odds, p2, p1)
    oriented["player1"] = requested_player1
    oriented["player2"] = requested_player2
    oriented["odds_matching_direction"] = "REVERSED_TO_MATCH_PLAYERS"
    return oriented


def _to_legacy_odds_item(odds: Dict[str, Any]) -> Dict[str, Any]:
    p1, p2 = _extract_odds_pair(odds)
    return {
        "source": odds.get("source") or odds.get("odds_source") or "TennisApi",
        "odds_source": odds.get("odds_source") or odds.get("source") or "TennisApi",
        "bookmaker": odds.get("bookmaker") or "TennisApi",
        "match_id": odds.get("match_id") or odds.get("event_id"),
        "event_id": odds.get("event_id") or odds.get("match_id"),
        "player1": _name_from_obj(odds.get("player1") or odds.get("home") or odds.get("home_team")),
        "player2": _name_from_obj(odds.get("player2") or odds.get("away") or odds.get("away_team")),
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
    p1, p2 = _extract_odds_pair(legacy)
    if p1 is None:
        p1 = legacy.get("odds")
    return {
        "source": legacy.get("source") or legacy.get("odds_source") or "LegacyOdds",
        "odds_source": legacy.get("odds_source") or legacy.get("source") or "LegacyOdds",
        "match_id": legacy.get("match_id") or legacy.get("event_id"),
        "event_id": legacy.get("event_id") or legacy.get("match_id"),
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
    """Find odds by robust player-pair matching."""
    if not player1 or not player2:
        return None

    req_p1 = _normalize_name(player1)
    req_p2 = _normalize_name(player2)
    req_pair = _pair_key(player1, player2)

    best: Optional[Tuple[float, str, Dict[str, Any], bool]] = None

    for item in odds_list:
        item_p1 = _item_player1(item)
        item_p2 = _item_player2(item)
        if not item_p1 or not item_p2:
            continue

        item_pair = _pair_key(item_p1, item_p2)
        direct_score = _name_match_score(req_p1, _normalize_name(item_p1)) + _name_match_score(req_p2, _normalize_name(item_p2))
        reverse_score = _name_match_score(req_p1, _normalize_name(item_p2)) + _name_match_score(req_p2, _normalize_name(item_p1))

        if req_pair and req_pair == item_pair:
            direct_score = max(direct_score, 1.98)

        candidate_score = direct_score
        reversed_order = False
        method = "PLAYER_PAIR_DIRECT"
        if reverse_score > direct_score:
            candidate_score = reverse_score
            reversed_order = True
            method = "PLAYER_PAIR_REVERSED"

        if candidate_score >= 1.42:
            if best is None or candidate_score > best[0]:
                best = (candidate_score, method, dict(item), reversed_order)

    if best is None:
        return None

    score, method, matched, reversed_order = best
    matched["odds_match_method"] = method
    matched["odds_match_score"] = round(score, 3)

    if reversed_order:
        original_p1, original_p2 = _extract_odds_pair(matched)
        matched = _apply_odds_pair_aliases(matched, original_p2, original_p1)
        matched["player1"] = player1
        matched["player2"] = player2
        matched["odds"] = original_p2
        matched["odds_matching_direction"] = "REVERSED_TO_MATCH_PLAYERS"

    return matched


def _item_player1(item: Dict[str, Any]) -> str:
    return _name_from_obj(
        item.get("player1")
        or item.get("home_team")
        or item.get("homeTeam")
        or item.get("home")
        or item.get("home_name")
        or item.get("participant1")
    )


def _item_player2(item: Dict[str, Any]) -> str:
    return _name_from_obj(
        item.get("player2")
        or item.get("away_team")
        or item.get("awayTeam")
        or item.get("away")
        or item.get("away_name")
        or item.get("participant2")
    )


def _name_from_obj(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in (
            "name",
            "fullName",
            "full_name",
            "displayName",
            "display_name",
            "shortName",
            "short_name",
            "slug",
        ):
            if value.get(key):
                return str(value.get(key))
        return ""
    return str(value)


def _normalize_name(name: Any) -> str:
    text = _name_from_obj(name).strip().lower().translate(_TRANSLATE)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace(".", " ").replace("-", " ").replace("_", " ").replace(",", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _compact_name(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_name(name))


def _pair_key(player1: Any, player2: Any) -> str:
    names = sorted([_compact_name(player1), _compact_name(player2)])
    return "|".join(names)


def _odds_item_identity_key(item: Dict[str, Any]) -> str:
    event_id = item.get("event_id") or item.get("match_id") or item.get("id")
    if event_id:
        return f"event:{event_id}"
    p1 = _item_player1(item)
    p2 = _item_player2(item)
    if p1 and p2:
        return f"pair:{_pair_key(p1, p2)}"
    return f"raw:{str(item)[:250]}"


def _name_variants(normalized: str) -> set:
    parts = normalized.split()
    keys = set()
    compact = _compact_name(normalized)
    if normalized:
        keys.add(normalized)
    if compact:
        keys.add(compact)
    if parts:
        last = parts[-1]
        keys.add(last)
        keys.add(_compact_name(last))
    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        last_two = " ".join(parts[-2:])
        keys.add(last_two)
        keys.add(_compact_name(last_two))
        keys.add(f"{first[0]} {last}")
        keys.add(f"{first[0]}{last}")
        # surname-first forms: Avanesyan E. == Elina Avanesyan
        keys.add(f"{last} {first[0]}")
        keys.add(f"{last}{first[0]}")
        if len(parts) > 2:
            initials = "".join(part[0] for part in parts[:-1])
            keys.add(f"{initials} {last}")
            keys.add(f"{initials}{last}")
    return {key for key in keys if key}


def _name_match_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ac = _compact_name(a)
    bc = _compact_name(b)
    if ac and ac == bc:
        return 1.0

    av = _name_variants(a)
    bv = _name_variants(b)
    common = av.intersection(bv)
    if common:
        # single surname match is useful but weaker than initial+surname/full match
        if any(len(key) >= 4 and " " not in key for key in common):
            return 0.72
        return 0.9

    a_parts = a.split()
    b_parts = b.split()
    if a_parts and b_parts and a_parts[-1] == b_parts[-1]:
        if a_parts[0][0] == b_parts[0][0]:
            return 0.86
        return 0.68

    ratio = SequenceMatcher(None, ac, bc).ratio() if ac and bc else 0.0
    if ratio >= 0.92:
        return 0.84
    if ratio >= 0.86:
        return 0.74
    return 0.0


def _names_match_normalized(a: str, b: str) -> bool:
    return _name_match_score(a, b) >= 0.68


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
