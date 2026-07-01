import os
import requests
import unicodedata
import re


SPORT_KEYS = [
    "tennis_atp",
    "tennis_wta",
]

REGIONS = "eu"
MARKETS = "h2h"
ODDS_FORMAT = "decimal"


def normalize_name(name):
    if not name:
        return ""

    text = str(name)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def token_set(name):
    return set(normalize_name(name).split())


def last_token(name):
    parts = normalize_name(name).split()
    if not parts:
        return ""
    return parts[-1]


def player_similarity(a, b):
    a_tokens = token_set(a)
    b_tokens = token_set(b)

    if not a_tokens or not b_tokens:
        return 0.0

    overlap = len(a_tokens.intersection(b_tokens))
    total = max(len(a_tokens), len(b_tokens))

    score = overlap / total

    if last_token(a) and last_token(a) == last_token(b):
        score += 0.35

    return min(score, 1.0)


def fetch_one_sport(api_key, sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"

    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
    }

    try:
        response = requests.get(url, params=params, timeout=20)

        if response.status_code != 200:
            print("ODDS API ERROR:", sport_key, response.status_code, response.text[:200])
            return []

        data = response.json()

    except Exception as e:
        print("ODDS FETCH ERROR:", sport_key, e)
        return []

    odds_matches = []

    for match in data:
        try:
            bookmakers = match.get("bookmakers", [])
            if not bookmakers:
                continue

            for bookmaker in bookmakers:
                markets = bookmaker.get("markets", [])

                for market in markets:
                    if market.get("key") != "h2h":
                        continue

                    outcomes = market.get("outcomes", [])

                    if len(outcomes) < 2:
                        continue

                    parsed_outcomes = []

                    for outcome in outcomes:
                        name = outcome.get("name")
                        price = outcome.get("price")

                        if not name or price is None:
                            continue

                        parsed_outcomes.append({
                            "name": name,
                            "normalized_name": normalize_name(name),
                            "price": float(price),
                        })

                    if len(parsed_outcomes) >= 2:
                        odds_matches.append({
                            "sport_key": sport_key,
                            "commence_time": match.get("commence_time"),
                            "home_team": match.get("home_team"),
                            "away_team": match.get("away_team"),
                            "bookmaker": bookmaker.get("key"),
                            "outcomes": parsed_outcomes,
                        })

                    break

                if odds_matches:
                    break

        except Exception:
            continue

    return odds_matches


def fetch_odds():
    api_key = os.environ.get("ODDS_API_KEY")

    if not api_key:
        print("NO API KEY")
        return []

    all_odds = []

    for sport_key in SPORT_KEYS:
        sport_odds = fetch_one_sport(api_key, sport_key)
        print("ODDS LOADED", sport_key, len(sport_odds))
        all_odds.extend(sport_odds)

    print("ODDS LOADED TOTAL:", len(all_odds))

    return all_odds


def find_player_price(player_name, outcomes):
    best_price = None
    best_score = 0.0

    for outcome in outcomes:
        score = player_similarity(player_name, outcome.get("name"))

        if score > best_score:
            best_score = score
            best_price = outcome.get("price")

    if best_score >= 0.55:
        return best_price

    return None


def find_match_odds(player1, player2, odds_matches):
    best_match = None
    best_score = 0.0

    for odds_match in odds_matches:
        outcomes = odds_match.get("outcomes", [])

        if len(outcomes) < 2:
            continue

        p1_best = 0.0
        p2_best = 0.0

        for outcome in outcomes:
            p1_best = max(p1_best, player_similarity(player1, outcome.get("name")))
            p2_best = max(p2_best, player_similarity(player2, outcome.get("name")))

        score = min(p1_best, p2_best)

        if score > best_score:
            best_score = score
            best_match = odds_match

    if best_match and best_score >= 0.55:
        odds1 = find_player_price(player1, best_match.get("outcomes", []))
        odds2 = find_player_price(player2, best_match.get("outcomes", []))

        return {
            "odds_player1": odds1,
            "odds_player2": odds2,
            "odds_source": best_match.get("bookmaker"),
            "odds_sport_key": best_match.get("sport_key"),
            "odds_commence_time": best_match.get("commence_time"),
            "match_score": round(best_score, 3),
        }

    return {
        "odds_player1": None,
        "odds_player2": None,
        "odds_source": None,
        "odds_sport_key": None,
        "odds_commence_time": None,
        "match_score": 0,
    }
