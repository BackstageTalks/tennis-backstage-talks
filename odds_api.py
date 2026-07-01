import requests


API_KEY = "5e5f606542fb15d9717aacae39b757c2"

BASE_URL = "https://api.the-odds-api.com/v4/sports"

REGIONS = "eu"
MARKETS = "h2h"

SPORTS = [
    "tennis_atp",
    "tennis_wta",
]


def fetch_odds_for_sport(sport):
    url = f"{BASE_URL}/{sport}/odds/"

    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
    }

    try:
        response = requests.get(url, params=params, timeout=20)

        if response.status_code != 200:
            print("ODDS API ERROR:", sport, response.status_code)
            return []

        data = response.json()

        print(f"ODDS RAW {sport}: {len(data)}")

        return data

    except Exception as e:
        print("ODDS FETCH ERROR:", sport, e)
        return []


def extract_match_odds(event):
    try:
        home = event.get("home_team")
        away = event.get("away_team")

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return None

        bookmaker = bookmakers[0]
        markets = bookmaker.get("markets", [])
        if not markets:
            return None

        outcomes = markets[0].get("outcomes", [])
        if len(outcomes) < 2:
            return None

        odds_map = {
            outcomes[0]["name"]: outcomes[0]["price"],
            outcomes[1]["name"]: outcomes[1]["price"],
        }

        return {
            "player1": home,
            "player2": away,
            "odds_player1": odds_map.get(home),
            "odds_player2": odds_map.get(away),
            "bookmaker": bookmaker.get("title"),
            "event_id": event.get("id"),
            "odds_source": "the_odds_api",
        }

    except Exception:
        return None


def fetch_odds():
    all_matches = []

    for sport in SPORTS:
        events = fetch_odds_for_sport(sport)

        for event in events:
            record = extract_match_odds(event)
            if record:
                all_matches.append(record)

    print("TOTAL ODDS MATCHES:", len(all_matches))
    return all_matches


def normalize_name(name):
    return str(name or "").lower().replace("-", " ").strip()


def match_score(a, b):
    a = normalize_name(a)
    b = normalize_name(b)

    if not a or not b:
        return 0

    if a == b:
        return 1.0

    if a in b or b in a:
        return 0.75

    return 0


def find_match_odds(player1, player2, odds_matches):
    best = None
    best_score = 0

    for m in odds_matches:
        score1 = match_score(player1, m["player1"])
        score2 = match_score(player2, m["player2"])

        score = (score1 + score2) / 2

        if score > best_score:
            best = m
            best_score = score

        # reverse
        score1_rev = match_score(player1, m["player2"])
        score2_rev = match_score(player2, m["player1"])

        score_rev = (score1_rev + score2_rev) / 2

        if score_rev > best_score:
            best = {
                "player1": m["player1"],
                "player2": m["player2"],
                "odds_player1": m["odds_player2"],
                "odds_player2": m["odds_player1"],
                "bookmaker": m["bookmaker"],
                "event_id": m["event_id"],
