from __future__ import annotations

import json
import os
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

TENNISAPI_HOST = "tennisapi1.p.rapidapi.com"
TENNISAPI_BASE_URL = "https://tennisapi1.p.rapidapi.com"
CACHE_DIR = Path("data/marq_ai")
CACHE_TTL_SECONDS = 60 * 60 * 12


def _debug(message: str) -> None:
    print(f"MARQ TENNISAPI DEBUG: {message}")


def _api_key() -> str:
    return os.getenv("RAPIDAPI_KEY", "").strip()


def _headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-rapidapi-host": TENNISAPI_HOST,
        "x-rapidapi-key": _api_key(),
    }


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for ch in [".", ",", "'", "`", "’", "-", "_", "(", ")", "[", "]"]:
        text = text.replace(ch, " ")
    return " ".join(text.split())


def _tokens(value: Any) -> set[str]:
    return set(_normalize_name(value).split())


def _name_score(a: str, b: str) -> float:
    na = _normalize_name(a)
    nb = _normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.92
    ta = _tokens(na)
    tb = _tokens(nb)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    if union == 0:
        return 0.0
    score = inter / union
    # Tennis APIs sometimes use "Surname F.". Reward surname-only matches.
    if list(ta)[-1:] and list(tb)[-1:]:
        if next(reversed(list(ta))) in tb or next(reversed(list(tb))) in ta:
            score = max(score, 0.60)
    return score


def _parse_date(date_only: str) -> Tuple[int, int, int]:
    dt = datetime.strptime(str(date_only)[:10], "%Y-%m-%d").date()
    return dt.day, dt.month, dt.year


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def _read_cache(path: Path, ttl_seconds: int = CACHE_TTL_SECONDS) -> Optional[Any]:
    try:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        saved_at = float(payload.get("saved_at", 0))
        if time.time() - saved_at > ttl_seconds:
            return None
        return payload.get("data")
    except Exception:
        return None


def _write_cache(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"saved_at": time.time(), "data": data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        _debug(f"cache write failed path={path} error={exc}")


def _get_json(path: str, cache_name: Optional[str] = None, force_refresh: bool = False) -> Optional[Any]:
    if not _api_key():
        _debug("RAPIDAPI_KEY missing")
        return None

    cache_file = _cache_path(cache_name) if cache_name else None
    if cache_file and not force_refresh:
        cached = _read_cache(cache_file)
        if cached is not None:
            return cached

    url = f"{TENNISAPI_BASE_URL}{path}"
    try:
        response = requests.get(url, headers=_headers(), timeout=25)
        if response.status_code == 429:
            _debug(f"rate limited path={path}")
            return None
        if response.status_code >= 400:
            _debug(f"http error status={response.status_code} path={path} body={response.text[:250]}")
            return None
        data = response.json()
        if cache_file:
            _write_cache(cache_file, data)
        return data
    except Exception as exc:
        _debug(f"request failed path={path} error={exc}")
        return None


def _extract_events(payload: Any) -> List[Dict[str, Any]]:
    if not payload:
        return []
    if isinstance(payload, dict):
        events = payload.get("events")
        if isinstance(events, list):
            return [event for event in events if isinstance(event, dict)]
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("events"), list):
            return [event for event in data["events"] if isinstance(event, dict)]
        if isinstance(data, list):
            return [event for event in data if isinstance(event, dict)]
    if isinstance(payload, list):
        return [event for event in payload if isinstance(event, dict)]
    return []


def _team_name(team: Any) -> str:
    if isinstance(team, dict):
        for key in ("name", "shortName", "fullName", "displayName", "slug"):
            value = team.get(key)
            if value:
                return str(value)
    return str(team or "")


def _event_home_away(event: Dict[str, Any]) -> Tuple[str, str]:
    home = _team_name(event.get("homeTeam") or event.get("home") or event.get("participant1"))
    away = _team_name(event.get("awayTeam") or event.get("away") or event.get("participant2"))
    return home, away


def _event_id(event: Dict[str, Any]) -> Optional[str]:
    for key in ("id", "eventId", "event_id", "matchId", "match_id"):
        value = event.get(key)
        if value not in (None, "", 0):
            return str(value)
    return None


