import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from tennisapi_client import TennisApiClient, normalize_event

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Europe/Bratislava")

VOID_STATUSES = {
    "VOID",
    "WALKOVER",
    "W/O",
    "WO",
    "RETIRED",
    "RETIREMENT",
    "RET",
    "CANCELLED",
    "CANCELED",
    "ABANDONED",
    "WITHDRAWN",
    "WITHDRAWAL",
    "DEFAULT",
    "NOT_PLAYED",
    "NOT PLAYED",
}

FINISHED_STATUSES = {
    "FINISHED",
    "ENDED",
    "COMPLETED",
    "COMPLETE",
    "AFTER_EXTRA_TIME",
    "FINAL",
}

RESULT_RELEVANT_STATUSES = FINISHED_STATUSES | VOID_STATUSES | {"POSTPONED"}


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


def safe_str(value: Any) -> str:
    return str(value or "").strip()


def status_text(event: Dict[str, Any]) -> str:
    candidates = [
        event.get("status"),
        event.get("status_type"),
        event.get("match_status"),
        event.get("event_status"),
        event.get("reason"),
        event.get("winner_type"),
        event.get("result_type"),
        event.get("type"),
        event.get("note"),
        event.get("description"),
    ]
    return " | ".join(safe_str(item) for item in candidates if item is not None).upper()


def is_void_status(event: Dict[str, Any]) -> bool:
    text = status_text(event)
    if not text:
        return False
    return any(keyword in text for keyword in VOID_STATUSES)


def normalize_status(event: Dict[str, Any]) -> str:
    text = status_text(event)
    if is_void_status(event):
        return "VOID"
    for status in FINISHED_STATUSES:
        if status in text:
            return "FINISHED"
    if "POSTPONED" in text:
        return "POSTPONED"
    return safe_str(event.get("status") or event.get("match_status") or "UNKNOWN").upper()


def get_first(event: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in event and event.get(key) not in [None, ""]:
            return event.get(key)
    return None


def player1_name(event: Dict[str, Any]) -> Optional[str]:
    return get_first(
        event,
        [
            "player1",
            "home",
            "home_name",
            "homeTeam",
            "home_team",
            "home_player",
            "participant1",
            "participant1_name",
            "player_home",
        ],
    )


def player2_name(event: Dict[str, Any]) -> Optional[str]:
    return get_first(
        event,
        [
            "player2",
            "away",
            "away_name",
            "awayTeam",
            "away_team",
            "away_player",
            "participant2",
            "participant2_name",
            "player_away",
        ],
    )


def winner_name(event: Dict[str, Any]) -> Optional[str]:
    winner = get_first(
        event,
        [
            "winner",
            "winner_name",
            "winnerName",
            "winning_player",
            "winner_player",
        ],
    )
    if winner:
        return winner

    winner_code = safe_str(get_first(event, ["winner_code", "winner_side", "winnerSide", "winner_team", "winnerTeam"])).lower()
    if winner_code in {"home", "1", "player1", "participant1"}:
        return player1_name(event)
    if winner_code in {"away", "2", "player2", "participant2"}:
        return player2_name(event)

    return None


def event_date(event: Dict[str, Any]) -> Optional[str]:
    explicit = get_first(event, ["date", "event_date", "match_date", "start_date"])
    if explicit:
        text = str(explicit)
        if len(text) >= 10 and text[4:5] == "-":
            return text[:10]

    timestamp = get_first(event, ["start_timestamp", "startTime", "start_time", "timestamp", "time"])
    return unix_to_local_date(timestamp)


def get_score_value(event: Dict[str, Any], keys: List[str]) -> Any:
    return get_first(event, keys)


def build_score(event: Dict[str, Any]) -> Optional[str]:
    existing = get_first(event, ["score", "result_score", "final_score", "match_score"])
    if existing:
        return str(existing)

    set_parts: List[str] = []
    for idx in range(1, 6):
        home = get_score_value(
            event,
            [
                f"home_score_period{idx}",
                f"home_score_period_{idx}",
                f"home_period_{idx}",
                f"home_set_{idx}",
                f"p1_set_{idx}",
                f"player1_set_{idx}",
                f"homePeriod{idx}",
            ],
        )
        away = get_score_value(
            event,
            [
                f"away_score_period{idx}",
                f"away_score_period_{idx}",
                f"away_period_{idx}",
                f"away_set_{idx}",
                f"p2_set_{idx}",
                f"player2_set_{idx}",
                f"awayPeriod{idx}",
            ],
        )
        if home is None or away is None:
            continue
        set_parts.append(f"{home}-{away}")

    if set_parts:
        return " ".join(set_parts)

    home_current = get_first(event, ["home_score_current", "home_current_score", "home_score", "p1_score"])
    away_current = get_first(event, ["away_score_current", "away_current_score", "away_score", "p2_score"])
    if home_current is not None and away_current is not None:
        return f"{home_current}-{away_current}"

    return None


def event_id(event: Dict[str, Any]) -> Any:
    return get_first(event, ["event_id", "match_id", "id", "eventId", "matchId"])


def safe_normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        normalized = normalize_event(event)
        if isinstance(normalized, dict):
            merged = dict(event)
            merged.update(normalized)
            return merged
    except Exception as exc:
        logger.debug("normalize_event failed: %s", exc)
    return dict(event)


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

    for event in raw_events or []:
        if isinstance(event, dict):
            normalized_events.append(safe_normalize_event(event))

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

def event_to_finished_result(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    normalized = safe_normalize_event(event)
    status = normalize_status(normalized)

    if status not in RESULT_RELEVANT_STATUSES and status not in {"VOID", "FINISHED"}:
        return None

    if status == "POSTPONED":
        # Postponed is not settled. Keep it out of finished results so checker keeps picks pending.
        return None

    player1 = player1_name(normalized)
    player2 = player2_name(normalized)

    if not player1 or not player2:
        return None

    score = build_score(normalized)
    winner = winner_name(normalized)
    final_status = "VOID" if is_void_status(normalized) else "FINISHED"

    return {
        "match_id": event_id(normalized),
        "event_id": event_id(normalized),
        "date": event_date(normalized),
        "player1": player1,
        "player2": player2,
        "winner": winner,
        "score": score,
        "status": final_status,
        "raw_status": status_text(normalized),
        "source": "tennisapi_pro",
        "match": normalized.get("match") or f"{player1} vs {player2}",
        "raw": normalized,
    }


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
            logger.warning("Failed fetching TennisApi results for %s: %s", target_date.date(), exc)
            continue

        for event in events:
            result = event_to_finished_result(event)
            if not result:
                continue

            key = (
                str(result.get("event_id") or result.get("match_id") or ""),
                str(result.get("date") or ""),
                str(result.get("player1") or ""),
                str(result.get("player2") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            all_results.append(result)

    return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Category IDs:", parse_category_ids())
    print("Lookback days:", parse_finished_lookback_days())
    results = fetch_finished_results()
    print(f"Finished results found: {len(results)}")
    for result in results[:20]:
        print(
            result.get("date"),
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
            "raw_status:",
            result.get("raw_status"),
        )
