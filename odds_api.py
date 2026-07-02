import os
import json
import requests
import unicodedata
from difflib import SequenceMatcher


#
# Providers:
#
# 1. The Odds API
#    Secret: ODDS_API_KEY
#
# 2. SportsGameOdds
#    Secret: SGOAPI
#

THE_ODDS_BASE_URL = "https://api.the-odds-api.com/v4"
SGO_BASE_URL = "https://api.sportsgameodds.com/v2"

ODDS_DEBUG_PATH = "public/odds_debug.json"

DEFAULT_REGIONS = "eu"
DEFAULT_MARKETS = "h2h"
DEFAULT_ODDS_FORMAT = "decimal"

SGO_LEAGUES = "ATP,WTA,ITF"
SGO_SPORT_ID = "TENNIS"


_DEBUG = {
    "provider_chain": [
        "The Odds API",
        "SportsGameOdds",
    ],

    "the_odds_api": {
        "sports_found": 0,
        "tennis_sport_keys": [],
        "events_from_api": 0,
        "error": None,
        "sample_events": [],
    },

    "sportsgameodds": {
        "events_from_api": 0,
        "error": None,
        "sample_events": [],
    },

    "matching": {
        "matched": 0,
        "unmatched": 0,
        "odds_found": 0,
        "odds_missing": 0,
        "from_the_odds_api": 0,
        "from_sportsgameodds": 0,
    },

    "examples_matched": [],
    "examples_unmatched": [],
}


def write_debug():
    os.makedirs(
        "public",
        exist_ok=True,
    )

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


