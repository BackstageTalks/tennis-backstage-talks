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
    Fallback TennisApi categories used only when the dynamic calendar category
    endpoint is unavailable or returns no category IDs.

    Provider-confirmed production flow is dynamic:
        /api/tennis/calendar/{day}/{month}/{year}/categories
        /api/tennis/category/{categoryId}/events/{day}/{month}/{year}

    Do not rely on these IDs as the primary source. They are only a fallback.
    """
    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3,6,72,871,213,785").strip()
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


def parse_min_minutes_before_start() -> int:
    """
    Do not publish picks for matches that already started or are too close to start.

    Default 5 minutes: if workflow runs late, matches already in progress/finished
    are skipped. Override with:
        MIN_MINUTES_BEFORE_MATCH_START=0
    """
    try:
        return int(os.getenv("MIN_MINUTES_BEFORE_MATCH_START", "5"))
    except Exception:
        return 5


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
# Category discovery helpers
# ----------------------------------------------------------------------


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        for key in ("categories", "events", "data", "items"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested

    return []


def _extract_category_id(category: Any) -> Optional[int]:
    if not isinstance(category, dict):
        return None

    raw_id = (
        category.get("id")
        or category.get("categoryId")
        or category.get("category_id")
        or category.get("cid")
    )

    try:
        return int(raw_id)
    except Exception:
        return None


def get_dynamic_category_ids(client: TennisApiClient, target_date: datetime) -> List[int]:
    """
    Provider-confirmed first step for TennisApi PRO fixtures.

    Returns only categories that have matches for the requested day.
    This avoids hardcoding ATP/WTA/Challenger/ITF category IDs.
    """
    day = target_date.day
    month = target_date.month
    year = target_date.year

    try:
        categories_payload = client.get_calendar_categories(day, month, year)
    except Exception as exc:
        logger.warning(
            "TennisApi calendar categories fetch failed. date=%s error=%s",
            target_date.date(),
            exc,
        )
        return []

    category_ids: List[int] = []
    seen = set()

    for category in _as_list(categories_payload):
        category_id = _extract_category_id(category)
        if category_id is None or category_id in seen:
            continue

        seen.add(category_id)
        category_ids.append(category_id)

    print(
        "FETCH_MATCHES DYNAMIC CATEGORIES:",
        category_ids,
        "date:",
        target_date.strftime("%Y-%m-%d"),
    )

    return category_ids


# ----------------------------------------------------------------------
# Public API consumed by prediction_engine_core.py
# ----------------------------------------------------------------------


def get_today_matches() -> List[Dict[str, Any]]:
    """
    Main fixture entrypoint used by prediction_engine_core.py.

    TennisApi PRO is primary and every returned match keeps:
        match_id / event_id / id

    Safety:
        Finished, cancelled, retired, walkover, live/in-progress and already-started
        matches are excluded from prediction snapshots.
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
                item.get("match_start"),
            )

    return matches


def get_matches_for_date(target_date: datetime) -> List[Dict[str, Any]]:
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=LOCAL_TZ)
    else:
        target_date = target_date.astimezone(LOCAL_TZ)

    client = TennisApiClient()

    dynamic_category_ids = get_dynamic_category_ids(client, target_date)
    fallback_category_ids = parse_category_ids()
    category_ids = dynamic_category_ids or fallback_category_ids

    if not dynamic_category_ids:
        print("FETCH_MATCHES USING FALLBACK CATEGORY IDS:", category_ids)

    all_matches: List[Dict[str, Any]] = []
    seen = set()

    skipped = {
        "invalid": 0,
        "duplicate": 0,
        "not_playable_status": 0,
        "wrong_local_date": 0,
        "already_started": 0,
    }

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

        print(
            "FETCH_MATCHES CATEGORY EVENTS:",
            category_id,
            len(events) if isinstance(events, list) else "invalid",
        )

        for event in events or []:
            match = normalize_tennisapi_event_for_model(
                event,
                target_date=target_date,
                skipped=skipped,
            )

            if not match:
                continue

            match_id = match.get("match_id")
            if match_id in seen:
                skipped["duplicate"] += 1
                continue

            seen.add(match_id)
            all_matches.append(match)

    all_matches.sort(key=lambda item: item.get("start_timestamp") or 0)

    print("FETCH_MATCHES SKIPPED:", skipped)
    return all_matches


