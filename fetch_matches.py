import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from tennisapi_client import TennisApiClient, normalize_event


logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Europe/Bratislava")


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------


def parse_category_ids() -> List[int]:
    """
    TennisApi categories used for fixtures.

    Current working set:
    - 3   = ATP / ATP events confirmed earlier
    - 6   = likely WTA / main women's tennis category candidate
    - 871 = WTA 125 confirmed from API response

    Override in GitHub Actions with:
        TENNISAPI_CATEGORY_IDS=3,6,871
    """
    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3,6,871").strip()
    category_ids: List[int] = []

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            category_ids.append(int(part))
        except Exception:
            logger.warning("Invalid TENNISAPI_CATEGORY_IDS item ignored: %s", part)

    return category_ids or [3]


def betting_day(date_time: Optional[datetime] = None) -> datetime:
    """
    Snapshot day logic aligned with project rule:
    before 06:00 SK/CZ treat as previous betting day.
    """
    if date_time is None:
        date_time = datetime.now(LOCAL_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=LOCAL_TZ)
    else:
        date_time = date_time.astimezone(LOCAL_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time


# ----------------------------------------------------------------------
# Public API consumed by prediction_engine_core.py
# ----------------------------------------------------------------------


def get_today_matches() -> List[Dict[str, Any]]:
    """
    Main fixture entrypoint used by prediction_engine_core.py.

    Important fix:
    Every returned match now keeps TennisApi event identity:
        match_id / event_id / id

    This allows odds_api.py to attach TennisApi odds via:
        /api/tennis/event/{event_id}/provider/1/winning-odds
    """
    target_dt = betting_day()
    matches = get_matches_for_date(target_dt)

    print("FETCH_MATCHES TENNISAPI COUNT:", len(matches))
    if matches[:5]:
        for item in matches[:5]:
            print(
                "FETCH_MATCHES SAMPLE:",
                item.get("match_id"),
                item.get("player1"),
                "vs",
                item.get("player2"),
                item.get("tournament"),
                item.get("category"),
            )

    return matches


def get_matches_for_date(target_date: datetime) -> List[Dict[str, Any]]:
    client = TennisApiClient()
    category_ids = parse_category_ids()

    all_matches: List[Dict[str, Any]] = []
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
                "TennisApi fixture fetch failed. category_id=%s date=%s error=%s",
                category_id,
                target_date.date(),
                exc,
            )
            continue

        for event in events:
            match = normalize_tennisapi_event_for_model(event)
            if not match:
                continue

            match_id = match.get("match_id")
            if match_id in seen:
                continue
            seen.add(match_id)
            all_matches.append(match)

    all_matches.sort(key=lambda item: item.get("start_timestamp") or 0)
    return all_matches


# ----------------------------------------------------------------------
# Normalization
# ----------------------------------------------------------------------


def normalize_tennisapi_event_for_model(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    normalized = normalize_event(event)

    match_id = normalized.get("match_id")
    player1 = normalized.get("player1")
    player2 = normalized.get("player2")

    if not match_id or not player1 or not player2:
        return None

    status = str(normalized.get("status") or "UNKNOWN").upper()

    # For prediction snapshot, keep playable matches. Finished results are handled elsewhere.
    if status in {"CANCELLED", "POSTPONED", "WALKOVER"}:
        return None

    category = normalized.get("category")
    tournament = normalized.get("tournament")
    surface = infer_surface_from_event(normalized)
    gender = infer_gender_from_category(category)
    best_of = infer_best_of(normalized)

    start_timestamp = normalized.get("start_timestamp")
    match_start = timestamp_to_iso_utc(start_timestamp)

    return {
        # Critical identity fields for odds/results pairing
        "match_id": match_id,
        "event_id": match_id,
        "id": match_id,
        "source": "TennisApi",

        # Core model fields
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}",
        "surface": surface,
        "tournament": tournament,
        "category": category,
        "gender": gender,
        "best_of": best_of,

        # Time fields consumed by prediction_engine_core.py
        "match_start": match_start,
        "start_time": match_start,
        "commence_time": match_start,
        "start_timestamp": start_timestamp,

        # Extra metadata
        "status": normalized.get("status"),
        "round": normalized.get("round"),
        "home_seed": normalized.get("home_seed"),
        "away_seed": normalized.get("away_seed"),
        "raw": normalized.get("raw"),
    }


def timestamp_to_iso_utc(timestamp: Any) -> Optional[str]:
    if not timestamp:
        return None

    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except Exception:
        return None


def infer_gender_from_category(category: Any) -> Optional[str]:
    text = str(category or "").lower()

    if "wta" in text or "women" in text:
        return "WTA"
    if "atp" in text or "challenger" in text:
        return "ATP"

    return str(category) if category else None


def infer_best_of(event: Dict[str, Any]) -> int:
    tournament = str(event.get("tournament") or "").lower()
    category = str(event.get("category") or "").lower()

    # Wimbledon/RG/AO/US Open men's main draw can be BO5.
    # Without a reliable round/gender signal, project default remains BO3.
    if "atp" in category and any(
        slam in tournament
        for slam in ["wimbledon", "roland garros", "australian open", "us open"]
    ):
        return 5

    return 3


def infer_surface_from_event(event: Dict[str, Any]) -> str:
    tournament = str(event.get("tournament") or "").lower()

    if "wimbledon" in tournament or "grass" in tournament:
        return "Grass"
    if "roland garros" in tournament or "clay" in tournament:
        return "Clay"
    if "hard" in tournament:
        return "Hard"

    return "Hard"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    matches = get_today_matches()
    print("Matches found:", len(matches))
    for match in matches[:30]:
        print(
            match.get("match_id"),
            match.get("player1"),
            "vs",
            match.get("player2"),
            "|",
            match.get("tournament"),
            "|",
            match.get("category"),
            "|",
            match.get("match_start"),
        )
