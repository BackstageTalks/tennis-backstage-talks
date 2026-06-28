from fetch_matches import get_today_matches
from welo import win_probability
from stats_engine import get_stats_for_players


TOP_N = 7


def fair_market_probs(odds1, odds2):
    if not odds1 or not odds2:
        return None, None, None

    raw1 = 1 / odds1
    raw2 = 1 / odds2
    overround = raw1 + raw2

    if overround <= 0:
        return None, None, None

    fair1 = raw1 / overround
    fair2 = raw2 / overround

    return fair1, fair2, overround


def classify_bookie_signal(pick, p1, p2, model_prob, odds1, odds2):
    fair1, fair2, overround = fair_market_probs(odds1, odds2)

    if fair1 is None or fair2 is None:
        return {
            "pick_odds": 1.90,
            "market_probability": None,
            "market_agrees": False,
            "bookie_value_edge": None,
            "overround": None,
            "bookie_signal": "NO_ODDS"
        }

    if pick == p1:
        pick_odds = odds1
        market_probability = fair1
        opponent_market_probability = fair2
    else:
        pick_odds = odds2
        market_probability = fair2
        opponent_market_probability = fair1

    market_agrees = market_probability >= opponent_market_probability
    value_edge = model_prob - market_probability

    if market_agrees and model_prob >= 0.58:
        signal = "BOOKIE_AND_MODEL_AGREE"
    elif value_edge >= 0.04:
        signal = "VALUE_EDGE"
    elif not market_agrees:
        signal = "MODEL_DISAGREES_WITH_MARKET"
    else:
        signal = "NEUTRAL_MARKET"

    return {
        "pick_odds": round(pick_odds, 3),
        "market_probability": round(market_probability, 3),
        "market_agrees": market_agrees,
        "bookie_value_edge": round(value_edge, 3),
        "overround": round(overround, 3),
        "bookie_signal": signal
    }


def metric_for_surface(player_stats, surface):
    if not player_stats:
        return {}

    surface_stats = player_stats.get("surface", {})

    if surface and surface != "Unknown":
        s = surface_stats.get(surface)

        if s and s.get("sample", 0) >= 3:
            return s

    last10 = player_stats.get("last10", {})

    if last10 and last10.get("sample", 0) >= 3:
        return last10

    return player_stats.get("career", {})


def classify_extra_signal(pick_metrics, opponent_metrics):
    signals = []

    avg_aces = pick_metrics.get("avg_aces")
    ace_rate = pick_metrics.get("ace_rate")
    opp_avg_aces = opponent_metrics.get("avg_aces")

    set_rate = pick_metrics.get("at_least_one_set_rate")
    sample = pick_metrics.get("sample", 0)

    win_rate = pick_metrics.get("win_rate")

    if win_rate is not None and sample >= 5 and win_rate >= 0.65:
        signals.append("✅ Strong recent form")

    if set_rate is not None and sample >= 5 and set_rate >= 0.75:
        signals.append("🎯 Strong over 0.5 set signal")

    elif set_rate is not None and sample >= 5 and set_rate >= 0.60:
        signals.append("✅ Medium over 0.5 set signal")

    if avg_aces is not None and sample >= 5 and avg_aces >= 5:
        signals.append("💣 High ace profile")

    if ace_rate is not None and sample >= 5 and ace_rate >= 0.07:
        signals.append("💣 High ace rate")

    if (
        avg_aces is not None
        and opp_avg_aces is not None
        and sample >= 5
        and avg_aces - opp_avg_aces >= 1.5
    ):
        signals.append("💣 Ace edge vs opponent")

    if not signals:
        signals.append("Model winner pick only")

    return signals


