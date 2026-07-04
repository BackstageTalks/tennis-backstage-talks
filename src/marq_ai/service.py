from .models import (
    MarqInput,
    MovementPoint,
)

from .engine import (
    calculate_marq,
)


def build_marq_ai(
    opening_odds: float,
    current_odds: float,
    movement_history: list,
):
    history = []

    for item in movement_history:
        history.append(
            MovementPoint(
                odds=float(
                    item.get("odds")
                ),
                timestamp=int(
                    item.get(
                        "timestamp",
                        0,
                    )
                ),
            )
        )

    marq_input = MarqInput(
        opening_odds=opening_odds,
        current_odds=current_odds,
        movement_history=history,
    )

    return calculate_marq(
        marq_input
    )
