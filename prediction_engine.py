import random

def compute_probabilities(player1, player2, tournament):
    # Zjednodušený model – nech to generuje čísla
    p1 = random.uniform(0.45, 0.65)
    p2 = 1 - p1
    return p1, p2

def compute_value_bet(prob, odds):
    fair_odds = 1 / prob
    value = odds - fair_odds
    return {
        "value": value,
        "is_value_bet": value > 0
    }
