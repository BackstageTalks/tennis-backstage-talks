import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from tennisapi_client import (
    TennisApiClient,
    fractional_to_decimal,
    normalize_event,
    normalize_winning_odds,
)

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Europe/Bratislava")
CACHE_DIR = Path("data/tennisapi_cache")


# ----------------------------------------------------------------------
# Config helpers
# ----------------------------------------------------------------------


def parse_category_ids() -> List[int]:
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
    return output


def provider_id() -> int:
    try:
        return int(os.getenv("TENNISAPI_PROVIDER_ID", "1"))
    except Exception:
        return 1


def betting_day_datetime(date_time: Optional[datetime] = None) -> datetime:
    if date_time is None:
        date_time = datetime.now(LOCAL_TZ)
    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=LOCAL_TZ)
    return date_time.astimezone(LOCAL_TZ)


def date_key(target_date: Optional[datetime] = None) -> str:
    return betting_day_datetime(target_date).strftime("%Y-%m-%d")


def ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_path(kind: str, target_date: Optional[datetime] = None) -> Path:
    ensure_cache_dir()
    return CACHE_DIR / f"{kind}_{date_key(target_date)}.json"


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        logger.warning("TennisApi cache load failed path=%s error=%s", path, exc)
        return default


# ----------------------------------------------------------------------
# Generic TennisApi extraction helpers
# ----------------------------------------------------------------------


def extract_event_from_payload(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        event = payload.get("event")
        if isinstance(event, dict):
            return event
        if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("event"), dict):
            return payload["data"]["event"]
        if payload.get("id") or payload.get("homeTeam") or payload.get("awayTeam"):
            return payload
    return None


