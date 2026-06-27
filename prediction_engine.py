from typing import Dict, Any

def surface_factor(surface: str) -> float:
    s = (surface or "").lower()
    if "hard" in s: return 1.0
    if "clay" in s: return 0.95
    if "grass" in s: return 1.05
    return 1.0

def stats_score(detail: Dict[str, Any], prefix: str) -> float:
    fs_pct = detail.get(f"{prefix}_first_serve_pct", 50)
    fs_won = detail.get(f"{prefix}_first_serve_won_pct", 50)
    ss_won = detail.get(f"{prefix}_second_serve_won_pct", 50)
    aces = detail.get(f"{prefix}_aces", 0)
    df = detail.get(f"{prefix}_double_faults", 0)

    score = (
        0.30 * (fs_pct / 100) +
        0.30 * (fs_won / 100) +
        0.20 * (ss_won / 100) +
        0.10 * (aces / 10) +
        0.10 * (1 - df / 10)
    )
    return max(0.01, min(score, 1.5))

def compute_prediction(match: Dict[str, Any], detail: Dict[str, Any], h2h: Dict[str, Any], ranks: Dict[str, int]) -> Dict[str, Any]:
    p1 = match["player1"]["name"]
    p2 = match["player2"]["name"]

    r1 = ranks.get(p1, 200)
    r2 = ranks.get(p2, 200)

    rank_factor_p1 = 1.0 + (200 - r1) / 400.0
    rank_factor_p2 = 1.0 + (200 - r2) / 400.0

    stats_p1 = stats_score(detail, "p1")
    stats_p2 = stats_score(detail, "p2")

    surface = match["tournament"].get("surface", "hard")
    sf = surface_factor(surface)

    raw_p1 = sf * rank_factor_p1 * stats_p1
    raw_p2 = sf * rank_factor_p2 * stats_p2

    total = raw_p1 + raw_p2
    prob1 = raw_p1 / total
    prob2 = raw_p2 / total

    return {
        "player1": p1,
        "player2": p2,
        "prob_player1": prob1,
        "prob_player2": prob2,
        "surface": surface,
        "rank_player1": r1,
        "rank_player2": r2,
    }
