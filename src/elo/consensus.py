def clamp(value, low, high):
    return max(low, min(high, value))


def calculate_consensus(
    tbt_ai,
    tbt_elo,
    tbt_yelo,
):
    """
    Inputs:
        0.00 - 1.00

    Example:
        tbt_ai   = 0.72
        tbt_elo  = 0.70
        tbt_yelo = 0.74
    """

    values = [
        float(tbt_ai),
        float(tbt_elo),
        float(tbt_yelo),
    ]

    spread = max(values) - min(values)

    # 0 spread = perfect agreement
    # 0.30 spread = terrible agreement

    normalized = 1.0 - (spread / 0.30)

    score = int(
        round(
            clamp(normalized, 0.0, 1.0) * 100
        )
    )

    if score >= 80:
        label = "HIGH"

    elif score >= 60:
        label = "MEDIUM"

    else:
        label = "LOW"

    return {
        "score": score,
        "label": label,
        "spread": round(spread, 3),
    }
