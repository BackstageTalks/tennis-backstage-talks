from fetch_matches import get_today_matches
from welo import win_probability
from stats_engine import get_stats_context


TOP_N = 7


def fair_market_probs(odds1, odds2):
    if not odds1 or not odds2:
        return None, None, None

    try:
        raw1 = 1 / float(odds1)
        raw2 = 1 / float(odds2)
    except Exception:
        return None, None, None

    overround = raw1 + raw2

    if overround <= 0:
        return None, None, None

    fair1 = raw1 / overround
    fair2 = raw2 / overround

    return fair1, fair2, overround


def calculate_ev(probability, odds):
    """
    EV je iba informačné číslo.
    EV = Win % * odds - 1
    """
    if odds is None:
        return None

    try:
        return round((float(probability) * float(odds)) - 1, 3)
    except Exception:
        return None


def classify_bookie_signal(pick, p1, p2, model_prob, odds1, odds2):
    """
    Kurz / bookmaker / market sú iba informačné údaje.
    Nepoužívajú sa na TOP winner poradie.
    """
    fair1, fair2, overround = fair_market_probs(odds1, odds2)

    if fair1 is None or fair2 is None:
        return {
            "pick_odds": None,
            "market_probability": None,
            "market_agrees": False,
            "bookie_value_edge": None,
            "overround": None,
            "bookie_signal": "NO_ODDS",
            "market_warning": "NO_ODDS"
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

    market_warning = None

    if value_edge >= 0.25:
        market_warning = "EXTREME_MODEL_MARKET_GAP"
    elif value_edge >= 0.15:
        market_warning = "HIGH_MODEL_MARKET_GAP"
    elif not market_agrees:
        market_warning = "MODEL_AGAINST_MARKET"

    if market_agrees and model_prob >= 0.57:
        signal = "MARKET_AND_MODEL_AGREE"
    elif not market_agrees:
        signal = "MODEL_AGAINST_MARKET"
    else:
        signal = "NEUTRAL_MARKET"

    return {
        "pick_odds": round(float(pick_odds), 3),
        "market_probability": round(market_probability, 3),
        "market_agrees": market_agrees,
        "bookie_value_edge": round(value_edge, 3),
        "overround": round(overround, 3),
        "bookie_signal": signal,
        "market_warning": market_warning
    }


def metric_for_surface(player_stats, surface):
    """
    Stats nechávame ako info.
    Nepoužívame ich na zmenu TOP winner poradia.
    """
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
    """
    Signály sú iba info.
    Neovplyvňujú TOP winner poradie.
    """
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
    """
    Alternatívne trhy ostávajú iba ako info.
    Neovplyvňujú winner pick.
    """
    alt_bets = []

    set_rate = pick_metrics.get("at_least_one_set_rate")
