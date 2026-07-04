# src/marq_ai/movements.py

from typing import List


def calculate_direction(
    opening_odds: float,
    current_odds: float
) -> float:
    """
    Market direction based on implied probability change.

    Positive = market supports the selection
    Negative = market moves against the selection
    """

    open_prob = 1.0 / opening_odds
    current_prob = 1.0 / current_odds

    return (current_prob - open_prob) * 100.0


def calculate_strength(
    opening_odds: float,
    current_odds: float
) -> float:
    """
    Absolute size of the odds move in %.
    """

    return abs(
        ((current_odds - opening_odds) / opening_odds) * 100.0
    )


def calculate_consistency(
    odds_history: List[float]
) -> float:
    """
    Measures how consistently odds moved in one direction.

    Returns:
        0   = chaotic movement
        50  = mixed movement
        100 = fully consistent movement
    """

    if len(odds_history) < 2:
        return 50.0

    up_moves = 0
    down_moves = 0

    for i in range(1, len(odds_history)):
        diff = odds_history[i] - odds_history[i - 1]

        if diff > 0:
            up_moves += 1
        elif diff < 0:
            down_moves += 1

    total_moves = up_moves + down_moves

    if total_moves == 0:
        return 50.0

    dominant_moves = max(up_moves, down_moves)

    return round(
        (dominant_moves / total_moves) * 100.0,
        2
    )


def calculate_steam_score(
    opening_odds: float,
    current_odds: float,
    odds_history: List[float]
) -> float:
    """
    Core Marq AI metric.

    Combines:
    - Direction
    - Move Strength
    - Movement Consistency

    Returns:
        0-100 score
    """

    direction = calculate_direction(
        opening_odds,
        current_odds
    )

    strength = calculate_strength(
        opening_odds,
        current_odds
    )

    consistency = calculate_consistency(
        odds_history
    )

    score = (
        50.0
        + (direction * 3.0)
        + (strength * 0.8)
        + ((consistency - 50.0) * 0.3)
    )

    return round(
        max(0.0, min(100.0, score)),
        2
    )
