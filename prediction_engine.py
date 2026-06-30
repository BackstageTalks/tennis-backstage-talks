from fetch_matches import get_today_matches
from welo import win_probability
from stats_engine import get_stats_context


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


def metric_for_surface(player_stats, surface):
    """
    Použité iba ako malé ELO+ upresnenie.
    Žiadne odds, EV, edge ani market consensus.
    """
    if not player_stats:
        return {}

    surface_stats = player_stats.get("surface", {})

    if surface and surface != "Unknown":
        s = surface_stats.get(surface)

        if s and s.get("sample", 0) >= 3:
            return s

    last10 = player_stats.get("last10", {})

    if last10 and last10.get("sample", 0) >= 3:
        return last10

    return player_stats.get("career", {})


def elo_plus_adjustment(player_metrics, opponent_metrics):
    """
    Malé ELO+ upresnenie podľa formy/povrchu.
    Max ±4 %.
    Nepoužíva odds, EV ani market.
    """
    adjustment = 0.0

    player_win = player_metrics.get("win_rate")
    opponent_win = opponent_metrics.get("win_rate")

    player_sample = player_metrics.get("sample", 0) or 0
    opponent_sample = opponent_metrics.get("sample", 0) or 0

    if (
        player_win is not None
        and opponent_win is not None
        and player_sample >= 4
        and opponent_sample >= 4
    ):
        adjustment += (player_win - opponent_win) * 0.05

    player_set = player_metrics.get("at_least_one_set_rate")
    opponent_set = opponent_metrics.get("at_least_one_set_rate")

    if (
        player_set is not None
        and opponent_set is not None
        and player_sample >= 5
        and opponent_sample >= 5
    ):
        adjustment += (player_set - opponent_set) * 0.015

    return clamp(adjustment, -0.04, 0.04)


def is_best_of_five(tournament):
    """
    Jednoduchý BO5 odhad.
    Wimbledon / Grand Slam ATP muži = BO5.
    WTA / women = BO3.
    Ostatné = BO3.
    """
    t = str(tournament or "").lower()

    if "wta" in t or "women" in t or "women's" in t:
        return False

    if "wimbledon" in t:
        return True

    if "grand slam" in t and ("atp" in t or "men" in t):
        return True

    return False


def build_sets_games_info(probability, bo_format):
    """
    Doplnkové info.
    Nepoužíva sa:
    - na výber víťaza
    - na TOP poradie
    - na filter kurzov
    """
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
            "bo_format": "BO5",
            "most_likely_sets": most_likely_sets,
            "sets_probability": round(sets_probability, 3),
            "sets_fair_odds": sets_fair_odds,
            "over_2_5_sets_probability": None,
            "under_2_5_sets_probability": None,
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
        "bo_format": "BO3",
        "most_likely_sets": most_likely_sets,
        "sets_probability": round(sets_probability, 3),
        "sets_fair_odds": sets_fair_odds,
        "over_2_5_sets_probability": round(over_2_5, 3),
        "under_2_5_sets_probability": round(under_2_5, 3),
        "over_3_5_sets_probability": None,
        "under_3_5_sets_probability": None,
        "over_4_5_sets_probability": None,
        "under_4_5_sets_probability": None,
        "expected_games": expected_games,
        "games_lean": games_lean,
        "note": "INFO ONLY - not used for winner selection"
    }


def build_reason(probability, odds, model_source, elo_adjustment):
    parts = []

    parts.append(f"Model: {model_source}")

    if probability >= 0.70:
        parts.append("very strong ELO+ win probability")
    elif probability >= 0.65:
        parts.append("strong ELO+ win probability")
    elif probability >= 0.60:
        parts.append("good ELO+ win probability")
    elif probability >= 0.55:
        parts.append("moderate ELO+ win probability")
    else:
        parts.append("low ELO+ edge")

    if odds is None:
        parts.append("no odds available")
    elif odds > MIN_TOP_ODDS:
        parts.append("odds above 1.50 requirement")
    else:
        parts.append("odds <= 1.50, excluded from TOP5")

    if elo_adjustment != 0:
        parts.append(f"ELO+ stats adjustment {elo_adjustment:+.3f}")

    return "; ".join(parts)


def build_tag(is_top_candidate, odds):
    if is_top_candidate:
        return "⭐ TOP5 ELO+ PICK"

    if odds is None:
        return "ALL ELO+ PREDICTION / NO ODDS"

    if odds <= MIN_TOP_ODDS:
        return "ALL ELO+ PREDICTION / ODDS TOO LOW"

    return "ALL ELO+ PREDICTION"


