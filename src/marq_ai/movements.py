def calculate_direction(open_odds: float, current_odds: float) -> float:
    open_prob = 1 / open_odds
    current_prob = 1 / current_odds

    return (current_prob - open_prob) * 100


def calculate_strength(open_odds: float, current_odds: float) -> float:
    return abs(
        ((current_odds - open_odds) / open_odds) * 100
    )
