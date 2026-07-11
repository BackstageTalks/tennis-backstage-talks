import json
import logging
import os
import http.client
import unicodedata
from datetime import timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tennisapi_client import TennisApiClient, normalize_winning_odds, fractional_to_decimal
from tennisapi_cache import get_daily_odds_items, betting_day_datetime

logger = logging.getLogger(__name__)

_ODDS_CACHE: Optional[List[Dict[str, Any]]] = None
_NO_ODDS_REPORT: List[Dict[str, Any]] = []

RAPID_HOST = "tennisapi1.p.rapidapi.com"
TENNIS_API_ATP_WTA_ITF_HOST = "tennis-api-atp-wta-itf.p.rapidapi.com"
ALL_SPORTS_HOST = "allsportsapi2.p.rapidapi.com"


# ----------------------------------------------------------------------
# Public API expected by prediction_engine_core.py
# ----------------------------------------------------------------------


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """Primary odds list used by prediction_engine_core.

    This keeps the existing working behaviour: load daily TennisApi odds items
    from tennisapi_cache. Additional fallback APIs are executed lazily inside
    find_match_odds() for a specific event_id, because fallback APIs generally
    need a concrete event id and may have strict daily limits.
    """
    global _ODDS_CACHE, _NO_ODDS_REPORT

    if kwargs.get("force_refresh"):
        _ODDS_CACHE = None
        _NO_ODDS_REPORT = []
        _write_no_odds_report()

    if _ODDS_CACHE is not None:
        return _ODDS_CACHE

    explicit_match_id = _extract_match_id_from_args_kwargs(args, kwargs)
    if explicit_match_id:
        item = get_any_event_odds(int(explicit_match_id))
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
    """Backward-compatible matcher with active per-event fallback chain.

    Matching priority:
      1) exact event_id / match_id in daily odds list
      2) direct event odds fallback chain by id:
         TennisApi PRO -> Tennis API ATP/WTA/ITF -> All Sports API
      3) normalized name matching, including reversed player order
      4) fuzzy normalized name matching
      5) NO_ODDS report entry
    """
    odds_list, match, player1, player2 = _parse_find_match_odds_args(args, kwargs)

    if not odds_list:
        odds_list = fetch_odds()

    match_id = None
    tournament = None
    start_time = None
    if isinstance(match, dict):
        match_id = match.get("match_id") or match.get("event_id") or match.get("id")
        player1 = player1 or match.get("player1") or match.get("home") or match.get("home_team")
        player2 = player2 or match.get("player2") or match.get("away") or match.get("away_team") or match.get("opponent")
        tournament = match.get("tournament")
        start_time = match.get("match_start") or match.get("start_time") or match.get("time")

    # 1) Exact ID in loaded daily odds list.
    if match_id:
        for item in odds_list:
            item_id = item.get("match_id") or item.get("event_id") or item.get("id")
            if item_id is not None and str(item_id) == str(match_id):
                out = dict(item)
                out.setdefault("matching_direction", "event_id")
                out.setdefault("matching_score", 1.0)
                return out

        # 2) Direct fallback: this is the key fix. Even if daily batch has no odds
        # for an event, call all configured event-level odds APIs.
        direct = get_any_event_odds(int(match_id))
        if direct:
            item = _to_legacy_odds_item(direct)
            if player1:
                item["player1"] = player1
                item["home_team"] = player1
                item["home"] = player1
            if player2:
                item["player2"] = player2
                item["away_team"] = player2
                item["away"] = player2
            item["match_id"] = match_id
            item["event_id"] = match_id
            item["matching_direction"] = "direct_event_fallback"
            item["matching_score"] = 1.0
            return item

    # 3-4) Name matching in loaded daily odds list.
    legacy = _find_in_legacy_odds_list(odds_list, player1, player2)
    if legacy:
        return legacy

    _record_no_odds(match_id, player1, player2, tournament, start_time, "event_id_and_name_matching_failed")
    return None


# ----------------------------------------------------------------------
# Event-level odds fallback chain
# ----------------------------------------------------------------------


