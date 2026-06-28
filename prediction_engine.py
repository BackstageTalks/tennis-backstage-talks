import random

def get_daily_predictions():
    players = [
        ("Djokovic", "Alcaraz"),
        ("Sinner", "Medvedev"),
        ("Zverev", "Rublev")
    ]

    predictions = []

    for p1, p2 in players:
        v1 = random.random()
        v2 = 1 - v1

        predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": "ATP Example",
            "value_player1": {"value": round(v1, 3)},
            "value_player2": {"value": round(v2, 3)}
        })

    return predictions
