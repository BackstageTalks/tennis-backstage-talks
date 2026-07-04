def classify_signal(score: float) -> str:

    if score >= 80:
        return "STRONG_SUPPORT"

    if score >= 65:
        return "SUPPORT"

    if score >= 45:
        return "NEUTRAL"

    if score >= 30:
        return "AGAINST"

    return "STRONG_AGAINST"
