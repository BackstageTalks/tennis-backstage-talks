from .models import (
    MarqInput,
    MarqOutput,
)

from .movements import (
    calculate_direction,
    calculate_strength,
    calculate_consistency,
    calculate_steam_score,
)

from .signals import classify_signal


def calculate_marq(
    data: MarqInput
) -> MarqOutput:

    odds_history = [
        point.odds
        for point in data.movement_history
    ]

    direction = calculate_direction(
        data.opening_odds,
        data.current_odds,
    )

    strength = calculate_strength(
        data.opening_odds,
        data.current_odds,
    )

    consistency = calculate_consistency(
        odds_history,
    )

    score = calculate_steam_score(
        data.opening_odds,
        data.current_odds,
        odds_history,
    )

    signal = classify_signal(
        score,
    )

    return MarqOutput(
        score=score,
        direction=direction,
        strength=strength,
        consistency=consistency,
        signal=signal,
    )
