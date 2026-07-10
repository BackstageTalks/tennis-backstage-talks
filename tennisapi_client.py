
import json
import logging
import os
import time
import http.client
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TennisApiError(Exception):
    """Generic TennisApi / RapidAPI client error."""


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for event in events:
        event_id = event.get("id") or event.get("event_id") or event.get("match_id")
        key = str(event_id or json.dumps(event, sort_keys=True, default=str))
        if key in seen:
            continue
        seen.add(key)
        result.append(event)
    return result


def fractional_to_decimal(value: Optional[str]) -> Optional[float]:
    """Convert fractional odds to decimal odds. Example: 73/100 -> 1.73."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "/" not in text:
        try:
            return float(text)
        except Exception:
            return None
    try:
        numerator, denominator = text.split("/", 1)
        denominator_f = float(denominator)
        if denominator_f == 0:
            return None
        return 1.0 + float(numerator) / denominator_f
    except Exception:
        return None


def unix_to_iso(timestamp: Optional[int]) -> Optional[str]:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except Exception:
        return None


def normalize_status(status: Any) -> str:
    if isinstance(status, dict):
        for key in ("description", "type", "status", "code", "name"):
            value = status.get(key)
            if value:
                return str(value).upper().strip()
    return str(status or "UNKNOWN").upper().strip()


def extract_event(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("event"), dict):
        return payload["event"]
    return payload if isinstance(payload, dict) else {}


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event = extract_event(event)
    home = event.get("homeTeam") or event.get("home") or event.get("homePlayer") or {}
    away = event.get("awayTeam") or event.get("away") or event.get("awayPlayer") or {}

    if isinstance(home, dict):
        player1 = home.get("name") or home.get("shortName") or home.get("slug")
    else:
        player1 = str(home) if home else None

    if isinstance(away, dict):
        player2 = away.get("name") or away.get("shortName") or away.get("slug")
    else:
        player2 = str(away) if away else None

    event_id = event.get("id") or event.get("eventId") or event.get("matchId")
    start_ts = event.get("startTimestamp") or event.get("startTime") or event.get("time")

    return {
        "id": event_id,
        "event_id": event_id,
        "match_id": event_id,
        "player1": player1,
        "player2": player2,
        "homeTeam": player1,
        "awayTeam": player2,
        "startTimestamp": start_ts,
        "match_start": unix_to_iso(start_ts) if isinstance(start_ts, (int, float, str)) and str(start_ts).isdigit() else event.get("match_start"),
        "status": event.get("status"),
        "status_text": normalize_status(event.get("status")),
        "tournament": safe_get(event, "tournament", "name") or safe_get(event, "season", "name"),
        "category": safe_get(event, "category", "name") or safe_get(event, "tournament", "category", "name"),
        "raw": event,
    }


def _choice_decimal(choice: Dict[str, Any]) -> Optional[float]:
    for key in ("decimalValue", "decimal", "value", "odds", "price"):
        if choice.get(key) is not None:
            try:
                return float(choice.get(key))
            except Exception:
                pass
    for key in ("fractionalValue", "fractional"):
        dec = fractional_to_decimal(choice.get(key))
        if dec is not None:
            return dec
    return None


def normalize_winning_odds(odds_payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalize common TennisApi winner odds payload shapes to player1/player2 prices."""
    if not isinstance(odds_payload, dict):
        return None

    # Direct AllSports-like shape.
    home = odds_payload.get("home")
    away = odds_payload.get("away")
    if isinstance(home, dict) and isinstance(away, dict):
        p1 = _choice_decimal(home)
        p2 = _choice_decimal(away)
        if p1 and p2:
            return {
                "odds_player1": round(p1, 3),
                "odds_player2": round(p2, 3),
                "p1_odds": round(p1, 3),
                "p2_odds": round(p2, 3),
                "home_odds": round(p1, 3),
                "away_odds": round(p2, 3),
                "bookmaker": odds_payload.get("bookmaker") or odds_payload.get("provider") or "TennisApi",
                "raw": odds_payload,
            }

    # Market/choices shape.
    containers: List[Any] = []
    for key in ("markets", "odds", "data", "result"):
        value = odds_payload.get(key)
        if value is not None:
            containers.append(value)
    containers.append(odds_payload)

    def collect_dicts(value: Any, output: List[Dict[str, Any]]) -> None:
        if isinstance(value, dict):
            output.append(value)
            for nested in value.values():
                collect_dicts(nested, output)
        elif isinstance(value, list):
            for item in value:
                collect_dicts(item, output)

    dicts: List[Dict[str, Any]] = []
    for container in containers:
        collect_dicts(container, dicts)

    for item in dicts:
        choices = item.get("choices") or item.get("outcomes") or item.get("selections")
        if isinstance(choices, list) and len(choices) >= 2:
            p1 = _choice_decimal(choices[0])
            p2 = _choice_decimal(choices[1])
            if p1 and p2:
                return {
                    "odds_player1": round(p1, 3),
                    "odds_player2": round(p2, 3),
                    "p1_odds": round(p1, 3),
                    "p2_odds": round(p2, 3),
                    "home_odds": round(p1, 3),
                    "away_odds": round(p2, 3),
                    "bookmaker": item.get("bookmaker") or item.get("provider") or item.get("providerName") or "TennisApi",
                    "raw": odds_payload,
                }

    return None