def request_json(
    url,
    params=None,
    headers=None,
):
    response = requests.get(
        url,
        params=params or {},
        headers=headers or {},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ==================================================
# The Odds API
# ==================================================

def get_the_odds_api_key():
    return os.getenv("ODDS_API_KEY")


def fetch_the_odds_sports():
    api_key = get_the_odds_api_key()

    if not api_key:
        raise ValueError(
            "Missing GitHub Secret ODDS_API_KEY"
        )

    data = request_json(
        f"{THE_ODDS_BASE_URL}/sports/",
        params={
            "apiKey": api_key,
        },
    )

    if not isinstance(data, list):
        raise ValueError(
            f"Unexpected sports response: {data}"
        )

    _DEBUG["the_odds_api"]["sports_found"] = len(data)

    return data


def get_the_odds_tennis_sport_keys():
    forced = os.getenv("ODDS_SPORT_KEYS")

    if forced:
        keys = [
            item.strip()
            for item in forced.split(",")
            if item.strip()
        ]

        _DEBUG["the_odds_api"]["tennis_sport_keys"] = keys

        return keys

    sports = fetch_the_odds_sports()

    keys = []

    for sport in sports:
        key = sport.get("key", "")
        group = sport.get("group", "")
        title = sport.get("title", "")

        text = f"{key} {group} {title}".lower()

        if "tennis" in text and sport.get("active") is True:
            keys.append(key)

    _DEBUG["the_odds_api"]["tennis_sport_keys"] = keys

    return keys


def fetch_the_odds_for_sport(sport_key):
    api_key = get_the_odds_api_key()

    regions = os.getenv(
        "ODDS_REGIONS",
        DEFAULT_REGIONS,
    )

    markets = os.getenv(
        "ODDS_MARKETS",
        DEFAULT_MARKETS,
    )

    odds_format = os.getenv(
        "ODDS_FORMAT",
        DEFAULT_ODDS_FORMAT,
    )

    data = request_json(
        f"{THE_ODDS_BASE_URL}/sports/{sport_key}/odds",
        params={
            "apiKey": api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
        },
    )

    if not isinstance(data, list):
        return []

    for event in data:
        event["_provider"] = "the_odds_api"
        event["_sport_key"] = sport_key

    return data


def fetch_the_odds_events():
    try:
        sport_keys = get_the_odds_tennis_sport_keys()

        all_events = []

        for sport_key in sport_keys:
            try:
                events = fetch_the_odds_for_sport(
                    sport_key
                )

                all_events.extend(events)

            except Exception as exc:
                _DEBUG["examples_unmatched"].append({
                    "provider": "the_odds_api",
                    "sport_key": sport_key,
                    "reason": f"odds_fetch_failed: {exc}",
                })

        _DEBUG["the_odds_api"]["events_from_api"] = len(all_events)
        _DEBUG["the_odds_api"]["error"] = None

        _DEBUG["the_odds_api"]["sample_events"] = [
            {
                "id": event.get("id"),
                "sport_key": event.get("_sport_key"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "bookmakers_count": len(event.get("bookmakers", [])),
            }
            for event in all_events[:20]
        ]

        return all_events

    except Exception as exc:
        _DEBUG["the_odds_api"]["events_from_api"] = 0
        _DEBUG["the_odds_api"]["error"] = str(exc)

        return []


def extract_the_odds_h2h(event):
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
        "source": "The Odds API",
    }


# ==================================================
# SportsGameOdds
# ==================================================

def get_sgo_api_key():
    return os.getenv("SGOAPI")


def fetch_sgo_events_page(cursor=None):
    api_key = get_sgo_api_key()

    if not api_key:
        raise ValueError(
            "Missing GitHub Secret SGOAPI"
        )

    params = {
        "apiKey": api_key,
        "sportID": SGO_SPORT_ID,
        "leagueID": SGO_LEAGUES,
        "oddsAvailable": "true",
        "limit": 100,
    }

    if cursor:
        params["cursor"] = cursor

    data = request_json(
        f"{SGO_BASE_URL}/events",
        params=params,
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Unexpected SGO response: {data}"
        )

    return data


def fetch_sgo_events(max_pages=3):
    try:
        all_events = []
        cursor = None

        for _ in range(max_pages):
            page = fetch_sgo_events_page(
                cursor=cursor
            )

            if page.get("success") is not True:
                raise ValueError(
                    page.get("error") or "SGO request failed"
                )

            data = page.get("data", [])

            if not isinstance(data, list):
                data = []

            for event in data:
                event["_provider"] = "sportsgameodds"

            all_events.extend(data)

            cursor = page.get("nextCursor")

            if not cursor:
                break

        _DEBUG["sportsgameodds"]["events_from_api"] = len(all_events)
        _DEBUG["sportsgameodds"]["error"] = None

        _DEBUG["sportsgameodds"]["sample_events"] = [
            summarize_sgo_event(event)
            for event in all_events[:20]
        ]

        return all_events

    except Exception as exc:
        _DEBUG["sportsgameodds"]["events_from_api"] = 0
        _DEBUG["sportsgameodds"]["error"] = str(exc)

        return []


def get_sgo_team_name(event, side):
    teams = event.get("teams", {})

    team = teams.get(side, {})

    names = team.get("names", {})

    return (
        names.get("long")
        or names.get("medium")
        or names.get("short")
        or team.get("name")
        or team.get("teamName")
        or ""
    )


def summarize_sgo_event(event):
    return {
        "eventID": event.get("eventID"),
        "sportID": event.get("sportID"),
        "leagueID": event.get("leagueID"),
        "home": get_sgo_team_name(event, "home"),
        "away": get_sgo_team_name(event, "away"),
        "startTime": event.get("startTime")
        or event.get("startsAt")
        or event.get("startDate"),
        "hasOdds": bool(event.get("odds")),
    }


def collect_numbers_from_obj(obj):
    """
    Generic recursive extractor for SGO odds-like numbers.
    We keep this defensive because SGO odds schema can vary by market/bookmaker.
    """

    found = []

    if isinstance(obj, dict):
        for key, value in obj.items():

            key_text = str(key).lower()

            if isinstance(value, (int, float)):
                if 1.01 <= float(value) <= 100:
                    if any(word in key_text for word in [
                        "odds",
                        "price",
                        "decimal",
                    ]):
                        found.append(float(value))

            elif isinstance(value, str):
                try:
                    numeric = float(value)

                    if 1.01 <= numeric <= 100:
                        if any(word in key_text for word in [
                            "odds",
                            "price",
                            "decimal",
                        ]):
                            found.append(numeric)

                except Exception:
                    pass

            else:
                found.extend(
                    collect_numbers_from_obj(value)
                )

    elif isinstance(obj, list):
        for item in obj:
            found.extend(
                collect_numbers_from_obj(item)
            )

    return found


def extract_sgo_odds(event):
    """
    Best-effort extraction from SportsGameOdds event.

    If exact market parsing is not available, this function scans event["odds"]
    for decimal odds-like values and returns first two reasonable prices.

    Debug output will show if SGO structure needs refinement.
    """

    home = get_sgo_team_name(event, "home")
    away = get_sgo_team_name(event, "away")

    odds_obj = event.get("odds")

    if odds_obj is None:
        return None

    values = collect_numbers_from_obj(
        odds_obj
    )

    unique_values = []

    for value in values:
        if value not in unique_values:
            unique_values.append(value)

    if len(unique_values) < 2:
        return None

    home_odds = unique_values[0]
    away_odds = unique_values[1]

    return {
        "home_odds": home_odds,
        "away_odds": away_odds,
        "bookmaker": "SportsGameOdds",
        "home_bookmaker": "SportsGameOdds",
        "away_bookmaker": "SportsGameOdds",
        "market_name": "unknown_moneyline_candidate",
        "source": "SportsGameOdds",
        "event_home": home,
        "event_away": away,
    }


# ==================================================
# Shared matching
# ==================================================

def get_event_names(event):
    provider = event.get("_provider")

    if provider == "sportsgameodds":
        return (
            get_sgo_team_name(event, "home"),
            get_sgo_team_name(event, "away"),
        )

    return (
        event.get("home_team")
        or event.get("home")
        or "",
        event.get("away_team")
        or event.get("away")
        or "",
    )


def event_match_score(player1, player2, event):
    home, away = get_event_names(event)

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
    provider=None,
):
    best_event = None
    best_meta = None
    best_score = 0

    for event in events:

        if provider and event.get("_provider") != provider:
            continue

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