def get_any_event_odds(event_id: int) -> Optional[Dict[str, Any]]:
    """Try all active event-level odds providers in priority order."""
    for provider_name, func in (
        ("TennisApiEventOdds", get_tennisapi_odds),
        ("tennis_api_atp_wta_itf", get_tennis_api_atp_wta_itf_odds),
        ("all_sports_api", get_all_sports_api_odds),
    ):
        try:
            odds = func(event_id)
            if odds:
                odds.setdefault("source", provider_name)
                odds.setdefault("odds_source", provider_name)
                odds.setdefault("match_id", event_id)
                odds.setdefault("event_id", event_id)
                return odds
        except Exception as exc:
            logger.debug("%s odds fallback failed event_id=%s error=%s", provider_name, event_id, exc)
    return None


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    try:
        client = TennisApiClient()
        payload = client.get_match_winning_odds(match_id)
        normalized = normalize_winning_odds(payload)
        if normalized:
            normalized["source"] = "TennisApiEventOdds"
            normalized["odds_source"] = "TennisApiEventOdds"
            normalized["match_id"] = match_id
            normalized["event_id"] = match_id
            return normalized
    except Exception as exc:
        logger.info("TennisApi odds failed. match_id=%s error=%s", match_id, exc)
    return None


def get_tennis_api_atp_wta_itf_odds(event_id: int) -> Optional[Dict[str, Any]]:
    key = os.getenv("TENNIS_API_ATP_WTA_ITF", "").strip()
    if not key:
        return None

    # Confirmed by user from RapidAPI snippet.
    paths = [
        f"/tennis/v2/extend/api/odds/arbitrage/{event_id}",
        f"/tennis/v2/extend/api/odds/summary/{event_id}",
    ]
    for path in paths:
        payload = _rapidapi_get_json(TENNIS_API_ATP_WTA_ITF_HOST, path, key)
        normalized = _normalize_generic_event_odds_payload(payload)
        if normalized:
            normalized["source"] = "tennis_api_atp_wta_itf"
            normalized["odds_source"] = "tennis_api_atp_wta_itf"
            normalized["bookmaker"] = normalized.get("bookmaker") or "Tennis API - ATP WTA ITF"
            normalized["match_id"] = event_id
            normalized["event_id"] = event_id
            normalized["raw"] = payload
            return normalized
    return None


def get_all_sports_api_odds(event_id: int) -> Optional[Dict[str, Any]]:
    key = os.getenv("ALL_SPORTS_API", "").strip()
    if not key:
        return None

    path = f"/api/tennis/event/{event_id}/provider/1/winning-odds"
    payload = _rapidapi_get_json(ALL_SPORTS_HOST, path, key)
    normalized = _normalize_all_sports_winning_odds(payload)
    if normalized:
        normalized["source"] = "all_sports_api"
        normalized["odds_source"] = "all_sports_api"
        normalized["bookmaker"] = normalized.get("bookmaker") or "All Sports API provider 1"
        normalized["match_id"] = event_id
        normalized["event_id"] = event_id
        normalized["raw"] = payload
        return normalized
    return None


def _rapidapi_get_json(host: str, path: str, api_key: str, timeout: int = 20) -> Dict[str, Any]:
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": host,
        "Content-Type": "application/json",
    }
    conn.request("GET", path, headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8", errors="replace")
    if res.status >= 400:
        logger.debug("RapidAPI HTTP %s host=%s path=%s body=%s", res.status, host, path, raw[:300])
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"data": data}
    except Exception:
        logger.debug("RapidAPI invalid JSON host=%s path=%s body=%s", host, path, raw[:300])
        return {}


