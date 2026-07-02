import os
import json
import requests
from difflib import SequenceMatcher


BASE_URL = "https://api.odds-api.io/v3"


def normalize(name):
    if not name:
        return ""

    replacements = {
        "á": "a",
        "ä": "a",
        "č": "c",
        "ď": "d",
        "é": "e",
        "ě": "e",
        "í": "i",
        "ľ": "l",
        "ĺ": "l",
        "ň": "n",
        "ó": "o",
        "ô": "o",
        "ö": "o",
        "ř": "r",
        "š": "s",
        "ť": "t",
        "ú": "u",
        "ů": "u",
        "ü": "u",
        "ý": "y",
        "ž": "z",
    }

    value = name.lower()

    for src, dst in replacements.items():
        value = value.replace(src, dst)

    value = value.replace("-", " ")
    value = value.replace(".", " ")

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

    return response.json()


def fetch_event_odds(event_id):
    api_key = get_api_key()

    response = requests.get(
        f"{BASE_URL}/odds",
        params={
            "apiKey": api_key,
            "eventId": event_id,
            "bookmakers": "Bet365",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def extract_ml_odds(data):
    bookmakers = data.get(
        "bookmakers",
        {}
    )

    for bookmaker in bookmakers.values():

        for market in bookmaker:

            if market.get("name") != "ML":
                continue

            odds = market.get(
                "odds",
                []
            )

            if not odds:
                continue

            item = odds[0]

            return {
                "home_odds": float(
                    item.get("home")
                ),
                "away_odds": float(
                    item.get("away")
                ),
            }

    return None


def find_best_event(
    player1,
    player2,
    events,
):
    best_event = None
    best_score = 0

    for event in events:

        home = event.get("home", "")
        away = event.get("away", "")

        score1 = (
            similarity(player1, home)
            +
            similarity(player2, away)
        )

        score2 = (
            similarity(player1, away)
            +
            similarity(player2, home)
        )

        score = max(score1, score2)

        if score > best_score:
            best_score = score
            best_event = event

    if best_score < 1.5:
        return None

    return best_event


def build_odds_cache(matches):

    events = fetch_tennis_events()

    cache = {}
    matched = 0

    unmatched = []

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

        event = find_best_event(
            player1,
            player2,
            events,
        )

        if not event:
            unmatched.append(
                f"{player1} vs {player2}"
            )
            continue

        try:

            odds_data = fetch_event_odds(
                event["id"]
            )

            ml = extract_ml_odds(
                odds_data
            )

            if not ml:
                unmatched.append(
                    f"{player1} vs {player2}"
                )
                continue

            cache[
                f"{player1}|{player2}"
            ] = ml

            matched += 1

        except Exception as exc:

            unmatched.append(
                f"{player1} vs {player2}: {exc}"
            )

    debug = {
        "events_from_api": len(events),
        "matches_requested": len(matches),
        "matched": matched,
        "unmatched": len(unmatched),
        "examples": unmatched[:20],
    }

    os.makedirs(
        "public",
        exist_ok=True,
    )

    with open(
        "public/odds_cache.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            cache,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with open(
        "public/odds_debug.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            debug,
            f,
            indent=2,
            ensure_ascii=False,
        )

    return cache


def get_odds(
    player1,
    player2,
):
    path = "public/odds_cache.json"

    if not os.path.exists(path):
        return None

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        cache = json.load(f)

    key = f"{player1}|{player2}"

    return cache.get(key)
