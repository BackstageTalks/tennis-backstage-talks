def get_signal(move_pct: float) -> str:
    if move_pct >= 5:
        return "SUPPORTING"

    if move_pct <= -5:
        return "AGAINST"

    return "NEUTRAL"