def build_alternative_bets(pick, pick_metrics):
    alt_bets = []

    set_rate = pick_metrics.get("at_least_one_set_rate")
    sample = pick_metrics.get("sample", 0)

    avg_aces = pick_metrics.get("avg_aces")

    if set_rate is not None and sample >= 5:
        if set_rate >= 0.75:
            alt_bets.append({
                "market": "Player to win over 0.5 sets",
                "pick": pick,
                "probability": round(set_rate, 3),
                "confidence": "STRONG",
                "sample": sample,
                "note": f"{pick} historically won at least one set in {round(set_rate * 100, 1)}% of tracked matches"
            })
        elif set_rate >= 0.60:
            alt_bets.append({
                "market": "Player to win over 0.5 sets",
                "pick": pick,
                "probability": round(set_rate, 3),
                "confidence": "MEDIUM",
                "sample": sample,
                "note": f"{pick} historically won at least one set in {round(set_rate * 100, 1)}% of tracked matches"
            })

    if avg_aces is not None and sample >= 5 and avg_aces >= 5:
        alt_bets.append({
            "market": "Ace profile watch",
            "pick": pick,
            "probability": None,
            "confidence": "WATCH",
            "sample": sample,
            "note": f"{pick} has high ace profile: {avg_aces} avg aces"
        })

    return alt_bets


def passes_quality_gate(pred):
    prob = pred.get("probability", 0)
    market_agrees = pred.get("market_agrees", False)
    value_edge = pred.get("bookie_value_edge")
    market_prob = pred.get("market_probability")
    signals = pred.get("extra_signals", [])

    strong_set = "🎯 Strong over 0.5 set signal" in signals
    medium_set = "✅ Medium over 0.5 set signal" in signals
    ace_edge = "💣 Ace edge vs opponent" in signals
    strong_form = "✅ Strong recent form" in signals

    # Najistejšie: model aj bookie sa zhodujú
    if prob >= 0.56 and market_agrees:
        return True

    # Trh tiež vidí hráča ako dosť silného
    if market_prob is not None and market_prob >= 0.54 and prob >= 0.55:
        return True

    # Value edge podľa reálnych kurzov
    if value_edge is not None and value_edge >= 0.04 and prob >= 0.54:
        return True

    # Silný zostavový / setový signál
    if prob >= 0.53 and (strong_set or ace_edge or strong_form):
        return True

    if prob >= 0.55 and medium_set:
        return True

    return False


def get_match_fields(match):
    if isinstance(match, dict):
        return {
            "player1": match["player1"],
            "player2": match["player2"],
            "tournament": match.get("tournament", "Tennis"),
            "odds_player1": match.get("odds_player1"),
            "odds_player2": match.get("odds_player2"),
            "odds_source": match.get("odds_source", "unknown"),
            "match_start": match.get("match_start"),
            "match_time_raw": match.get("match_time_raw")
        }

    p1, p2, tournament = match

    return {
        "player1": p1,
        "player2": p2,
        "tournament": tournament,
        "odds_player1": None,
        "odds_player2": None,
        "odds_source": "missing",
        "match_start": None,
        "match_time_raw": None
    }


