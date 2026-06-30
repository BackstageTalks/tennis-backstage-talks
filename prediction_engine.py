from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_source import load_tennis_abstract_elo, predict_match_with_tennis_abstract

TOP_N = 5
MIN_TOP_ODDS = 1.50


def safe_float(x):
    try:
        return float(x)
    except:
        return None


def is_main_tour(tournament):
    t = str(tournament).lower()

    if "atp" in t or "wta" in t:
        return True

    if "wimbledon" in t or "grand slam" in t:
        return True

    return False


def get_match_fields(m):
    if isinstance(m, dict):
        return {
            "player1": m["player1"],
            "player2": m["player2"],
            "tournament": m.get("tournament", ""),
            "odds_player1": m.get("odds_player1"),
            "odds_player2": m.get("odds_player2"),
        }

    p1, p2, t = m

    return {
        "player1": p1,
        "player2": p2,
        "tournament": t,
        "odds_player1": None,
        "odds_player2": None,
    }


def build_all_predictions():
    raw_matches = get_today_matches()

    if not raw_matches:
        print("NO MATCHES")
        return []

    matches = [get_match_fields(m) for m in raw_matches]

    # filter ATP/WTA
    matches = [m for m in matches if is_main_tour(m["tournament"])]

    players = list({
        p for m in matches for p in [m["player1"], m["player2"]]
    })

    stats_map, surface_map = get_stats_context(players, matches)

    elo_data = load_tennis_abstract_elo()

    output = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]

        surface = surface_map.get(f"{p1}::{p2}", "Unknown")

        elo = predict_match_with_tennis_abstract(
            p1, p2, surface, elo_data
        )

        # skip without ELO
        if not elo or not elo.get("available"):
            continue

        prob1 = elo["probability_player1"]
        prob2 = elo["probability_player2"]

        odds1 = safe_float(m["odds_player1"])
        odds2 = safe_float(m["odds_player2"])

        if prob1 >= prob2:
            pick = p1
            opponent = p2
            prob = prob1
            odds = odds1
        else:
            pick = p2
            opponent = p1
            prob = prob2
            odds = odds2

        output.append({
            "player1": p1,
            "player2": p2,
            "pick": pick,
            "opponent": opponent,
            "probability": round(prob, 3),
            "odds": odds,
            "model_source": "TENNIS_ABSTRACT_ELO"
        })

    output.sort(key=lambda x: x["probability"], reverse=True)

    print("TOTAL MATCHES WITH ELO:", len(output))

    return output


def get_daily_predictions():
    all_predictions = build_all_predictions()

    eligible = [
        p for p in all_predictions
        if p["odds"] is not None
        and safe_float(p["odds"]) is not None
        and safe_float(p["odds"]) > MIN_TOP_ODDS
    ]

    eligible.sort(key=lambda x: x["probability"], reverse=True)

    top = eligible[:TOP_N]

    print("TOP PICKS:", len(top))

    for p in top:
        print(
            p["pick"],
            "vs",
            p["opponent"],
            "| prob:",
            p["probability"],
            "| odds:",
            p["odds"]
        )

    return top
