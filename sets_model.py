from typing import Any, Dict, Optional


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_probability(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number > 1.0:
        return number / 100.0
    return number


def favorite_side(probability_player1: Any, probability_player2: Any) -> str:
    p1 = normalize_probability(probability_player1) or 0.5
    p2 = normalize_probability(probability_player2) or 0.5
    return "p1" if p1 >= p2 else "p2"


def infer_bo(match: Dict[str, Any]) -> int:
    try:
        best_of = int(match.get("best_of") or 3)
        return 5 if best_of == 5 else 3
    except Exception:
        return 3


def infer_is_doubles(match: Dict[str, Any]) -> bool:
    text = " ".join([
        str(match.get("match") or ""),
        str(match.get("tournament") or ""),
        str(match.get("category") or ""),
    ]).lower()
    return "doubles" in text


def market_set_pressure(best_of: int, total_games: Optional[Dict[str, Any]], tie_break: Optional[Dict[str, Any]]) -> float:
    """
    Returns 0..1 where higher means longer/tighter match.
    Uses total games line, over probability and tie-break probability.
    """
    pressure = 0.50

    if isinstance(total_games, dict):
        line = safe_float(total_games.get("line"))
        over_prob = normalize_probability(total_games.get("over_probability"))

        if best_of == 5:
            if line is not None:
                # 34.5 short, 40.5 medium-long, 44.5 very long.
                pressure += (line - 38.5) / 18.0
        else:
            if line is not None:
                # 19.5 short, 22.5 medium, 24.5 long.
                pressure += (line - 22.0) / 10.0

        if over_prob is not None:
            pressure += (over_prob - 0.50) * 0.60

    if isinstance(tie_break, dict):
        tie_prob = normalize_probability(tie_break.get("yes_probability"))
        if tie_prob is not None:
            # Tie-break likely => tighter sets => longer match.
            pressure += (tie_prob - 0.35) * 0.35

    return clamp(pressure, 0.05, 0.95)


def dominance_score(match_probability: Optional[float], first_set_probability: Optional[float]) -> float:
    """
    0..1 dominance. Higher => cleaner/shorter win.
    """
    p_match = match_probability if match_probability is not None else 0.5
    p_first = first_set_probability if first_set_probability is not None else p_match
    return clamp(((p_match - 0.50) * 1.3) + ((p_first - 0.50) * 0.7), -0.45, 0.45)


def bo3_distribution(winner_side: str, match_prob: float, first_set_prob: Optional[float], pressure: float) -> Dict[str, float]:
    dom = dominance_score(match_prob, first_set_prob)
    three_sets = clamp(0.30 + pressure * 0.34 - max(dom, 0) * 0.20, 0.18, 0.62)
    fav_win = clamp(match_prob, 0.35, 0.85)
    fav_straight = clamp((1 - three_sets) * (0.55 + max(dom, 0) * 0.70), 0.20, 0.70)
    fav_deciding = clamp(three_sets * fav_win, 0.08, 0.45)
    dog_deciding = clamp(three_sets * (1 - fav_win), 0.05, 0.35)
    dog_straight = max(0.02, 1.0 - fav_straight - fav_deciding - dog_deciding)

    if winner_side == "p1":
        dist = {"2-0": fav_straight, "2-1": fav_deciding, "1-2": dog_deciding, "0-2": dog_straight}
    else:
        dist = {"0-2": fav_straight, "1-2": fav_deciding, "2-1": dog_deciding, "2-0": dog_straight}
    return normalize_dist(dist)


def bo5_distribution(winner_side: str, match_prob: float, first_set_prob: Optional[float], pressure: float) -> Dict[str, float]:
    dom = dominance_score(match_prob, first_set_prob)
    five_sets = clamp(0.16 + pressure * 0.28 - max(dom, 0) * 0.10, 0.08, 0.42)
    four_sets = clamp(0.30 + pressure * 0.10 - abs(dom) * 0.05, 0.20, 0.45)
    three_sets = clamp(1.0 - five_sets - four_sets, 0.20, 0.58)

    fav_win = clamp(match_prob, 0.35, 0.88)
    fav_three = three_sets * (0.62 + max(dom, 0) * 0.60)
    dog_three = max(0.01, three_sets - fav_three)
    fav_four = four_sets * fav_win
    dog_four = four_sets * (1 - fav_win)
    fav_five = five_sets * fav_win
    dog_five = five_sets * (1 - fav_win)

    if winner_side == "p1":
        dist = {"3-0": fav_three, "3-1": fav_four, "3-2": fav_five, "2-3": dog_five, "1-3": dog_four, "0-3": dog_three}
    else:
        dist = {"0-3": fav_three, "1-3": fav_four, "2-3": fav_five, "3-2": dog_five, "3-1": dog_four, "3-0": dog_three}
    return normalize_dist(dist)


def normalize_dist(dist: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(v, 0.0) for v in dist.values())
    if total <= 0:
        return dist
    return {k: round(max(v, 0.0) / total, 4) for k, v in dist.items()}


def expected_sets_from_dist(dist: Dict[str, float]) -> float:
    total = 0.0
    for score, prob in dist.items():
        try:
            a, b = score.split("-")
            total += (int(a) + int(b)) * float(prob)
        except Exception:
            pass
    return round(total, 2)


def probability_of_max_sets(dist: Dict[str, float], best_of: int) -> float:
    max_sets = 5 if best_of == 5 else 3
    total = 0.0
    for score, prob in dist.items():
        try:
            a, b = score.split("-")
            if int(a) + int(b) == max_sets:
                total += float(prob)
        except Exception:
            pass
    return round(total, 4)


def most_likely_score(dist: Dict[str, float]) -> str:
    if not dist:
        return "-"
    return max(dist.items(), key=lambda item: item[1])[0]


def build_market_aware_sets(
    match: Dict[str, Any],
    elo_prediction: Dict[str, Any],
    odds_data: Optional[Dict[str, Any]] = None,
    set_markets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    odds_data = odds_data or {}
    set_markets = set_markets or {}

    best_of = infer_bo(match)
    if infer_is_doubles(match):
        best_of = 3

    p1_model = normalize_probability(elo_prediction.get("probability_player1"))
    p2_model = normalize_probability(elo_prediction.get("probability_player2"))

    mw = set_markets.get("match_winner") if isinstance(set_markets, dict) else None
    fsw = set_markets.get("first_set_winner") if isinstance(set_markets, dict) else None
    tg = set_markets.get("total_games") if isinstance(set_markets, dict) else None
    tb = set_markets.get("tie_break") if isinstance(set_markets, dict) else None

    if isinstance(mw, dict) and mw.get("p1_probability") is not None:
        p1_match = float(mw["p1_probability"])
        p2_match = float(mw["p2_probability"])
    else:
        p1_match = p1_model if p1_model is not None else 0.5
        p2_match = p2_model if p2_model is not None else 1.0 - p1_match

    if p1_match >= p2_match:
        winner_side = "p1"
        match_prob = p1_match
        first_prob = fsw.get("p1_probability") if isinstance(fsw, dict) else None
    else:
        winner_side = "p2"
        match_prob = p2_match
        first_prob = fsw.get("p2_probability") if isinstance(fsw, dict) else None

    pressure = market_set_pressure(best_of, tg, tb)

    if best_of == 5:
        dist = bo5_distribution(winner_side, match_prob, first_prob, pressure)
        max_label = "5 Sets"
    else:
        dist = bo3_distribution(winner_side, match_prob, first_prob, pressure)
        max_label = "3 Sets"

    expected_sets = expected_sets_from_dist(dist)
    max_sets_prob = probability_of_max_sets(dist, best_of)
    score = most_likely_score(dist)

    games_line = tg.get("line") if isinstance(tg, dict) else None
    over_prob = tg.get("over_probability") if isinstance(tg, dict) else None
    under_prob = tg.get("under_probability") if isinstance(tg, dict) else None
    games_pick = None
    if games_line is not None and over_prob is not None:
        games_pick = f"Over {games_line}" if over_prob >= 0.50 else f"Under {games_line}"

    tie_break_probability = tb.get("yes_probability") if isinstance(tb, dict) else None

    return {
        "expected_sets": expected_sets,
        "sets_probability": max_sets_prob,
        "sets_probability_label": max_label,
        "most_likely_score": score,
        "most_likely_score_probability": dist.get(score),
        "score_probabilities": dist,
        "score_basis": "player1_vs_player2",

        # First-set market enrichment.
        "first_set_player1_odds": fsw.get("p1_odds") if isinstance(fsw, dict) else None,
        "first_set_player2_odds": fsw.get("p2_odds") if isinstance(fsw, dict) else None,
        "first_set_player1_probability": fsw.get("p1_probability") if isinstance(fsw, dict) else None,
        "first_set_player2_probability": fsw.get("p2_probability") if isinstance(fsw, dict) else None,

        # Games market enrichment.
        "expected_games": games_line,
        "games_line": games_line,
        "games_pick": games_pick,
        "games_over_odds": tg.get("over_odds") if isinstance(tg, dict) else None,
        "games_under_odds": tg.get("under_odds") if isinstance(tg, dict) else None,
        "games_over_probability": round(float(over_prob), 4) if over_prob is not None else None,
        "games_under_probability": round(float(under_prob), 4) if under_prob is not None else None,

        # Tie-break market enrichment.
        "tie_break_yes_odds": tb.get("yes_odds") if isinstance(tb, dict) else None,
        "tie_break_no_odds": tb.get("no_odds") if isinstance(tb, dict) else None,
        "tie_break_probability": round(float(tie_break_probability), 4) if tie_break_probability is not None else None,

        "sets_model_source": "TennisApiMarkets" if set_markets else "ModelFallback",
    }
