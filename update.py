import json
import datetime
import os

from prediction_engine import compute_probabilities, compute_value_bet

# Fallback zápasy – použijú sa vždy, keď API nič nevráti
TEST_MATCHES = [
    {
        "player1": "Novak Djokovic",
        "player2": "Carlos Alcaraz",
        "tournament": "Wimbledon",
        "p1_odds": 1.80,
        "p2_odds": 2.10
    },
    {
        "player1": "Jannik Sinner",
        "player2": "Daniil Medvedev",
        "tournament": "ATP Finals",
        "p1_odds": 1.65,
        "p2_odds": 2.30
    }
]

def get_matches():
    # API zatiaľ vypnuté – vždy vráti prázdno
    return []

def main():
    matches = get_matches()

    if not matches:
        print("No matches found, using TEST_MATCHES")
        matches = TEST_MATCHES

    predictions = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        t = m["tournament"]
        p1_odds = m["p1_odds"]
        p2_odds = m["p2_odds"]

        prob1, prob2 = compute_probabilities(p1, p2, t)

        vb1 = compute_value_bet(prob1, p1_odds)
        vb2 = compute_value_bet(prob2, p2_odds)

        vb1["odds"] = p1_odds
        vb2["odds"] = p2_odds

        pred = {
            "player1": p1,
            "player2": p2,
            "tournament": t,
            "prob_player1": prob1,
            "prob_player2": prob2,
            "value_player1": vb1,
            "value_player2": vb2,
        }

        predictions.append(pred)

    os.makedirs("data", exist_ok=True)
    today = datetime.date.today().isoformat()
    path = f"data/predictions_{today}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(predictions)} predictions to {path}")

if __name__ == "__main__":
    main()