# ----------------------------------------------------------------------
# Normalization + filtering
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# TennisApi metadata helpers
# ----------------------------------------------------------------------


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _deep_find_first(obj: Any, keys: set) -> Any:
    """
    Recursively find the first non-empty value for any key in `keys`.
    Used defensively because TennisApi payloads can expose tournament ids under
    event.tournament.id, event.uniqueTournament.id, event.competition.id, etc.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key) in keys and value is not None and value != "":
                return value
        for value in obj.values():
            found = _deep_find_first(value, keys)
            if found is not None and found != "":
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_first(item, keys)
            if found is not None and found != "":
                return found
    return None


def _deep_find_dict_with_keys(obj: Any, wanted_names: set) -> Optional[Dict[str, Any]]:
    """
    Find a nested dict that looks like a TennisApi tournament/competition object.
    """
    if isinstance(obj, dict):
        name = str(obj.get("name") or obj.get("tournamentName") or obj.get("competitionName") or "").lower()
        if name and any(token in name for token in wanted_names):
            return obj
        for key, value in obj.items():
            if str(key).lower() in wanted_names and isinstance(value, dict):
                return value
            nested = _deep_find_dict_with_keys(value, wanted_names)
            if nested:
                return nested
    elif isinstance(obj, list):
        for item in obj:
            nested = _deep_find_dict_with_keys(item, wanted_names)
            if nested:
                return nested
    return None


def normalize_surface_label(value: Any) -> Dict[str, Any]:
    """
    Normalize raw API surface text without guessing.

    Rule agreed in project:
      - any raw text containing "hard" maps to Hard
      - Carpet is kept as real surface, but model bucket is Hard until carpet ELO exists
      - unknown stays Unknown, never default Hard
    """
    raw = str(value or "").strip()
    text = raw.lower()

    environment = None
    if "indoor" in text:
        environment = "Indoor"
    elif "outdoor" in text:
        environment = "Outdoor"

    flags = []
    if "clay" in text:
        surface = "Clay"
        bucket = "Clay"
        selected = "clay_elo"
    elif "grass" in text:
        surface = "Grass"
        bucket = "Grass"
        selected = "grass_elo"
    elif "carpet" in text:
        surface = "Carpet"
        bucket = "Hard"
        selected = "hard_elo"
        flags.append("CARPET_AS_HARD_FALLBACK")
    elif "hard" in text:
        surface = "Hard"
        bucket = "Hard"
        selected = "hard_elo"
    else:
        surface = "Unknown"
        bucket = "Unknown"
        selected = "overall_elo"
        if raw:
            flags.append("UNKNOWN_SURFACE_RAW")
        else:
            flags.append("NO_SURFACE_RAW")

    return {
        "surface": surface,
        "surface_raw": raw or None,
        "surface_environment": environment,
        "surface_model_bucket": bucket,
        "thinq_selected_elo_type": selected,
        "surface_flags": flags,
    }


def extract_tournament_metadata(normalized: Dict[str, Any], raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preserve all tournament identifiers needed by THINQ surface resolver.
    This is the missing link for calling:
      /api/tennis/tournament/{tournament_id}/info
    """
    raw = raw_event if isinstance(raw_event, dict) else {}

    tournament_dict = _deep_find_dict_with_keys(raw, {"tournament", "competition"}) or {}
    unique_tournament_dict = _deep_find_dict_with_keys(raw, {"uniquetournament", "unique_tournament"}) or {}
    category_dict = _deep_find_dict_with_keys(raw, {"category"}) or {}

    tournament_id = _first_non_empty(
        normalized.get("tournament_id"),
        normalized.get("tournamentId"),
        raw.get("tournament_id"),
        raw.get("tournamentId"),
        tournament_dict.get("id"),
        tournament_dict.get("tournamentId"),
        _deep_find_first(raw, {"tournament_id", "tournamentId"}),
    )

    unique_tournament_id = _first_non_empty(
        normalized.get("unique_tournament_id"),
        normalized.get("uniqueTournamentId"),
        raw.get("unique_tournament_id"),
        raw.get("uniqueTournamentId"),
        unique_tournament_dict.get("id"),
        unique_tournament_dict.get("uniqueTournamentId"),
        tournament_dict.get("uniqueTournamentId"),
        _deep_find_first(raw, {"unique_tournament_id", "uniqueTournamentId"}),
    )

    competition_id = _first_non_empty(
        normalized.get("competition_id"),
        normalized.get("competitionId"),
        raw.get("competition_id"),
        raw.get("competitionId"),
        tournament_dict.get("competitionId"),
        tournament_dict.get("competition_id"),
        _deep_find_first(raw, {"competition_id", "competitionId"}),
    )

    category_id = _first_non_empty(
        normalized.get("category_id"),
        normalized.get("categoryId"),
        raw.get("category_id"),
        raw.get("categoryId"),
        category_dict.get("id"),
        _deep_find_first(raw, {"category_id", "categoryId"}),
    )

    raw_surface = _first_non_empty(
        normalized.get("surface_raw"),
        normalized.get("surfaceType"),
        normalized.get("surface"),
        raw.get("surface_raw"),
        raw.get("surfaceType"),
        raw.get("surface"),
        tournament_dict.get("surfaceType"),
        tournament_dict.get("surface"),
        _deep_find_first(raw, {"surfaceType", "surface", "courtSurface", "groundType"}),
    )

    surface_info = normalize_surface_label(raw_surface)
    if surface_info["surface"] != "Unknown":
        surface_info["surface_source"] = "tennisapi_event_payload"
        surface_info["surface_confidence"] = "MEDIUM"
    else:
        surface_info["surface_source"] = "unknown"
        surface_info["surface_confidence"] = "LOW"

    return {
        "tournament_id": tournament_id,
        "tournamentId": tournament_id,
        "unique_tournament_id": unique_tournament_id,
        "uniqueTournamentId": unique_tournament_id,
        "competition_id": competition_id,
        "competitionId": competition_id,
        "category_id": category_id,
        "categoryId": category_id,
        **surface_info,
    }



