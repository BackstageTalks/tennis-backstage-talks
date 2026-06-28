import json
import datetime
import os
from prediction_engine import get_daily_predictions

def save_predictions():
    today = datetime.date.today().isoformat()

    os.makedirs("public", exist_ok=True)

    path = f"public/predictions_{today}.json"

    try:
        predictions = get_daily_predictions()
        print("Generated:", len(predictions))
    except Exception as e:
        print("ERROR:", e)
        predictions = [{
            "player1": "Fallback",
            "player2": "Fallback",
            "tournament": "Fallback",
            "probability_player1": 0.6,
            "odds_player1": 1.8,
            "value": 0.02,
            "confidence": 0.1,
            "score": 0.1
        }]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4)

    print("Saved:", path)


if __name__ == "__main__":
    save_predictions()
