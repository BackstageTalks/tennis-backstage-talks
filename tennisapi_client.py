import os
import json
import time
import logging
import http.client
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


class TennisApiError(Exception):
    pass


class TennisApiClient:
    """
    TennisApi / REcodeX PRO client cez RapidAPI.

    Potvrdené endpointy:
    - /api/tennis/category/{category_id}/events/{day}/{month}/{year}
    - getTennisMatchDetails endpoint cez match/event id
    - getMatchWinningOdds cez match id + provider id

    Poznámka:
    Niektoré RapidAPI endpoint pathy sa môžu líšiť podľa názvu endpointu.
    Preto detail/odds používajú viac kandidátskych URL a prvá úspešná odpoveď sa vráti.
    """

    BASE_HOST = "tennisapi1.p.rapidapi.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        rapidapi_host: str = BASE_HOST,
        timeout: int = 30,
        max_retries: int = 2,
        retry_sleep_seconds: float = 0.7,
    ):
        self.api_key = api_key or os.getenv("TENNISAPI_RAPIDAPI_KEY", "").strip()
        self.rapidapi_host = rapidapi_host
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_sleep_seconds = retry_sleep_seconds

        if not self.api_key:
            raise TennisApiError(
                "Missing TennisApi key. Set TENNISAPI_RAPIDAPI_KEY environment variable."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.rapidapi_host,
            "Content-Type": "application/json",
        }

    def _request_json(self, method: str, path: str) -> Dict[str, Any]:
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                conn = http.client.HTTPSConnection(
                    self.rapidapi_host,
                    timeout=self.timeout,
                )

                conn.request(
                    method.upper(),
                    path,
                    headers=self._headers(),
                )

                res = conn.getresponse()
                raw = res.read().decode("utf-8", errors="replace")

                if res.status >= 400:
                    raise TennisApiError(
                        f"TennisApi HTTP {res.status} for {path}: {raw[:500]}"
                    )

                if not raw:
                    return {}

                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise TennisApiError(
                        f"TennisApi returned invalid JSON for {path}: {raw[:500]}"
                    ) from exc

            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_sleep_seconds)
                else:
                    break

        raise TennisApiError(f"TennisApi request failed for {path}: {last_error}")

    def _try_paths(self, paths: List[str]) -> Dict[str, Any]:
        errors = []

        for path in paths:
            try:
                data = self._request_json("GET", path)
                if isinstance(data, dict):
                    return data
            except Exception as exc:
                errors.append(f"{path} -> {exc}")

        raise TennisApiError("All TennisApi candidate paths failed: " + " | ".join(errors))

    # ---------------------------------------------------------------------
    # Fixtures / Events
    # ---------------------------------------------------------------------

    def get_events_by_category_date(
        self,
        category_id: int,
        day: int,
        month: int,
        year: int,
    ) -> List[Dict[str, Any]]:
        path = f"/api/tennis/category/{category_id}/events/{day}/{month}/{year}"
        data = self._request_json("GET", path)

        events = data.get("events", [])
        if not isinstance(events, list):
            return []

        return events

    def get_events_by_date(
        self,
        target_date: datetime,
        category_ids: List[int],
    ) -> List[Dict[str, Any]]:
        all_events = []

        day = target_date.day
        month = target_date.month
        year = target_date.year

        for category_id in category_ids:
            try:
                events = self.get_events_by_category_date(
                    category_id=category_id,
                    day=day,
                    month=month,
                    year=year,
                )
                all_events.extend(events)
            except Exception as exc:
                logger.warning(
                    "TennisApi category fetch failed. category_id=%s date=%s error=%s",
                    category_id,
                    target_date.date(),
                    exc,
                )

        return deduplicate_events(all_events)

    # ---------------------------------------------------------------------
    # Match details
    # ---------------------------------------------------------------------

    def get_match_details(self, match_id: int) -> Dict[str, Any]:
        """
        Vracia celý detail zápasu.

        Podľa RapidAPI endpointu getTennisMatchDetails môže byť path jedna z týchto.
        Prvá funkčná sa použije.
        """
        paths = [
            f"/api/tennis/event/{match_id}",
            f"/api/tennis/match/{match_id}",
            f"/api/tennis/matches/{match_id}",
            f"/api/tennis/event/{match_id}/details",
            f"/api/tennis/match/{match_id}/details",
        ]

        return self._try_paths(paths)

    # ---------------------------------------------------------------------
    # Live
    # ---------------------------------------------------------------------

    def get_live_matches(self) -> List[Dict[str, Any]]:
        paths = [
            "/api/tennis/matches/live",
            "/api/tennis/events/live",
            "/api/tennis/live",
        ]

        data = self._try_paths(paths)

        if isinstance(data.get("events"), list):
            return data["events"]

        if isinstance(data.get("matches"), list):
            return data["matches"]

        if isinstance(data.get("event"), dict):
            return [data["event"]]

        return []

    # ---------------------------------------------------------------------
    # Odds
    # ---------------------------------------------------------------------

    def get_match_winning_odds(
        self,
        match_id: int,
        provider_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        provider_id = provider_id or int(os.getenv("TENNISAPI_PROVIDER_ID", "1"))

        paths = [
            f"/api/tennis/match/{match_id}/winning-odds/{provider_id}",
            f"/api/tennis/event/{match_id}/winning-odds/{provider_id}",
            f"/api/tennis/match/{match_id}/odds/{provider_id}",
            f"/api/tennis/event/{match_id}/odds/{provider_id}",
            f"/api/tennis/match/{match_id}/winningOdds/{provider_id}",
        ]

        try:
            return self._try_paths(paths)
        except Exception as exc:
            logger.warning("TennisApi winning odds failed. match_id=%s error=%s", match_id, exc)
            return None

    def get_all_odds_for_event(self, match_id: int) -> Optional[Dict[str, Any]]:
        paths = [
            f"/api/tennis/event/{match_id}/odds",
            f"/api/tennis/match/{match_id}/odds",
            f"/api/tennis/event/{match_id}/all-odds",
            f"/api/tennis/match/{match_id}/all-odds",
            f"/api/tennis/event/{match_id}/allOdds",
            f"/api/tennis/match/{match_id}/allOdds",
        ]

        try:
            return self._try_paths(paths)
        except Exception as exc:
            logger.warning("TennisApi all odds failed. match_id=%s error=%s", match_id, exc)
            return None


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur = data

    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)

    return cur if cur is not None else default


