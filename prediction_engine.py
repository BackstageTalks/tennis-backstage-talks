from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_engine import load, predict
from odds_api import fetch_odds

TOP_N = 5
MIN_ODDS = 1.50


def normalize(name):
    return name.lower().strip()


def name_variants(name):
    parts = normalize(name).split()

    variants = set()
    variants.add(parts[-1])

    if len(parts) > 1:
        variants.add(parts[0])
        variants.add(parts[0] + " " + parts[-1])

    variants.add(" ".join(parts))

    return variants


def find_odds(p1, p2, odds_map):
    v1 = name_variants(p1)
    v2 = name_variants(p2)

    for k in odds_map:
        if any(x in k for x in v1) and any(x in k for x in v2):
            return odds_map[k]

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

    odds_map = fetch_odds()

    players = list(set([m["player1"] for m in matches] +
                       [m["player2"] for m in matches]))

    stats_map, surface_map = get_stats_context(players, matches)
    elo_store = load()

    all_preds = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        match_time = m["match_time"]

        surface = surface_map.get(p1 + "::" + p2, "hard")

        pred = predict(p1, p2, surface, elo_store)

        prob1 = pred["probability_player1"]
        prob2 = pred["probability_player2"]

        match_odds = find_odds(p1, p2, odds_map)

        odds1 = None
        odds2 = None

        if match_odds:
            odds1, odds2 = match_odds

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
            "time": match_time
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
