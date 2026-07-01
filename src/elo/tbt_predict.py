from .service import EloService
from .probability import win_probability


service = EloService()


def predict(
    player1,
    player2,
    tour="atp",
    surface=None,
):
    p1 = service.get_player_record(
        player1,
        tour=tour,
        surface=surface,
    )

    p2 = service.get_player_record(
        player2,
        tour=tour,
        surface=surface,
    )

    elo_prob = win_probability(
        p1["elo"],
        p2["elo"],
    )

    yelo_prob = win_probability(
        p1["yelo"],
        p2["yelo"],
    )

    return {
        "elo_probability": elo_prob,
        "yelo_probability": yelo_prob,
        "player1": p1,
        "player2": p2,
    }