def _normalize_all_sports_winning_odds(payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    odds_obj = payload.get("odds") if isinstance(payload.get("odds"), dict) else data
    home = odds_obj.get("home") if isinstance(odds_obj, dict) else None
    away = odds_obj.get("away") if isinstance(odds_obj, dict) else None
    if not isinstance(home, dict) or not isinstance(away, dict):
        return _normalize_generic_event_odds_payload(payload)
    p1 = _extract_decimal_from_dict(home)
    p2 = _extract_decimal_from_dict(away)
    if p1 and p2:
        return {
            "home_odds": p1,
            "away_odds": p2,
            "p1_odds": p1,
            "p2_odds": p2,
            "odds_player1": p1,
            "odds_player2": p2,
        }
    return None


def _normalize_generic_event_odds_payload(payload: Any) -> Optional[Dict[str, Any]]:
    """Flexible parser for multiple odds API response shapes.

    Supports shapes like:
      {home:{fractionalValue}, away:{fractionalValue}}
      {result:{Full Time Result:{Bet365:{od1, od2}}}}
      nested market objects with home/away or od1/od2 fields.
    """
    if not isinstance(payload, dict):
        return None
    candidates: List[Dict[str, Any]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            candidates.append(obj)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(payload)

    for obj in candidates:
        # home/away dicts
        if isinstance(obj.get("home"), dict) and isinstance(obj.get("away"), dict):
            p1 = _extract_decimal_from_dict(obj["home"])
            p2 = _extract_decimal_from_dict(obj["away"])
            if p1 and p2:
                return _odds_dict(p1, p2, obj.get("bookmaker") or obj.get("provider"))

        # direct home/away fields
        p1 = _first_decimal(obj, ["home_odds", "homeOdds", "home", "od1", "odd1", "price1", "odds1"])
        p2 = _first_decimal(obj, ["away_odds", "awayOdds", "away", "od2", "odd2", "price2", "odds2"])
        if p1 and p2 and p1 > 1.0 and p2 > 1.0:
            provider = obj.get("bookmaker") or obj.get("provider") or obj.get("source")
            return _odds_dict(p1, p2, provider)

        # choices list
        choices = obj.get("choices")
        if isinstance(choices, list) and len(choices) >= 2:
            c1 = _extract_decimal_from_dict(choices[0]) if isinstance(choices[0], dict) else None
            c2 = _extract_decimal_from_dict(choices[1]) if isinstance(choices[1], dict) else None
            if c1 and c2:
                return _odds_dict(c1, c2, obj.get("bookmaker") or obj.get("sourceName"))

    return None


def _odds_dict(p1: float, p2: float, provider: Any = None) -> Dict[str, Any]:
    out = {
        "home_odds": round(float(p1), 4),
        "away_odds": round(float(p2), 4),
        "p1_odds": round(float(p1), 4),
        "p2_odds": round(float(p2), 4),
        "odds_player1": round(float(p1), 4),
        "odds_player2": round(float(p2), 4),
    }
    if provider:
        out["bookmaker"] = str(provider)
    return out


def _extract_decimal_from_dict(obj: Dict[str, Any]) -> Optional[float]:
    for key in ("decimalValue", "decimal", "price", "odds", "value", "currentOdd", "od", "od1", "od2"):
        value = obj.get(key)
        dec = _to_float_or_none(value)
        if dec and dec > 1.0:
            return round(dec, 4)
    for key in ("fractionalValue", "initialFractionalValue", "fractional"):
        value = obj.get(key)
        if value:
            dec = fractional_to_decimal(str(value))
            if dec and dec > 1.0:
                return round(dec, 4)
    return None


def _first_decimal(obj: Dict[str, Any], keys: List[str]) -> Optional[float]:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, dict):
            dec = _extract_decimal_from_dict(value)
        else:
            dec = _to_float_or_none(value)
            if not dec and isinstance(value, str) and "/" in value:
                dec = fractional_to_decimal(value)
        if dec and dec > 1.0:
            return round(dec, 4)
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
    enriched.update(odds)
    enriched["odds_status"] = "OK"
    return enriched


def get_odds(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_odds_for_match(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_match_odds_for_event(match_id: int) -> Optional[Dict[str, Any]]:
    return get_any_event_odds(match_id)


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

    for arg in args:
        if isinstance(arg, list):
            odds_list = [x for x in arg if isinstance(x, dict)]
        elif isinstance(arg, dict):
            match = arg
        elif isinstance(arg, str):
            if player1 is None:
                player1 = arg
            elif player2 is None:
                player2 = arg

    return odds_list, match, player1, player2


def _to_legacy_odds_item(odds: Dict[str, Any]) -> Dict[str, Any]:
    p1 = odds.get("p1_odds") or odds.get("home_odds") or odds.get("odds_player1")
    p2 = odds.get("p2_odds") or odds.get("away_odds") or odds.get("odds_player2")
    return {
        "source": odds.get("odds_source") or odds.get("source") or "TennisApi",
        "odds_source": odds.get("odds_source") or odds.get("source") or "TennisApi",
        "bookmaker": odds.get("bookmaker") or odds.get("provider") or odds.get("source") or "TennisApi",
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
    p1 = legacy.get("odds_player1") or legacy.get("p1_odds") or legacy.get("home_odds") or legacy.get("odds") or legacy.get("odds1") or legacy.get("price1")
    p2 = legacy.get("odds_player2") or legacy.get("p2_odds") or legacy.get("away_odds") or legacy.get("odds2") or legacy.get("price2")
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
    if not player1 or not player2:
        return None

    requested_p1 = _normalize_name(player1)
    requested_p2 = _normalize_name(player2)
    best_fuzzy: Tuple[float, Optional[Dict[str, Any]], bool] = (0.0, None, False)

    for item in odds_list:
        item_p1 = item.get("player1") or item.get("home_team") or item.get("home")
        item_p2 = item.get("player2") or item.get("away_team") or item.get("away")
        norm_item_p1 = _normalize_name(item_p1)
        norm_item_p2 = _normalize_name(item_p2)

        direct = _names_match_normalized(requested_p1, norm_item_p1) and _names_match_normalized(requested_p2, norm_item_p2)
        reversed_match = _names_match_normalized(requested_p1, norm_item_p2) and _names_match_normalized(requested_p2, norm_item_p1)
        if direct:
            out = dict(item)
            out.setdefault("matching_direction", "names_direct")
            out.setdefault("matching_score", 1.0)
            return out
        if reversed_match:
            return _swap_legacy_item(item, player1, player2, "names_reversed", 1.0)

        direct_score = (_similarity(requested_p1, norm_item_p1) + _similarity(requested_p2, norm_item_p2)) / 2
        reversed_score = (_similarity(requested_p1, norm_item_p2) + _similarity(requested_p2, norm_item_p1)) / 2
        if direct_score > best_fuzzy[0]:
            best_fuzzy = (direct_score, item, False)
        if reversed_score > best_fuzzy[0]:
            best_fuzzy = (reversed_score, item, True)

    if best_fuzzy[1] is not None and best_fuzzy[0] >= 0.90:
        if best_fuzzy[2]:
            return _swap_legacy_item(best_fuzzy[1], player1, player2, "fuzzy_reversed", best_fuzzy[0])
        out = dict(best_fuzzy[1])
        out.setdefault("matching_direction", "fuzzy_direct")
        out.setdefault("matching_score", round(best_fuzzy[0], 4))
        return out

    return None


def _swap_legacy_item(item: Dict[str, Any], player1: str, player2: str, direction: str, score: float) -> Dict[str, Any]:
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
    swapped["matching_direction"] = direction
    swapped["matching_score"] = round(score, 4)
    return swapped


def _normalize_name(name: Any) -> str:
    value = str(name or "").lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    for ch in (".", "-", "_", "'", "`", "´"):
        value = value.replace(ch, " ")
    return " ".join(value.split())


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


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if _names_match_normalized(a, b):
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _record_no_odds(match_id: Any, player1: Any, player2: Any, tournament: Any, start_time: Any, reason: str) -> None:
    entry = {
        "match_id": match_id,
        "event_id": match_id,
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}" if player1 and player2 else None,
        "tournament": tournament,
        "start_time": start_time,
        "tried_sources": ["TennisApiDailyOdds", "TennisApiEventOdds", "tennis_api_atp_wta_itf", "all_sports_api"],
        "no_odds_reason": reason,
    }
    key = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    existing = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in _NO_ODDS_REPORT}
    if key not in existing:
        _NO_ODDS_REPORT.append(entry)
        _write_no_odds_report()


def _write_no_odds_report() -> None:
    try:
        path = Path("public/no_odds_report.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(_NO_ODDS_REPORT, file, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.debug("Failed to write no_odds_report.json: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    odds = fetch_odds(force_refresh=True)
    print(f"Odds found: {len(odds)}")
    for item in odds[:20]:
        print(item.get("match_id"), item.get("player1"), "vs", item.get("player2"), item.get("odds_player1"), item.get("odds_player2"), item.get("odds_source"))
