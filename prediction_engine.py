from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_source import load_tennis_abstract_elo, predict_match_with_tennis_abstract


TOP_N = 5
MIN_TOP_ODDS = 1.50


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def get_match_fields(match):
    if isinstance(match, dict):
        return {
            "player1": match["player1"],
            "player2": match["player2"],
            "tournament": match.get("tournament", "Tennis"),
            "odds_player1": match.get("odds_player1"),
            "odds_player2": match.get("odds_player2"),
            "odds_source": match.get("odds_source", "unknown"),
            "match_start": match.get("match_start"),
            "match_time_raw": match.get("match_time_raw"),
        }

    p1, p2, tournament = match

    return {
        "player1": p1,
        "player2": p2,
        "tournament": tournament,
        "odds_player1": None,
        "odds_player2": None,
        "odds_source": "missing",
        "match_start": None,
        "match_time_raw": None,
    }


def is_best_of_five(tournament):
    t = str(tournament or "").lower()

    if "wta" in t or "women" in t or "women's" in t:
        return False

    if "wimbledon" in t:
        return True

    if "grand slam" in t and ("atp" in t or "men" in t):
        return True

    return False


def build_sets_games_info(probability, bo_format):
    if probability is None:
        return {
            "most_likely_sets": None,
            "sets_probability": None,
            "sets_fair_odds": None,
            "expected_games": None,
            "games_lean": None,
            "note": "INFO ONLY - not used for winner selection"
        }

    p = clamp(probability, 0.05, 0.95)
    edge = abs(p - 0.5)

    if bo_format == "BO5":
        over_3_5 = clamp(0.76 - edge * 0.90, 0.34, 0.82)
        under_3_5 = 1 - over_3_5

        over_4_5 = clamp(0.45 - edge * 0.70, 0.15, 0.50)
        under_4_5 = 1 - over_4_5

        expected_games = round(clamp(39.5 - edge * 22.0, 29.0, 46.0), 1)

        if over_4_5 >= 0.43:
            most_likely_sets = "5 sets"
            sets_probability = over_4_5
        elif over_3_5 >= 0.55:
            most_likely_sets = "4+ sets"
            sets_probability = over_3_5
        else:
            most_likely_sets = "3 sets"
            sets_probability = under_3_5

        sets_fair_odds = round(1 / sets_probability, 2)

        if expected_games >= 39.0:
            games_lean = "Over 38.5"
        elif expected_games <= 36.5:
            games_lean = "Under 37.5"
        else:
            games_lean = "No clear games lean"

        return {
            "most_likely_sets": most_likely_sets,
            "sets_probability": round(sets_probability, 3),
            "sets_fair_odds": sets_fair_odds,
            "over_3_5_sets_probability": round(over_3_5, 3),
            "under_3_5_sets_probability": round(under_3_5, 3),
            "over_4_5_sets_probability": round(over_4_5, 3),
            "under_4_5_sets_probability": round(under_4_5, 3),
            "expected_games": expected_games,
            "games_lean": games_lean,
            "note": "INFO ONLY - not used for winner selection"
        }

    over_2_5 = clamp(0.62 - edge * 1.00, 0.32, 0.62)
    under_2_5 = 1 - over_2_5

    expected_games = round(clamp(23.0 - edge * 11.0, 18.0, 24.5), 1)

    if over_2_5 >= under_2_5:
        most_likely_sets = "3 sets"
        sets_probability = over_2_5
    else:
        most_likely_sets = "2 sets"
        sets_probability = under_2_5

    sets_fair_odds = round(1 / sets_probability, 2)

    if expected_games >= 22.2:
        games_lean = "Over 21.5"
    elif expected_games <= 20.8:
        games_lean = "Under 21.5"
    else:
        games_lean = "No clear games lean"

    return {
        "most_likely_sets": most_likely_sets,
        "sets_probability": round(sets_probability, 3),
        "sets_fair_odds": sets_fair_odds,
        "over_2_5_sets_probability": round(over_2_5, 3),
        "under_2_5_sets_probability": round(under_2_5, 3),
        "expected_games": expected_games,
        "games_lean": games_lean,
        "note": "INFO ONLY - not used for winner selection"
    }


def build_no_elo_prediction(m, surface):
    p1 = m["player1"]
    p2 = m["player2"]

    return {
        "player1": p1,
        "player2": p2,
        "tournament": m["tournament"],
        "surface": surface,

        "pick": None,
        "opponent": None,

        "probability": None,
        "opponent_probability": None,
        "confidence": None,

        "score": None,
        "winner_rank_score": None,

        "odds": None,
        "odds_player1": safe_float(m.get("odds_player1")),
        "odds_player2": safe_float(m.get("odds_player2")),
        "odds_source": m.get("odds_source"),

        "model_source": "NO_STANDARD_ELO_AVAILABLE",
        "model_version": "TENNIS_ABSTRACT_ELO_V1",

        "elo_player1": None,
        "elo_player2": None,
        "elo_type": None,

        "bet_tag": "NO STANDARD ELO AVAILABLE",
        "short_reason": "No Tennis Abstract Elo available for one or both players.",

        "ev_score": None,
        "ev_percent": None,
        "market_probability": None,
        "bookie_value_edge": None,
        "market_agrees": None,
        "bookie_signal": "NOT_USED",
        "market_warning": "NOT_USED",
        "overround": None,

        "match_start": m.get("match_start"),
        "match_time_raw": m.get("match_time_raw"),

        "alternative_market_info": build_sets_games_info(None, "BO3"),
        "extra_signals": [
            "No standard Elo prediction available",
            "WELO disabled"
        ],
        "alternative_bets": []
    }


