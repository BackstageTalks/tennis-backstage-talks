from welo import win_probability
from fetch_matches import get_today_matches

def get_daily_predictions():
    matches = get_today_matches()

    if not matches:
        return []

    predictions = []

    for p1, p2, tournament in matches:
        prob = win_probability(p1, p2)

        odds = 1.90
        implied = 1 / odds

        value = prob - implied
        confidence = abs(prob - 0.5)

        score = (prob * 0.6) + (confidence * 0.2) + (value * 0.2)

        predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "probability": round(prob, 3),
            "odds": odds,
            "value": round(value, 3),
            "confidence": round(confidence, 3),
            "score": round(score, 3)
        })

    predictions.sort(key=lambda x: x["score"], reverse=True)

    top4 = predictions[:4]

    elite = [p for p in predictions if p["probability"] > 0.6][:2]

    final = elite + [p for p in top4 if p not in elite]

    return final