def normalize_tennisapi_event_for_model(
    event: Dict[str, Any],
    target_date: datetime,
    skipped: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    normalized = normalize_event(event)

    match_id = normalized.get("match_id")
    player1 = normalized.get("player1")
    player2 = normalized.get("player2")

    if not match_id or not player1 or not player2:
        increment(skipped, "invalid")
        return None

    status = str(normalized.get("status") or "UNKNOWN").upper()

    # Only future scheduled/not-started matches can enter prediction snapshot.
    # This prevents yesterday/already-played matches from appearing in TOP/TOP7.
    if status not in {"NOT_STARTED", "UNKNOWN"}:
        increment(skipped, "not_playable_status")
        return None

    start_timestamp = normalized.get("start_timestamp")
    start_dt_utc = timestamp_to_datetime_utc(start_timestamp)

    if start_dt_utc is not None:
        start_dt_local = start_dt_utc.astimezone(LOCAL_TZ)
        target_local_date = target_date.astimezone(LOCAL_TZ).date()

        # Defensive guard: only keep matches from the selected betting date.
        if start_dt_local.date() != target_local_date:
            increment(skipped, "wrong_local_date")
            return None

        min_minutes = parse_min_minutes_before_start()
        earliest_allowed_start = datetime.now(timezone.utc) + timedelta(minutes=min_minutes)

        if start_dt_utc <= earliest_allowed_start:
            increment(skipped, "already_started")
            return None

    category = normalized.get("category")
    tournament = normalized.get("tournament")
    raw_event = normalized.get("raw") if isinstance(normalized.get("raw"), dict) else event
    metadata = extract_tournament_metadata(normalized, raw_event)
    surface = metadata.get("surface") or "Unknown"
    gender = infer_gender_from_category(category)
    best_of = infer_best_of(normalized)
    match_start = timestamp_to_iso_utc(start_timestamp)

    return {
        # Critical identity fields for odds/results pairing.
        "match_id": match_id,
        "event_id": match_id,
        "id": match_id,
        "source": "TennisApiPROCategoryEvents",

        # Core model fields.
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}",
        "surface": surface,
        "tournament": tournament,
        "category": category,
        "gender": gender,
        "best_of": best_of,

        # Tournament identifiers for THINQ surface resolver.
        "tournament_id": metadata.get("tournament_id"),
        "tournamentId": metadata.get("tournamentId"),
        "unique_tournament_id": metadata.get("unique_tournament_id"),
        "uniqueTournamentId": metadata.get("uniqueTournamentId"),
        "competition_id": metadata.get("competition_id"),
        "competitionId": metadata.get("competitionId"),
        "category_id": metadata.get("category_id"),
        "categoryId": metadata.get("categoryId"),

        # Surface audit fields. Final high-confidence surface can still be upgraded
        # later by THINQ surface_loader from tournament metadata endpoint.
        "surface_raw": metadata.get("surface_raw"),
        "surface_environment": metadata.get("surface_environment"),
        "surface_model_bucket": metadata.get("surface_model_bucket"),
        "surface_source": metadata.get("surface_source"),
        "surface_confidence": metadata.get("surface_confidence"),
        "surface_flags": metadata.get("surface_flags"),
        "thinq_selected_elo_type": metadata.get("thinq_selected_elo_type"),

        # Time fields consumed by prediction_engine_core.py.
        "match_start": match_start,
        "start_time": match_start,
        "commence_time": match_start,
        "start_timestamp": start_timestamp,

        # Extra metadata.
        "status": normalized.get("status"),
        "round": normalized.get("round"),
        "home_seed": normalized.get("home_seed"),
        "away_seed": normalized.get("away_seed"),
        "raw": raw_event,
    }


