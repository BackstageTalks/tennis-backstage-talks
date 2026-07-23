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
from src.bst_ai.service import build_bst_ai_comparison
from src.marq_ai import build_marq_from_match
from mcp_module import build_mcp_player_stats, mcp_adjustment
from tennisapi_set_markets import get_set_markets
from sets_model import build_market_aware_sets
from tennisapi_h2h import build_h2h_context


TOP_N = 5
MIN_ODDS = 1.50
MIN_TOP_PROBABILITY = 0.0

LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value):
    try:
        if value is None or value == "":
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

            return dt.astimezone(LOCAL_TZ).strftime("%H:%M")

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
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))

        return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d")

    except Exception:
        text = str(start_value)
        if len(text) >= 10:
            return text[:10]

    return None


def normalize_match(match):
    match_id = match.get("match_id") or match.get("event_id") or match.get("id")

    return {
        "match_id": match_id,
        "event_id": match_id,
        "id": match_id,
        "player1": match.get("player1"),
        "player2": match.get("player2"),
        "surface": match.get("surface"),
        "tournament": match.get("tournament"),
        "category": match.get("category"),
        "gender": match.get("gender"),
        "best_of": match.get("best_of"),
        "match_start": match.get("match_start"),
        "start_time": match.get("start_time"),
        "commence_time": match.get("commence_time"),
        "time": format_match_time(match),
    }


def infer_surface(surface_map, player1, player2, match):
    if match.get("surface"):
        return match.get("surface")

    return surface_map.get(f"{player1}::{player2}") or "Hard"


