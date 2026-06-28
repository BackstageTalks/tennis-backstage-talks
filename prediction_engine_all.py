from fetch_matches import get_today_matches
from welo import win_probability
from stats_engine import get_stats_context

from prediction_engine import (
    get_match_fields,
    metric_for_surface,
    classify_bookie_signal,
    classify_extra_signal,
    build_alternative_bets,
)


def get_all_daily_predictions():
    raw_matches = get_today_matches()

    if not raw_matches:
        print("NO REAL MATCHES FOUND FOR ALL")
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
        tournament = m.get("tournament", "")

        odds1 = m.get("odds_player1")
        odds2 = m.get("odds_player2")

        base_prob1 = win_probability(p1, p2)

        match_key = f"{p1}::{p2}"
        surface = surface_map.get(match_key, "Unknown")

        p1_stats = stats_map.get(p1, {})
        p2_stats = stats_map.get(p2, {})

        p1_metrics = metric_for_surface(p1_stats, surface)
        p2_metrics = metric_for_surface(p2_stats, surface)

        p1_win = p1_metrics.get("win_rate")
        p2_win = p2_metrics.get("win_rate")

        p1_set = p1_metrics.get("at_least_one_set_rate")
        p2_set = p2_metrics.get("at_least_one_set_rate")

        boost = 0

        if p1_win is not None and p2_win is not None:
            boost += (p1_win - p2_win) * 0.10

        if p1_set is not None and p2_set is not None:
            boost += (p1_set - p2_set) * 0.04

        boost = max(-0.08, min(0.08, boost))

        prob1 = max(0.05, min(0.95, base_prob1 + boost))
        prob2 = 1 - prob1

        if prob1 >= prob2:
            pick = p1
            opponent = p2
            pick_probability = prob1
            opponent_probability = prob2
            pick_metrics = p1_metrics
            opponent_metrics = p2_metrics
        else:
            pick = p2
            opponent = p1
            pick_probability = prob2
            opponent_probability = prob1
            pick_metrics = p2_metrics
            opponent_metrics = p1_metrics

        odds_info = classify_bookie_signal(
            pick=pick,
            p1=p1,
            p2=p2,
            model_prob=pick_probability,
            odds1=odds1,
            odds2=odds2,
        )

        pick_odds = odds_info["pick_odds"]
        implied_probability = round(1 / pick_odds, 3) if pick_odds else None

        extra_signals = classify_extra_signal(pick_metrics, opponent_metrics)
        alternative_bets = build_alternative_bets(pick, pick_metrics)

        confidence = abs(pick_probability - 0.5)

        all_predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "surface": surface,

            "pick": pick,
            "opponent": opponent,

            "probability": round(pick_probability, 3),
            "opponent_probability": round(opponent_probability, 3),
            "confidence": round(confidence, 3),

            "odds": pick_odds,
            "odds_player1": odds1,
            "odds_player2": odds2,
            "odds_source": m.get("odds_source"),
            "implied_probability": implied_probability,
            "market_probability": odds_info["market_probability"],
            "market_agrees": odds_info["market_agrees"],
            "bookie_value_edge": odds_info["bookie_value_edge"],
            "overround": odds_info["overround"],
            "bookie_signal": odds_info["bookie_signal"],

            "match_start": m.get("match_start"),
            "match_time_raw": m.get("match_time_raw"),

            "pick_stats": stats_map.get(pick, {}),
            "opponent_stats": stats_map.get(opponent, {}),
            "pick_metrics": pick_metrics,
            "opponent_metrics": opponent_metrics,
            "extra_signals": extra_signals,
            "alternative_bets": alternative_bets,
        })

    all_predictions.sort(
        key=lambda x: (
            str(x.get("match_start", "")),
            -float(x.get("probability", 0)),
        )
    )

    print("ALL PICKS:", len(all_predictions))

    for p in all_predictions:
        print(
            "ALL:",
            p["pick"],
            "vs",
            p["opponent"],
            "| time:",
            p.get("match_start"),
            "| prob:",
            p["probability"],
            "| odds:",
            p["odds"],
        )

    return all_predictions
