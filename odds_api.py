import os
import json
import requests
import unicodedata
from difflib import SequenceMatcher


BASE_URL = "https://api.sportsgameodds.com/v2"

ODDS_DEBUG_PATH = "public/odds_debug.json"

SPORT_ID = "TENNIS"
LEAGUE_IDS = "ATP,WTA,ITF"


_DEBUG = {
    "provider": "SportsGameOdds",
    "sportID": SPORT_ID,
    "leagueID": LEAGUE_IDS,

    "events_from_api": 0,
    "fetch_error": None,
    "raw_success": None,
    "raw_error": None,
    "request_strategy": None,

    "matched": 0,
    "unmatched": 0,
    "odds_found": 0,
    "odds_missing": 0,

    "sample_events": [],
    "examples_matched": [],
    "examples_unmatched": [],
    "examples_parsing_failed": [],
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


def get_api_key():
    api_key = os.getenv("SGOAPI")

    if not api_key:
        raise ValueError(
            "Missing GitHub Secret SGOAPI"
        )

    return api_key


def request_json(url, params=None):
    api_key = get_api_key()

    final_params = params or {}
    final_params["apiKey"] = api_key

    response = requests.get(
        url,
        params=final_params,
        headers={
            "x-api-key": api_key,
            "accept": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_team_name(event, side):
    teams = event.get("teams") or {}
    team = teams.get(side) or {}
    names = team.get("names") or {}

    return (
        names.get("long")
        or names.get("medium")
        or names.get("short")
        or team.get("name")
        or team.get("teamName")
        or team.get("displayName")
        or ""
    )


def summarize_event(event):
    odds_obj = event.get("odds")

    if isinstance(odds_obj, dict):
        odds_keys = list(odds_obj.keys())[:50]
    else:
        odds_keys = []

    return {
        "eventID": event.get("eventID"),
        "sportID": event.get("sportID"),
        "leagueID": event.get("leagueID"),
        "home": get_team_name(event, "home"),
        "away": get_team_name(event, "away"),
        "startTime": (
            event.get("startTime")
            or event.get("startsAt")
            or event.get("startDate")
            or event.get("scheduledTime")
        ),
        "hasOdds": bool(event.get("odds")),
        "odds_type": type(odds_obj).__name__,
        "odds_keys": odds_keys,
    }


def fetch_events_page(params, cursor=None):
    final_params = dict(params)

    if cursor:
        final_params["cursor"] = cursor

    data = request_json(
        f"{BASE_URL}/events",
        params=final_params,
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Unexpected SGO response: {data}"
        )

    return data


def fetch_events_with_strategy(strategy_name, params, max_pages=3):
    all_events = []
    cursor = None

    for _ in range(max_pages):
        page = fetch_events_page(
            params=params,
            cursor=cursor,
        )

        _DEBUG["raw_success"] = page.get("success")
        _DEBUG["raw_error"] = page.get("error")

        if page.get("success") is not True:
            raise ValueError(
                page.get("error")
                or "SportsGameOdds request failed"
            )

        data = page.get("data") or []

        if not isinstance(data, list):
            data = []

        for event in data:
            event["_provider"] = "sportsgameodds"
            event["_strategy"] = strategy_name

        all_events.extend(data)

        cursor = page.get("nextCursor")

        if not cursor:
            break

    return all_events


def fetch_sgo_events():
    """
    Try several strategies.

    Strategy 1:
        strict tennis + ATP/WTA/ITF + oddsAvailable

    Strategy 2:
        tennis + oddsAvailable without league filter

    Strategy 3:
        ATP/WTA/ITF + oddsAvailable without sport filter

    Strategy 4:
        tennis + oddsPresent
    """

    strategies = [
        (
            "sport_league_oddsAvailable",
            {
                "sportID": SPORT_ID,
                "leagueID": LEAGUE_IDS,
                "oddsAvailable": "true",
                "limit": 100,
            },
        ),
        (
            "sport_only_oddsAvailable",
            {
                "sportID": SPORT_ID,
                "oddsAvailable": "true",
                "limit": 100,
            },
        ),
        (
            "league_only_oddsAvailable",
            {
                "leagueID": LEAGUE_IDS,
                "oddsAvailable": "true",
                "limit": 100,
            },
        ),
        (
            "sport_only_oddsPresent",
            {
                "sportID": SPORT_ID,
                "oddsPresent": "true",
                "limit": 100,
            },
        ),
    ]

    last_error = None

    for strategy_name, params in strategies:
        try:
            events = fetch_events_with_strategy(
                strategy_name=strategy_name,
                params=params,
            )

            if events:
                _DEBUG["request_strategy"] = strategy_name
                return events

        except Exception as exc:
            last_error = str(exc)

    if last_error:
        raise ValueError(last_error)

    _DEBUG["request_strategy"] = "no_events_from_all_strategies"

    return []


def fetch_odds():
    """
    Existing prediction engines call this function.

    Returns:
        list of SportsGameOdds tennis events.
    """

    try:
        events = fetch_sgo_events()

        _DEBUG["events_from_api"] = len(events)
        _DEBUG["fetch_error"] = None

        _DEBUG["sample_events"] = [
            summarize_event(event)
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
    home = get_team_name(
        event,
        "home",
    )

    away = get_team_name(
        event,
        "away",
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


def american_to_decimal(value):
    number = float(value)

    if number > 0:
        return round(
            1 + number / 100,
            4,
        )

    return round(
        1 + 100 / abs(number),
        4,
    )


def decimal_or_american_to_decimal(value):
    try:
        number = float(value)
    except Exception:
        return None

    if 1.01 <= number <= 100:
        return number

    if -10000 <= number <= -100:
        return american_to_decimal(number)

    if 100 <= number <= 10000:
        return american_to_decimal(number)

    return None


def collect_odds_candidates(obj, path=""):
    """
    Defensive recursive parser.

    SportsGameOdds odds schema can be nested.
    We scan for decimal/american odds-like values under paths
    containing odds, price, decimal, open, close, american.
    """

    candidates = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key).lower()

            new_path = (
                f"{path}.{key_text}"
                if path
                else key_text
            )

            if isinstance(value, (int, float, str)):
                number = decimal_or_american_to_decimal(value)

                if number is not None:
                    if any(
                        word in new_path
                        for word in [
                            "odds",
                            "price",
                            "decimal",
                            "open",
                            "close",
                            "american",
                        ]
                    ):
                        candidates.append({
                            "path": new_path,
                            "value": number,
                            "raw": value,
                        })

            elif isinstance(value, (dict, list)):
                candidates.extend(
                    collect_odds_candidates(
                        value,
                        new_path,
                    )
                )

    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            new_path = f"{path}[{index}]"

            candidates.extend(
                collect_odds_candidates(
                    item,
                    new_path,
                )
            )

    return candidates


def path_side(path):
    text = path.lower()

    if "home" in text:
        return "home"

    if "away" in text:
        return "away"

    if "opposing" in text:
        return "away"

    return None


def extract_sgo_moneyline_odds(event):
    odds_obj = event.get("odds")

    if odds_obj is None:
        return None

    candidates = collect_odds_candidates(
        odds_obj
    )

    if not candidates:
        return None

    home_odds = None
    away_odds = None

    home_path = None
    away_path = None

    for candidate in candidates:
        side = path_side(
            candidate["path"]
        )

        if side == "home" and home_odds is None:
            home_odds = candidate["value"]
            home_path = candidate["path"]

        elif side == "away" and away_odds is None:
            away_odds = candidate["value"]
            away_path = candidate["path"]

    if home_odds is not None and away_odds is not None:
        return {
            "home_odds": home_odds,
            "away_odds": away_odds,
            "bookmaker": "SportsGameOdds",
            "home_bookmaker": "SportsGameOdds",
            "away_bookmaker": "SportsGameOdds",
            "market_name": "moneyline",
            "home_path": home_path,
            "away_path": away_path,
            "candidates_seen": candidates[:20],
        }

    unique = []

    for candidate in candidates:
        value = candidate["value"]

        if value not in unique:
            unique.append(value)

    if len(unique) >= 2:
        return {
            "home_odds": unique[0],
            "away_odds": unique[1],
            "bookmaker": "SportsGameOdds",
            "home_bookmaker": "SportsGameOdds",
            "away_bookmaker": "SportsGameOdds",
            "market_name": "moneyline_fallback",
            "home_path": None,
            "away_path": None,
            "candidates_seen": candidates[:20],
        }

    return None


def find_match_odds(player1, player2, odds_data):
    """
    Existing prediction engines call this function.

    Returns:
    {
        "odds_player1": 1.75,
        "odds_player2": 2.10,
        "bookmaker": "SportsGameOdds",
        "odds_source": "SportsGameOdds"
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

    odds = extract_sgo_moneyline_odds(
        event
    )

    if not odds:
        _DEBUG["matched"] += 1
        _DEBUG["odds_missing"] += 1

        if len(_DEBUG["examples_parsing_failed"]) < 30:
            _DEBUG["examples_parsing_failed"].append({
                "player1": player1,
                "player2": player2,
                "event_home": meta.get("home"),
                "event_away": meta.get("away"),
                "eventID": event.get("eventID"),
                "odds_keys": (
                    list(event.get("odds", {}).keys())[:50]
                    if isinstance(event.get("odds"), dict)
                    else []
                ),
                "raw_event_sample": summarize_event(event),
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
        "odds_source": "SportsGameOdds",
        "event_home": meta.get("home"),
        "event_away": meta.get("away"),
        "event_id": event.get("eventID"),
        "leagueID": event.get("leagueID"),
        "sportID": event.get("sportID"),
        "market_name": odds.get("market_name"),
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
            "eventID": event.get("eventID"),
            "odds_player1": odds_player1,
            "odds_player2": odds_player2,
            "bookmaker": odds.get("bookmaker"),
            "market_name": odds.get("market_name"),
            "home_path": odds.get("home_path"),
            "away_path": odds.get("away_path"),
            "score": round(
                meta["score"],
                3,
            ),
        })

    write_debug()

    return result
