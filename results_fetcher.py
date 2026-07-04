import os
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tennisapi_client import TennisApiClient, normalize_event


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------


def parse_category_ids() -> List[int]:
    """
    TennisApi category IDs.

    Confirmed from our RapidAPI test:
    - ATP = 3

    Add WTA/Challenger/ITF later after you confirm their IDs in RapidAPI.
    Example GitHub env/secret variable:
        TENNISAPI_CATEGORY_IDS=3,6,12
    """
    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3").strip()
    category_ids: List[int] = []

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            category_ids.append(int(part))
        except ValueError:
            logger.warning("Invalid TennisApi category id ignored: %s", part)

    return category_ids or [3]


def parse_finished_lookback_days() -> int:
    try:
        return int(os.getenv("RESULTS_LOOKBACK_DAYS", "7"))
    except Exception:
        return 7


# ----------------------------------------------------------------------
# Fixtures / snapshot functions used by update.py or other modules
# ----------------------------------------------------------------------


def fetch_tennisapi_events_for_date(
    target_date: datetime,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    client = TennisApiClient()
    category_ids = category_ids or parse_category_ids()

    raw_events = client.get_events_by_date(
        target_date=target_date,
        category_ids=category_ids,
    )

    normalized_events: List[Dict[str, Any]] = []

    for event in raw_events:
        try:
            normalized = normalize_event(event)
            if not normalized.get("match_id"):
                continue
            if not normalized.get("player1") or not normalized.get("player2"):
                continue
            normalized_events.append(normalized)
        except Exception as exc:
            logger.warning("Failed to normalize TennisApi event: %s", exc)

    return normalized_events


def fetch_daily_fixtures(target_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    target_date = target_date or datetime.now()
    tennisapi_events = fetch_tennisapi_events_for_date(target_date)

    if tennisapi_events:
        logger.info(
            "Fetched %s fixtures from TennisApi for %s",
            len(tennisapi_events),
            target_date.date(),
        )
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
    """
    Main function expected by results_checker.py.

    Returns normalized finished results from TennisApi for the last N days.
    results_checker.py then matches stored picks against these results.
    """
    lookback_days = lookback_days or parse_finished_lookback_days()
    category_ids = category_ids or parse_category_ids()

    today = datetime.now()
    all_results: List[Dict[str, Any]] = []
    seen = set()

    for offset in range(lookback_days):
        target_date = today - timedelta(days=offset)
        try:
            events = fetch_tennisapi_events_for_date(
                target_date=target_date,
                category_ids=category_ids,
            )
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

    # Keep only finished/void-like matches. Scheduled/live remain pending in results_checker.
    if status not in ["FINISHED", "WALKOVER", "RETIRED", "CANCELLED", "POSTPONED"]:
        return None

    player1 = event.get("player1")
    player2 = event.get("player2")

    if not player1 or not player2:
        return None

    winner = event.get("winner")
    result_status = "VOID" if status in ["WALKOVER", "RETIRED", "CANCELLED", "POSTPONED"] else "FINISHED"

    return {
        "source": "TennisApi",
        "match_id": event.get("match_id"),
        "player1": player1,
        "player2": player2,
        "winner": winner,
        "score": build_score(event),
        "status": result_status,
        "match": f"{player1} vs {player2}",
        "tournament": event.get("tournament"),
        "category": event.get("category"),
        "start_time_utc": event.get("start_time_utc"),
        "raw": event.get("raw", event),
    }


def build_score(event: Dict[str, Any]) -> Optional[str]:
    """
    Builds a readable tennis score.

    If per-set periods exist, returns e.g. "6-4 7-6".
    Otherwise falls back to current set score e.g. "2-1".
    """
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


# ----------------------------------------------------------------------
# Debug CLI
# ----------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Category IDs:", parse_category_ids())
    print("Lookback days:", parse_finished_lookback_days())

    results = fetch_finished_results()
    print(f"Finished results found: {len(results)}")

    for result in results[:20]:
        print(
            result.get("match_id"),
            result.get("player1"),
            "vs",
            result.get("player2"),
            "winner:",
            result.get("winner"),
            "score:",
            result.get("score"),
            "status:",
            result.get("status"),
        )
