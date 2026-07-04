from .models import (
    MarqInput,
    MovementPoint,
)


def extract_opening_odds(
    odds_summary: dict,
) -> float | None:

    try:
        return float(
            odds_summary["start"]["od1"]
        )

    except Exception:
        return None


def extract_current_odds(
    recent_odds: dict,
) -> float | None:

    try:
        result = recent_odds.get(
            "result",
            {}
        )

        full_time = result.get(
            "Full Time Result",
            {}
        )

        bookmaker = next(
            iter(full_time.values())
        )

        return float(
            bookmaker["od1"]
        )

    except Exception:
        return None


def build_movement_history(
    opening_odds: float,
    current_odds: float,
):

    return [
        MovementPoint(
            odds=opening_odds,
            timestamp=0,
        ),
        MovementPoint(
            odds=current_odds,
            timestamp=1,
        ),
    ]


def build_marq_input(
    odds_summary: dict,
    recent_odds: dict,
):

    opening_odds = extract_opening_odds(
        odds_summary
    )

    current_odds = extract_current_odds(
        recent_odds
    )

    if (
        opening_odds is None
        or current_odds is None
    ):
        return None

    movement_history = (
        build_movement_history(
            opening_odds,
            current_odds,
        )
    )

    return MarqInput(
        opening_odds=opening_odds,
        current_odds=current_odds,
        movement_history=movement_history,
    )
