def classify_signal(score: float) -> str:

    if score >= 80:
        return "BULLISH"

    if score >= 65:
        return "SUPPORT"

    if score >= 45:
        return "NEUTRAL"

    if score >= 30:
        return "CAUTION"

    return "BEARISH"