def increment(counter: Optional[Dict[str, int]], key: str) -> None:
    if isinstance(counter, dict):
        counter[key] = int(counter.get(key, 0)) + 1


def timestamp_to_datetime_utc(timestamp: Any) -> Optional[datetime]:
    if not timestamp:
        return None

    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except Exception:
        return None


def timestamp_to_iso_utc(timestamp: Any) -> Optional[str]:
    dt = timestamp_to_datetime_utc(timestamp)
    return dt.isoformat() if dt else None


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

    # Doubles should not be inferred as classic BO5 for set model.
    if "doubles" in tournament:
        return 3

    if "atp" in category and any(
        slam in tournament
        for slam in ["wimbledon", "roland garros", "australian open", "us open"]
    ):
        return 5

    return 3


def infer_surface_from_event(event: Dict[str, Any]) -> str:
    """
    Backward-compatible helper. Never guess Hard by default.
    Prefer explicit raw surface-like fields if they exist, else Unknown.
    """
    raw_surface = _first_non_empty(
        event.get("surface_raw"),
        event.get("surfaceType"),
        event.get("surface"),
        _deep_find_first(event.get("raw"), {"surfaceType", "surface", "courtSurface", "groundType"}),
    )
    return normalize_surface_label(raw_surface).get("surface") or "Unknown"


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
            match.get("status"),
            "|",
            match.get("match_start"),
        )
