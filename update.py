import json
import os
import datetime
from prediction_engine import get_daily_predictions


def run():
    os.makedirs("public", exist_ok=True)

    preds = get_daily_predictions()

    print("Generated predictions:", len(preds))
    print(preds)

    today = datetime.date.today().isoformat()
    filename = f"public/predictions_{today}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(preds, f, indent=4, ensure_ascii=False)

    print("Saved prediction file:", filename)

    print("Public folder after save:")
    print(os.listdir("public"))


if __name__ == "__main__":
    run()
