from welo import win_probability

def get_daily_predictions():
    matches = [
        ("Djokovic", "Alcaraz", "Wimbledon"),
        ("Sinner", "Medvedev", "ATP Finals"),
        ("Zverev", "Rublev", "ATP 500"),
        ("Rune", "Tsitsipas", "ATP 250"),
        ("Ruud", "Hurkacz", "ATP 250"),
        ("Fritz", "Paul", "ATP 500")
    ]

    predictions = []

    for p1, p2, tournament in matches:
        prob1 = win_probability(p1, p2)
        prob2 = 1 - prob1

        confidence = abs(prob1 - 0.5)
        value1 = prob1 - 0.5

        # 🔥 SMART SCORE
        score = (prob1 * 0.6) + (confidence * 0.4)

        predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "probability_player1": round(prob1, 3),
            "probability_player2": round(prob2, 3),
            "confidence": round(confidence, 3),
            "value_player1": {"value": round(value1, 3)},
            "score": round(score, 3)
        })

    # ✅ zoradenie podľa kvality
    predictions = sorted(predictions, key=lambda x: x["score"], reverse=True)

    # ✅ 1. DAILY PICKS (vždy 4)
    daily_picks = predictions[:4]

    # ✅ 2. ELITE PICKS (len top kvalita)
    elite_picks = [
        p for p in predictions
        if p["probability_player1"] > 0.60
        and p["confidence"] > 0.10
    ]

    elite_picks = elite_picks[:2]  # max 2 top picky

    # ✅ spojenie (elite budú navrchu)
    final = elite_picks + [p for p in daily_picks if p not in elite_picks]

    return final
