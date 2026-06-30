from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_engine import load, predict

TOP_N = 5
MIN_ODDS = 1.50


def safe_float(x):
    try:
        return float(x)
    except:
        return None


def normalize_match(m):
    if isinstance(m, dict):
        return m

    return {
        "player1": m[0],
        "player2": m[1],
        "tournament": m[2] if len(m) > 2 else "Unknown",
        "odds_player1": None,
        "odds_player2": None
    }


def build_all_predictions():
    raw = get_today_matches()
    matches = [normalize_match(x) for x in raw]

    players = list(set([m["player1"] for m in matches] +
                       [m["player2"] for m in matches]))

    stats_map, surface_map = get_stats_context(players, matches)

    elo_store = load()

    all_preds = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]

        key = f"{p1}::{p2}"
        surface = surface_map.get(key, "hard")

        pred = predict(p1, p2, surface, elo_store)

        prob1 = pred["probability_player1"]
        prob2 = pred["probability_player2"]

        odds1 = safe_float(m.get("odds_player1"))
        odds2 = safe_float(m.get("odds_player2"))

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
            "odds": odds
        })

    all_preds.sort(key=lambda x: x["probability"], reverse=True)

    print("TOTAL MATCHES:", len(all_preds))

    return all_preds


def get_top_predictions():
    all_preds = build_all_predictions()

    filtered = [
        p for p in all_preds
        if p["odds"] is not None and p["odds"] > MIN_ODDS
    ]

    top = filtered[:TOP_N]

    print("TOP COUNT:", len(top))

    return top