class TennisApiClient:
    """Thin RapidAPI client used by the project.

    The primary host is configurable because the project uses multiple RapidAPI
    tennis products. Defaults are intentionally environment-driven.
    """

    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY") or os.getenv("TENNISAPI_RAPIDAPI_KEY")
        self.host = host or os.getenv("TENNISAPI_RAPIDAPI_HOST") or os.getenv("RAPIDAPI_HOST") or "tennisapi1.p.rapidapi.com"
        self.base_url = (base_url or os.getenv("TENNISAPI_BASE_URL") or f"https://{self.host}").rstrip("/")
        self.timeout = int(os.getenv("TENNISAPI_TIMEOUT", "25"))

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise TennisApiError("Missing RAPIDAPI_KEY / TENNISAPI_RAPIDAPI_KEY")
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
            "Content-Type": "application/json",
        }

    def get(self, path: str) -> Any:
        import requests
        url = f"{self.base_url}{path}"
        response = requests.get(url, headers=self._headers(), timeout=self.timeout)
        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            raise TennisApiError(f"HTTP {response.status_code} for {path}: {response.text[:300]}")
        try:
            return response.json()
        except Exception as exc:
            raise TennisApiError(f"Invalid JSON for {path}: {exc}") from exc

    def get_calendar_categories(self, day: int, month: int, year: int) -> Any:
        return self.get(f"/api/tennis/calendar/{day}/{month}/{year}/categories")

    def get_category_events(self, category_id: Any, day: int, month: int, year: int) -> Any:
        return self.get(f"/api/tennis/category/{category_id}/events/{day}/{month}/{year}")

    def get_event_odds(self, event_id: Any) -> Any:
        return self.get(f"/api/tennis/event/{event_id}/odds")

    def get_match_winning_odds(self, match_id: Any, provider_id: Optional[int] = None) -> Any:
        if provider_id is not None:
            # Common REcodeX/TennisApi-like endpoint.
            try:
                return self.get(f"/api/tennis/event/{match_id}/provider/{provider_id}/winning-odds")
            except Exception:
                pass
        return self.get_event_odds(match_id)

    def get_events_for_date(self, day: int, month: int, year: int) -> List[Dict[str, Any]]:
        categories_payload = self.get_calendar_categories(day, month, year)
        categories = _extract_list(categories_payload, ("categories", "data", "result"))
        events: List[Dict[str, Any]] = []
        for category in categories:
            if not isinstance(category, dict):
                continue
            category_id = category.get("id") or category.get("categoryId") or category.get("cid")
            if not category_id:
                continue
            payload = self.get_category_events(category_id, day, month, year)
            raw_events = _extract_list(payload, ("events", "data", "result"))
            for raw in raw_events:
                if isinstance(raw, dict):
                    item = normalize_event(raw)
                    item["tennisapi_category_id"] = category_id
                    item["tennisapi_category_name"] = category.get("name") or category.get("categoryName")
                    events.append(item)
        return deduplicate_events(events)


def _extract_list(payload: Any, keys: tuple) -> List[Any]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _extract_list(value, keys)
                if nested:
                    return nested
        if all(isinstance(value, dict) for value in payload.values()):
            return list(payload.values())
    return []
