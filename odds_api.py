import os
import json
import requests
import unicodedata
from difflib import SequenceMatcher


BASE_URL = "https://api.sportsgameodds.com/v2"

ODDS_DEBUG_PATH = "public/odds_debug.json"

SPORT_ID = "TENNIS"
LEAGUE_IDS = "ATP,WTA,ITF"

# We try to request moneyline/home market + opposing odds.
# If SGO schema differs, debug will show what came back.
ODD_ID = "points-home-game-ml-home"


_DEBUG = {
    "provider": "SportsGameOdds",
    "sportID": SPORT_ID,
    "leagueID": LEAGUE_IDS,
    "events_from_api": 0,
    "fetch_error": None,

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


def request_json(url, params=None, headers=None):
    response = requests.get(
        url,
        params=params or {},
        headers=headers or {},
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_team_name(event, side):
    """
    SportsGameOdds normally stores participants under:
    event["teams"]["home"]["names"]["long"]
    event["teams"]["away"]["names"]["long"]
    """

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
        "odds_keys": (
            list(event.get("odds", {}).keys())[:20]
            if isinstance(event.get("odds"), dict)
            else []
        ),
    }


def fetch_events_page(cursor=None):
    api_key = get_api_key()

    params = {
        "apiKey": api_key,
        "sportID": SPORT_ID,
        "leagueID": LEAGUE_IDS,
        "oddsAvailable": "true",
        "limit": 100,

        # Moneyline candidate + opposing odds.
        # If this is too restrictive, remove oddID later.
        "oddID": ODD_ID,
        "includeOpposingOdds": "true",
    }

    if cursor:
        params["cursor"] = cursor

    data = request_json(
        f"{BASE_URL}/events",
        params=params,
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Unexpected SGO response: {data}"
        )

    return data


def fetch_sgo_events(max_pages=3):
    all_events = []
    cursor = None

    for _ in range(max_pages):
        page = fetch_events_page(
            cursor=cursor
        )

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

        all_events.extend(data)

        cursor = page.get("nextCursor")

        if not cursor:
            break

    return all_events


def fetch_odds():
    """
    Existing prediction engines call this function.

    Returns:
        list of SportsGameOdds tennis events with available odds.
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

    # Max score = 2.0.
    # 1.50 allows small spelling differences.
    if best_score < 1.50:
        return None, None

    return best_event, best_meta


def is_decimal_odd(value):
    try:
        number = float(value)
    except Exception:
        return False

    return 1.01 <= number <= 100


def extract_number(value):
    try:
        number = float(value)
    except Exception:
        return None

    if 1.01 <= number <= 100:
        return number

    return None


def collect_odds_candidates(obj, path=""):
    """
    Defensive recursive parser.

    SGO odds schema can be nested. We scan for decimal odds-like values
    under keys/paths containing odds, price, decimal, or close/open odds.

    Returns list:
    [
        {
            "path": "...",
            "value": 1.83
        }
    ]
    """

    candidates = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key).lower()
            new_path = f"{path}.{key_text}" if path else key_text

            if isinstance(value, (int, float, str)):
                number = extract_number(value)

                if number is not None:
                    if any(
                        word in new_path
                        for word in [
                            "odds",
                            "price",
                            "decimal",
                            "open",
                            "close",
                        ]
                    ):
                        candidates.append({
                            "path": new_path,
                            "value": number,
                        })

            if isinstance(value, (dict, list)):
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


def side_from_path(path):
    text = path.lower()

    if "home" in text:
        return "home"

    if "away" in text:
        return "away"

    if "opposing" in text:
        return "away"

    return None


def extract_sgo_moneyline_odds(event):
    """
    Try to extract home/away moneyline decimal odds from SGO event.

    First tries path-based side detection.
    If that fails, falls back to first two reasonable odds candidates.
    """

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
        path = candidate["path"]
        value = candidate["value"]

        side = side_from_path(path)

        if side == "home" and home_odds is None:
            home_odds = value
            home_path = path

        if side == "away" and away_odds is None:
            away_odds = value
            away_path = path

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

    # Fallback: use first two unique candidate values.
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
