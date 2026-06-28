import json, os

FILE = "public/history.json"

def load():
    if not os.path.exists(FILE):
        return []
    return json.load(open(FILE))

def save(data):
    json.dump(data, open(FILE, "w"), indent=4)

def record(preds):
    hist = load()

    for p in preds:
        hist.append({
            "p1": p["player1"],
            "p2": p["player2"],
            "odds": p["odds"],
            "result": None
        })

    save(hist)

def evaluate():
    pass
