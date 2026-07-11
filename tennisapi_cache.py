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
            logger.warning("Invalid TennisApi category id ignored: %s", part)

    return output or [3]


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
    else:
        date_time = date_time.astimezone(LOCAL_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time


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

        data = payload.get("data")
        if isinstance(data, dict):
            event = data.get("event")
            if isinstance(event, dict):
                return event
            if data.get("homeTeam") or data.get("awayTeam"):
                return data

        if payload.get("homeTeam") or payload.get("awayTeam"):
            return payload

    return None


def event_home_away(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    home = event.get("homeTeam") or {}
    away = event.get("awayTeam") or {}

    player1 = home.get("name") or home.get("shortName") or event.get("home")
    player2 = away.get("name") or away.get("shortName") or event.get("away")

    return player1, player2


def extract_markets(raw_odds: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_odds, dict):
        return []

    markets = raw_odds.get("markets")
    if isinstance(markets, list):
        return [item for item in markets if isinstance(item, dict)]

    odds = raw_odds.get("odds")
    if isinstance(odds, list):
        return [item for item in odds if isinstance(item, dict)]

    data = raw_odds.get("data")
    if isinstance(data, dict):
        markets = data.get("markets")
        if isinstance(markets, list):
            return [item for item in markets if isinstance(item, dict)]

    if raw_odds.get("choices"):
        return [raw_odds]

    return []


def select_full_time_market(raw_odds: Any) -> Optional[Dict[str, Any]]:
    markets = extract_markets(raw_odds)

    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        market_group = str(market.get("marketGroup") or "").strip().lower()
        market_period = str(market.get("marketPeriod") or "").strip().lower()

        if (
            market_name == "full time"
            and ("home" in market_group or market_group == "home/away")
            and market_period in ("match", "")
        ):
            return market

    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        if market_name in ("full time", "match winner", "winner", "to win"):
            return market

    return markets[0] if markets else None


def choice_to_decimal(choice: Dict[str, Any]) -> Optional[float]:
    if not isinstance(choice, dict):
        return None

    for key in ["fractionalValue", "initialFractionalValue", "value", "decimalValue", "price", "odds"]:
        value = choice.get(key)
        if value is None:
            continue

        if key in ["fractionalValue", "initialFractionalValue"]:
            decimal = fractional_to_decimal(str(value))
        else:
            try:
                decimal = float(value)
            except Exception:
                decimal = None

        if decimal and decimal > 1.0:
            return round(decimal, 4)

    return None


def pick_home_away_choices(choices: List[Dict[str, Any]], player1: str, player2: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if len(choices) < 2:
        return {}, {}

    p1 = normalize_name(player1)
    p2 = normalize_name(player2)
    choice_for_p1 = None
    choice_for_p2 = None

    for choice in choices:
        text = normalize_choice_text(choice)
        name = str(choice.get("name") or "").strip()

        if name == "1":
            choice_for_p1 = choice_for_p1 or choice
        elif name == "2":
            choice_for_p2 = choice_for_p2 or choice

        if text:
            if p1 and p1 in text:
                choice_for_p1 = choice
            if p2 and p2 in text:
                choice_for_p2 = choice

    if choice_for_p1 and choice_for_p2:
        return choice_for_p1, choice_for_p2

    return choices[0], choices[1]


def normalize_choice_text(choice: Dict[str, Any]) -> str:
    values = []
    for key in ["name", "label", "choiceName", "participantName", "sourceName", "marketName"]:
        value = choice.get(key)
        if value:
            values.append(str(value))
    return normalize_name(" ".join(values))


def normalize_name(value: Any) -> str:
    return (
        str(value or "")
        .lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


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

    client = TennisApiClient()
    category_ids = category_ids or parse_category_ids()
    all_events: List[Dict[str, Any]] = []
    seen = set()

    for category_id in category_ids:
        try:
            events = client.get_events_by_category_date(
                category_id=category_id,
                day=target_date.day,
                month=target_date.month,
                year=target_date.year,
            )
        except Exception as exc:
            logger.warning(
                "TennisApi cached events fetch failed category_id=%s date=%s error=%s",
                category_id,
                target_date.date(),
                exc,
            )
            continue

        for event in events:
            if not isinstance(event, dict):
                continue
            event_id = event.get("id")
            if event_id in seen:
                continue
            seen.add(event_id)
            event["_cache_category_id"] = category_id
            all_events.append(event)

    save_json(path, all_events)
    print("TennisApi cache events:", len(all_events), str(path))
    return all_events


# ----------------------------------------------------------------------
# Daily odds cache
# ----------------------------------------------------------------------


def get_daily_odds_payload(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Batch daily odds endpoint:
        /api/tennis/events/odds/{day}/{month}/{year}
    """
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_batch", target_date)

    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, dict):
            return cached

    client = TennisApiClient()

    try:
        payload = client.get_events_odds_by_date(
            day=target_date.day,
            month=target_date.month,
            year=target_date.year,
        )
    except Exception as exc:
        api_path = f"/api/tennis/events/odds/{target_date.day}/{target_date.month}/{target_date.year}"
        logger.warning("TennisApi daily odds batch failed path=%s error=%s", api_path, exc)
        payload = {}

    save_json(path, payload)
    odds_obj = payload.get("odds") if isinstance(payload, dict) else None
    count = len(odds_obj) if isinstance(odds_obj, dict) else 0
    print("TennisApi cache daily odds batch:", count, str(path))
    return payload if isinstance(payload, dict) else {}


def get_daily_odds_items(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
    include_event_fallback: bool = True,
) -> List[Dict[str, Any]]:
    """
    Returns model-compatible odds list:
        player1, player2, match_id/event_id, odds_player1, odds_player2.

    Important behaviour:
    - Category events are processed first.
    - Then every event_id from /events/odds/date is checked.
    - If an odds event is missing from category events, /api/tennis/event/{event_id}
      is used to fetch match details and build an odds item.
    """
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_items", target_date)

    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, list):
            return cached

    client = TennisApiClient()
    events = get_events_for_date(target_date, force_refresh=force_refresh)
    batch = get_daily_odds_payload(target_date, force_refresh=force_refresh)
    batch_odds = batch.get("odds") if isinstance(batch, dict) else {}
    if not isinstance(batch_odds, dict):
        batch_odds = {}

    items: List[Dict[str, Any]] = []
    seen_item_ids = set()
    events_by_id: Dict[str, Dict[str, Any]] = {}

    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        events_by_id[str(event_id)] = event

    # First pass: category events.
    for event_id, event in events_by_id.items():
        raw_odds = batch_odds.get(str(event_id)) or batch_odds.get(event_id)
        item = normalize_daily_odds_item(event, raw_odds)

        if not item and include_event_fallback:
            item = fetch_event_winning_odds_item(client, event, int(event_id))

        if item:
            seen_item_ids.add(str(event_id))
            items.append(item)

    # Second pass: odds batch events that did not appear in category events.
    # This is key for using the paid TennisApi odds feed properly.
    for event_id_raw, raw_odds in batch_odds.items():
        event_id = str(event_id_raw)
        if event_id in seen_item_ids:
            continue

        event = events_by_id.get(event_id)
        if not event:
            try:
                detail_payload = client.get_match_details(int(event_id))
                event = extract_event_from_payload(detail_payload) or {}
            except Exception as exc:
                logger.debug("TennisApi detail fetch for odds-batch event failed event_id=%s error=%s", event_id, exc)
                event = {}

        if not event:
            continue

        item = normalize_daily_odds_item(event, raw_odds)
        if item:
            seen_item_ids.add(event_id)
            items.append(item)

    save_json(path, items)
    print("TennisApi cache odds items:", len(items), str(path))
    return items


def fetch_event_winning_odds_item(
    client: TennisApiClient,
    event: Dict[str, Any],
    event_id: int,
) -> Optional[Dict[str, Any]]:
    """Event-level TennisApi PRO odds fallback chain.

    This is the important coverage fix: if TennisApiDailyOdds does not contain
    a match, do not stop. Try all event-level PRO odds endpoints first:
    1. getMatchWinningOdds
    2. getMatchBettingOdds
    3. getAllOddsForEvent
    4. getMatchFeaturedOdds
    """
    attempts = [
        (
            "TennisApiMatchWinningOdds",
            lambda: client.get_match_winning_odds(event_id, provider_id()),
            normalize_winning_odds,
        ),
        (
            "TennisApiMatchBettingOdds",
            lambda: client.get_match_betting_odds(event_id),
            normalize_event_market_odds_payload,
        ),
        (
            "TennisApiAllOddsForEvent",
            lambda: client.get_all_odds_for_event(event_id, provider_id()),
            normalize_event_market_odds_payload,
        ),
        (
            "TennisApiMatchFeaturedOdds",
            lambda: client.get_match_featured_odds(event_id),
            normalize_event_market_odds_payload,
        ),
    ]

    for source_name, fetcher, normalizer in attempts:
        try:
            payload = fetcher()
            normalized = normalizer(payload)
            if normalized:
                return legacy_item_from_normalized_event_odds(
                    event,
                    normalized,
                    source_name=source_name,
                )
        except Exception as exc:
            logger.debug(
                "Event odds fallback failed source=%s event_id=%s error=%s",
                source_name,
                event_id,
                exc,
            )

    return None

def normalize_daily_odds_item(event: Dict[str, Any], raw_odds: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(event, dict):
        return None
    if not isinstance(raw_odds, dict):
        return None

    event = extract_event_from_payload(event) or event
    player1, player2 = event_home_away(event)
    event_id = event.get("id")

    if not player1 or not player2 or not event_id:
        return None

    full_time_market = select_full_time_market(raw_odds)
    if not full_time_market:
        return None

    choices = full_time_market.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        return None

    choice1, choice2 = pick_home_away_choices(choices, player1, player2)
    odds1 = choice_to_decimal(choice1)
    odds2 = choice_to_decimal(choice2)

    if odds1 is None or odds2 is None:
        return None

    return {
        "source": "TennisApiDailyOdds",
        "odds_source": "TennisApiDailyOdds",
        "bookmaker": raw_odds.get("sourceName") or raw_odds.get("bookmaker") or "TennisApi",
        "match_id": event_id,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "home_team": player1,
        "away_team": player2,
        "home": player1,
        "away": player2,
        "match": f"{player1} vs {player2}",
        "tournament": (event.get("tournament") or {}).get("name"),
        "category": ((event.get("tournament") or {}).get("category") or {}).get("name"),
        "start_timestamp": event.get("startTimestamp"),
        "start_time_utc": normalize_event(event).get("start_time_utc"),
        "odds_player1": odds1,
        "odds_player2": odds2,
        "p1_odds": odds1,
        "p2_odds": odds2,
        "home_odds": odds1,
        "away_odds": odds2,
        "odds": odds1,
        "odds1": odds1,
        "odds2": odds2,
        "price1": odds1,
        "price2": odds2,
        "market_name": full_time_market.get("marketName") or raw_odds.get("marketName"),
        "market_id": full_time_market.get("marketId") or raw_odds.get("marketId"),
        "raw": raw_odds,
    }


def legacy_item_from_normalized_event_odds(event: Dict[str, Any], normalized: Dict[str, Any], source_name: str = "TennisApiEventOdds") -> Optional[Dict[str, Any]]:
    event = extract_event_from_payload(event) or event
    player1, player2 = event_home_away(event)
    event_id = event.get("id")

    if not player1 or not player2 or not event_id:
        return None

    p1 = normalized.get("p1_odds") or normalized.get("home_odds")
    p2 = normalized.get("p2_odds") or normalized.get("away_odds")

    if p1 is None or p2 is None:
        return None

    return {
        "source": source_name,
        "odds_source": source_name,
        "bookmaker": "TennisApi",
        "match_id": event_id,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "home_team": player1,
        "away_team": player2,
        "home": player1,
        "away": player2,
        "match": f"{player1} vs {player2}",
        "tournament": (event.get("tournament") or {}).get("name"),
        "category": ((event.get("tournament") or {}).get("category") or {}).get("name"),
        "start_timestamp": event.get("startTimestamp"),
        "start_time_utc": normalize_event(event).get("start_time_utc"),
        "odds_player1": p1,
        "odds_player2": p2,
        "p1_odds": p1,
        "p2_odds": p2,
        "home_odds": p1,
        "away_odds": p2,
        "odds": p1,
        "odds1": p1,
        "odds2": p2,
        "price1": p1,
        "price2": p2,
        "raw": normalized.get("raw", normalized),
    }


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
