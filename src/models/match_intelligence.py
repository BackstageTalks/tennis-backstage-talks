def clamp(value, low, high):
    return max(low, min(high, value))


def build_match_intelligence(
    probability,
    odds=None,
    consensus_score=None,
):
    """
    probability:
        0.50 - 0.85

    odds:
        bookmaker odds

    consensus_score:
        0 - 100
    """

    probability = float(probability)

    #
    # Expected sets
    #

    if probability >= 0.75:

        expected_sets = 2.2
        sets_probability = 0.30

    elif probability >= 0.70:

        expected_sets = 2.4
        sets_probability = 0.40

    elif probability >= 0.65:

        expected_sets = 2.5
        sets_probability = 0.48

    elif probability >= 0.60:

        expected_sets = 2.6
        sets_probability = 0.54

    elif probability >= 0.55:

        expected_sets = 2.7
        sets_probability = 0.60

    else:

        expected_sets = 2.8
        sets_probability = 0.65

    #
    # Expected games
    #

    expected_games = (
        21.0 +
        (sets_probability * 4.0)
    )

    expected_games = round(
        expected_games,
        1,
    )

    #
    # Games pick
    #

    if expected_games >= 23.5:

        games_pick = "Over 22.5"
        games_line = 22.5

    elif expected_games >= 22.5:

        games_pick = "Over 21.5"
        games_line = 21.5

    else:

        games_pick = "Under 22.5"
        games_line = 22.5

    #
    # Consensus tag
    #

    tag = "INFO ONLY"

    if consensus_score is not None:

        if consensus_score >= 85:
            tag = "PLAY"

        elif consensus_score >= 70:
            tag = "PLAY SMALL"

        elif consensus_score >= 55:
            tag = "WATCH"

    return {
        "expected_sets": round(
            expected_sets,
            1,
        ),

        "sets_probability": round(
            sets_probability,
            3,
        ),

        "expected_games": expected_games,

        "games_pick": games_pick,

        "games_line": games_line,

        "tag": tag,
    }
