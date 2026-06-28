from welo import win_probability

# ✅ SIMULOVANÉ BOOKMAKER ODDS (neskôr nahradíš API)
ODDS = {
    ("Djokovic", "Alcaraz"): (1.70, 2.10),
    ("Sinner", "Medvedev"): (1.85, 1.95),
    ("Zverev", "Rublev"): (1.80, 2.00),
    ("Rune", "Tsitsipas"): (2.00, 1.80),
    ("Ruud", "Hurkacz"): (1.75, 2.05),
    ("Fritz", "Paul"): (1.65, 2.20)
}


def get_odds(p1, p2):
    return ODDS.get((p1, p2), (1.90, 1.90))


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

        odds1, odds2 = get_odds(p1, p2)

        implied1 = 1 / odds1

        # 🔥 VALUE (kľúč)
        value = prob1 - implied1

        confidence = abs(prob1 - 0.5)

        # 🔥 SCORE (kombinácia stability + value)
        score = (prob1 * 0.6) + (confidence * 0.2) + (value * 0.2)

        predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "probability_player1": round(prob1, 3),
            "probability_player2": round(prob2, 3),
            "odds_player1": odds1,
            "implied_probability": round(implied1, 3),
            "value": round(value, 3),
            "confidence": round(confidence, 3),
            "score": round(score, 3)
        })

    # ✅ zoradiť podľa kvality
    predictions = sorted(predictions, key=lambda x: x["score"], reverse=True)

    # ✅ DAILY PICKS (vždy 4)
    daily = predictions[:4]

    # ✅ ELITE PICKS (len pozitívny value + vysoká pravdepodobnosť)
    elite = [
        p for p in predictions
        if p["value"] > 0.03 and p["probability_player1"] > 0.60
    ]
    elite = elite[:2]

    # ✅ spojenie (elite hore)
    final = elite + [p for p in daily if p not in elite]

    return final
