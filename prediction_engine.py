from fetch_matches import get_today_matches
from welo import win_probability
from stats_engine import get_stats_for_players


def classify_extra_signal(pick_stats, opponent_stats):
    signals = []

    avg_aces = pick_stats.get("avg_aces")
    ace_sample = pick_stats.get("aces_sample", 0)

    opp_avg_aces = opponent_stats.get("avg_aces")

    set_rate = pick_stats.get("at_least_one_set_rate")
    set_sample = pick_stats.get("matches_with_score", 0)

    if (
        avg_aces is not None
        and ace_sample >= 10
        and avg_aces >= 5
    ):
        signals.append("💣 High ace potential")

    if (
        avg_aces is not None
        and opp_avg_aces is not None
        and ace_sample >= 10
        and avg_aces - opp_avg_aces >= 1.5
    ):
        signals.append("💣 Ace edge vs opponent")

    if (
        set_rate is not None
        and set_sample >= 10
        and set_rate >= 0.75
    ):
        signals.append("🎯 Strong set safety")

    elif (
        set_rate is not None
        and set_sample >= 10
        and set_rate >= 0.60
    ):
        signals.append("✅ Medium set safety")

    if not signals:
        signals.append("Model winner pick only")

    return signals


def get_daily_predictions():
    matches = get_today_matches()

    if not matches:
        print("NO REAL MATCHES FOUND")
        return []

    players = []

    for p1, p2, tournament in matches:
        if p1 not in players:
            players.append(p1)
        if p2 not in players:
            players.append(p2)

    stats_map = get_stats_for_players(players)

    predictions = []

    for p1, p2, tournament in matches:
        prob1 = win_probability(p1, p2)
        prob2 = 1 - prob1

        if prob1 >= prob2:
            pick = p1
            opponent = p2
            pick_probability = prob1
            opponent_probability = prob2
        else:
            pick = p2
            opponent = p1
            pick_probability = prob2
            opponent_probability = prob1

        confidence = abs(pick_probability - 0.5)

        odds = 1.90
        implied = 1 / odds
        value = pick_probability - implied

        if pick_probability < 0.52:
            continue

        pick_stats = stats_map.get(pick, {})
        opponent_stats = stats_map.get(opponent, {})

        extra_signals = classify_extra_signal(pick_stats, opponent_stats)

        score = (pick_probability * 0.75) + (confidence * 0.10)

        if "🎯 Strong set safety" in extra_signals:
            score += 0.06

        if "✅ Medium set safety" in extra_signals:
            score += 0.03

        if "💣 Ace edge vs opponent" in extra_signals:
            score += 0.04

        if "💣 High ace potential" in extra_signals:
            score += 0.02

        predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": tournament,

            "pick": pick,
            "opponent": opponent,

            "probability": round(pick_probability, 3),
            "opponent_probability": round(opponent_probability, 3),
            "odds": odds,
            "value": round(value, 3),
            "confidence": round(confidence, 3),
            "score": round(score, 3),

            "pick_stats": pick_stats,
            "opponent_stats": opponent_stats,
            "extra_signals": extra_signals
        })

    predictions.sort(key=lambda x: x["score"], reverse=True)

    final = predictions[:4]

    print("FINAL PICKS:", len(final))
    for p in final:
        print(
            "PICK:",
            p["pick"],
            "to beat",
            p["opponent"],
            "| prob:",
            p["probability"],
            "| signals:",
            p["extra_signals"]
        )

    return final