def extract_odds_for_event(event):
    provider = event.get("_provider")

    if provider == "sportsgameodds":
        return extract_sgo_odds(event)

    return extract_the_odds_h2h(event)


# ==================================================
# Public API used by prediction engines
# ==================================================

def fetch_odds():
    """
    Compatibility function used by prediction_engine_top.py
    and prediction_engine_all.py.

    Returns combined list of events from:
    - The Odds API
    - SportsGameOdds
    """

    the_odds_events = fetch_the_odds_events()
    sgo_events = fetch_sgo_events()

    combined = (
        the_odds_events
        +
        sgo_events
    )

    write_debug()

    return combined


def find_match_odds(
    player1,
    player2,
    odds_data,
):
    """
    Existing prediction engines expect this function.

    Returns:
    {
        "odds_player1": 1.75,
        "odds_player2": 2.10,
        "bookmaker": "...",
        "odds_source": "The Odds API" | "SportsGameOdds"
    }

    If not found, returns {}.
    """

    if not odds_data:
        _DEBUG["matching"]["unmatched"] += 1
        _DEBUG["matching"]["odds_missing"] += 1

        if len(_DEBUG["examples_unmatched"]) < 30:
            _DEBUG["examples_unmatched"].append({
                "player1": player1,
                "player2": player2,
                "reason": "no_odds_data",
            })

        write_debug()

        return {}

    #
    # Provider priority:
    # 1. The Odds API
    # 2. SportsGameOdds
    #

    for provider in [
        "the_odds_api",
        "sportsgameodds",
    ]:

        event, meta = find_best_event(
            player1,
            player2,
            odds_data,
            provider=provider,
        )

        if not event or not meta:
            continue

        odds = extract_odds_for_event(
            event
        )

        if not odds:
            continue

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
            "odds_source": odds.get("source"),
            "event_home": meta.get("home"),
            "event_away": meta.get("away"),
            "event_id": event.get("id") or event.get("eventID"),
            "sport_key": event.get("sport_key")
            or event.get("_sport_key")
            or event.get("leagueID"),
            "market_name": odds.get("market_name"),
            "match_score": round(
                meta["score"],
                3,
            ),
        }

        _DEBUG["matching"]["matched"] += 1
        _DEBUG["matching"]["odds_found"] += 1

        if provider == "the_odds_api":
            _DEBUG["matching"]["from_the_odds_api"] += 1
        else:
            _DEBUG["matching"]["from_sportsgameodds"] += 1

        if len(_DEBUG["examples_matched"]) < 30:
            _DEBUG["examples_matched"].append({
                "provider": provider,
                "player1": player1,
                "player2": player2,
                "event_home": meta.get("home"),
                "event_away": meta.get("away"),
                "event_id": event.get("id") or event.get("eventID"),
                "odds_player1": odds_player1,
                "odds_player2": odds_player2,
                "bookmaker": odds.get("bookmaker"),
                "market_name": odds.get("market_name"),
                "score": round(
                    meta["score"],
                    3,
                ),
            })

        write_debug()

        return result

    _DEBUG["matching"]["unmatched"] += 1
    _DEBUG["matching"]["odds_missing"] += 1

    if len(_DEBUG["examples_unmatched"]) < 30:
        _DEBUG["examples_unmatched"].append({
            "player1": player1,
            "player2": player2,
            "reason": "no_matching_event_or_no_odds",
        })

    write_debug()

    return {}
