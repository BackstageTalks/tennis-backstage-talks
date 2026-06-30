import requests
import os


def fetch_odds():
    key = os.environ.get("ODDS_API_KEY")

    url = "https://api.the-odds-api.com/v4/sports/tennis_atp/odds/"
    params = {
        "apiKey": key,
        "regions": "eu",
        "markets": "h2h"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
    except:
        return []

    out = []

    for m in data:
        try:
            t = m["teams"]
            o = m["bookmakers"][0]["markets"][0]["outcomes"]

            out.append({
                "p1": t[0],
                "p2": t[1],
                "odds1": o[0]["price"],
                "odds2": o[1]["price"]
            })
        except:
            continue

    print("ODDS LOADED:", len(out))
    return out
``
