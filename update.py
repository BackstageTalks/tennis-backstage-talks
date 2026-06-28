import json
import os
import datetime
from prediction_engine import get_daily_predictions
from tracker import record, evaluate


def run():
    os.makedirs("public", exist_ok=True)

    # ✅ najprv vyhodnoť staré zápasy
    evaluate()

    # ✅ generuj nové predikcie
    preds = get_daily_predictions()

    print("Generated:", len(preds))

    # ✅ ulož JSON
    filename = f"public/predictions_{datetime.date.today().isoformat()}.json"
    with open(filename, "w") as f:
        json.dump(preds, f, indent=4)

    print("Saved:", filename)

    # ✅ ulož do histórie
    record(preds)


if __name__ == "__main__":
    run()
