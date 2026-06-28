import json
import os
import datetime

from prediction_engine import get_daily_predictions
from prediction_engine_all import get_all_daily_predictions


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def run():
    os.makedirs("public", exist_ok=True)

    today = datetime.date.today().isoformat()

    top_preds = get_daily_predictions()
    top_preds = top_preds[:7]

    top_filename = f"public/predictions_{today}.json"
    save_json(top_filename, top_preds)

    print("Generated TOP predictions:", len(top_preds))
    print("Saved TOP prediction file:", top_filename)

    all_preds = get_all_daily_predictions()

    all_filename = f"public/all_predictions_{today}.json"
    save_json(all_filename, all_preds)

    print("Generated ALL predictions:", len(all_preds))
    print("Saved ALL prediction file:", all_filename)

    print("Public folder after save:")
    print(os.listdir("public"))


if __name__ == "__main__":
    run()
