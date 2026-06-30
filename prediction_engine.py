from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_source import load_tennis_abstract_elo, predict_match_with_tennis_abstract

TOP_N = 5
MIN_ODDS = 1.50

def safe_float(x):
    try:
        return float(x)
    except:
        return None

def build_no_elo(m, surface, missing):
    return {
        "player1": m["player1"],
        "player2": m["player2"],
        "probability": None,
        "model_source": "NO_STANDARD_ELO",
        "missing_elo_players": missing,
    }

def build_standard(m, p):
    p1 = m["player1"]
    p2 = m["player2"]

    prob1 = p["probability_player1"]
    prob2 = p["probability_player2"]

    if prob1 >= prob2:
        pick = p1
        prob = prob1
        odds = safe_float(m["odds_player1"])
    else:
        pick = p2
        prob = prob2
        odds = safe_float(m["odds_player2"])

    return {
        "player1": p1,
        "player2": p2,
        "pick": pick,
        "probability": round(prob, 3),
        "odds": odds,
        "model_source": "TENNIS_ABSTRACT_ELO"
    }

def validate(all_preds):
    total = len(all_preds)
    good = sum(1 for p in all_preds if p["model_source"] == "TENNIS_ABSTRACT_ELO")

    coverage = good / total if total else 0
    print("ELO COVERAGE:", coverage)

    if total < 10 or good < 5 or coverage < 0.3:
        raise Exception("DATA QUALITY FAIL")

def build_all_predictions():
    raw = get_today_matches()
    matches = [m if isinstance(m, dict) else {
        "player1": m[0],
        "player2": m[1],
        "tournament": m[2]
    } for m in raw]

    players = list({m["player1"] for m in matches} | {m["player2"] for m in matches})

    stats_map, surface_map = get_stats_context(players, matches)

    elo = load_tennis_abstract_elo()

    all_preds = []
    missing_log = set()

    for m in matches:
        key = f"{m['player1']}::{m['player2']}"
        surface = surface_map.get(key, "hard")

        pred = predict_match_with_tennis_abstract(
            m["player1"],
            m["player2"],
            surface,
            elo
        )

        if not pred or not pred["available"]:
            for p in pred.get("missing_players", []):
                missing_log.add(p)

            all_preds.append(build_no_elo(m, surface, pred.get("missing_players", [])))
            continue

        all_preds.append(build_standard(m, pred))

    print("\nMISSING PLAYERS:")
    for p in list(missing_log)[:20]:
        print("-", p)

    all_preds.sort(key=lambda x: x.get("probability") or 0, reverse=True)

    validate(all_preds)

    return all_preds

def get_daily_predictions():
    all_preds = build_all_predictions()

    valid = [
        p for p in all_preds
        if p["model_source"] == "TENNIS_ABSTRACT_ELO"
        and p["odds"] is not None
        and p["odds"] > MIN_ODDS
    ]

    return valid[:TOP_N]
``
