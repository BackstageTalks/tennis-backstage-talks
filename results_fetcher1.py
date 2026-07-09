import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from tennisapi_client import TennisApiClient, normalize_event


logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Europe/Bratislava")


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


def parse_finished_lookback_days() -> int:
    try:
        return int(os.getenv("RESULTS_LOOKBACK_DAYS", "90"))
    except Exception:
        return 90


def unix_to_local_date(timestamp: Any) -> Optional[str]:
    try:
        if not timestamp:
            return None
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
    except Exception:
        return None


# ----------------------------------------------------------------------
# Fixtures / snapshot functions
# ----------------------------------------------------------------------


def fetch_tennisapi_events_for_date(
    target_date: datetime,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    client = TennisApiClient()
    category_ids = category_ids or parse_category_ids()
    raw_events = client.get_events_by_date(target_date=target_date, category_ids=category_ids)
    normalized_events: List[Dict[str, Any]] = []

    for event in raw_events:
        try:
            normalized = normalize_event(event)
            if not normalized.get("match_id"):
                continue
            if not normalized.get("player1") or not normalized.get("player2"):
                continue
            normalized["date"] = unix_to_local_date(normalized.get("start_timestamp"))
            normalized_events.append(normalized)
        except Exception as exc:
            logger.warning("Failed to normalize TennisApi event: %s", exc)

    return normalized_events


def fetch_daily_fixtures(target_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    target_date = target_date or datetime.now(LOCAL_TZ)
    tennisapi_events = fetch_tennisapi_events_for_date(target_date)
    if tennisapi_events:
        logger.info("Fetched %s fixtures from TennisApi for %s", len(tennisapi_events), target_date.date())
        return tennisapi_events
    logger.warning("TennisApi returned no fixtures for %s", target_date.date())
    return []


def get_matches_for_snapshot(target_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    return fetch_daily_fixtures(target_date)


# ----------------------------------------------------------------------
# Finished results for results_checker.py
# ----------------------------------------------------------------------


def fetch_finished_results(
    lookback_days: Optional[int] = None,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    lookback_days = lookback_days or parse_finished_lookback_days()
    category_ids = category_ids or parse_category_ids()
    today = datetime.now(LOCAL_TZ)
    all_results: List[Dict[str, Any]] = []
    seen = set()

    for offset in range(lookback_days):
        target_date = today - timedelta(days=offset)
        try:
            events = fetch_tennisapi_events_for_date(target_date=target_date, category_ids=category_ids)
        except Exception as exc:
            logger.warning("Finished results fetch failed for %s: %s", target_date.date(), exc)
            continue

        for event in events:
            match_id = event.get("match_id")
            if match_id in seen:
                continue
            seen.add(match_id)
            result = event_to_finished_result(event)
            if result:
                all_results.append(result)

    logger.info("TennisApi finished results found: %s", len(all_results))
    return all_results


def event_to_finished_result(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = str(event.get("status") or "").upper()
    if status not in ["FINISHED", "WALKOVER", "RETIRED", "CANCELLED", "POSTPONED"]:
        return None

    player1 = event.get("player1")
    player2 = event.get("player2")
    if not player1 or not player2:
        return None

    result_status = "VOID" if status in ["WALKOVER", "RETIRED", "CANCELLED", "POSTPONED"] else "FINISHED"
    result_date = event.get("date") or unix_to_local_date(event.get("start_timestamp"))

    return {
        "source": "TennisApi",
        "match_id": event.get("match_id"),
        "event_id": event.get("event_id") or event.get("match_id"),
        "date": result_date,
        "player1": player1,
        "player2": player2,
        "winner": event.get("winner"),
        "score": build_score(event),
        "status": result_status,
        "match": f"{player1} vs {player2}",
        "tournament": event.get("tournament"),
        "category": event.get("category"),
        "start_time_utc": event.get("start_time_utc"),
        "raw": event.get("raw", event),
    }


def build_score(event: Dict[str, Any]) -> Optional[str]:
    set_parts: List[str] = []
    for idx in range(1, 6):
        h = event.get(f"home_score_period{idx}")
        a = event.get(f"away_score_period{idx}")
        if h is None or a is None:
            continue
        set_parts.append(f"{h}-{a}")
    if set_parts:
        return " ".join(set_parts)

    h_current = event.get("home_score_current")
    a_current = event.get("away_score_current")
    if h_current is not None and a_current is not None:
        return f"{h_current}-{a_current}"
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Category IDs:", parse_category_ids())
    print("Lookback days:", parse_finished_lookback_days())
    results = fetch_finished_results()
    print(f"Finished results found: {len(results)}")
    for result in results[:20]:
        print(result.get("date"), result.get("match_id"), result.get("player1"), "vs", result.get("player2"), "winner:", result.get("winner"), "score:", result.get("score"), "status:", result.get("status"))
