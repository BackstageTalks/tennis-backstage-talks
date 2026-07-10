
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from tennisapi_client import TennisApiClient, normalize_event, normalize_winning_odds

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Europe/Bratislava")
CACHE_DIR = Path("data/tennisapi_cache")


def parse_category_ids() -> List[int]:
    """Legacy optional category list. New flow discovers categories dynamically."""
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


def normalize_name(value: Any) -> str:
    return str(value or "").lower().replace(".", "").replace("-", " ").replace("_", " ").strip()


def event_home_away(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    event = event.get("raw") if isinstance(event.get("raw"), dict) and not event.get("player1") else event
    player1 = event.get("player1")
    player2 = event.get("player2")
    if player1 or player2:
        return player1, player2
    normalized = normalize_event(event)
    return normalized.get("player1"), normalized.get("player2")


def get_events_for_date(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Correct Tennis API date flow.

    Do NOT use retired /api/tennis/events/{day}/{month}/{year}.
    Use calendar categories, then category events.
    """
    target_date = betting_day_datetime(target_date)
    path = cache_path("events", target_date)

    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, list):
            return cached

    client = TennisApiClient()
    day = int(target_date.day)
    month = int(target_date.month)
    year = int(target_date.year)

    events = client.get_events_for_date(day, month, year)
    save_json(path, events)
    return events


def legacy_item_from_normalized_event_odds(event: Dict[str, Any], normalized: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    player1, player2 = event_home_away(event)
    event_id = event.get("id") or event.get("event_id") or event.get("match_id")
    if not player1 or not player2:
        return None

    p1 = normalized.get("odds_player1") or normalized.get("p1_odds") or normalized.get("home_odds")
    p2 = normalized.get("odds_player2") or normalized.get("p2_odds") or normalized.get("away_odds")
    if p1 is None or p2 is None:
        return None

    return {
        "player1": player1,
        "player2": player2,
        "match_id": event_id,
        "event_id": event_id,
        "odds_event_id": event_id,
        "odds_player1": p1,
        "odds_player2": p2,
        "p1_odds": p1,
        "p2_odds": p2,
        "home_odds": p1,
        "away_odds": p2,
        "bookmaker": normalized.get("bookmaker") or "TennisApi",
        "odds_source": normalized.get("odds_source") or "rapid_api",
        "source": normalized.get("source") or normalized.get("odds_source") or "rapid_api",
        "raw": normalized.get("raw", normalized),
    }


def fetch_event_winning_odds_item(client: TennisApiClient, event: Dict[str, Any], event_id: int) -> Optional[Dict[str, Any]]:
    try:
        event_odds_payload = client.get_match_winning_odds(event_id, provider_id())
        normalized = normalize_winning_odds(event_odds_payload)
        if normalized:
            normalized["odds_source"] = normalized.get("odds_source") or "rapid_api"
            return legacy_item_from_normalized_event_odds(event, normalized)
    except Exception as exc:
        logger.debug("Event odds fallback failed event_id=%s error=%s", event_id, exc)
    return None


def get_daily_odds_payload(target_date: Optional[datetime] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """Compatibility function. Daily batch odds endpoint may not exist for all products."""
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_batch", target_date)
    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, dict):
            return cached
    payload: Dict[str, Any] = {"events": []}
    save_json(path, payload)
    return payload


def get_daily_odds_items(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
    include_event_fallback: bool = True,
) -> List[Dict[str, Any]]:
    """Return model-compatible odds items for the betting day."""
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_items", target_date)

    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, list):
            return cached

    client = TennisApiClient()
    events = get_events_for_date(target_date, force_refresh=force_refresh)
    items: List[Dict[str, Any]] = []

    if include_event_fallback:
        for event in events:
            event_id = event.get("event_id") or event.get("match_id") or event.get("id")
            if not event_id:
                continue
            try:
                item = fetch_event_winning_odds_item(client, event, int(event_id))
                if item:
                    items.append(item)
            except Exception as exc:
                logger.debug("Daily odds item failed event_id=%s error=%s", event_id, exc)

    save_json(path, items)
    return items


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
