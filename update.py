import json
import datetime
import os
from prediction_engine import get_daily_predictions

def save_predictions():
    today = datetime.date.today().isoformat()

    # Ukladáme do PUBLIC, aby to GitHub Pages videl
    os.makedirs("public", exist_ok=True)
    path = f"public/predictions_{today}.json"

    predictions = get_daily_predictions()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4)

    print(f"Predictions saved → {path}")

if __name__ == "__main__":
    save_predictions()
