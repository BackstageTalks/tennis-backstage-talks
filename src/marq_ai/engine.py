from .models import MarqInput, MarqOutput
from .signals import get_signal


def calculate_marq(input_data: MarqInput) -> MarqOutput:

    open_prob = 1 / input_data.opening_odds
    current_prob = 1 / input_data.current_odds

    move_pct = (current_prob - open_prob) * 100

    marq_probability = max(
        35.0,
        min(
            65.0,
            50 + move_pct
        )
    )

    return MarqOutput(
        probability=round(marq_probability, 1),
        move_pct=round(move_pct, 2),
        signal=get_signal(move_pct)
    )
