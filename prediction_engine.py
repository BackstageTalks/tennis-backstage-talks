# prediction_engine.py
from typing import Dict, Any

def surface_factor(surface: str) -> float:
    s = surface.lower()
    if "hard" in s: return 1.0
    if "clay" in s: return 0.95
    if "grass" in s: return 1.05
    return 1.0

def stats_score(detail: Dict[str, Any], p: str) -> float:
    fs_pct = detail.get(f"{p}_first_serve_pct", 0.60)
    fs_won = detail.get(f"{p}_first_serve_won_pct", 0.70)
    ss_won = detail.get(f"{p}_second_serve_won_pct", 0.50)
    aces = detail.get(f"p{1 if p=='p1' else 2}_aces", 2)
    df = detail.get(f"p{1 if p=='p1' else 2}_double_faults", 2)

    score = (
        0.25 * fs_pct +
        0.25 * fs_won +
        0.20 * ss_won +
        0.15 * (aces / 10) +
        0.15 * (1 - df / 10)
    )
    return max(0.01, min(score, 1.5))

def h2h_score(h2h: Dict[str, Any], p: str) -> float:
    rec = h2h.get("h2h", {})
    wins = rec.get(f"{p}_wins", 0)
    losses = rec.get(f"{p}_losses", 0)
    total = wins + losses
    if total == 0:
        return 1.0
    return 0.9 + 0.2 * (wins / total)

def compute_prediction(match: Dict[str, Any], detail: Dict[str, Any], h2h: Dict[str, Any], ranks: Dict[str, int]) -> Dict[str, Any]:
    p1 = match["player1"]["name"]
    p2 = match["player2"]["name"]

    r1 = ranks.get(p1, 200)
    r2 = ranks.get(p2, 200)

    rank_factor_p1 = 1.0 + (200 - r1) / 400.0
    rank_factor_p2 = 1.0 + (200 - r2) / 400.0

    stats_p1 = stats_score(detail, "p1")
    stats_p2 = stats_score(detail, "p2")

    h2h_p1 = h2h_score(h2h, "player1")
    h2h_p2 = h2h_score(h2h, "player2")

    surface = match["tournament"].get("surface", "hard")
    sf = surface_factor(surface)

    raw_p1 = sf * rank_factor_p1 * stats_p1 * h2h_p1
    raw_p2 = sf * rank_factor_p2 * stats_p2 * h2h_p2

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
