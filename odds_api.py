import os
import json
import requests
import unicodedata
from difflib import SequenceMatcher


BASE_URL = "https://api.the-odds-api.com/v4"

ODDS_DEBUG_PATH = "public/odds_debug.json"

DEFAULT_REGIONS = "eu"
DEFAULT_MARKETS = "h2h"
DEFAULT_ODDS_FORMAT = "decimal"


_DEBUG = {
    "provider": "The Odds API",
    "secret_name": "ODDS_API_KEY",
    "strategy": None,

    "sports_found": 0,
    "tennis_sport_keys": [],

    "events_from_api": 0,
    "fetch_error": None,

    "matched": 0,
    "unmatched": 0,
    "odds_found": 0,
    "odds_missing": 0,

    "sample_events": [],
    "examples_matched": [],
    "examples_unmatched": [],
}


def write_debug():
    os.makedirs("public", exist_ok=True)

    with open(
        ODDS_DEBUG_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            _DEBUG,
            file,
            indent=2,
            ensure_ascii=False,
        )


def normalize(name):
    if not name:
        return ""

    value = str(name)

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()
    value = value.replace("-", " ")
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = value.replace("'", "")
    value = value.replace("’", "")
    value = value.replace("`", "")

    return " ".join(value.split())


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize(a),
        normalize(b),
    ).ratio()


def get_api_key():
    api_key = os.getenv("ODDS_API_KEY")

    if not api_key:
        raise ValueError(
            "Missing GitHub Secret ODDS_API_KEY"
        )

    return api_key


def request_json(url, params):
    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_upcoming_odds():
    """
    Fetch all upcoming odds and filter tennis events in code.
    """

    api_key = get_api_key()

    data = request_json(
        f"{BASE_URL}/sports/upcoming/odds/",
        params={
            "apiKey": api_key,
            "regions": DEFAULT_REGIONS,
            "markets": DEFAULT_MARKETS,
            "oddsFormat": DEFAULT_ODDS_FORMAT,
        },
    )

    if not isinstance(data, list):
        raise ValueError(
            f"Unexpected upcoming odds response: {data}"
        )

    tennis_events = []

    for event in data:
        sport_key = str(
            event.get("sport_key", "")
        ).lower()

        sport_title = str(
            event.get("sport_title", "")
        ).lower()

        if "tennis" in sport_key or "tennis" in sport_title:
            event["_provider"] = "the_odds_api"
            event["_strategy"] = "upcoming"
            tennis_events.append(event)

    return tennis_events


def fetch_sports():
    api_key = get_api_key()

    data = request_json(
        f"{BASE_URL}/sports/",
        params={
            "apiKey": api_key,
        },
    )

    if not isinstance(data, list):
        raise ValueError(
            f"Unexpected sports response: {data}"
        )

    _DEBUG["sports_found"] = len(data)

    return data


def get_tennis_sport_keys():
    sports = fetch_sports()

    keys = []

    for sport in sports:
        key = sport.get("key", "")
        group = sport.get("group", "")
        title = sport.get("title", "")

        text = f"{key} {group} {title}".lower()

        if "tennis" in text and sport.get("active") is True:
            keys.append(key)

    _DEBUG["tennis_sport_keys"] = keys

    return keys


def fetch_odds_for_sport(sport_key):
    api_key = get_api_key()

    data = request_json(
        f"{BASE_URL}/sports/{sport_key}/odds",
        params={
            "apiKey": api_key,
            "regions": DEFAULT_REGIONS,
            "markets": DEFAULT_MARKETS,
            "oddsFormat": DEFAULT_ODDS_FORMAT,
        },
    )

    if not isinstance(data, list):
        return []

    for event in data:
        event["_provider"] = "the_odds_api"
        event["_strategy"] = "sport_key"
        event["_sport_key"] = sport_key

    return data


def fetch_by_tennis_sport_keys():
    keys = get_tennis_sport_keys()

    all_events = []

    for key in keys:
        try:
            events = fetch_odds_for_sport(key)
            all_events.extend(events)

        except Exception as exc:
            if len(_DEBUG["examples_unmatched"]) < 20:
                _DEBUG["examples_unmatched"].append({
                    "sport_key": key,
                    "reason": f"fetch_failed: {exc}",
                })

    return all_events


