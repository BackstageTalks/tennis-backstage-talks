import json
import os
from datetime import datetime

FILE = "data/bet_history.jsonl"


def save_today_bets(bets):
    os.makedirs("data", exist_ok=True)

    today = datetime.utcnow().strftime("%Y-%m-%d")

    with open(FILE, "a", encoding="utf-8") as f:
        for b in bets:
            record = {
                "date": today,
                "player1": b["player1"],
                "player2": b["player2"],
                "pick": b["pick"],
                "probability": b["probability"],
                "odds": b["odds"],
                "result": None,
                "profit": None
            }

            f.write(json.dumps(record) + "\n")

    print("SAVED BETS:", len(bets))


def load_history():
    if not os.path.exists(FILE):
        return []

    with open(FILE, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]
