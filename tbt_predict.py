from .service import EloService
from .probability import win_probability


_service = EloService()


def predict(
    player1,
    player2,
    tour="atp",
    surface=None,
):
    p1 = _service.get_player_record(
        player1,
        tour=tour,
        surface=surface,
    )

    p2 = _service.get_player_record(
        player2,
        tour=tour,
        surface=surface,
    )

    elo_probability = win_probability(
        p1["elo"],
        p2["elo"],
    )

    yelo_probability = win_probability(
        p1["yelo"],
        p2["yelo"],
    )

    combined_probability = (
        0.7 * elo_probability +
        0.3 * yelo_probability
    )

    return {
        "player1": p1,
        "player2": p2,

        "elo_probability": round(
            elo_probability,
            4,
        ),

        "yelo_probability": round(
            yelo_probability,
            4,
        ),

        "combined_probability": round(
            combined_probability,
            4,
        ),
    }