def build_all_predictions():
    """
    ALL:
    - každý zápas dostane ELO+ predikciu víťaza
    - nič sa nefiltruje
    """
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

    all_predictions = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        tournament = m["tournament"]

        odds1 = safe_float(m.get("odds_player1"))
        odds2 = safe_float(m.get("odds_player2"))

        base_prob1 = clamp(win_probability(p1, p2), 0.05, 0.95)

        match_key = f"{p1}::{p2}"
        surface = surface_map.get(match_key, "Unknown")

        p1_stats = stats_map.get(p1, {})
        p2_stats = stats_map.get(p2, {})

        p1_metrics = metric_for_surface(p1_stats, surface)
        p2_metrics = metric_for_surface(p2_stats, surface)

        p1_adjustment = elo_plus_adjustment(p1_metrics, p2_metrics)
        adjusted_prob1 = clamp(base_prob1 + p1_adjustment, 0.05, 0.95)
        adjusted_prob2 = 1 - adjusted_prob1

        if adjusted_prob1 >= adjusted_prob2:
            pick = p1
            opponent = p2
            pick_probability = adjusted_prob1
            opponent_probability = adjusted_prob2
            pick_odds = odds1
            pick_metrics = p1_metrics
            opponent_metrics = p2_metrics
            base_pick_probability = base_prob1
            applied_adjustment = p1_adjustment
        else:
            pick = p2
            opponent = p1
            pick_probability = adjusted_prob2
            opponent_probability = adjusted_prob1
            pick_odds = odds2
            pick_metrics = p2_metrics
            opponent_metrics = p1_metrics
            base_pick_probability = 1 - base_prob1
            applied_adjustment = -p1_adjustment

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

            "model_source": "ELO_PLUS",
            "base_elo_probability": round(base_pick_probability, 3),
            "elo_stats_adjustment": round(applied_adjustment, 3),

            "bet_tag": "ALL ELO+ PREDICTION",
            "short_reason": "",
            "win_tier": "",
            "model_flags": [],

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

            "pick_stats": stats_map.get(pick, {}),
            "opponent_stats": stats_map.get(opponent, {}),
            "pick_metrics": pick_metrics,
            "opponent_metrics": opponent_metrics,

            "alternative_market_info": alternative_market_info,

            "extra_signals": [
                "ELO+ winner prediction only",
                "No EV used",
                "No edge used",
                "No market consensus used",
                "Sets/games info is informational only"
            ],
            "alternative_bets": []
        }

        all_predictions.append(pred)

    all_predictions.sort(
        key=lambda x: x.get("probability", 0),
        reverse=True
    )

    return all_predictions


def get_daily_predictions():
    """
    TOP:
    - 5 najlepších ELO+ predikcií
    - kurz na vybraného hráča musí byť > 1.50
    - výber podľa najvyššej pravdepodobnosti uhádnutia víťaza
    """
    all_predictions = build_all_predictions()

    eligible = [
        p for p in all_predictions
        if p.get("odds") is not None
        and float(p.get("odds")) > MIN_TOP_ODDS
    ]

    eligible.sort(
        key=lambda x: x.get("probability", 0),
        reverse=True
    )

    final = eligible[:TOP_N]

    for p in all_predictions:
        is_top = p in final
        odds = p.get("odds")

        p["bet_tag"] = build_tag(
            is_top_candidate=is_top,
            odds=odds
        )

        p["short_reason"] = build_reason(
            probability=p.get("probability", 0),
            odds=odds,
            model_source=p.get("model_source"),
            elo_adjustment=p.get("elo_stats_adjustment", 0)
        )

    for p in final:
        p["bet_tag"] = "⭐ TOP5 ELO+ PICK"

        p["short_reason"] = build_reason(
            probability=p.get("probability", 0),
            odds=p.get("odds"),
            model_source=p.get("model_source"),
            elo_adjustment=p.get("elo_stats_adjustment", 0)
        )

    print("FINAL TOP5 ELO+ PICKS:", len(final))

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
            "| base_elo:",
            p.get("base_elo_probability"),
            "| adj:",
            p.get("elo_stats_adjustment"),
            "| sets:",
            alt.get("most_likely_sets"),
            "| expected_games:",
            alt.get("expected_games"),
            "| games_lean:",
            alt.get("games_lean"),
            "| reason:",
            p["short_reason"]
        )

    return final
