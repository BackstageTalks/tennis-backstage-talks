from fetch_matches import get_today_matches
from welo import win_probability


def get_daily_predictions():
    matches = get_today_matches()

    if not matches:
        print("NO REAL MATCHES FOUND")
        return []

    predictions = []

    for p1, p2, tournament in matches:
        prob = win_probability(p1, p2)
        confidence = abs(prob - 0.5)

        odds = 1.90
        implied = 1 / odds
        value = prob - implied

        # odstráň úplné coinflipy
        if prob < 0.52:
            continue

        score = (prob * 0.85) + (confidence * 0.15)

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

    final = predictions[:4]

    print("FINAL PICKS:", len(final))
    for p in final:
        print(p["player1"], "vs", p["player2"], "| prob:", p["probability"])

    return final
