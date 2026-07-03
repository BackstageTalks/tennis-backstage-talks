import math


def elo_probability(rating_a, rating_b):
    if rating_a is None:
        return None

    if rating_b is None:
        return None

    try:
        rating_a = float(rating_a)
        rating_b = float(rating_b)

    except Exception:
        return None

    probability = 1.0 / (
        1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0)
    )

    return probability
