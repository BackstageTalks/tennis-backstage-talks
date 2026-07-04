from .provider import (
    fetch_marq_market_data,
)

from .transformer import (
    build_marq_input,
)

from .engine import (
    calculate_marq,
)


def build_marq_from_match(
    player1: str,
    player2: str,
    date_only: str,
):

    market_data = fetch_marq_market_data(
        player1=player1,
        player2=player2,
        date_only=date_only,
    )

    if not market_data:
        return None

    odds_summary = market_data.get(
        "odds_summary"
    )

    recent_odds = market_data.get(
        "recent_odds"
    )

    marq_input = build_marq_input(
        odds_summary=odds_summary,
        recent_odds=recent_odds,
    )

    if not marq_input:
        return None

    return calculate_marq(
        marq_input
    )
