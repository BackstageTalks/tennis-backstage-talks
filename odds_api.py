import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher

import requests


ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4/sports"

DEFAULT_SPORT_KEYS = [
    "tennis_atp_wimbledon",
    "tennis_wta_wimbledon",
    "tennis_atp",
    "tennis_wta",
]

DEFAULT_REGIONS = "eu,uk,us,au"
DEFAULT_MARKETS = "h2h"
DEFAULT_ODDS_FORMAT = "decimal"

REQUEST_TIMEOUT_SECONDS = 25

MATCH_SCORE_THRESHOLD = 0.82
OUTCOME_SCORE_THRESHOLD = 0.84

DEBUG_PATH = "public/odds_debug.json"


def get_api_key():
    return os.getenv("ODDS_API_KEY")


def get_sport_keys():
    value = os.getenv("ODDS_SPORT_KEYS")

    if not value:
        return DEFAULT_SPORT_KEYS

    keys = []

    for item in value.split(","):
        item = item.strip()

        if item:
            keys.append(item)

    if not keys:
        return DEFAULT_SPORT_KEYS

    return keys


def get_regions():
    return os.getenv(
        "ODDS_REGIONS",
        DEFAULT_REGIONS,
    )


def normalize_name(name):
    if name is None:
        return ""

    text = str(name).strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    replacements = {
        "-": " ",
        "_": " ",
        ".": " ",
        ",": " ",
        "'": " ",
        "’": " ",
        "`": " ",
        "´": " ",
        "(": " ",
        ")": " ",
        "[": " ",
        "]": " ",
        "{": " ",
        "}": " ",
        "/": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def name_tokens(name):
    normalized = normalize_name(name)

    if not normalized:
        return []

    return [
        token
        for token in normalized.split(" ")
        if token
    ]


def sorted_token_key(name):
    tokens = name_tokens(name)

    return " ".join(
        sorted(tokens)
    )


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def sequence_score(left, right):
    left_normalized = normalize_name(left)
    right_normalized = normalize_name(right)

    if not left_normalized or not right_normalized:
        return 0.0

    if left_normalized == right_normalized:
        return 1.0

    if sorted_token_key(left_normalized) == sorted_token_key(right_normalized):
        return 0.98

    return SequenceMatcher(
        None,
        left_normalized,
        right_normalized,
    ).ratio()


def token_overlap_score(left, right):
    left_tokens = set(
        name_tokens(left)
    )

    right_tokens = set(
        name_tokens(right)
    )

    if not left_tokens or not right_tokens:
        return 0.0

    intersection = left_tokens.intersection(
        right_tokens
    )

    union = left_tokens.union(
        right_tokens
    )

    if not union:
        return 0.0

    return len(intersection) / len(union)


def last_name_score(left, right):
    left_tokens = name_tokens(left)
    right_tokens = name_tokens(right)

    if not left_tokens or not right_tokens:
        return 0.0

    left_last = left_tokens[-1]
    right_last = right_tokens[-1]

    if left_last != right_last:
        return 0.0

    if len(left_tokens) == 1 or len(right_tokens) == 1:
        return 0.82

    left_initials = "".join(
        token[0]
        for token in left_tokens[:-1]
        if token
    )

    right_initials = "".join(
        token[0]
        for token in right_tokens[:-1]
        if token
    )


    if left_initials and right_initials:
        if left_initials == right_initials:
            return 0.95

        if left_initials[0] == right_initialsreturn 0.88

    return 0.86



def name_match_score(left, right):
    scores = [
        sequence_score(left, right),
        token_overlap_score(left, right),
        last_name_score(left, right),
    ]

    return max(scores)


def event_match_score(player1, player2, event):
    home_team = event.get("home_team")
    away_team = event.get("away_team")

    if not home_team or not away_team:
        return 0.0

    direct_score = (
        name_match_score(player1, home_team)
        + name_match_score(player2, away_team)
    ) / 2.0

    reverse_score = (
        name_match_score(player1, away_team)
        + name_match_score(player2, home_team)
    ) / 2.0

    return max(
        direct_score,
        reverse_score,
    )


def confidence_label(score):
    if score >= 0.97:
        return "exact"

    if score >= 0.90:
        return "strong"

    if score >= MATCH_SCORE_THRESHOLD:
        return "fuzzy"

    return "low"


def is_h2h_market(market):
    return market.get("key") == "h2h"


def iter_h2h_outcomes(event):
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if not is_h2h_market(market):
                continue

            for outcome in market.get("outcomes", []):
                name = outcome.get("name")
                price = safe_float(
                    outcome.get("price")
                )

                if not name:
                    continue

                if price is None:
                    continue

                yield {
                    "name": name,
                    "price": price,
                }


def best_price_for_player(event, player_name):
    best_price = None
    best_score = 0.0

    for outcome in iter_h2h_outcomes(event):
        score = name_match_score(
            player_name,
            outcome.get("name"),
        )

        if score < OUTCOME_SCORE_THRESHOLD:
            continue

        price = outcome.get("price")

        if best_price is None or price > best_price:
            best_price = price
            best_score = score

    return best_price, best_score


def extract_event_odds_for_players(event, player1, player2):
    odds_player1, score_player1 = best_price_for_player(
        event,
        player1,
    )

    odds_player2, score_player2 = best_price_for_player(
        event,
        player2,
    )

    return {
        "odds_player1": odds_player1,
        "odds_player2": odds_player2,
        "player1_odds_match_score": round(score_player1, 3),
        "player2_odds_match_score": round(score_player2, 3),
    }


def request_odds_for_sport(sport_key):
    api_key = get_api_key()

    if not api_key:
        print(
            "ODDS API KEY MISSING: ODDS_API_KEY environment variable is not set."
        )

        return []

    url = f"{ODDS_API_BASE_URL}/{sport_key}/odds"

    params = {
        "apiKey": api_key,
        "regions": get_regions(),
        "markets": DEFAULT_MARKETS,
        "oddsFormat": DEFAULT_ODDS_FORMAT,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            print(
                "ODDS API SPORT NOT FOUND:",
                sport_key,
            )

            return []

        if response.status_code == 422:
            print(
                "ODDS API SPORT UNAVAILABLE OR INVALID:",
                sport_key,
                response.text[:300],
            )

            return []

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            print(
                "ODDS API UNEXPECTED RESPONSE:",
                sport_key,
                type(data),
            )

            return []

        print(
            "ODDS API FETCHED:",
            sport_key,
            "events:",
            len(data),
        )

        return data

    except Exception as exc:
        print(
            "ODDS API REQUEST ERROR:",
            sport_key,
            str(exc),
        )

        return []


def deduplicate_events(events):
    seen = set()
    unique_events = []

    for event in events:
        event_id = event.get("id")

        if event_id:
            key = event_id

        else:
            key = (
                normalize_name(event.get("home_team"))
                + "::"
                + normalize_name(event.get("away_team"))
                + "::"
                + str(event.get("commence_time"))
            )

        if key in seen:
            continue

        seen.add(key)
        unique_events.append(event)

    return unique_events


def save_odds_debug(events):
    try:
        os.makedirs(
            "public",
            exist_ok=True,
        )

        payload = {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "events_count": len(events),

            "events": [
                {
                    "id": event.get("id"),
                    "sport_key": event.get("sport_key"),
                    "sport_title": event.get("sport_title"),
                    "commence_time": event.get("commence_time"),
                    "home_team": event.get("home_team"),
                    "away_team": event.get("away_team"),
                    "bookmakers_count": len(
                        event.get("bookmakers", [])
                    ),
                }
                for event in events
            ],
        }

        with open(
            DEBUG_PATH,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                indent=2,
                ensure_ascii=False,
            )

    except Exception as exc:
        print(
            "ODDS DEBUG SAVE ERROR:",
            str(exc),
        )


def fetch_odds():
    all_events = []

    for sport_key in get_sport_keys():
        events = request_odds_for_sport(
            sport_key,
        )

        all_events.extend(events)

    unique_events = deduplicate_events(
        all_events,
    )

    print(
        "ODDS API TOTAL UNIQUE EVENTS:",
        len(unique_events),
    )

    save_odds_debug(
        unique_events,
    )

    return unique_events


def find_best_event(player1, player2, odds_matches):
    best_event = None
    best_score = 0.0

    for event in odds_matches or []:
        score = event_match_score(
            player1,
            player2,
            event,
        )

        if score > best_score:
            best_score = score
            best_event = event

    if best_score < MATCH_SCORE_THRESHOLD:
        return None, best_score

    return best_event, best_score


def find_match_odds(player1, player2, odds_matches):
    event, event_score = find_best_event(
        player1,
        player2,
        odds_matches,
    )

    if not event:
        return {
            "odds_player1": None,
            "odds_player2": None,
            "odds_source": "the_odds_api",
            "matched_event": None,
            "match_confidence": "not_matched",
        }

    extracted = extract_event_odds_for_players(
        event,
        player1,
        player2,
    )

    matched_event = (
        f"{event.get('home_team')} vs {event.get('away_team')}"
    )

    result = {
        "odds_player1": extracted.get("odds_player1"),
        "odds_player2": extracted.get("odds_player2"),
        "odds_source": "the_odds_api",

        # Internal/debug fields only.
        # These do not need to be displayed on the website.
        "matched_event": matched_event,
        "match_confidence": confidence_label(
            event_score,
        ),
        "event_match_score": round(
            event_score,
            3,
        ),
        "player1_odds_match_score":
            extracted.get("player1_odds_match_score"),
        "player2_odds_match_score":
            extracted.get("player2_odds_match_score"),
    }

    if (
        result["odds_player1"] is None
        or result["odds_player2"] is None
    ):
        print(
            "ODDS MATCHED EVENT BUT MISSING PLAYER PRICE:",
            player1,
            "vs",
            player2,
            "matched_event:",
            matched_event,
            "event_score:",
            round(event_score, 3),
            "odds_player1:",
            result["odds_player1"],
            "odds_player2:",
            result["odds_player2"],
        )

    return result