def build_safe_marq_ai(
    match,
    player1,
    player2,
    pick,
    odds_player1=None,
    odds_player2=None,
):
    match_date = format_match_date(match)

    if not match_date:
        print("MARQ DEBUG: match_date missing", player1, "vs", player2)
        return None

    try:
        return build_marq_from_match(
            player1=player1,
            player2=player2,
            date_only=match_date,
            pick=pick,
            odds_player1=odds_player1,
            odds_player2=odds_player2,
            event_id=match.get("event_id") or match.get("match_id") or match.get("id"),
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



def derive_marq_display_fields(marq_ai, model_probability):
    def as_float(value):
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    pick_pct = as_float(marq_ai.get("marq_crowd_pick_pct"))
    if pick_pct is None:
        pick_pct = as_float(marq_ai.get("marq_pick_pct"))

    model_pct = as_float(model_probability)
    if model_pct is not None and model_pct <= 1.0:
        model_pct *= 100.0

    edge_pct = None
    if model_pct is not None and pick_pct is not None:
        edge_pct = round(model_pct - pick_pct, 1)

    initial_pick = as_float(marq_ai.get("marq_initial_pick_odds"))
    current_pick = as_float(marq_ai.get("marq_current_pick_odds"))
    if initial_pick is None:
        initial_pick = as_float(marq_ai.get("marq_opening"))
    if current_pick is None:
        current_pick = as_float(marq_ai.get("marq_latest"))

    move_pct = as_float(marq_ai.get("marq_move_pct"))
    if move_pct is None:
        move_pct = as_float(marq_ai.get("marq_market_move_pct"))
    if move_pct is not None:
        move_pct = abs(move_pct)

    if move_pct is None and initial_pick and current_pick and initial_pick > 1 and current_pick > 1:
        move_pct = abs((current_pick - initial_pick) / initial_pick) * 100.0

    move_signal = marq_ai.get("marq_move_signal")
    move_range = marq_ai.get("marq_move_range")

    if initial_pick and current_pick and initial_pick > 1 and current_pick > 1:
        same_odds = abs(current_pick - initial_pick) < 0.0001
        if move_pct is None and not same_odds:
            move_pct = abs((current_pick - initial_pick) / initial_pick) * 100.0
        if move_range is None and not same_odds:
            move_range = f"{initial_pick:.2f} -> {current_pick:.2f}"
        if not move_signal or str(move_signal).upper() in {"UNKNOWN", "STABLE"}:
            if move_pct is None or move_pct < 2.0:
                move_signal = "Stable"
            else:
                if move_pct < 6.0:
                    strength = "Slight"
                elif move_pct < 12.0:
                    strength = "Medium"
                else:
                    strength = "Strong"
                direction = "Toward" if current_pick < initial_pick else "Against"
                move_signal = f"{strength} {direction}"

    return {
        "marq_edge_pct": edge_pct,
        "marq_move_pct": round(move_pct, 1) if move_pct is not None else None,
        "marq_move_range": move_range,
        "marq_display_move_signal": move_signal,
    }


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

    prob1 = safe_float(elo_prediction.get("probability_player1"))
    prob2 = safe_float(elo_prediction.get("probability_player2"))

    if prob1 is None:
        prob1 = 0.5

    if prob2 is None:
        prob2 = 0.5

    odds1 = safe_float(
        odds_data.get("odds_player1")
        or odds_data.get("p1_odds")
        or odds_data.get("home_odds")
        or odds_data.get("odds1")
        or odds_data.get("price1")
    )

    odds2 = safe_float(
        odds_data.get("odds_player2")
        or odds_data.get("p2_odds")
        or odds_data.get("away_odds")
        or odds_data.get("odds2")
        or odds_data.get("price2")
    )

    form1 = get_player_form(form_store, player1, surface)
    form2 = get_player_form(form_store, player2, surface)

    if prob1 >= prob2:
        pick = player1
        opponent = player2
        base_probability = prob1
        pick_odds = odds1
    else:
        pick = player2
        opponent = player1
        base_probability = prob2
        pick_odds = odds2

    form_adjustment = calculate_form_adjustment(
        pick_form=form1,
        opponent_form=form2,
    )

    final_probability = base_probability + form_adjustment["total_adjustment"]

    final_probability += mcp_adjustment(pick, mcp_stats)
    final_probability -= mcp_adjustment(opponent, mcp_stats)

    final_probability = clamp(final_probability, 0.15, 0.85)

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
        odds_player1=odds1,
        odds_player2=odds2,
    )

    if not isinstance(marq_ai, dict):
        marq_ai = {}

    set_markets = {}

    try:
        event_id = match.get("event_id") or match.get("match_id") or match.get("id")

        if event_id:
            set_markets = get_set_markets(int(event_id))

    except Exception as exc:
        print("SETS MARKET ERROR:", player1, "vs", player2, str(exc))
        set_markets = {}

    sets_info = build_market_aware_sets(
        match=match,
        elo_prediction=elo_prediction,
        odds_data=odds_data,
        set_markets=set_markets,
    )

    h2h_info = {}
    try:
        event_id = match.get("event_id") or match.get("match_id") or match.get("id")
        h2h_info = build_h2h_context(
            event_id=event_id,
            player1=player1,
            player2=player2,
            pick=pick,
            surface=surface,
        )
    except Exception as exc:
        print("H2H ERROR:", player1, "vs", player2, str(exc))
        h2h_info = {}

    marq_display = derive_marq_display_fields(marq_ai, final_probability)

    # Keep tag simple; TOP5 selection is handled in prediction_engine_top.py.
    bet_tag = "INFO ONLY"

    return {
        "match_id": match.get("match_id"),
        "event_id": match.get("event_id"),
        "match": f"{player1} vs {player2}",
        "pick": pick,
        "opponent": opponent,
        "player1": player1,
        "player2": player2,
        "tournament": match.get("tournament"),
        "gender": match.get("gender"),
        "best_of": match.get("best_of") or 3,
        "surface": surface,
        "probability": round(final_probability, 3),

        # DATA AI / Corq / Thinq.
        "corq_ai_probability": bst_ai.get("corq_ai_probability"),
        "bst_ai_probability": bst_ai.get("bst_ai_probability"),
        "ai_match": bst_ai.get("ai_match"),
        "ai_gap": bst_ai.get("ai_gap"),
        "ai_signed_gap": bst_ai.get("ai_signed_gap"),
        "ai_lean": bst_ai.get("ai_lean"),
        "ai_direction_match": bst_ai.get("ai_direction_match"),
        "ai_match_color": bst_ai.get("ai_match_color"),
        "bst_ai_status": bst_ai.get("bst_ai_status"),
        "bst_ai_reason": bst_ai.get("bst_ai_reason"),
        "bst_ai_rating_type": bst_ai.get("bst_ai_rating_type"),
        "bst_player1_found": bst_ai.get("bst_player1_found"),
        "bst_player2_found": bst_ai.get("bst_player2_found"),

        # ------------------------------------------------------------------
        # MARQ legacy fields.
        # ------------------------------------------------------------------
        "marq_ai_score": marq_ai.get("marq_ai_score"),
        "marq_ai_signal": marq_ai.get("marq_ai_signal"),
        "marq_ai_direction": marq_ai.get("marq_ai_direction"),
        "marq_ai_strength": marq_ai.get("marq_ai_strength"),
        "marq_ai_consistency": marq_ai.get("marq_ai_consistency"),
        "marq_ai_reason": marq_ai.get("marq_ai_reason"),
        "marq_event_id": marq_ai.get("marq_event_id"),
        "marq_outcome_key": marq_ai.get("marq_outcome_key"),
        "marq_source": marq_ai.get("marq_source"),
        "marq_market_name": marq_ai.get("marq_market_name"),
        "marq_opening": marq_ai.get("marq_opening"),
        "marq_latest": marq_ai.get("marq_latest"),
        "marq_market_move_pct": marq_ai.get("marq_market_move_pct"),
        "marq_probability_change_pp": marq_ai.get("marq_probability_change_pp"),
        "marq_opponent_move_pct": marq_ai.get("marq_opponent_move_pct"),

        # ------------------------------------------------------------------
        # MARQ v1 MARKET VIEW fields.
        # ------------------------------------------------------------------
        "marq_market_view": marq_ai.get("marq_market_view"),

        "marq_crowd_player1_pct": marq_ai.get("marq_crowd_player1_pct"),
        "marq_crowd_player2_pct": marq_ai.get("marq_crowd_player2_pct"),
        "marq_crowd_pick_pct": marq_ai.get("marq_crowd_pick_pct"),
        "marq_crowd_opponent_pct": marq_ai.get("marq_crowd_opponent_pct"),

        "marq_move_signal": marq_ai.get("marq_move_signal"),
        "marq_sharp_signal": marq_ai.get("marq_sharp_signal"),
        "marq_sharp_pick_pct": marq_ai.get("marq_sharp_pick_pct"),
        "marq_quality_signal": marq_ai.get("marq_quality_signal"),
        "marq_clv_status": marq_ai.get("marq_clv_status"),

        "marq_provider_count": marq_ai.get("marq_provider_count"),
        "marq_market_spread_pct": marq_ai.get("marq_market_spread_pct"),
        "marq_market_median_odds": marq_ai.get("marq_market_median_odds"),
        "marq_outlier_count": marq_ai.get("marq_outlier_count"),

        "marq_initial_pick_odds": marq_ai.get("marq_initial_pick_odds"),
        "marq_current_pick_odds": marq_ai.get("marq_current_pick_odds"),
        "marq_initial_opponent_odds": marq_ai.get("marq_initial_opponent_odds"),
        "marq_current_opponent_odds": marq_ai.get("marq_current_opponent_odds"),

        # Clean MARQ UI fields.
        "marq_edge_pct": marq_ai.get("marq_edge_pct") or marq_display.get("marq_edge_pct"),
        "marq_move_pct": marq_ai.get("marq_move_pct") or marq_display.get("marq_move_pct"),
        "marq_move_range": marq_ai.get("marq_move_range") or marq_display.get("marq_move_range"),
        "marq_display_move_signal": marq_ai.get("marq_display_move_signal") or marq_display.get("marq_display_move_signal"),

        "marq_exchange_available": marq_ai.get("marq_exchange_available"),
        "marq_exchange_provider": marq_ai.get("marq_exchange_provider"),
        "marq_exchange_market_id": marq_ai.get("marq_exchange_market_id"),
        "marq_exchange_total_matched": marq_ai.get("marq_exchange_total_matched"),
        "marq_exchange_total_available": marq_ai.get("marq_exchange_total_available"),
        "marq_exchange_pick_price": marq_ai.get("marq_exchange_pick_price"),
        "marq_exchange_opponent_price": marq_ai.get("marq_exchange_opponent_price"),

        # H2H history context, informational only. No impact on pick or probability.
        "h2h_total_matches": h2h_info.get("h2h_total_matches"),
        "h2h_pick_wins": h2h_info.get("h2h_pick_wins"),
        "h2h_opponent_wins": h2h_info.get("h2h_opponent_wins"),
        "h2h_pick_win_pct": h2h_info.get("h2h_pick_win_pct"),
        "h2h_same_surface_matches": h2h_info.get("h2h_same_surface_matches"),
        "h2h_same_surface_pick_wins": h2h_info.get("h2h_same_surface_pick_wins"),
        "h2h_same_surface_pick_win_pct": h2h_info.get("h2h_same_surface_pick_win_pct"),
        "h2h_signal": h2h_info.get("h2h_signal"),
        "h2h_adjustment": h2h_info.get("h2h_adjustment"),
        "h2h_adjustment_pct": h2h_info.get("h2h_adjustment_pct"),
        "h2h_component_pct": h2h_info.get("h2h_component_pct"),
        "thinq_h2h_pct": h2h_info.get("thinq_h2h_pct"),
        "h2h_display_pct": h2h_info.get("thinq_h2h_pct"),
        "h2h_reason": h2h_info.get("h2h_reason"),
        "h2h_recent_result": h2h_info.get("h2h_recent_result"),
        "h2h_endpoint_path": h2h_info.get("h2h_endpoint_path"),

        # Core model fields.
        "base_probability": round(base_probability, 3),
        "odds": pick_odds,
        "odds_player1": odds1,
        "odds_player2": odds2,
        "time": match.get("time"),
        "match_start": match.get("match_start"),

        # Odds metadata.
        "bookmaker": odds_data.get("bookmaker"),
        "odds_source": odds_data.get("odds_source") or odds_data.get("source"),
        "odds_event_id": odds_data.get("event_id") or odds_data.get("match_id"),
        "odds_matching_direction": odds_data.get("matching_direction"),
        "odds_matching_score": odds_data.get("matching_score"),
        "no_odds_reason": odds_data.get("no_odds_reason"),
        "fallback_tried_sources": odds_data.get("fallback_tried_sources"),

        # Sets model.
        "expected_sets": sets_info.get("expected_sets"),
        "sets_probability": sets_info.get("sets_probability"),
        "sets_probability_label": sets_info.get("sets_probability_label"),
        "set_win_probability": None,
        "most_likely_score": sets_info.get("most_likely_score"),
        "most_likely_score_probability": sets_info.get("most_likely_score_probability"),
        "score_probabilities": sets_info.get("score_probabilities"),
        "score_basis": sets_info.get("score_basis"),

        # First set market enrichment.
        "first_set_player1_odds": sets_info.get("first_set_player1_odds"),
        "first_set_player2_odds": sets_info.get("first_set_player2_odds"),
        "first_set_player1_probability": sets_info.get("first_set_player1_probability"),
        "first_set_player2_probability": sets_info.get("first_set_player2_probability"),

        # Games and tie-break market enrichment.
        "expected_games": sets_info.get("expected_games"),
        "games_pick": sets_info.get("games_pick"),
        "games_line": sets_info.get("games_line"),
        "games_over_odds": sets_info.get("games_over_odds"),
        "games_under_odds": sets_info.get("games_under_odds"),
        "games_over_probability": sets_info.get("games_over_probability"),
        "games_under_probability": sets_info.get("games_under_probability"),
        "tie_break_yes_odds": sets_info.get("tie_break_yes_odds"),
        "tie_break_no_odds": sets_info.get("tie_break_no_odds"),
        "tie_break_probability": sets_info.get("tie_break_probability"),
        "sets_model_source": sets_info.get("sets_model_source"),

        # Misc.
        "bet_tag": bet_tag,
        "form_adjustment": form_adjustment.get("total_adjustment"),
        "top_mode": None,
        "top_reason": None,
    }