def fetch_odds():
    """
    Existing prediction engines call this function.

    Returns:
        list of tennis events from The Odds API.
    """

    try:
        events = fetch_upcoming_odds()

        if events:
            _DEBUG["strategy"] = "upcoming"
        else:
            events = fetch_by_tennis_sport_keys()
            _DEBUG["strategy"] = "sport_keys_fallback"

        _DEBUG["events_from_api"] = len(events)
        _DEBUG["fetch_error"] = None

        _DEBUG["sample_events"] = [
            {
                "id": event.get("id"),
                "sport_key": event.get("sport_key") or event.get("_sport_key"),
                "sport_title": event.get("sport_title"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "bookmakers_count": len(event.get("bookmakers", [])),
                "strategy": event.get("_strategy"),
            }
            for event in events[:20]
        ]

        write_debug()

        return events

    except Exception as exc:
        _DEBUG["events_from_api"] = 0
        _DEBUG["fetch_error"] = str(exc)

        write_debug()

        print(
            "fetch_odds error:",
            exc,
        )

        return []


def event_match_score(player1, player2, event):
    home = (
        event.get("home_team")
        or event.get("home")
        or ""
    )

    away = (
        event.get("away_team")
        or event.get("away")
        or ""
    )

    direct_score = (
        similarity(player1, home)
        +
        similarity(player2, away)
    )

    reversed_score = (
        similarity(player1, away)
        +
        similarity(player2, home)
    )

    if direct_score >= reversed_score:
        return {
            "score": direct_score,
            "orientation": "direct",
            "home": home,
            "away": away,
        }

    return {
        "score": reversed_score,
        "orientation": "reversed",
        "home": home,
        "away": away,
    }


def find_best_event(player1, player2, events):
    best_event = None
    best_meta = None
    best_score = 0

    for event in events:
        meta = event_match_score(
            player1,
            player2,
            event,
        )

        score = meta["score"]

        if score > best_score:
            best_score = score
            best_event = event
            best_meta = meta

    if best_score < 1.50:
        return None, None

    return best_event, best_meta


def extract_h2h_odds(event):
    home_team = (
        event.get("home_team")
        or event.get("home")
        or ""
    )

    away_team = (
        event.get("away_team")
        or event.get("away")
        or ""
    )

    bookmakers = event.get(
        "bookmakers",
        [],
    )

    best_home = None
    best_away = None

    best_home_bookmaker = None
    best_away_bookmaker = None

    markets_seen = []

    for bookmaker in bookmakers:
        bookmaker_title = (
            bookmaker.get("title")
            or bookmaker.get("key")
            or "unknown"
        )

        markets = bookmaker.get(
            "markets",
            [],
        )

        for market in markets:
            market_key = market.get("key")
            markets_seen.append(market_key)

            if market_key != "h2h":
                continue

            outcomes = market.get(
                "outcomes",
                [],
            )

            for outcome in outcomes:
                outcome_name = outcome.get("name")
                price = outcome.get("price")

                if outcome_name is None or price is None:
                    continue

                try:
                    price = float(price)
                except Exception:
                    continue

                sim_home = similarity(
                    outcome_name,
                    home_team,
                )

                sim_away = similarity(
                    outcome_name,
                    away_team,
                )

                if sim_home >= sim_away:
                    if best_home is None or price > best_home:
                        best_home = price
                        best_home_bookmaker = bookmaker_title
                else:
                    if best_away is None or price > best_away:
                        best_away = price
                        best_away_bookmaker = bookmaker_title

    if best_home is None or best_away is None:
        return None

    if best_home_bookmaker == best_away_bookmaker:
        bookmaker = best_home_bookmaker
    else:
        bookmaker = "best_available"

    return {
        "home_odds": best_home,
        "away_odds": best_away,
        "bookmaker": bookmaker,
        "home_bookmaker": best_home_bookmaker,
        "away_bookmaker": best_away_bookmaker,
        "market_name": "h2h",
    }


def find_match_odds(player1, player2, odds_data):
    """
    Existing prediction engines call this function.

    Returns:
    {
        "odds_player1": 1.75,
        "odds_player2": 2.10,
        "bookmaker": "...",
        "odds_source": "The Odds API"
    }

    If not found:
    {}
    """

    if not odds_data:
        _DEBUG["unmatched"] += 1
        _DEBUG["odds_missing"] += 1

        if len(_DEBUG["examples_unmatched"]) < 30:
            _DEBUG["examples_unmatched"].append({
                "player1": player1,
                "player2": player2,
                "reason": "no_odds_data",
            })

        write_debug()

        return {}

    event, meta = find_best_event(
        player1,
        player2,
        odds_data,
    )

    if not event or not meta:
        _DEBUG["unmatched"] += 1
        _DEBUG["odds_missing"] += 1

        if len(_DEBUG["examples_unmatched"]) < 30:
            _DEBUG["examples_unmatched"].append({
                "player1": player1,
                "player2": player2,
                "reason": "no_matching_event",
            })

        write_debug()

        return {}

    odds = extract_h2h_odds(event)

    if not odds:
        _DEBUG["matched"] += 1
        _DEBUG["odds_missing"] += 1

        if len(_DEBUG["examples_unmatched"]) < 30:
            _DEBUG["examples_unmatched"].append({
                "player1": player1,
                "player2": player2,
                "event_home": meta.get("home"),
                "event_away": meta.get("away"),
                "event_id": event.get("id"),
                "reason": "no_h2h_market",
            })

        write_debug()

        return {}

    if meta["orientation"] == "direct":
        odds_player1 = odds["home_odds"]
        odds_player2 = odds["away_odds"]
    else:
        odds_player1 = odds["away_odds"]
        odds_player2 = odds["home_odds"]

    result = {
        "odds_player1": odds_player1,
        "odds_player2": odds_player2,
        "bookmaker": odds.get("bookmaker"),
        "home_bookmaker": odds.get("home_bookmaker"),
        "away_bookmaker": odds.get("away_bookmaker"),
        "odds_source": "The Odds API",
        "event_home": meta.get("home"),
        "event_away": meta.get("away"),
        "event_id": event.get("id"),
        "sport_key": event.get("sport_key") or event.get("_sport_key"),
        "market_name": "h2h",
        "match_score": round(
            meta["score"],
            3,
        ),
    }

    _DEBUG["matched"] += 1
    _DEBUG["odds_found"] += 1

    if len(_DEBUG["examples_matched"]) < 30:
        _DEBUG["examples_matched"].append({
            "player1": player1,
            "player2": player2,
            "event_home": meta.get("home"),
            "event_away": meta.get("away"),
            "event_id": event.get("id"),
            "odds_player1": odds_player1,
            "odds_player2": odds_player2,
            "bookmaker": odds.get("bookmaker"),
            "score": round(
                meta["score"],
                3,
            ),
        })

    write_debug()

    return result
