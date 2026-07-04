from .models import (
    MarqInput,
    MovementPoint,
)


def build_marq_input(
    opening_odds: float,
    current_odds: float,
    movements: list,
):
    history = []

    for item in movements:
        history.append(
            MovementPoint(
                odds=float(item["od1"]),
                timestamp=int(item["sourceAddTime"]),
            )
        )

    return MarqInput(
        opening_odds=opening_odds,
        current_odds=current_odds,
        movement_history=history,
    )