def _team_name(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("name", "fullName", "full_name", "displayName", "display_name", "shortName", "short_name", "slug"):
            if value.get(key):
                return str(value.get(key)).strip()
        return None
    text = str(value).strip()
    return text or None


def event_home_away(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    event = extract_event_from_payload(event) or event or {}
    home = (
        event.get("homeTeam")
        or event.get("home_team")
        or event.get("home")
        or event.get("player1")
        or event.get("participant1")
    )
    away = (
        event.get("awayTeam")
        or event.get("away_team")
        or event.get("away")
        or event.get("player2")
        or event.get("participant2")
    )
    return _team_name(home), _team_name(away)


def normalize_name(value: Any) -> str:
    return (
        str(value or "")
        .lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


def extract_markets(raw_odds: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_odds, dict):
        return []

    candidates: List[Any] = []
    for key in ("markets", "odds", "data", "choices", "bookmakers"):
        value = raw_odds.get(key)
        if value is not None:
            candidates.append(value)

    markets: List[Dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("choices"), list) or isinstance(value.get("outcomes"), list):
                markets.append(value)
            for nested_key in ("markets", "odds", "data", "bookmakers"):
                nested = value.get(nested_key)
                if isinstance(nested, (list, dict)):
                    walk(nested)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for candidate in candidates:
        walk(candidate)

    # Some endpoints return the market itself as the root object.
    if isinstance(raw_odds.get("choices"), list) or isinstance(raw_odds.get("outcomes"), list):
        markets.append(raw_odds)

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for market in markets:
        key = json.dumps(market, sort_keys=True, default=str)[:500]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(market)
    return deduped


def _market_name(market: Dict[str, Any]) -> str:
    values = []
    for key in ("name", "marketName", "market_name", "label", "type", "marketType"):
        value = market.get(key)
        if value:
            values.append(str(value))
    return normalize_name(" ".join(values))


def _market_choices(market: Dict[str, Any]) -> List[Dict[str, Any]]:
    choices = market.get("choices") or market.get("outcomes") or market.get("participants")
    if isinstance(choices, list):
        return [choice for choice in choices if isinstance(choice, dict)]
    return []


def select_full_time_market(raw_odds: Any) -> Optional[Dict[str, Any]]:
    markets = extract_markets(raw_odds)
    if not markets:
        return None

    preferred_terms = [
        "match winner",
        "winner",
        "full time",
        "fulltime",
        "to win",
        "home away",
        "1x2",
    ]

    for market in markets:
        name = _market_name(market)
        if len(_market_choices(market)) < 2:
            continue
        if any(term in name for term in preferred_terms):
            return market

    for market in markets:
        if len(_market_choices(market)) >= 2:
            return market
    return None


def choice_to_decimal(choice: Dict[str, Any]) -> Optional[float]:
    if not isinstance(choice, dict):
        return None

    for key in ("decimalValue", "decimal", "price", "odds", "value", "current", "latest"):
        value = choice.get(key)
        if value is None or value == "":
            continue
        try:
            number = float(str(value).replace(",", "."))
            if number > 1.0:
                return number
        except Exception:
            pass

    for key in ("fractionalValue", "fractional", "fraction"):
        value = choice.get(key)
        if value:
            converted = fractional_to_decimal(str(value))
            if converted and converted > 1.0:
                return converted
    return None


def normalize_choice_text(choice: Dict[str, Any]) -> str:
    values = []
    for key in ("name", "label", "choiceName", "participantName", "sourceName", "marketName"):
        value = choice.get(key)
        if value:
            values.append(str(value))
    return normalize_name(" ".join(values))


def _names_match(a: Any, b: Any) -> bool:
    a_norm = normalize_name(a)
    b_norm = normalize_name(b)
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm:
        return True
    a_parts = a_norm.split()
    b_parts = b_norm.split()
    if a_parts and b_parts and a_parts[-1] == b_parts[-1]:
        return True
    return a_norm in b_norm or b_norm in a_norm


def pick_home_away_choices(choices: List[Dict[str, Any]], player1: str, player2: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if len(choices) < 2:
        return {}, {}

    p1_choice: Optional[Dict[str, Any]] = None
    p2_choice: Optional[Dict[str, Any]] = None

    for choice in choices:
        choice_text = normalize_choice_text(choice)
        if p1_choice is None and _names_match(choice_text, player1):
            p1_choice = choice
        if p2_choice is None and _names_match(choice_text, player2):
            p2_choice = choice

    if p1_choice and p2_choice:
        return p1_choice, p2_choice

    # Fallback to API order. For TennisApi event odds, the first two outcomes are usually home/away.
    return choices[0], choices[1]


def normalize_event_market_odds_payload(raw_odds: Any) -> Optional[Dict[str, Any]]:
    """Normalize TennisApi event-level market odds payloads.

    Returns a model-compatible object with player1/player2 odds fields when the endpoint
    contains a two-outcome match winner market.
    """
    market = select_full_time_market(raw_odds)
    if not market:
        return None
    choices = _market_choices(market)
    if len(choices) < 2:
        return None

    first = choices[0]
    second = choices[1]
    odds1 = choice_to_decimal(first)
    odds2 = choice_to_decimal(second)
    if odds1 is None or odds2 is None:
        return None

    bookmaker = None
    for key in ("bookmaker", "provider", "bookmakerName", "providerName"):
        value = market.get(key)
        if value:
            bookmaker = _team_name(value) or str(value)
            break

    return {
        "source": "TennisApi",
        "odds_source": "TennisApi",
        "bookmaker": bookmaker or "TennisApi",
        "home_odds": odds1,
        "away_odds": odds2,
        "p1_odds": odds1,
        "p2_odds": odds2,
        "odds_player1": odds1,
        "odds_player2": odds2,
        "odds": odds1,
        "odds1": odds1,
        "odds2": odds2,
        "price1": odds1,
        "price2": odds2,
        "market_name": market.get("name") or market.get("marketName") or "Match Winner",
        "raw": raw_odds,
    }


def _extract_odds_payload_from_daily_item(item: Dict[str, Any]) -> Any:
    if not isinstance(item, dict):
        return None
    for key in ("odds", "markets", "eventOdds", "winningOdds", "data"):
        value = item.get(key)
        if value is not None:
            return value
    return item


def normalize_daily_odds_item(event: Dict[str, Any], raw_odds: Any) -> Optional[Dict[str, Any]]:
    event = extract_event_from_payload(event) or event
    if not isinstance(event, dict) or not isinstance(raw_odds, dict):
        return None

    player1, player2 = event_home_away(event)
    if not player1 or not player2:
        return None

    normalized = normalize_event_market_odds_payload(raw_odds)
    if not normalized:
        return None

    event_id = event.get("id") or event.get("event_id") or event.get("match_id")
    normalized.update(
        {
            "match_id": event_id,
            "event_id": event_id,
            "player1": player1,
            "player2": player2,
            "home_team": player1,
            "away_team": player2,
            "source": normalized.get("source") or "TennisApiDailyOdds",
            "odds_source": normalized.get("odds_source") or "TennisApiDailyOdds",
        }
    )
    return normalized


def legacy_item_from_normalized_event_odds(event: Dict[str, Any], normalized: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event = extract_event_from_payload(event) or event
    player1, player2 = event_home_away(event)
    event_id = event.get("id") or event.get("event_id") or event.get("match_id")

    if not player1 or not player2 or not isinstance(normalized, dict):
        return None

    p1 = (
        normalized.get("odds_player1")
        or normalized.get("p1_odds")
        or normalized.get("home_odds")
        or normalized.get("home")
        or normalized.get("home_odds_decimal")
        or normalized.get("odds1")
        or normalized.get("price1")
    )
    p2 = (
        normalized.get("odds_player2")
        or normalized.get("p2_odds")
        or normalized.get("away_odds")
        or normalized.get("away")
        or normalized.get("away_odds_decimal")
        or normalized.get("odds2")
        or normalized.get("price2")
    )

    try:
        p1 = float(p1) if p1 is not None else None
        p2 = float(p2) if p2 is not None else None
    except Exception:
        return None

    if p1 is None or p2 is None:
        return None

    return {
        "source": normalized.get("source") or "TennisApiMatchWinningOdds",
        "odds_source": normalized.get("odds_source") or normalized.get("source") or "TennisApiMatchWinningOdds",
        "bookmaker": normalized.get("bookmaker") or "TennisApi",
        "match_id": event_id,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "home_team": player1,
        "away_team": player2,
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
        "raw": normalized.get("raw", normalized),
    }


# ----------------------------------------------------------------------
# Client call helpers
# ----------------------------------------------------------------------


def _try_client_method(client: TennisApiClient, names: List[str], *args: Any) -> Any:
    for name in names:
        method = getattr(client, name, None)
        if not callable(method):
            continue
        try:
            return method(*args)
        except TypeError:
            continue
    return None


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("events", "data", "items", "categories"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
    return []


# ----------------------------------------------------------------------
# Events cache
# ----------------------------------------------------------------------


def get_events_for_date(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    target_date = betting_day_datetime(target_date)
    path = cache_path("events", target_date)
    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, list):
            return cached

    category_ids = category_ids or parse_category_ids()
    client = TennisApiClient()
    day = int(target_date.strftime("%d"))
    month = int(target_date.strftime("%m"))
    year = int(target_date.strftime("%Y"))

    events: List[Dict[str, Any]] = []

    # Preferred newer flow: calendar categories -> category events.
    categories_payload = _try_client_method(
        client,
        ["get_calendar_categories", "get_categories_for_date", "get_tennis_calendar_categories"],
        day,
        month,
        year,
    )
    categories = _as_list(categories_payload)
    dynamic_category_ids: List[int] = []
    for category in categories:
        if isinstance(category, dict):
            cid = category.get("id") or category.get("categoryId") or category.get("category_id")
            try:
                dynamic_category_ids.append(int(cid))
            except Exception:
                pass

    scan_category_ids = dynamic_category_ids or category_ids
    for category_id in scan_category_ids:
        payload = _try_client_method(
            client,
            ["get_category_events", "get_events_for_category", "get_tennis_category_events"],
            int(category_id),
            day,
            month,
            year,
        )
        for item in _as_list(payload):
            event = extract_event_from_payload(item) or item
            if isinstance(event, dict):
                events.append(normalize_event(event))

    # Fallback for older client implementations.
    if not events:
        payload = _try_client_method(
            client,
            ["get_events_for_date", "get_events", "get_tennis_events_for_date"],
            day,
            month,
            year,
        )
        for item in _as_list(payload):
            event = extract_event_from_payload(item) or item
            if isinstance(event, dict):
                events.append(normalize_event(event))

    events = deduplicate_events(events)
    save_json(path, events)
    print("TennisApi cache events:", len(events))
    return events


def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        key = event.get("id") or event.get("event_id") or event.get("match_id")
        if not key:
            home, away = event_home_away(event)
            key = f"{home}|{away}|{event.get('startTimestamp') or event.get('match_start')}"
        if key in seen:
            continue
        seen.add(key)
        output.append(event)
    return output


# ----------------------------------------------------------------------
# Daily odds cache
# ----------------------------------------------------------------------


def get_daily_odds_payload(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Fetch/cache TennisApi PRO batch daily odds payload."""
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_batch", target_date)
    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, dict):
            return cached

    client = TennisApiClient()
    day = int(target_date.strftime("%d"))
    month = int(target_date.strftime("%m"))
    year = int(target_date.strftime("%Y"))

    payload = _try_client_method(
        client,
        [
            "get_daily_odds",
            "get_events_odds",
            "get_tennis_events_odds",
            "get_tennis_daily_odds",
            "get_events_odds_for_date",
        ],
        day,
        month,
        year,
    )

    if not isinstance(payload, dict):
        payload = {}

    save_json(path, payload)
    print("TennisApi cache daily odds batch:", len(_as_list(payload)))
    return payload


def _extract_daily_payload_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = _as_list(payload)
    return [item for item in items if isinstance(item, dict)]


def get_daily_odds_items(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
    include_event_fallback: bool = True,
) -> List[Dict[str, Any]]:
    """Returns model-compatible odds list:

    player1, player2, match_id/event_id, odds_player1, odds_player2.
    Primary source is TennisApi PRO daily odds batch. Optional fallback uses
    paid TennisApi event-level winning odds for events without batch odds.
    """
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_items", target_date)
    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, list):
            return cached

    events = get_events_for_date(target_date, force_refresh=force_refresh)
    payload = get_daily_odds_payload(target_date, force_refresh=force_refresh)

    items: List[Dict[str, Any]] = []
    seen_event_ids = set()

    for daily_item in _extract_daily_payload_items(payload):
        event = extract_event_from_payload(daily_item) or daily_item
        raw_odds = _extract_odds_payload_from_daily_item(daily_item)
        normalized = normalize_daily_odds_item(event, raw_odds)
        if normalized:
            event_id = normalized.get("event_id") or normalized.get("match_id")
            if event_id:
                seen_event_ids.add(str(event_id))
            items.append(normalized)

    if include_event_fallback:
        try:
            client = TennisApiClient()
            for event in events:
                event_id = event.get("id") or event.get("event_id") or event.get("match_id")
                if not event_id or str(event_id) in seen_event_ids:
                    continue
                fallback_item = fetch_event_winning_odds_item(client, event, int(event_id))
                if fallback_item:
                    seen_event_ids.add(str(event_id))
                    items.append(fallback_item)
        except Exception as exc:
            logger.warning("TennisApi event fallback loop failed error=%s", exc)

    items = deduplicate_odds_items(items)
    save_json(path, items)
    print("TennisApi cache odds items:", len(items))
    return items


def deduplicate_odds_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("event_id") or item.get("match_id")
        if not key:
            key = f"{normalize_name(item.get('player1'))}|{normalize_name(item.get('player2'))}"
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def fetch_event_winning_odds_item(
    client: TennisApiClient,
    event: Dict[str, Any],
    event_id: int,
) -> Optional[Dict[str, Any]]:
    try:
        event_odds_payload = client.get_match_winning_odds(event_id, provider_id())
        normalized = normalize_winning_odds(event_odds_payload)
        if normalized:
            return legacy_item_from_normalized_event_odds(event, normalized)
    except Exception as exc:
        logger.debug("Event odds fallback failed event_id=%s error=%s", event_id, exc)
    return None


# ----------------------------------------------------------------------
# CLI warmup
# ----------------------------------------------------------------------


def warm_cache(force_refresh: bool = True) -> None:
    target_date = betting_day_datetime()
    print("TennisApi cache warmup date:", target_date.strftime("%Y-%m-%d"))
    events = get_events_for_date(target_date, force_refresh=force_refresh)
    odds_items = get_daily_odds_items(target_date, force_refresh=force_refresh)
    print("TennisApi cache warmup events:", len(events))
    print("TennisApi cache warmup odds_items:", len(odds_items))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    warm_cache(force_refresh=True)
