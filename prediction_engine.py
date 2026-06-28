from welo import win_probability
from fetch_matches import get_today_matches

def get_daily_predictions():
    matches = get_today_matches()

    predictions = []

    for p1, p2, tournament in matches:
        prob = win_probability(p1, p2)

        odds = 1.90
        implied = 1 / odds

        value = prob - implied
        confidence = abs(prob - 0.5)

        predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "probability": round(prob, 3),
            "odds": odds,
            "value": round(value, 3),
            "confidence": round(confidence, 3)
        })

    # ✅ záloha
    backup = predictions.copy()

    # ✅ filtre (kľúčové!)
    predictions = [
        p for p in predictions
        if p["probability"] >= 0.55 and p["confidence"] > 0.05
    ]

    # ✅ fallback
    if len(predictions) < 2:
        predictions = backup

    # ✅ scoring
    for p in predictions:
        p["score"] = (p["probability"] * 0.85) + (p["confidence"] * 0.15)

    predictions.sort(key=lambda x: x["score"], reverse=True)

    # ✅ flexible output
    if len(predictions) >= 4:
        final = predictions[:4]
    else:
        final = predictions[:len(predictions)]

    return final
