from __future__ import annotations

import json
import os
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

import requests

TENNISAPI_HOST = "tennisapi1.p.rapidapi.com"
TENNISAPI_BASE_URL = "https://tennisapi1.p.rapidapi.com"
CACHE_DIR = Path("data/marq_ai")
CACHE_TTL_SECONDS = 60 * 60 * 12

# TennisApi provider ids verified from the provider list in RapidAPI Playground.
# Keep it moderate for a smooth run. We can extend later.
DEFAULT_PROVIDER_IDS = [1]

_RUN_EVENTS_ODDS_CACHE: Dict[str, Dict[str, Any]] = {}
_RUN_DETAILS_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
_RUN_PROVIDER_ODDS_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
_RUN_FAILED_DATES: set[str] = set()
_RATE_LIMITED = False


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
    global _RATE_LIMITED

    if _RATE_LIMITED:
        _debug(f"skip request because rate_limit flag active path={path}")
        return None

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
        status = response.status_code
        content_type = response.headers.get("content-type", "")
        text_preview = (response.text or "")[:350].replace("\n", " ")
        _debug(f"http status={status} path={path} content_type={content_type} body_preview={text_preview}")

        if status == 204:
            return None
        if status == 429:
            _RATE_LIMITED = True
            _debug(f"rate limited path={path}")
            return None
        if status >= 400:
            return None
        if not response.text or not response.text.strip():
            return None

        try:
            data = response.json()
        except Exception as exc:
            _debug(f"json parse failed path={path} error={exc} body_preview={text_preview}")
            return None

        if cache_file:
            _write_cache(cache_file, data)
        return data

    except Exception as exc:
        _debug(f"request failed path={path} error={exc}")
        return None


def _parse_date(date_only: str) -> Tuple[int, int, int]:
    dt = datetime.strptime(str(date_only)[:10], "%Y-%m-%d").date()
    return dt.day, dt.month, dt.year


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
    score = len(ta & tb) / len(ta | tb)
    if ta and tb:
        # Surname-only / abbreviated-name support. Token order is not reliable after set(),
        # so this just gives a small boost when any last-looking token overlaps.
        ta_sorted = sorted(ta)
        tb_sorted = sorted(tb)
        if ta_sorted[-1] in tb or tb_sorted[-1] in ta:
            score = max(score, 0.60)
    return score


def _team_name(team: Any) -> str:
    if isinstance(team, dict):
        for key in ("name", "shortName", "fullName", "displayName", "slug"):
            value = team.get(key)
            if value:
                return str(value)
    return str(team or "")


def _extract_event(payload: Any) -> Optional[Dict[str, Any]]:
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


def _event_home_away(event: Dict[str, Any]) -> Tuple[str, str]:
    home = _team_name(event.get("homeTeam") or event.get("home") or event.get("participant1"))
    away = _team_name(event.get("awayTeam") or event.get("away") or event.get("participant2"))
    return home, away


def _fractional_to_decimal(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 1 else None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            numerator = float(left.strip())
            denominator = float(right.strip())
            if denominator == 0:
                return None
            return round(1.0 + numerator / denominator, 5)
        except Exception:
            return None
    try:
        number = float(text)
        return number if number > 1 else None
    except Exception:
        return None


def _extract_markets(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        markets = payload.get("markets")
        if isinstance(markets, list):
            return [m for m in markets if isinstance(m, dict)]
        odds = payload.get("odds")
        if isinstance(odds, list):
            return [m for m in odds if isinstance(m, dict)]
        data = payload.get("data")
        if isinstance(data, dict):
            markets = data.get("markets")
            if isinstance(markets, list):
                return [m for m in markets if isinstance(m, dict)]
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict)]
    if isinstance(payload, list):
        return [m for m in payload if isinstance(m, dict)]
    return []