def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for event in events:
        event_id = event.get("id")
        if event_id is None:
            result.append(event)
            continue

        if event_id in seen:
            continue

        seen.add(event_id)
        result.append(event)

    return result


def fractional_to_decimal(value: Optional[str]) -> Optional"""
    "73/100" -> 1.73
    "11/10"  -> 2.10
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()

    try:
        if "/" in value:
            left, right = value.split("/", 1)
            numerator = float(left)
            denominator = float(right)
            if denominator == 0:
                return None
            return round(1.0 + numerator / denominator, 4)

        return round(float(value), 4)

    except Exception:
        return None


def unix_to_iso(timestamp: Optional[int]) -> Optionalif not timestamp:
        return None

    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except Exception:
        return None


def normalize_status(status: Any) -> str:
    if not isinstance(status, dict):
        return "UNKNOWN"

    status_type = str(status.get("type", "")).lower().strip()
    description = str(status.get("description", "")).lower().strip()
    code = status.get("code")

    if status_type in {"finished", "ended"} or description in {"ended", "finished"} or code == 100:
        return "FINISHED"

    if status_type in {"inprogress", "in_progress", "live"}:
        return "LIVE"

    if status_type in {"notstarted", "not_started", "scheduled"}:
        return "NOT_STARTED"

    if status_type in {"cancelled", "canceled"}:
        return "CANCELLED"

    if status_type in {"postponed"}:
        return "POSTPONED"

    if status_type in {"retired"}:
        return "RETIRED"

    if status_type in {"walkover"}:
        return "WALKOVER"

    return status_type.upper() if status_type else "UNKNOWN"


def extract_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    getTennisMatchDetails vracia podľa screenshotu:
    {
        "event": {...}
    }

    Ale fixtures endpoint vracia priamo event objekt.
    """
    if isinstance(payload, dict) and isinstance(payload.get("event"), dict):
        return payload["event"]

    return payload if isinstance(payload, dict) else {}


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event = extract_event(event)

    home_team = event.get("homeTeam") or {}
    away_team = event.get("awayTeam") or {}
    tournament = event.get("tournament") or {}
    unique_tournament = tournament.get("uniqueTournament") or event.get("uniqueTournament") or {}
    category = tournament.get("category") or event.get("category") or {}
    status = event.get("status") or {}

    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}

    winner_code = event.get("winnerCode")
    winner_name = None

    if winner_code == 1:
        winner_name = home_team.get("name")
    elif winner_code == 2:
        winner_name = away_team.get("name")

    return {
        "source": "TennisApi",
        "match_id": event.get("id"),
        "custom_id": event.get("customId"),
        "slug": event.get("slug"),

        "player1": home_team.get("name"),
        "player2": away_team.get("name"),
        "home_team_id": home_team.get("id"),
        "away_team_id": away_team.get("id"),
        "home_seed": event.get("homeTeamSeed"),
        "away_seed": event.get("awayTeamSeed"),

        "tournament": unique_tournament.get("name") or tournament.get("name"),
        "tournament_slug": unique_tournament.get("slug") or tournament.get("slug"),
        "category": category.get("name"),
        "category_id": category.get("id"),

        "round": safe_get(event, "roundInfo", "name"),
        "round_number": safe_get(event, "roundInfo", "round"),

        "start_timestamp": event.get("startTimestamp"),
        "start_time_utc": unix_to_iso(event.get("startTimestamp")),

        "status_raw": status,
        "status": normalize_status(status),

        "winner_code": winner_code,
        "winner": winner_name,

        "home_score_current": home_score.get("current"),
        "away_score_current": away_score.get("current"),
        "home_score_period1": home_score.get("period1"),
        "away_score_period1": away_score.get("period1"),
        "home_score_period2": home_score.get("period2"),
        "away_score_period2": away_score.get("period2"),
        "home_score_period3": home_score.get("period3"),
        "away_score_period3": away_score.get("period3"),
        "home_score_period4": home_score.get("period4"),
        "away_score_period4": away_score.get("period4"),
        "home_score_period5": home_score.get("period5"),
        "away_score_period5": away_score.get("period5"),

        "raw": event,
    }


def normalize_winning_odds(odds_payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(odds_payload, dict):
        return None

    home = odds_payload.get("home") or {}
    away = odds_payload.get("away") or {}

    if not home or not away:
        return None

    home_fractional = home.get("fractionalValue")
    away_fractional = away.get("fractionalValue")

    home_decimal = fractional_to_decimal(home_fractional)
    away_decimal = fractional_to_decimal(away_fractional)

    if home_decimal is None or away_decimal is None:
        return None

    return {
        "source": "TennisApi",
        "home_odds": home_decimal,
        "away_odds": away_decimal,
        "p1_odds": home_decimal,
        "p2_odds": away_decimal,

        "home_fractional": home_fractional,
        "away_fractional": away_fractional,

        "home_expected": home.get("expected"),
        "away_expected": away.get("expected"),
        "home_actual": home.get("actual"),
        "away_actual": away.get("actual"),

        "home_odds_id": home.get("id"),
        "away_odds_id": away.get("id"),

        "raw": odds_payload,
    }