def fetch_events_by_date(date_only: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
    day, month, year = _parse_date(date_only)
    path = f"/api/tennis/events/{day}/{month}/{year}"
    cache_name = f"tennisapi_events_{year:04d}_{month:02d}_{day:02d}.json"
    payload = _get_json(path, cache_name=cache_name, force_refresh=force_refresh)
    events = _extract_events(payload)
    _debug(f"events date={date_only} count={len(events)}")
    return events


def find_event_for_match(
    player1: str,
    player2: str,
    date_only: str,
    force_refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    events = fetch_events_by_date(date_only, force_refresh=force_refresh)
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for event in events:
        home, away = _event_home_away(event)
        if not home or not away:
            continue

        direct = (_name_score(player1, home) + _name_score(player2, away)) / 2.0
        reverse = (_name_score(player1, away) + _name_score(player2, home)) / 2.0
        score = max(direct, reverse)

        if score > best_score:
            best_score = score
            best = {
                "event": event,
                "event_id": _event_id(event),
                "home_name": home,
                "away_name": away,
                "match_direction": "direct" if direct >= reverse else "reverse",
                "match_score": round(score, 4),
            }

    if not best or not best.get("event_id") or best_score < 0.58:
        _debug(f"event not matched player1={player1} player2={player2} date={date_only} best_score={best_score:.3f}")
        return None

    _debug(
        "event matched "
        f"player1={player1} player2={player2} event_id={best['event_id']} "
        f"home={best['home_name']} away={best['away_name']} direction={best['match_direction']} score={best['match_score']}"
    )
    return best


def _fractional_to_decimal(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        decimal = float(value)
        return decimal if decimal > 1 else None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", ".")
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            numerator = float(left.strip())
            denominator = float(right.strip())
            if denominator == 0:
                return None
            return round(1.0 + numerator / denominator, 4)
        except Exception:
            return None
    try:
        decimal = float(text)
        return decimal if decimal > 1 else None
    except Exception:
        return None


def fetch_event_odds(event_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    path = f"/api/tennis/event/{event_id}/odds"
    cache_name = f"tennisapi_odds_{event_id}.json"
    return _get_json(path, cache_name=cache_name, force_refresh=force_refresh)


def fetch_winning_odds(event_id: str, provider_id: int = 1, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    path = f"/api/tennis/event/{event_id}/provider/{provider_id}/winning-odds"
    cache_name = f"tennisapi_winning_odds_{event_id}_{provider_id}.json"
    return _get_json(path, cache_name=cache_name, force_refresh=force_refresh)


def _extract_markets(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        markets = payload.get("markets")
        if isinstance(markets, list):
            return [market for market in markets if isinstance(market, dict)]
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("markets"), list):
            return [market for market in data["markets"] if isinstance(market, dict)]
        if isinstance(data, list):
            return [market for market in data if isinstance(market, dict)]
    if isinstance(payload, list):
        return [market for market in payload if isinstance(market, dict)]
    return []


def _select_full_time_market(markets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for market in markets:
        name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        group = str(market.get("marketGroup") or "").strip().lower()
        period = str(market.get("marketPeriod") or "").strip().lower()
        if name == "full time" and ("home" in group or group == "home/away") and period in ("match", ""):
            return market
    for market in markets:
        name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        if name in ("full time", "match winner", "winner", "to win"):
            return market
    return markets[0] if markets else None


def _extract_choices(market: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    choices = market.get("choices") or market.get("outcomes") or []
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(choices, list):
        return result
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        name = str(choice.get("name") or choice.get("choice") or choice.get("label") or "").strip()
        if name not in ("1", "2"):
            lowered = name.lower()
            if lowered in ("home", "player1", "team1"):
                name = "1"
            elif lowered in ("away", "player2", "team2"):
                name = "2"
        if name in ("1", "2"):
            current = _fractional_to_decimal(
                choice.get("fractionalValue")
                or choice.get("decimalValue")
                or choice.get("value")
                or choice.get("odds")
            )
            initial = _fractional_to_decimal(
                choice.get("initialFractionalValue")
                or choice.get("initialDecimalValue")
                or choice.get("initialValue")
                or choice.get("openingOdds")
            )
            result[name] = {
                "current": current,
                "opening": initial or current,
                "raw": choice,
                "change": choice.get("change"),
            }
    return result


def parse_event_odds(payload: Any) -> Optional[Dict[str, Any]]:
    markets = _extract_markets(payload)
    market = _select_full_time_market(markets)
    if not market:
        return None
    choices = _extract_choices(market)
    if "1" not in choices or "2" not in choices:
        return None
    return {
        "market_name": market.get("marketName") or market.get("name"),
        "market_group": market.get("marketGroup"),
        "market_period": market.get("marketPeriod"),
        "choices": choices,
    }


def _resolve_pick_outcome_key(player1: str, player2: str, pick: Optional[str]) -> str:
    if not pick:
        return "od1"
    p1 = _normalize_name(player1)
    p2 = _normalize_name(player2)
    pk = _normalize_name(pick)
    if pk == p1 or pk in p1 or p1 in pk or (_tokens(pk) & _tokens(p1)):
        return "od1"
    if pk == p2 or pk in p2 or p2 in pk or (_tokens(pk) & _tokens(p2)):
        return "od2"
    return "od1"


def fetch_marq_market_data(
    player1: str,
    player2: str,
    date_only: str,
    pick: Optional[str] = None,
    odds_player1: Optional[float] = None,
    odds_player2: Optional[float] = None,
    force_refresh: bool = False,
    **_: Any,
) -> Optional[Dict[str, Any]]:
    """
    Main Marq datasource provider.

    Primary source: TennisApi on RapidAPI
    - GET /api/tennis/events/{day}/{month}/{year}
    - GET /api/tennis/event/{event_id}/odds

    Fallback: already known odds_player1 / odds_player2, if supplied by caller.
    """

    event_match = find_event_for_match(player1, player2, date_only, force_refresh=force_refresh)
    if not event_match:
        if odds_player1 and odds_player2:
            return {
                "source": "fallback_existing_odds",
                "event_id": None,
                "player1": player1,
                "player2": player2,
                "home_name": player1,
                "away_name": player2,
                "match_direction": "direct",
                "pick_outcome_key": _resolve_pick_outcome_key(player1, player2, pick),
                "odds": {
                    "od1": {"opening": float(odds_player1), "latest": float(odds_player1), "current": float(odds_player1)},
                    "od2": {"opening": float(odds_player2), "latest": float(odds_player2), "current": float(odds_player2)},
                },
                "raw": None,
            }
        return None

    event_id = str(event_match["event_id"])
    raw_odds = fetch_event_odds(event_id, force_refresh=force_refresh)
    parsed = parse_event_odds(raw_odds)

    if not parsed:
        _debug(f"odds missing or unparsable event_id={event_id}")
        return None

    # API choice 1=home, 2=away. Convert to project od1/od2 = original player1/player2.
    if event_match["match_direction"] == "direct":
        choice_for_od1 = "1"
        choice_for_od2 = "2"
    else:
        choice_for_od1 = "2"
        choice_for_od2 = "1"

    c1 = parsed["choices"].get(choice_for_od1, {})
    c2 = parsed["choices"].get(choice_for_od2, {})

    result = {
        "source": "tennisapi1",
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "home_name": event_match["home_name"],
        "away_name": event_match["away_name"],
        "match_direction": event_match["match_direction"],
        "match_score": event_match["match_score"],
        "pick_outcome_key": _resolve_pick_outcome_key(player1, player2, pick),
        "market_name": parsed.get("market_name"),
        "market_group": parsed.get("market_group"),
        "market_period": parsed.get("market_period"),
        "odds": {
            "od1": {
                "opening": c1.get("opening"),
                "latest": c1.get("current"),
                "current": c1.get("current"),
                "change": c1.get("change"),
            },
            "od2": {
                "opening": c2.get("opening"),
                "latest": c2.get("current"),
                "current": c2.get("current"),
                "change": c2.get("change"),
            },
        },
        "raw": raw_odds,
    }

    _debug(
        "market data ok "
        f"event_id={event_id} source=tennisapi1 pick={pick} outcome={result['pick_outcome_key']} "
        f"od1={result['odds']['od1']} od2={result['odds']['od2']}"
    )
    return result
