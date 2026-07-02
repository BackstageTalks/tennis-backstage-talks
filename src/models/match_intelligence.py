def clamp(value, low, high):
    return max(low, min(high, value))


GRAND_SLAMS = [
    "wimbledon",
    "australian open",
    "us open",
    "roland garros",
    "french open",
]


def is_grand_slam(tournament):
    if not tournament:
        return False

    tournament = str(tournament).lower()

    return any(gs in tournament for gs in GRAND_SLAMS)


def infer_best_of_from_tournament(tournament):
    if not tournament:
        return 3

    text = str(tournament).lower()

    is_slam = is_grand_slam(text)

    is_men = (
        "men" in text
        or "atp" in text
    )

    is_women = (
        "women" in text
        or "wta" in text
    )

    if is_slam and is_men and not is_women:
        return 5

    return 3


def normalize_best_of(best_of, tournament=None):
    try:
        value = int(best_of)

        if value == 5:
            return 5

        if value == 3:
            return 3

    except Exception:
        pass

    return infer_best_of_from_tournament(tournament)


def build_match_intelligence(
    probability,
    odds=None,
    consensus_score=None,
    tournament=None,
    best_of=None,
):
    """
    probability:
        0.50 - 0.85

    odds:
        bookmaker odds

    consensus_score:
        0 - 100

    tournament:
        e.g. Wimbledon Men Singles

    best_of:
        3 or 5
    """

    probability = float(probability)

    best_of = normalize_best_of(
        best_of,
        tournament,
    )

    #
    # Best of 5
    #

    if best_of == 5:

        if probability >= 0.75:
            expected_sets = 3.4
            sets_probability = 0.25

        elif probability >= 0.70:
            expected_sets = 3.7
            sets_probability = 0.35

        elif probability >= 0.65:
            expected_sets = 4.0
            sets_probability = 0.45

        elif probability >= 0.60:
            expected_sets = 4.2
            sets_probability = 0.55

        elif probability >= 0.55:
            expected_sets = 4.4
            sets_probability = 0.65

        else:
            expected_sets = 4.6
            sets_probability = 0.75

        sets_probability_label = "5 Sets"

        expected_games = round(
            31.0 + (sets_probability * 10.0),
            1,
        )

        if expected_games >= 40.5:
            games_pick = "Over 39.5"
            games_line = 39.5

        elif expected_games >= 37.5:
            games_pick = "Over 36.5"
            games_line = 36.5

        else:
            games_pick = "Under 39.5"
            games_line = 39.5

    #
    # Best of 3
    #

    else:

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

        sets_probability_label = "3 Sets"

        expected_games = round(
            21.0 + (sets_probability * 4.0),
            1,
        )

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

        "sets_probability_label": sets_probability_label,

        "expected_games": expected_games,

        "games_pick": games_pick,

        "games_line": games_line,

        "best_of": best_of,

        "tag": tag,
    }
