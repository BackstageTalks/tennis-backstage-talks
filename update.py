import json, os, datetime
from prediction_engine import get_daily_predictions
from tracker import record, evaluate

def run():
    os.makedirs("public", exist_ok=True)

    evaluate()

    preds = get_daily_predictions()

    print("Generated:", len(preds))

    with open(f"public/predictions_{datetime.date.today().isoformat()}.json", "w") as f:
        json.dump(preds, f, indent=4)

    record(preds)

if __name__ == "__main__":
    run()
