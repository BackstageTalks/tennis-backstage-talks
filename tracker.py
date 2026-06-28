import json
import os
import unicodedata
from results_fetcher import get_finished_matches

FILE = "public/history.json"

def normalize(name):
    name = name.lower()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.replace(".", "").strip()
    return name.split()[-1]

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
            "pick": p["player1"],
            "odds": p["odds"],
            "result": None
        })

    save(hist)

def evaluate():
    hist = load()
    results = get_finished_matches()

    updated = 0

    for h in hist:
        if h["result"] is not None:
            continue

        hp = {normalize(h["p1"]), normalize(h["p2"])}

        for r in results:
            rp = {normalize(r["player1"]), normalize(r["player2"])}

            if hp == rp:
                win = normalize(r["winner"])

                h["result"] = "win" if normalize(h["pick"]) == win else "loss"
                updated += 1
                break

    save(hist)
    print("Updated:", updated)

def stats():
    hist = load()
    done = [h for h in hist if h["result"]]

    if not done:
        return {"acc": 0, "roi": 0, "n": 0}

    wins = sum(1 for h in done if h["result"] == "win")
    total = len(done)

    profit = 0
    for h in done:
        profit += (h["odds"] - 1) if h["result"] == "win" else -1

    return {
        "acc": round((wins / total) * 100, 1),
        "roi": round((profit / total) * 100, 1),
        "n": total
    }
