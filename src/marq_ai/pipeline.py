from .provider import (
    fetch_marq_market_data,
)

from .transformer import (
    build_marq_input,
    resolve_outcome_key,
)

from .engine import (
    calculate_marq,
)


def build_marq_from_match(
    player1: str,
    player2: str,
    date_only: str,
    pick: str | None = None,
):
    market_data = fetch_marq_market_data(
        player1=player1,
        player2=player2,
        date_only=date_only,
    )

    if not market_data:
        print(
            "MARQ DEBUG: market_data missing",
            player1,
            "vs",
            player2,
            date_only,
        )

        return None

    odds_summary = market_data.get(
        "odds_summary"
    )

    recent_odds = market_data.get(
        "recent_odds"
    )

    outcome_key = resolve_outcome_key(
        player1=player1,
        player2=player2,
        pick=pick,
    )

    marq_input = build_marq_input(
        odds_summary=odds_summary,
        recent_odds=recent_odds,
        outcome_key=outcome_key,
    )

    if not marq_input:
        print(
            "MARQ DEBUG: input missing",
            "event_id=",
            market_data.get("event_id"),
            "outcome_key=",
            outcome_key,
            "summary=",
            "yes" if odds_summary else "no",
            "recent=",
            "yes" if recent_odds else "no",
        )

        return None

    output = calculate_marq(
        marq_input
    )

    print(
        "MARQ DEBUG: score",
        player1,
        "vs",
        player2,
        "pick=",
        pick,
        "event_id=",
        market_data.get("event_id"),
        "outcome_key=",
        outcome_key,
        "score=",
        output.score,
        "signal=",
        output.signal,
    )

    return output
