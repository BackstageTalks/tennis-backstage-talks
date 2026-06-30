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


def build_no_elo(match, surface, missing):
    return {
        "player1": match["player1"],
        "player2": match["player2"],
        "tournament": match.get("tournament"),
        "surface": surface,
        "pick": None,
        "probability": None,
        "odds": None,
        "model_source": "NO_STANDARD_ELO",
        "missing_elo_players": missing,
    }


def build_standard(match, pred):
    p1 = match["player1"]
    p2 = match["player2"]

    prob1 = pred["probability_player1"]
    prob2 = pred["probability_player2"]

    odds1 = safe_float(match.get("odds_player1"))
    odds2 = safe_float(match.get("odds_player2"))

    if prob1 >= prob2:
        pick = p1
        prob = prob1
        odds = odds1
    else:
        pick = p2
        prob = prob2
        odds = odds2

    return {
        "player1": p1,
        "player2": p2,
        "tournament": match.get("tournament"),
        "pick": pick,
        "probability": round(prob, 3),
        "odds": odds,
        "model_source": "TENNIS_ABSTRACT_ELO",
    }


def validate(predictions):
    total = len(predictions)
    with_elo = sum(
        1 for p in predictions if p["model_source"] == "TENNIS_ABSTRACT_ELO"
    )

    coverage = with_elo / total if total else 0

    print("\nDATA QUALITY:")
    print("TOTAL:", total)
    print("WITH ELO:", with_elo)
    print("COVERAGE:", round(coverage, 3))

    if total < 5:
        raise Exception("Too few matches")

    if with_elo < 3:
        raise Exception("Too few ELO matches")

    if coverage < 0.3:
        raise Exception("Low ELO coverage")


def normalize_match(m):
    if isinstance(m, dict):
        return m
    else:
        # fallback tuple
        return {
            "player1": m[0],
            "player2": m[1],
            "tournament": m[2] if len(m) > 2 else "Unknown",
            "odds_player1": None,
            "odds_player2": None,
        }


def build_all_predictions():
    raw_matches = get_today_matches()
    matches = [normalize_match(m) for m in raw_matches]

    players = list(
        set(
            [m["player1"] for m in matches] +
            [m["player2"] for m in matches]
        )
    )

    stats_map, surface_map = get_stats_context(players, matches)

    elo_data = load_tennis_abstract_elo()

    all_predictions = []
    missing_players_log = set()

    for match in matches:
        p1 = match["player1"]
        p2 = match["player2"]

        key = f"{p1}::{p2}"
        surface = surface_map.get(key, "hard")

        pred = predict_match_with_tennis_abstract(
            p1,
            p2,
            surface,
            elo_data
        )

        if not pred or not pred.get("available"):
            if pred:
                for x in pred.get("missing_players", []):
                    missing_players_log.add(x)

            all_predictions.append(
                build_no_elo(match, surface, pred.get("missing_players", []) if pred else [])
            )
            continue

        all_predictions.append(
            build_standard(match, pred)
        )

    print("\nMISSING ELO PLAYERS:")
    for p in list(missing_players_log)[:20]:
        print("-", p)

    all_predictions.sort(
        key=lambda x: x.get("probability") or 0,
        reverse=True
    )

    validate(all_predictions)

    return all_predictions


def get_daily_predictions():
    all_predictions = build_all_predictions()

    filtered = [
        p for p in all_predictions
        if p["model_source"] == "TENNIS_ABSTRACT_ELO"
        and p.get("odds") is not None
        and p["odds"] > MIN_ODDS
    ]

    return filtered[:TOP_N]
