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
        or match.get("datetime")
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

            return local_dt.strftime("%d.%m.%Y %H:%M %Z")

        except Exception:
            pass

    raw = match.get("time")

    if raw:
        raw_text = str(raw).strip()

        for fmt in ["%I:%M %p", "%H:%M"]:
            try:
                parsed = datetime.strptime(raw_text, fmt)
                adjusted = parsed + timedelta(hours=2)
                return adjusted.strftime("%H:%M CEST")
            except Exception:
                continue

        return raw_text

    return "TBD"


def normalize_match(match):
    if isinstance(match, dict):
        return {
            "player1": match.get("player1"),
            "player2": match.get("player2"),
            "tournament": match.get("tournament", "Tennis"),
            "surface": match.get("surface"),
            "odds_player1": safe_float(match.get("odds_player1")),
            "odds_player2": safe_float(match.get("odds_player2")),
            "odds_source": match.get("odds_source"),
            "match_start": match.get("match_start"),
            "time": format_match_time(match),
        }

    return {
        "player1": match[0] if len(match) > 0 else None,
        "player2": match[1] if len(match) > 1 else None,
        "tournament": "Tennis",
        "surface": None,
        "odds_player1": None,
        "odds_player2": None,
        "odds_source": None,
        "match_start": None,
        "time": "TBD",
    }


def infer_surface(surface_map, player1, player2, match=None):
    if match and match.get("surface"):
        return match.get("surface")

    key = f"{player1}::{player2}"
    reverse_key = f"{player2}::{player1}"

    return (
        surface_map.get(key)
        or surface_map.get(reverse_key)
        or "Hard"
    )


def build_prediction_record(match, surface, elo_prediction, odds_data, form_store):
    player1 = match["player1"]
    player2 = match["player2"]

    prob1 = elo_prediction["probability_player1"]
    prob2 = elo_prediction["probability_player2"]

    odds1 = safe_float(match.get("odds_player1"))
    odds2 = safe_float(match.get("odds_player2"))

    if odds1 is None:
        odds1 = safe_float(odds_data.get("odds_player1"))

    if odds2 is None:
        odds2 = safe_float(odds_data.get("odds_player2"))

    form1 = get_player_form(form_store, player1, surface)
    form2 = get_player_form(form_store, player2, surface)

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

    final_probability = clamp(
        base_probability + form_adjustment["total_adjustment"],
        0.15,
        0.85,
    )

    return {
        "match": f"{player1} vs {player2}",
        "pick": pick,
        "opponent": opponent,
        "surface": surface,

        "base_probability": round(base_probability, 3),
        "probability": round(final_probability, 3),

        "odds": odds,
        "odds_source": odds_data.get("odds_source"),

        "elo_found_player1": elo_prediction.get("elo_found_player1"),
        "elo_found_player2": elo_prediction.get("elo_found_player2"),

        "elo_match_score_player1": elo_prediction.get("elo_match_score_player1"),
        "elo_match_score_player2": elo_prediction.get("elo_match_score_player2"),

        "time": match.get("time"),
    }


def build_all_predictions():
    raw_matches = get_today_matches()

    matches = [normalize_match(m) for m in raw_matches]
    matches = [m for m in matches if m.get("player1") and m.get("player2")]

    players = []
    for m in matches:
        players.append(m["player1"])
        players.append(m["player2"])

    try:
        stats_map, surface_map = get_stats_context(players, matches)
    except Exception:
        surface_map = {}

    elo_store = load()
    form_store = load_form_store()
    odds_matches = fetch_odds()

    all_predictions = []

    for match in matches:
        surface = infer_surface(
            surface_map,
            match["player1"],
            match["player2"],
            match
        )

        elo_prediction = predict(
            match["player1"],
            match["player2"],
            surface,
            elo_store
        )

        odds_data = find_match_odds(
            match["player1"],
            match["player2"],
            odds_matches
        )

        prediction = build_prediction_record(
            match,
            surface,
            elo_prediction,
            odds_data,
            form_store,
        )

        all_predictions.append(prediction)

    all_predictions.sort(
        key=lambda x: x.get("probability") or 0,
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
        and p.get("elo_found_player1")
        and p.get("elo_found_player2")
    ]

    eligible.sort(
        key=lambda x: x.get("probability"),
        reverse=True
    )

    return eligible[:TOP_N]


def get_daily_predictions():
    return get_top_predictions()
