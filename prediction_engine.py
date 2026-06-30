from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_engine import load, predict
from odds_api import fetch_odds

TOP_N = 5
MIN_ODDS = 1.50


def normalize(name):
    return name.lower().strip()


def last(name):
    return normalize(name).split()[-1]


def match_players(a1, a2, b1, b2):
    return (
        (last(a1) == last(b1) and last(a2) == last(b2)) or
        (last(a1) == last(b2) and last(a2) == last(b1))
    )


def find_odds(p1, p2, odds_matches):
    for m in odds_matches:
        if match_players(p1, p2, m["p1"], m["p2"]):
            return m
    return None


def normalize_match(m):
    return {
        "player1": m.get("player1") or m[0],
        "player2": m.get("player2") or m[1],
        "match_time": m.get("time") or m.get("start_time") or "TBD"
    }


def build_all_predictions():
    raw = get_today_matches()
    matches = [normalize_match(x) for x in raw]

    odds_matches = fetch_odds()

    players = list(set([m["player1"] for m in matches] +
                       [m["player2"] for m in matches]))

    stats_map, surface_map = get_stats_context(players, matches)
    elo_store = load()

    all_preds = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        time = m["match_time"]

        pred = predict(p1, p2, "hard", elo_store)

        prob1 = pred["probability_player1"]
        prob2 = pred["probability_player2"]

        odds_data = find_odds(p1, p2, odds_matches)

        odds1 = odds2 = None
        if odds_data:
            odds1 = odds_data["odds1"]
            odds2 = odds_data["odds2"]

        if prob1 >= prob2:
            pick = p1
            prob = prob1
            odds = odds1
        else:
            pick = p2
            prob = prob2
            odds = odds2

        all_preds.append({
            "player1": p1,
            "player2": p2,
            "pick": pick,
            "probability": round(prob, 3),
            "odds": odds,
            "time": time
        })

    all_preds.sort(key=lambda x: x["probability"], reverse=True)

    print("TOTAL MATCHES:", len(all_preds))

    return all_preds


def get_top_predictions(all_preds):
    valid = [
        p for p in all_preds
        if p["odds"] is not None and p["odds"] >= MIN_ODDS
    ]

    print("VALID ODDS:", len(valid))

    return valid[:TOP_N]