def build_all_predictions():
    raw_matches = get_today_matches()

    if not raw_matches:
        print("NO REAL MATCHES FOUND")
        return []

    matches = [get_match_fields(m) for m in raw_matches]

    players = []

    for m in matches:
        if m["player1"] not in players:
            players.append(m["player1"])

        if m["player2"] not in players:
            players.append(m["player2"])

    stats_map, surface_map = get_stats_context(players, matches)

    elo_data = load_tennis_abstract_elo(force_refresh=False)

    all_predictions = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        tournament = m["tournament"]

        odds1 = safe_float(m.get("odds_player1"))
        odds2 = safe_float(m.get("odds_player2"))

        match_key = f"{p1}::{p2}"
        surface = surface_map.get(match_key, "Unknown")

        elo_prediction = predict_match_with_tennis_abstract(
            player1=p1,
            player2=p2,
            surface=surface,
            elo_data=elo_data
        )

        if not elo_prediction:
            all_predictions.append(build_no_elo_prediction(m, surface))
            continue

        prob1 = elo_prediction["probability_player1"]
        prob2 = elo_prediction["probability_player2"]

        if prob1 >= prob2:
            pick = p1
            opponent = p2
            pick_probability = prob1
            opponent_probability = prob2
            pick_odds = odds1
            pick_elo = elo_prediction["elo_player1"]
            opponent_elo = elo_prediction["elo_player2"]
            elo_type = elo_prediction["elo_type_player1"]
        else:
            pick = p2
            opponent = p1
            pick_probability = prob2
            opponent_probability = prob1
            pick_odds = odds2
            pick_elo = elo_prediction["elo_player2"]
            opponent_elo = elo_prediction["elo_player1"]
            elo_type = elo_prediction["elo_type_player2"]

        bo_format = "BO5" if is_best_of_five(tournament) else "BO3"

        alternative_market_info = build_sets_games_info(
            probability=pick_probability,
            bo_format=bo_format
        )

        pred = {
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "surface": surface,

            "pick": pick,
            "opponent": opponent,

            "probability": round(pick_probability, 3),
            "opponent_probability": round(opponent_probability, 3),
            "confidence": round(abs(pick_probability - 0.5), 3),

            "score": round(pick_probability, 3),
            "winner_rank_score": round(pick_probability, 3),

            "odds": pick_odds,
            "odds_player1": odds1,
            "odds_player2": odds2,
            "odds_source": m.get("odds_source"),

            "model_source": "TENNIS_ABSTRACT_ELO",
            "model_version": elo_prediction.get("model_version"),

            "elo_player": round(pick_elo, 1) if pick_elo is not None else None,
            "elo_opponent": round(opponent_elo, 1) if opponent_elo is not None else None,
            "elo_type": elo_type,

            "bet_tag": "STANDARD ELO PREDICTION",
            "short_reason": "Tennis Abstract Elo prediction. WELO disabled.",

            "ev_score": None,
            "ev_percent": None,
            "market_probability": None,
            "bookie_value_edge": None,
            "market_agrees": None,
            "bookie_signal": "NOT_USED",
            "market_warning": "NOT_USED",
            "overround": None,

            "match_start": m.get("match_start"),
            "match_time_raw": m.get("match_time_raw"),

            "alternative_market_info": alternative_market_info,

            "extra_signals": [
                "Tennis Abstract Elo winner prediction only",
                "WELO disabled",
                "No EV used",
                "No edge used",
                "No market consensus used",
                "Sets/games info is informational only"
            ],
            "alternative_bets": []
        }

        all_predictions.append(pred)

    all_predictions.sort(
        key=lambda x: (
            x.get("probability") is not None,
            x.get("probability") or 0
        ),
        reverse=True
    )

    return all_predictions


def get_daily_predictions():
    all_predictions = build_all_predictions()

    eligible = [
        p for p in all_predictions
        if p.get("model_source") == "TENNIS_ABSTRACT_ELO"
        and p.get("odds") is not None
        and float(p.get("odds")) > MIN_TOP_ODDS
        and p.get("probability") is not None
    ]

    eligible.sort(
        key=lambda x: x.get("probability", 0),
        reverse=True
    )

    final = eligible[:TOP_N]

    for p in final:
        p["bet_tag"] = "TOP5 STANDARD ELO PICK"
        p["short_reason"] = "Top 5 Tennis Abstract Elo pick with odds above 1.50. WELO disabled."

    print("FINAL TOP5 STANDARD ELO PICKS:", len(final))

    for p in final:
        alt = p.get("alternative_market_info", {})

        print(
            "PICK:",
            p["pick"],
            "to beat",
            p["opponent"],
            "| prob:",
            p["probability"],
            "| odds:",
            p["odds"],
            "| elo:",
            p.get("elo_player"),
            "vs",
            p.get("elo_opponent"),
            "| elo_type:",
            p.get("elo_type"),
            "| sets:",
            alt.get("most_likely_sets"),
            "| expected_games:",
            alt.get("expected_games")
        )

    return final
