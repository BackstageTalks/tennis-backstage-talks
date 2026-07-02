from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_engine import load, predict
from odds_api import fetch_odds, find_match_odds
from form_engine import (
    load_form_store,
    get_player_form,
    calculate_form_adjustment,
)

from src.models.match_intelligence import (
    build_match_intelligence,
)

# MCP
from mcp_module import build_mcp_player_stats, mcp_adjustment


TOP_N = 5
MIN_ODDS = 1.45
MIN_TOP_PROBABILITY = 0.57

LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def format_match_time(match):
    start_value = (
        match.get("match_start")
        or match.get("start_time")
        or match.get("commence_time")
    )

    if start_value:
        try:
            text = str(start_value)

            if text.endswith("Z"):
                text = text.replace("Z", "+00:00")

            dt = datetime.fromisoformat(text)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))

            local_dt = dt.astimezone(LOCAL_TZ)
            return local_dt.strftime("%H:%M")
        except Exception:
            pass

    return "TBD"


def normalize_match(match):
    return {
        "player1": match.get("player1"),
        "player2": match.get("player2"),
        "surface": match.get("surface"),
        "tournament": match.get("tournament"),
        "match_start": match.get("match_start"),
        "time": format_match_time(match),
    }


def infer_surface(surface_map, p1, p2, match):
    if match.get("surface"):
        return match.get("surface")

    key = f"{p1}::{p2}"
    return surface_map.get(key) or "Hard"


def build_prediction_record(
    match,
    surface,
    elo_prediction,
    odds_data,
    form_store,
    mcp_stats,
):
    player1 = match["player1"]
    player2 = match["player2"]

    prob1 = elo_prediction["probability_player1"]
    prob2 = elo_prediction["probability_player2"]

    odds1 = safe_float(
        odds_data.get("odds_player1")
    )

    odds2 = safe_float(
        odds_data.get("odds_player2")
    )

    form1 = get_player_form(
        form_store,
        player1,
        surface,
    )

    form2 = get_player_form(
        form_store,
        player2,
        surface,
    )

    if prob1 >= prob2:
        pick = player1
        opponent = player2
        base_probability = prob1
        odds = odds1

    else:
        pick = player2
        opponent = player1
        base_probability = prob2
        odds = odds2

    form_adjustment = calculate_form_adjustment(
        pick_form=form1,
        opponent_form=form2,
    )

    final_probability = (
        base_probability +
        form_adjustment["total_adjustment"]
    )

    # MCP BOOST

    final_probability += mcp_adjustment(
        pick,
        mcp_stats,
    )

    final_probability -= mcp_adjustment(
        opponent,
        mcp_stats,
    )

    final_probability = clamp(
        final_probability,
        0.15,
        0.85,
    )

    match_info = build_match_intelligence(
        probability=final_probability,
        odds=odds,
    )

    return {
        "match": f"{player1} vs {player2}",
        "pick": pick,
        "opponent": opponent,

        "probability": round(
            final_probability,
            3,
        ),

        "odds": odds,

        "time": match.get("time"),

        "expected_sets":
            match_info["expected_sets"],

        "sets_probability":
            match_info["sets_probability"],

        "expected_games":
            match_info["expected_games"],

        "games_pick":
            match_info["games_pick"],

        "games_line":
            match_info["games_line"],

        "bet_tag":
            match_info["tag"],
    }


def build_all_predictions():
    raw_matches = get_today_matches()

    matches = [
        normalize_match(m)
        for m in raw_matches
    ]

    matches = [
        m for m in matches
        if m["player1"] and m["player2"]
    ]

    players = []

    for m in matches:
        players.append(m["player1"])
        players.append(m["player2"])

    try:
        stats_map, surface_map = get_stats_context(
            players,
            matches,
        )

    except Exception:
        surface_map = {}

    elo_store = load()
    form_store = load_form_store()
    odds_matches = fetch_odds()

    mcp_stats = build_mcp_player_stats()

    all_predictions = []

    for match in matches:

        surface = infer_surface(
            surface_map,
            match["player1"],
            match["player2"],
            match,
        )

        elo_prediction = predict(
            match["player1"],
            match["player2"],
            surface,
            elo_store,
        )

        odds_data = find_match_odds(
            match["player1"],
            match["player2"],
            odds_matches,
        )

        pred = build_prediction_record(
            match,
            surface,
            elo_prediction,
            odds_data,
            form_store,
            mcp_stats,
        )

        all_predictions.append(pred)

    all_predictions.sort(
        key=lambda x: x.get(
            "probability",
            0,
        ),
        reverse=True,
    )

    return all_predictions


def get_top_predictions(all_predictions=None):

    if all_predictions is None:
        all_predictions = build_all_predictions()

    eligible = [
        p for p in all_predictions
        if p.get("odds") is not None
        and p.get("odds") >= MIN_ODDS
        and p.get("probability") >= MIN_TOP_PROBABILITY
    ]

    return eligible[:TOP_N]


def get_daily_predictions():
    return get_top_predictions()