def build_all_predictions():
    raw_matches = get_today_matches()

    matches = [normalize_match(match) for match in raw_matches]
    matches = [match for match in matches if match["player1"] and match["player2"]]

    players = []

    for match in matches:
        players.append(match["player1"])
        players.append(match["player2"])

    try:
        stats_map, surface_map = get_stats_context(players, matches)
    except Exception as exc:
        print("STATS CONTEXT ERROR:", str(exc))
        surface_map = {}

    elo_store = load()
    form_store = load_form_store()
    odds_matches = fetch_odds()

    print(
        "PREDICTION ODDS LIST COUNT:",
        len(odds_matches) if isinstance(odds_matches, list) else "invalid",
    )

    mcp_stats = build_mcp_player_stats()

    all_predictions = []
    odds_hit_count = 0
    odds_miss_count = 0

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

        odds_data = find_match_odds(odds_matches, match)

        if odds_data:
            odds_hit_count += 1
        else:
            odds_miss_count += 1

            if odds_miss_count <= 20:
                print(
                    "ODDS MATCH MISS:",
                    match.get("player1"),
                    "vs",
                    match.get("player2"),
                    "match_id:",
                    match.get("match_id"),
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

    print("ODDS MATCH HITS:", odds_hit_count)
    print("ODDS MATCH MISSES:", odds_miss_count)

    all_predictions.sort(
        key=lambda item: item.get("probability", 0),
        reverse=True,
    )

    return all_predictions


def get_top_predictions(all_predictions=None):
    if all_predictions is None:
        all_predictions = build_all_predictions()

    eligible = [
        prediction
        for prediction in all_predictions
        if prediction.get("odds") is not None and prediction.get("odds") > MIN_ODDS
    ]

    eligible.sort(
        key=lambda item: item.get("probability", 0),
        reverse=True,
    )

    return eligible[:TOP_N]


def get_daily_predictions():
    return get_top_predictions()
