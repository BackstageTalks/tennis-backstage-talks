from datetime import datetime
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

from src.bst_ai.service import (
    build_bst_ai_comparison,
)

from src.marq_ai import (
    build_marq_from_match,
)

from mcp_module import build_mcp_player_stats, mcp_adjustment


TOP_N = 5

MIN_ODDS = 1.50

MIN_TOP_PROBABILITY = 0.0

LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
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
                dt = dt.replace(
                    tzinfo=ZoneInfo("UTC"),
                )

            local_dt = dt.astimezone(
                LOCAL_TZ,
            )

            return local_dt.strftime("%H:%M")

        except Exception:
            pass

    return "TBD"


def format_match_date(match):
    start_value = (
        match.get("match_start")
        or match.get("start_time")
        or match.get("commence_time")
    )

    if not start_value:
        return None

    try:
        text = str(start_value)

        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=ZoneInfo("UTC"),
            )

        local_dt = dt.astimezone(
            LOCAL_TZ,
        )

        return local_dt.strftime("%Y-%m-%d")

    except Exception:
        text = str(start_value)

        if len(text) >= 10:
            return text[:10]

    return None


def normalize_match(match):
    return {
        "player1": match.get("player1"),
        "player2": match.get("player2"),
        "surface": match.get("surface"),
        "tournament": match.get("tournament"),
        "gender": match.get("gender"),
        "best_of": match.get("best_of"),
        "match_start": match.get("match_start"),
        "time": format_match_time(match),
    }


def infer_surface(surface_map, player1, player2, match):
    if match.get("surface"):
        return match.get("surface")

    key = f"{player1}::{player2}"

    return surface_map.get(key) or "Hard"


def build_safe_marq_ai(match, player1, player2, pick):
    match_date = format_match_date(match)

    if not match_date:
        print(
            "MARQ DEBUG: match_date missing",
            player1,
            "vs",
            player2,
        )

        return None

    try:
        return build_marq_from_match(
            player1=player1,
            player2=player2,
            date_only=match_date,
            pick=pick,
        )

    except Exception as exc:
        print(
            "MARQ AI ERROR:",
            player1,
            "vs",
            player2,
            "pick:",
            pick,
            "date:",
            match_date,
            str(exc),
        )

        return None


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

    odds_data = odds_data or {}

    prob1 = safe_float(
        elo_prediction.get("probability_player1")
    )

    prob2 = safe_float(
        elo_prediction.get("probability_player2")
    )

    if prob1 is None:
        prob1 = 0.5

    if prob2 is None:
        prob2 = 0.5

    odds1 = safe_float(
        odds_data.get("odds_player1"),
    )

    odds2 = safe_float(
        odds_data.get("odds_player2"),
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
        base_probability
        + form_adjustment["total_adjustment"]
    )

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
        tournament=match.get("tournament"),
        best_of=match.get("best_of"),
    )

    bet_tag = (
        match_info.get("tag")
        or match_info.get("bet_tag")
        or "INFO ONLY"
    )

    bst_ai = build_bst_ai_comparison(
        player1=player1,
        player2=player2,
        pick=pick,
        surface=surface,
        corq_probability=final_probability,
        tour=match.get("gender"),
    )

    marq_ai = build_safe_marq_ai(
        match=match,
        player1=player1,
        player2=player2,
        pick=pick,
    )

    return {
        "match": f"{player1} vs {player2}",
        "pick": pick,
        "opponent": opponent,

        "player1": player1,
        "player2": player2,

        "tournament": match.get("tournament"),
        "gender": match.get("gender"),
        "best_of": match_info.get("best_of"),
        "surface": surface,

        "probability": round(
            final_probability,
            3,
        ),

        "corq_ai_probability": bst_ai.get(
            "corq_ai_probability"
        ),

        "bst_ai_probability": bst_ai.get(
            "bst_ai_probability"
        ),

        "ai_match": bst_ai.get(
            "ai_match"
        ),

        "ai_gap": bst_ai.get(
            "ai_gap"
        ),

        "ai_signed_gap": bst_ai.get(
            "ai_signed_gap"
        ),

        "ai_lean": bst_ai.get(
            "ai_lean"
        ),

        "ai_direction_match": bst_ai.get(
            "ai_direction_match"
        ),

        "ai_match_color": bst_ai.get(
            "ai_match_color"
        ),

        "bst_ai_status": bst_ai.get(
            "bst_ai_status"
        ),

        "bst_ai_reason": bst_ai.get(
            "bst_ai_reason"
        ),

        "bst_ai_rating_type": bst_ai.get(
            "bst_ai_rating_type"
        ),

        "bst_player1_found": bst_ai.get(
            "bst_player1_found"
        ),

        "bst_player2_found": bst_ai.get(
            "bst_player2_found"
        ),

        "marq_ai_score": getattr(
            marq_ai,
            "score",
            None,
        ),

        "marq_ai_signal": getattr(
            marq_ai,
            "signal",
            None,
        ),

        "marq_ai_direction": getattr(
            marq_ai,
            "direction",
            None,
        ),

        "marq_ai_strength": getattr(
            marq_ai,
            "strength",
            None,
        ),

        "marq_ai_consistency": getattr(
            marq_ai,
            "consistency",
            None,
        ),

        "base_probability": round(
            base_probability,
            3,
        ),

        "odds": odds,

        "time": match.get("time"),
        "match_start": match.get("match_start"),

        "bookmaker": odds_data.get("bookmaker"),
        "odds_source": odds_data.get("odds_source"),

        "expected_sets":
            match_info.get("expected_sets"),

        "sets_probability":
            match_info.get("sets_probability"),

        "sets_probability_label":
            match_info.get("sets_probability_label"),

        "set_win_probability":
            match_info.get("set_win_probability"),

        "most_likely_score":
            match_info.get("most_likely_score"),

        "most_likely_score_probability":
            match_info.get("most_likely_score_probability"),

        "score_probabilities":
            match_info.get("score_probabilities"),

        "expected_games":
            match_info.get("expected_games"),

        "games_pick":
            match_info.get("games_pick"),

        "games_line":
            match_info.get("games_line"),

        "bet_tag": bet_tag,

        "form_adjustment":
            form_adjustment.get("total_adjustment"),

        "top_mode": None,
        "top_reason": None,
    }


def build_all_predictions():
    raw_matches = get_today_matches()

    matches = [
        normalize_match(match)
        for match in raw_matches
    ]

    matches = [
        match
        for match in matches
        if match["player1"] and match["player2"]
    ]

    players = []

    for match in matches:
        players.append(match["player1"])
        players.append(match["player2"])

    try:
        stats_map, surface_map = get_stats_context(
            players,
            matches,
        )

    except Exception as exc:
        print(
            "STATS CONTEXT ERROR:",
            str(exc),
        )

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

        prediction = build_prediction_record(
            match,
            surface,
            elo_prediction,
            odds_data,
            form_store,
            mcp_stats,
        )

        all_predictions.append(prediction)

    all_predictions.sort(
        key=lambda item: item.get(
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
        prediction
        for prediction in all_predictions
        if prediction.get("odds") is not None
        and prediction.get("odds") > MIN_ODDS
    ]

    eligible.sort(
        key=lambda item: item.get(
            "probability",
            0,
        ),
        reverse=True,
    )

    return eligible[:TOP_N]


def get_daily_predictions():
    return get_top_predictions()
