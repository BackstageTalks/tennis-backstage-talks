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
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return []
        return r.json()
    except Exception:
        return []


def extract_match_odds(event):
    try:
        home = event.get("home_team")
        away = event.get("away_team")

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return None

        best_odds1 = None
        best_odds2 = None

        for book in bookmakers:
            markets = book.get("markets", [])
            if not markets:
                continue

            outcomes = markets[0].get("outcomes", [])
            if len(outcomes) < 2:
                continue

            o1 = outcomes[0]["price"]
            o2 = outcomes[1]["price"]

            if best_odds1 is None or o1 > best_odds1:
                best_odds1 = o1

            if best_odds2 is None or o2 > best_odds2:
                best_odds2 = o2

        if best_odds1 is None or best_odds2 is None:
            return None

        return {
            "player1": home,
            "player2": away,
            "odds_player1": best_odds1,
            "odds_player2": best_odds2,
            "event_id": event.get("id"),
            "odds_source": "the_odds_api"
        }

    except Exception:
        return None


def fetch_odds():
    all_matches = []

    for sport in SPORTS:
        events = fetch_odds_for_sport(sport)

        for e in events:
            rec = extract_match_odds(e)
            if rec:
                all_matches.append(rec)

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

        s1 = match_score(player1, m["player1"])
        s2 = match_score(player2, m["player2"])

        score = (s1 + s2) / 2

        if score > best_score:
            best = m
            best_score = score

        # reverse
        sr1 = match_score(player1, m["player2"])
        sr2 = match_score(player2, m["player1"])

        score_r = (sr1 + sr2) / 2

        if score_r > best_score:
            best = {
                "player1": m["player1"],
                "player2": m["player2"],
                "odds_player1": m["odds_player2"],
                "odds_player2": m["odds_player1"],
                "event_id": m["event_id"],
                "odds_source": m["odds_source"]
            }
            best_score = score_r

    return best if best else {}
