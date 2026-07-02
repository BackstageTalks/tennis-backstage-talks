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

    return infer_best_of_from_tournament(
        tournament
    )


def bo3_match_win_probability(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    return (
        (p ** 2)
        + (2.0 * (p ** 2) * q)
    )


def bo5_match_win_probability(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    return (
        (p ** 3)
        + (3.0 * (p ** 3) * q)
        + (6.0 * (p ** 3) * (q ** 2))
    )


def match_win_probability_from_set_probability(
    set_win_probability,
    best_of,
):
    if best_of == 5:
        return bo5_match_win_probability(
            set_win_probability
        )

    return bo3_match_win_probability(
        set_win_probability
    )


def estimate_set_win_probability(
    match_win_probability,
    best_of,
):
    """
    Convert match win probability into implied set win probability.

    BO3:
        P(match win) = p^2 + 2*p^2*(1-p)

    BO5:
        P(match win) = p^3 + 3*p^3*(1-p) + 6*p^3*(1-p)^2

    We solve p by binary search.
    """

    target = clamp(
        float(match_win_probability),
        0.01,
        0.99,
    )

    low = 0.01
    high = 0.99

    for _ in range(70):
        mid = (low + high) / 2.0

        estimated = match_win_probability_from_set_probability(
            mid,
            best_of,
        )

        if estimated < target:
            low = mid

        else:
            high = mid

    return (low + high) / 2.0


def normalize_distribution(distribution):
    total = sum(distribution.values())

    if total <= 0:
        return distribution

    return {
        key: value / total
        for key, value in distribution.items()
    }


def score_distribution_bo3(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    distribution = {
        "2-0": p * p,
        "2-1": 2.0 * p * p * q,
        "1-2": 2.0 * p * q * q,
        "0-2": q * q,
    }

    return normalize_distribution(
        distribution
    )


def score_distribution_bo5(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    distribution = {
        "3-0": p ** 3,
        "3-1": 3.0 * (p ** 3) * q,
        "3-2": 6.0 * (p ** 3) * (q ** 2),
        "2-3": 6.0 * (p ** 2) * (q ** 3),
        "1-3": 3.0 * p * (q ** 3),
        "0-3": q ** 3,
    }

    return normalize_distribution(
        distribution
    )


def sets_count_from_score(score):
    try:
        left, right = str(score).split("-")

        return int(left) + int(right)

    except Exception:
        return 0


def expected_sets_from_distribution(distribution):
    total = 0.0

    for score, probability in distribution.items():
        total += (
            sets_count_from_score(score)
            * probability
        )

    return total


def deciding_set_probability(distribution, best_of):
    if best_of == 5:
        return (
            distribution.get("3-2", 0.0)
            + distribution.get("2-3", 0.0)
        )

    return (
        distribution.get("2-1", 0.0)
        + distribution.get("1-2", 0.0)
    )


def most_likely_score(distribution):
    if not distribution:
        return None

    return max(
        distribution.items(),
        key=lambda item: item[1],
    )[0]


def rounded_score_probabilities(distribution):
    return {
        score: round(probability, 4)
        for score, probability in distribution.items()
    }


def expected_games_placeholder(
    expected_sets,
    deciding_probability,
    best_of,
):
    """
    Compatibility-only field.

    This is intentionally conservative and should not be treated
    as a final game/serve model.

    The website should not display games recommendation until
    a real game/serve model is implemented.
    """

    if best_of == 5:
        base_games_per_set = 9.6
        deciding_bonus = 2.0

    else:
        base_games_per_set = 9.4
        deciding_bonus = 1.2

    value = (
        expected_sets * base_games_per_set
        + deciding_probability * deciding_bonus
    )

    return round(value, 1)


def games_market_placeholder(expected_games, best_of):
    """
    Compatibility-only field.

    Kept so older render/build code does not crash.
    Do not use as betting recommendation.
    """

    if best_of == 5:
        return {
            "games_pick": "INFO ONLY",
            "games_line": None,
        }

    return {
        "games_pick": "INFO ONLY",
        "games_line": None,
    }


def build_score_model(probability, best_of):
    set_win_probability = estimate_set_win_probability(
        probability,
        best_of,
    )

    if best_of == 5:
        distribution = score_distribution_bo5(
            set_win_probability
        )

        sets_probability_label = "5 Sets"

    else:
        distribution = score_distribution_bo3(
            set_win_probability
        )

        sets_probability_label = "3 Sets"

    expected_sets = expected_sets_from_distribution(
        distribution
    )

    sets_probability = deciding_set_probability(
        distribution,
        best_of,
    )

    likely_score = most_likely_score(
        distribution
    )

    expected_games = expected_games_placeholder(
        expected_sets,
        sets_probability,
        best_of,
    )

    games_market = games_market_placeholder(
        expected_games,
        best_of,
    )

    return {
        "set_win_probability": set_win_probability,
        "score_probabilities": distribution,
        "expected_sets": expected_sets,
        "sets_probability": sets_probability,
        "sets_probability_label": sets_probability_label,
        "most_likely_score": likely_score,
        "expected_games": expected_games,
        "games_pick": games_market["games_pick"],
        "games_line": games_market["games_line"],
    }


def build_consensus_tag(consensus_score):
    tag = "INFO ONLY"

    if consensus_score is not None:

        if consensus_score >= 85:
            tag = "PLAY"

        elif consensus_score >= 70:
            tag = "PLAY SMALL"

        elif consensus_score >= 55:
            tag = "WATCH"

    return tag


def build_match_intelligence(
    probability,
    odds=None,
    consensus_score=None,
    tournament=None,
    best_of=None,
):
    """
    Match Intelligence v2.

    This model uses:
    - final match win probability
    - best_of 3 or 5

    It estimates set win probability and derives:
    - score distribution
    - expected sets
    - deciding set probability
    - most likely score

    It does not yet provide a real game/serve model.
    """

    probability = clamp(
        float(probability),
        0.01,
        0.99,
    )

    best_of = normalize_best_of(
        best_of,
        tournament,
    )

    score_model = build_score_model(
        probability,
        best_of,
    )

    tag = build_consensus_tag(
        consensus_score
    )

    return {
        "expected_sets": round(
            score_model["expected_sets"],
            1,
        ),

        "sets_probability": round(
            score_model["sets_probability"],
            3,
        ),

        "sets_probability_label":
            score_model["sets_probability_label"],

        "expected_games":
            score_model["expected_games"],

        "games_pick":
            score_model["games_pick"],

        "games_line":
            score_model["games_line"],

        "best_of":
            best_of,

        "set_win_probability": round(
            score_model["set_win_probability"],
            4,
        ),

        "most_likely_score":
            score_model["most_likely_score"],

        "score_probabilities":
            rounded_score_probabilities(
                score_model["score_probabilities"]
            ),

        "tag":
            tag,
    }
