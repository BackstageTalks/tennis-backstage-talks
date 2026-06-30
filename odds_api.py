import requests
import os


def normalize(name):
    return name.lower().strip()


def last(name):
    return normalize(name).split()[-1]


def fetch_odds():
    API_KEY = os.environ.get("ODDS_API_KEY")

    if not API_KEY:
        print("NO API KEY ❌")
        return []

    url = "https://api.the-odds-api.com/v4/sports/tennis_atp/odds/"

    params = {
        "apiKey": API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    try:
        r = requests.get(url, params=params, timeout=15)

        if r.status_code != 200:
            print("ODDS API ERROR:", r.status_code)
            return []

        data = r.json()

    except Exception as e:
        print("ODDS FETCH FAIL:", e)
        return []

    matches = []

    for m in data:
        try:
            teams = m.get("teams", [])
            if len(teams) != 2:
                continue

            p1 = teams[0]
            p2 = teams[1]

            bookmakers = m.get("bookmakers", [])

            for b in bookmakers:
                for market in b.get("markets", []):
                    if market.get("key") == "h2h":
                        outcomes = market.get("outcomes", [])
                        if len(outcomes) >= 2:
                            matches.append({
                                "p1": p1,
                                "p2": p2,
                                "odds1": outcomes[0]["price"],
                                "odds2": outcomes[1]["price"]
                            })
                        break
                break

        except:
            continue

    print("ODDS LOADED:", len(matches))

    return matches
``
