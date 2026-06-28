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
        print("Predictions generated:", predictions)
    except Exception as e:
        print("ERROR:", e)
        predictions = [
            {
                "player1": "Fallback A",
                "player2": "Fallback B",
                "tournament": "Fallback",
                "value_player1": {"value": 0.5},
                "value_player2": {"value": 0.5}
            }
        ]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4)

    print("Saved:", path)


if __name__ == "__main__":
    save_predictions()
