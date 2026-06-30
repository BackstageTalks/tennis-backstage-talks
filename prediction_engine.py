from fetch_matches import get_today_matches
from elo_engine import load, predict
from odds_api import fetch_odds

TOP_N = 5
MIN_ODDS = 1.50


def norm(name):
    return name.lower().strip().split()[-1]


def match(p1, p2, o1, o2):
    return (
        (norm(p1) == norm(o1) and norm(p2) == norm(o2)) or
        (norm(p1) == norm(o2) and norm(p2) == norm(o1))
    )


def find_odds(p1, p2, odds):
    for m in odds:
        if match(p1, p2, m["p1"], m["p2"]):
            return m
    return None


def build_all_predictions():
    matches = get_today_matches()
    odds = fetch_odds()
    elo = load()

    out = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        t = m.get("time", "")

        pred = predict(p1, p2, "hard", elo)

        o = find_odds(p1, p2, odds)

        odds1 = o["odds1"] if o else None
        odds2 = o["odds2"] if o else None

        if pred["probability_player1"] >= pred["probability_player2"]:
            pick = p1
            prob = pred["probability_player1"]
            od = odds1
        else:
            pick = p2
            prob = pred["probability_player2"]
            od = odds2

        out.append({
            "player1": p1,
            "player2": p2,
            "pick": pick,
            "probability": round(prob, 3),
            "odds": od,
            "time": t
        })

    return sorted(out, key=lambda x: x["probability"], reverse=True)


def get_top_predictions(all_preds):
    valid = [
        x for x in all_preds
        if x["odds"] and x["odds"] >= MIN_ODDS
    ]

    return valid[:TOP_N]
