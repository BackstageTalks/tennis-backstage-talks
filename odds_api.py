import requests
import os


def normalize(name):
    return name.lower().strip()


def key(p1, p2):
    return normalize(p1) + "::" + normalize(p2)


def fetch_odds():
    API_KEY = os.environ.get("ODDS_API_KEY")

    if not API_KEY:
        print("NO API KEY ❌")
        return {}

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
            return {}

        data = r.json()

    except Exception as e:
        print("ODDS FETCH FAIL:", e)
        return {}

    odds_map = {}

    for match in data:
        try:
            teams = match.get("teams", [])
            if len(teams) != 2:
                continue

            p1 = teams[0]
            p2 = teams[1]

            bookmakers = match.get("bookmakers", [])

            # vezmeme prvý bookmaker (stačí)
            for b in bookmakers:
                markets = b.get("markets", [])

                for m in markets:
                    if m.get("key") == "h2h":
                        outcomes = m.get("outcomes", [])

                        if len(outcomes) >= 2:
                            odds1 = outcomes[0]["price"]
                            odds2 = outcomes[1]["price"]

                            odds_map[key(p1, p2)] = (odds1, odds2)

                        break
                break

        except:
            continue

    print("ODDS LOADED:", len(odds_map))

    return odds_map
