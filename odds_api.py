import os
import json
import requests
import unicodedata
from difflib import SequenceMatcher


BASE_URL = "https://api.odds-api.io/v3"

ODDS_CACHE_PATH = "public/odds_cache.json"
ODDS_DEBUG_PATH = "public/odds_debug.json"

DEFAULT_BOOKMAKERS = "Bet365,Unibet,SingBet,Betfair"


_EVENT_ODDS_CACHE = {}

_DEBUG = {
    "provider": "Odds-API.io",
    "events_from_api": 0,
    "fetch_odds_error": None,
    "matched": 0,
    "unmatched": 0,
    "odds_found": 0,
    "odds_missing": 0,
    "examples_unmatched": [],
    "examples_matched": [],
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
        char for char in value
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
    api_key = os.getenv("APIIO")

    if not api_key:
        raise ValueError(
            "Missing GitHub Secret APIIO"
        )

    return api_key


def fetch_tennis_events(limit=500):
    api_key = get_api_key()

    response = requests.get(
        f"{BASE_URL}/events",
        params={
            "apiKey": api_key,
            "sport": "tennis",
            "limit": limit,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError(
            f"Unexpected events response: {data}"
        )

    return data


def fetch_event_odds(event_id):
    if event_id in _EVENT_ODDS_CACHE:
        return _EVENT_ODDS_CACHE[event_id]

    api_key = get_api_key()

    bookmakers = os.getenv(
        "ODDS_BOOKMAKERS",
        DEFAULT_BOOKMAKERS,
    )

    response = requests.get(
        f"{BASE_URL}/odds",
        params={
            "apiKey": api_key,
            "eventId": event_id,
            "bookmakers": bookmakers,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    _EVENT_ODDS_CACHE[event_id] = data

    return data


def extract_ml_odds(data):
    bookmakers = data.get(
        "bookmakers",
        {},
    )

    if not isinstance(bookmakers, dict):
        return None

    for bookmaker_name, markets in bookmakers.items():

        if not isinstance(markets, list):
            continue

        for market in markets:

            market_name = str(
                market.get("name", "")
            ).upper()

            if market_name not in [
                "ML",
                "MONEYLINE",
                "MATCH WINNER",
                "WINNER",
            ]:
                continue

            odds_list = market.get(
                "odds",
                [],
            )

            if not odds_list:
                continue

            item = odds_list[0]

            home = item.get("home")
            away = item.get("away")

            if home is None or away is None:
                continue

            try:
                return {
                    "bookmaker": bookmaker_name,
                    "home_odds": float(home),
                    "away_odds": float(away),
                }

            except Exception:
                continue

    return None


def event_match_score(player1, player2, event):
    home = event.get("home", "")
    away = event.get("away", "")

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


def find_best_event(
    player1,
    player2,
    events,
):
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


def fetch_odds():
    """
    Compatibility function used by prediction_engine_top.py
    and prediction_engine_all.py.

    Returns list of tennis events from Odds-API.io.
    """

    try:
        events = fetch_tennis_events()

        _DEBUG["events_from_api"] = len(events)
        _DEBUG["fetch_odds_error"] = None

        write_debug()

        return events

    except Exception as exc:

        _DEBUG["events_from_api"] = 0
        _DEBUG["fetch_odds_error"] = str(exc)

        write_debug()

        print(
            "fetch_odds error:",
            exc,
        )

        return []


def find_match_odds(
    player1,
    player2,
    odds_data,
):
    """
    Compatibility function used by prediction engines.

    Returns:
    {
        "odds_player1": 1.75,
        "odds_player2": 2.10,
        "bookmaker": "Bet365",
        "odds_source": "Odds-API.io",
        "event_home": "...",
        "event_away": "...",
        "match_score": 1.82
    }

    If no odds found, returns empty dict.
    """

    if not odds_data:
        _DEBUG["unmatched"] += 1
        _DEBUG["odds_missing"] += 1

        if len(_DEBUG["examples_unmatched"]) < 20:
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

        if len(_DEBUG["examples_unmatched"]) < 20:
            _DEBUG["examples_unmatched"].append({
                "player1": player1,
                "player2": player2,
                "reason": "no_matching_event",
            })

        write_debug()

        return {}

    try:
        odds_response = fetch_event_odds(
            event["id"]
        )

        ml = extract_ml_odds(
            odds_response
        )

        if not ml:

            _DEBUG["matched"] += 1
            _DEBUG["odds_missing"] += 1

            if len(_DEBUG["examples_unmatched"]) < 20:
                _DEBUG["examples_unmatched"].append({
                    "player1": player1,
                    "player2": player2,
                    "event_home": event.get("home"),
                    "event_away": event.get("away"),
                    "reason": "no_ml_odds",
                })

            write_debug()

            return {}

        if meta["orientation"] == "direct":
            odds_player1 = ml["home_odds"]
            odds_player2 = ml["away_odds"]

        else:
            odds_player1 = ml["away_odds"]
            odds_player2 = ml["home_odds"]

        result = {
            "odds_player1": odds_player1,
            "odds_player2": odds_player2,
            "bookmaker": ml.get("bookmaker"),
            "odds_source": "Odds-API.io",
            "event_home": event.get("home"),
            "event_away": event.get("away"),
            "match_score": round(
                meta["score"],
                3,
            ),
        }

        _DEBUG["matched"] += 1
        _DEBUG["odds_found"] += 1

        if len(_DEBUG["examples_matched"]) < 20:
            _DEBUG["examples_matched"].append({
                "player1": player1,
                "player2": player2,
                "event_home": event.get("home"),
                "event_away": event.get("away"),
                "odds_player1": odds_player1,
                "odds_player2": odds_player2,
                "bookmaker": ml.get("bookmaker"),
                "score": round(
                    meta["score"],
                    3,
                ),
            })

        write_debug()

        return result

    except Exception as exc:

        _DEBUG["matched"] += 1
        _DEBUG["odds_missing"] += 1

        if len(_DEBUG["examples_unmatched"]) < 20:
            _DEBUG["examples_unmatched"].append({
                "player1": player1,
                "player2": player2,
                "event_home": event.get("home"),
                "event_away": event.get("away"),
                "reason": str(exc),
            })

        write_debug()

        print(
            f"Odds lookup failed for {player1} vs {player2}:",
            exc,
        )

        return {}


def build_odds_cache(matches):
    """
    Optional helper.
    Builds odds cache for list of matches.
    """

    events = fetch_odds()

    cache = {}

    for match in matches:

        player1 = (
            match.get("player1")
            or match.get("pick")
            or ""
        )

        player2 = (
            match.get("player2")
            or match.get("opponent")
            or ""
        )

        odds = find_match_odds(
            player1,
            player2,
            events,
        )

        if odds:
            cache[
                f"{player1}|{player2}"
            ] = odds

    os.makedirs(
        "public",
        exist_ok=True,
    )

    with open(
        ODDS_CACHE_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            cache,
            file,
            indent=2,
            ensure_ascii=False,
        )

    write_debug()

    return cache


def get_odds(
    player1,
    player2,
):
    """
    Optional cache reader.
    """

    if not os.path.exists(
        ODDS_CACHE_PATH
    ):
        return None

    with open(
        ODDS_CACHE_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        cache = json.load(file)

    return cache.get(
        f"{player1}|{player2}"
    )