def get_daily_predictions():
    raw_matches = get_today_matches()

    if not raw_matches:
        print("NO REAL MATCHES FOUND")
        return []

    matches = [get_match_fields(m) for m in raw_matches]

    players = []

    for m in matches:
        if m["player1"] not in players:
            players.append(m["player1"])
        if m["player2"] not in players:
            players.append(m["player2"])

    stats_map, surface_map = get_stats_context(players, matches)

    predictions = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        tournament = m["tournament"]

        odds1 = m.get("odds_player1")
        odds2 = m.get("odds_player2")

        base_prob1 = win_probability(p1, p2)
        base_prob2 = 1 - base_prob1

        match_key = f"{p1}::{p2}"
        surface = surface_map.get(match_key, "Unknown")

        p1_stats = stats_map.get(p1, {})
        p2_stats = stats_map.get(p2, {})

        p1_metrics = metric_for_surface(p1_stats, surface)
        p2_metrics = metric_for_surface(p2_stats, surface)

        # Form adjustment
        prob1 = base_prob1

        p1_win = p1_metrics.get("win_rate")
        p2_win = p2_metrics.get("win_rate")

        p1_set = p1_metrics.get("at_least_one_set_rate")
        p2_set = p2_metrics.get("at_least_one_set_rate")

        boost = 0

        if p1_win is not None and p2_win is not None:
            boost += (p1_win - p2_win) * 0.10

        if p1_set is not None and p2_set is not None:
            boost += (p1_set - p2_set) * 0.04

        boost = max(-0.08, min(0.08, boost))

        prob1 = max(0.05, min(0.95, prob1 + boost))
        prob2 = 1 - prob1

        if prob1 >= prob2:
            pick = p1
            opponent = p2
            pick_probability = prob1
            opponent_probability = prob2
            pick_metrics = p1_metrics
            opponent_metrics = p2_metrics
        else:
            pick = p2
            opponent = p1
            pick_probability = prob2
            opponent_probability = prob1
            pick_metrics = p2_metrics
            opponent_metrics = p1_metrics

        confidence = abs(pick_probability - 0.5)

        odds_info = classify_bookie_signal(
            pick=pick,
            p1=p1,
            p2=p2,
            model_prob=pick_probability,
            odds1=odds1,
            odds2=odds2
        )

        pick_odds = odds_info["pick_odds"]
        implied_probability = round(1 / pick_odds, 3) if pick_odds else None

        extra_signals = classify_extra_signal(pick_metrics, opponent_metrics)
        alternative_bets = build_alternative_bets(pick, pick_metrics)

        score = (pick_probability * 0.60) + (confidence * 0.10)

        if odds_info["market_agrees"]:
            score += 0.06

        if odds_info["bookie_value_edge"] is not None and odds_info["bookie_value_edge"] > 0.03:
            score += 0.05

        if "🎯 Strong over 0.5 set signal" in extra_signals:
            score += 0.08

        if "✅ Medium over 0.5 set signal" in extra_signals:
            score += 0.04

        if "✅ Strong recent form" in extra_signals:
            score += 0.05

        if "💣 Ace edge vs opponent" in extra_signals:
            score += 0.04

        if "💣 High ace profile" in extra_signals:
            score += 0.02

        pred = {
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "surface": surface,

            "pick": pick,
            "opponent": opponent,

            "probability": round(pick_probability, 3),
            "opponent_probability": round(opponent_probability, 3),
            "confidence": round(confidence, 3),

            "odds": pick_odds,
            "odds_player1": odds1,
            "odds_player2": odds2,
            "odds_source": m.get("odds_source"),
            "implied_probability": implied_probability,
            "market_probability": odds_info["market_probability"],
            "market_agrees": odds_info["market_agrees"],
            "bookie_value_edge": odds_info["bookie_value_edge"],
            "overround": odds_info["overround"],
            "bookie_signal": odds_info["bookie_signal"],

            "match_start": m.get("match_start"),
            "match_time_raw": m.get("match_time_raw"),

            "score": round(score, 3),

            "pick_stats": stats_map.get(pick, {}),
            "opponent_stats": stats_map.get(opponent, {}),
            "pick_metrics": pick_metrics,
            "opponent_metrics": opponent_metrics,
            "extra_signals": extra_signals,
            "alternative_bets": alternative_bets
        }

        if passes_quality_gate(pred):
            predictions.append(pred)

    predictions.sort(key=lambda x: x["score"], reverse=True)

    final = predictions[:TOP_N]

    print("FINAL PICKS:", len(final))

    for p in final:
        print(
            "PICK:",
            p["pick"],
            "to beat",
            p["opponent"],
            "| prob:",
            p["probability"],
            "| odds:",
            p["odds"],
            "| market_prob:",
            p["market_probability"],
            "| value_edge:",
            p["bookie_value_edge"],
            "| market_agrees:",
            p["market_agrees"],
            "| signals:",
            p["extra_signals"]
        )

    return final
