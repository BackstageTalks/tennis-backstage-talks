from .rapid_api import (
    get_event_id,
    get_odds_summary,
    get_recent_odds,
)


def fetch_marq_market_data(
    player1: str,
    player2: str,
    date_only: str,
):

    event_id = get_event_id(
        player1=player1,
        player2=player2,
        date_only=date_only,
    )

    if not event_id:
        return None

    odds_summary = get_odds_summary(
        event_id
    )

    recent_odds = get_recent_odds(
        event_id
    )

    return {
        "event_id": event_id,
        "odds_summary": odds_summary,
        "recent_odds": recent_odds,
    }
