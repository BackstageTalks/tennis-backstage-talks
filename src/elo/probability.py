def win_probability(rating_a, rating_b):
    return 1 / (
        1 + 10 ** (
            (rating_b - rating_a) / 400
        )
    )
