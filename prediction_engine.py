from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_source import load_tennis_abstract_elo, predict_match_with_tennis_abstract

TOP_N = 5
MIN_TOP_ODDS = 1.50


def safe_float(x):
    try:
        return float(x)
    except:
        return None


def is_main_tour(t):
    t = str(t).lower()

    if "atp" in t or "wta" in t:
        return True

    if "wimbledon" in t or "grand slam" in t:
        return True

    return False