def _select_full_time_market(markets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        market_group = str(market.get("marketGroup") or "").strip().lower()
        market_period = str(market.get("marketPeriod") or "").strip().lower()
        if market_name == "full time" and ("home" in market_group or market_group == "home/away") and market_period in ("match", ""):
            return market
    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        if market_name in ("full time", "match winner", "winner", "to win"):
            return market
    return None


def _choice_side(choice: Dict[str, Any]) -> Optional[str]:
    name = str(choice.get("name") or choice.get("choice") or choice.get("label") or "").strip()
    lowered = name.lower()

    if name in ("1", "2"):
        return name
    if lowered in ("home", "player1", "player 1", "team1", "team 1"):
        return "1"
    if lowered in ("away", "player2", "player 2", "team2", "team 2"):
        return "2"
    return None


def _choice_current_decimal(choice: Dict[str, Any]) -> Optional[float]:
    return _fractional_to_decimal(
        choice.get("fractionalValue")
        or choice.get("decimalValue")
        or choice.get("value")
        or choice.get("odds")
        or choice.get("price")
    )


def _choice_initial_decimal(choice: Dict[str, Any]) -> Optional[float]:
    return _fractional_to_decimal(
        choice.get("initialFractionalValue")
        or choice.get("initialDecimalValue")
        or choice.get("openingFractionalValue")
        or choice.get("openingDecimalValue")
    )


def _safe_numeric(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _extract_choice_markets(market: Dict[str, Any]) -> Dict[str, Any]:
    choices = market.get("choices") or market.get("outcomes") or []
    output: Dict[str, Any] = {
        "odds_1": None,
        "odds_2": None,
        "initial_1": None,
        "initial_2": None,
        "change_1": None,
        "change_2": None,
        "choice_source_id_1": None,
        "choice_source_id_2": None,
    }

    if not isinstance(choices, list):
        return output

    for choice in choices:
        if not isinstance(choice, dict):
            continue

        side = _choice_side(choice)
        if side not in ("1", "2"):
            continue

        current = _choice_current_decimal(choice)
        initial = _choice_initial_decimal(choice)
        change = _safe_numeric(choice.get("change"))
        source_id = choice.get("sourceId")

        if side == "1":
            output["odds_1"] = current
            output["initial_1"] = initial
            output["change_1"] = change
            output["choice_source_id_1"] = source_id
        else:
            output["odds_2"] = current
            output["initial_2"] = initial
            output["change_2"] = change
            output["choice_source_id_2"] = source_id

    return output


def _extract_choice_odds(market: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    extracted = _extract_choice_markets(market)
    return extracted.get("odds_1"), extracted.get("odds_2")


def fetch_events_odds_by_date(date_only: str, force_refresh: bool = False) -> Dict[str, Any]:
    if date_only in _RUN_EVENTS_ODDS_CACHE and not force_refresh:
        return _RUN_EVENTS_ODDS_CACHE[date_only]
    if date_only in _RUN_FAILED_DATES and not force_refresh:
        return {}

    day, month, year = _parse_date(date_only)
    path = f"/api/tennis/events/odds/{day}/{month}/{year}"
    cache_name = f"tennisapi_events_odds_{year:04d}_{month:02d}_{day:02d}.json"
    payload = _get_json(path, cache_name=cache_name, force_refresh=force_refresh)

    result: Dict[str, Any] = {}
    if isinstance(payload, dict):
        odds = payload.get("odds")
        if isinstance(odds, dict):
            result = odds
        elif isinstance(odds, list):
            for item in odds:
                if isinstance(item, dict):
                    event_id = item.get("id") or item.get("eventId") or item.get("event_id")
                    if event_id:
                        result[str(event_id)] = item
        elif isinstance(payload.get("results"), dict):
            result = payload["results"]

    if not result:
        _RUN_FAILED_DATES.add(date_only)

    _RUN_EVENTS_ODDS_CACHE[date_only] = result
    _debug(f"events odds date={date_only} count={len(result)}")
    return result


def fetch_match_details(event_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    if event_id in _RUN_DETAILS_CACHE and not force_refresh:
        return _RUN_DETAILS_CACHE[event_id]

    # Confirmed by RapidAPI snippet: /api/tennis/event/{id}
    path = f"/api/tennis/event/{event_id}"
    cache_name = f"tennisapi_match_details_{event_id}.json"
    payload = _get_json(path, cache_name=cache_name, force_refresh=force_refresh)
    event = _extract_event(payload)

    if event:
        _RUN_DETAILS_CACHE[event_id] = event
        home, away = _event_home_away(event)
        _debug(f"match details ok event_id={event_id} path={path} home={home} away={away}")
        return event

    _RUN_DETAILS_CACHE[event_id] = None
    _debug(f"match details missing event_id={event_id}")
    return None


def find_tennisapi_event_for_match(player1: str, player2: str, date_only: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    odds_by_event = fetch_events_odds_by_date(date_only, force_refresh=force_refresh)
    if not odds_by_event:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    # Limit detail lookups to keep workflow smooth.
    for event_id in list(odds_by_event.keys())[:250]:
        event = fetch_match_details(str(event_id), force_refresh=force_refresh)
        if not event:
            continue
        home, away = _event_home_away(event)
        if not home or not away:
            continue

        direct = (_name_score(player1, home) + _name_score(player2, away)) / 2.0
        reverse = (_name_score(player1, away) + _name_score(player2, home)) / 2.0
        score = max(direct, reverse)

        if score > best_score:
            best_score = score
            best = {
                "event_id": str(event_id),
                "event": event,
                "home_name": home,
                "away_name": away,
                "match_direction": "direct" if direct >= reverse else "reverse",
                "match_score": round(score, 4),
                "bulk_odds": odds_by_event.get(str(event_id)),
            }

        if best_score >= 0.98:
            break

    if not best or best_score < 0.58:
        _debug(f"event not matched from odds feed player1={player1} player2={player2} date={date_only} best_score={best_score:.3f}")
        return None

    _debug(
        "event matched from odds feed "
        f"player1={player1} player2={player2} event_id={best['event_id']} "
        f"home={best['home_name']} away={best['away_name']} direction={best['match_direction']} score={best['match_score']}"
    )
    return best


def fetch_provider_odds(event_id: str, provider_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    key = f"{event_id}:{provider_id}"
    if key in _RUN_PROVIDER_ODDS_CACHE and not force_refresh:
        return _RUN_PROVIDER_ODDS_CACHE[key]

    # Main PRO market endpoint. It gives Full time, First set winner, Total games,
    # Tie break in match, plus initialFractionalValue/fractionalValue/change.
    candidates = [
        f"/api/tennis/event/{event_id}/odds/{provider_id}/all",
        # Fallbacks. Winning odds is useful only for Crowd, not for Move.
        f"/api/tennis/event/{event_id}/odds",
        f"/api/tennis/event/{event_id}/provider/{provider_id}/winning-odds",
        f"/api/tennis/event/{event_id}/provider/{provider_id}/odds",
    ]

    best_payload: Optional[Dict[str, Any]] = None
    best_market_count = 0

    for idx, path in enumerate(candidates):
        cache_name = f"tennisapi_provider_odds_{event_id}_{provider_id}_{idx}.json"
        payload = _get_json(path, cache_name=cache_name, force_refresh=force_refresh)
        markets = _extract_markets(payload)
        if markets:
            market_count = len(markets)
            if market_count > best_market_count:
                best_payload = payload
                best_market_count = market_count
            _debug(
                f"provider odds candidate ok event_id={event_id} "
                f"provider_id={provider_id} path={path} markets={len(markets)}"
            )
            # First candidate is the richest endpoint in current tests, use it immediately.
            if idx == 0:
                _RUN_PROVIDER_ODDS_CACHE[key] = payload
                return payload

    if best_payload is not None:
        _RUN_PROVIDER_ODDS_CACHE[key] = best_payload
        return best_payload

    _RUN_PROVIDER_ODDS_CACHE[key] = None
    _debug(f"provider odds missing event_id={event_id} provider_id={provider_id}")
    return None


def _quote_from_payload(payload: Any, event_id: str, provider_id: Optional[int], provider_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    markets = _extract_markets(payload)
    market = _select_full_time_market(markets)
    if not market:
        return None

    extracted = _extract_choice_markets(market)
    odds_1 = extracted.get("odds_1")
    odds_2 = extracted.get("odds_2")
    if odds_1 is None or odds_2 is None:
        return None

    initial_1 = extracted.get("initial_1")
    initial_2 = extracted.get("initial_2")

    return {
        "event_id": str(event_id),
        "provider_id": provider_id,
        "provider_name": provider_name or (f"provider_{provider_id}" if provider_id is not None else "bulk"),
        "source": "TennisApiPRO",
        "bookmaker": provider_name or (f"provider_{provider_id}" if provider_id is not None else "bulk"),
        "market_name": market.get("marketName") or market.get("name") or "Full time",
        "market_group": market.get("marketGroup"),
        "market_period": market.get("marketPeriod"),
        "market_id": market.get("marketId"),
        "source_id": market.get("sourceId"),
        "odds_1": odds_1,
        "odds_2": odds_2,
        "initial_1": initial_1,
        "initial_2": initial_2,
        "opening_1": initial_1,
        "opening_2": initial_2,
        "change_1": extracted.get("change_1"),
        "change_2": extracted.get("change_2"),
        "choice_source_id_1": extracted.get("choice_source_id_1"),
        "choice_source_id_2": extracted.get("choice_source_id_2"),
    }


def collect_market_quotes(event_id: str, bulk_odds: Any = None, provider_ids: Optional[List[int]] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    provider_ids = provider_ids or DEFAULT_PROVIDER_IDS
    quotes: List[Dict[str, Any]] = []

    bulk_quote = _quote_from_payload(bulk_odds, event_id=event_id, provider_id=None, provider_name="bulk")
    if bulk_quote:
        quotes.append(bulk_quote)

    for provider_id in provider_ids:
        payload = fetch_provider_odds(event_id, provider_id, force_refresh=force_refresh)
        quote = _quote_from_payload(payload, event_id=event_id, provider_id=provider_id)
        if quote:
            signature = (round(quote["odds_1"], 4), round(quote["odds_2"], 4), quote.get("provider_id"))
            existing = {
                (round(q["odds_1"], 4), round(q["odds_2"], 4), q.get("provider_id"))
                for q in quotes
            }
            if signature not in existing:
                quotes.append(quote)

    _debug(f"market quotes event_id={event_id} count={len(quotes)}")
    return quotes


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


def _fallback_existing_odds(player1: str, player2: str, pick: Optional[str], odds_player1: Optional[float], odds_player2: Optional[float]) -> Optional[Dict[str, Any]]:
    try:
        od1 = float(odds_player1) if odds_player1 is not None else None
        od2 = float(odds_player2) if odds_player2 is not None else None
    except Exception:
        return None

    if od1 is None or od2 is None or od1 <= 1 or od2 <= 1:
        return None

    return {
        "source": "fallback_existing_odds_thin_market",
        "event_id": None,
        "player1": player1,
        "player2": player2,
        "home_name": player1,
        "away_name": player2,
        "match_direction": "direct",
        "pick_outcome_key": _resolve_pick_outcome_key(player1, player2, pick),
        "market_quotes": [
            {
                "event_id": None,
                "provider_id": None,
                "provider_name": "existing_odds",
                "market_name": "match_winner",
                "odds_1": od1,
                "odds_2": od2,
                "initial_1": od1,
                "initial_2": od2,
                "opening_1": od1,
                "opening_2": od2,
                "change_1": 0,
                "change_2": 0,
            }
        ],
        "odds": {
            "od1": {"opening": od1, "latest": od1, "current": od1, "change": 0},
            "od2": {"opening": od2, "latest": od2, "current": od2, "change": 0},
        },
    }


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
    event_match = find_tennisapi_event_for_match(player1, player2, date_only, force_refresh=force_refresh)

    if event_match:
        event_id = str(event_match["event_id"])
        quotes = collect_market_quotes(event_id, bulk_odds=event_match.get("bulk_odds"), force_refresh=force_refresh)
        if quotes:
            if event_match["match_direction"] == "direct":
                od1_quotes = [q["odds_1"] for q in quotes if q.get("odds_1")]
                od2_quotes = [q["odds_2"] for q in quotes if q.get("odds_2")]
            else:
                od1_quotes = [q["odds_2"] for q in quotes if q.get("odds_2")]
                od2_quotes = [q["odds_1"] for q in quotes if q.get("odds_1")]

            od1 = float(median(od1_quotes)) if od1_quotes else None
            od2 = float(median(od2_quotes)) if od2_quotes else None

            if event_match["match_direction"] == "direct":
                initial1_quotes = [q.get("initial_1") for q in quotes if q.get("initial_1")]
                initial2_quotes = [q.get("initial_2") for q in quotes if q.get("initial_2")]
                change1_quotes = [q.get("change_1") for q in quotes if q.get("change_1") is not None]
                change2_quotes = [q.get("change_2") for q in quotes if q.get("change_2") is not None]
            else:
                initial1_quotes = [q.get("initial_2") for q in quotes if q.get("initial_2")]
                initial2_quotes = [q.get("initial_1") for q in quotes if q.get("initial_1")]
                change1_quotes = [q.get("change_2") for q in quotes if q.get("change_2") is not None]
                change2_quotes = [q.get("change_1") for q in quotes if q.get("change_1") is not None]

            initial1 = float(median(initial1_quotes)) if initial1_quotes else od1
            initial2 = float(median(initial2_quotes)) if initial2_quotes else od2
            change1 = float(median(change1_quotes)) if change1_quotes else 0
            change2 = float(median(change2_quotes)) if change2_quotes else 0

            result = {
                "source": "tennisapi_market_quality",
                "event_id": event_id,
                "player1": player1,
                "player2": player2,
                "home_name": event_match["home_name"],
                "away_name": event_match["away_name"],
                "match_direction": event_match["match_direction"],
                "match_score": event_match["match_score"],
                "pick_outcome_key": _resolve_pick_outcome_key(player1, player2, pick),
                "market_quotes": quotes,
                "odds": {
                    "od1": {"opening": initial1, "latest": od1, "current": od1, "change": change1},
                    "od2": {"opening": initial2, "latest": od2, "current": od2, "change": change2},
                },
            }
            _debug(f"market quality data ok event_id={event_id} quotes={len(quotes)} od1={od1} od2={od2}")
            return result

        _debug(f"event matched but no provider quotes event_id={event_id}")

    fallback = _fallback_existing_odds(player1, player2, pick, odds_player1, odds_player2)
    if fallback:
        _debug(f"using fallback thin market player1={player1} player2={player2} odds1={odds_player1} odds2={odds_player2}")
        return fallback

    return None
