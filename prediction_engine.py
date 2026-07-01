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
MIN_ODDS = 1.50

# Bootstrap threshold.
# Start lower to collect enough real candidates.
# We will tighten this after 100-300 settled PLAY candidates.
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

    raw = (
        match.get("match_time_raw")
        or match.get("time")
        or match.get("match_time")
    )

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
            "odds_player1": safe_float(match.get("odds_player1")),
            "odds_player2": safe_float(match.get("odds_player2")),
            "odds_source": match.get("odds_source"),
            "match_start": match.get("match_start"),
            "match_time_raw": match.get("match_time_raw"),
            "time": format_match_time(match),
        }

    return {
        "player1": match[0] if len(match) > 0 else None,
        "player2": match[1] if len(match) > 1 else None,
        "tournament": match[2] if len(match) > 2 else "Tennis",
        "odds_player1": None,
        "odds_player2": None,
        "odds_source": None,
        "match_start": None,
        "match_time_raw": None,
        "time": "TBD",
    }


def infer_surface(surface_map, player1, player2):
    key = f"{player1}::{player2}"
    return surface_map.get(key, "Hard")


def is_best_of_five(tournament):
    text = str(tournament or "").lower()

    if "wta" in text or "women" in text or "women's" in text:
        return False

    if "wimbledon" in text:
        return True

    if "grand slam" in text and ("atp" in text or "men" in text):
        return True

    return False


def build_sets_games_info(probability, tournament):
    if probability is None:
        return {
            "bo_format": None,
            "most_likely_sets": None,
            "sets_probability": None,
            "sets_fair_odds": None,
            "expected_games": None,
            "games_lean": None,
            "note": "INFO ONLY - not used for TOP selection",
        }

    p = clamp(probability, 0.05, 0.95)
    edge = abs(p - 0.5)

    bo_format = "BO5" if is_best_of_five(tournament) else "BO3"

    if bo_format == "BO5":
        over_3_5 = clamp(0.76 - edge * 0.90, 0.34, 0.82)
        under_3_5 = 1 - over_3_5

        over_4_5 = clamp(0.45 - edge * 0.70, 0.15, 0.50)

        expected_games = round(clamp(39.5 - edge * 22.0, 29.0, 46.0), 1)

        if over_4_5 >= 0.43:
            most_likely_sets = "5 sets"
            sets_probability = over_4_5
        elif over_3_5 >= 0.55:
            most_likely_sets = "4+ sets"
            sets_probability = over_3_5
        else:
            most_likely_sets = "3 sets"
            sets_probability = under_3_5

        sets_fair_odds = round(1 / sets_probability, 2)

        if expected_games >= 39.0:
            games_lean = "Over 38.5"
        elif expected_games <= 36.5:
            games_lean = "Under 37.5"
        else:
            games_lean = "No clear games lean"

        return {
            "bo_format": "BO5",
            "most_likely_sets": most_likely_sets,
            "sets_probability": round(sets_probability, 3),
            "sets_fair_odds": sets_fair_odds,
            "expected_games": expected_games,
            "games_lean": games_lean,
            "note": "INFO ONLY - not used for TOP selection",
        }

    over_2_5 = clamp(0.62 - edge * 1.00, 0.32, 0.62)
    under_2_5 = 1 - over_2_5

    expected_games = round(clamp(23.0 - edge * 11.0, 18.0, 24.5), 1)

    if over_2_5 >= under_2_5:
        most_likely_sets = "3 sets"
        sets_probability = over_2_5
    else:
        most_likely_sets = "2 sets"
        sets_probability = under_2_5

    sets_fair_odds = round(1 / sets_probability, 2)

    if expected_games >= 22.2:
        games_lean = "Over 21.5"
    elif expected_games <= 20.8:
        games_lean = "Under 21.5"
    else:
        games_lean = "No clear games lean"

    return {
        "bo_format": "BO3",
        "most_likely_sets": most_likely_sets,
        "sets_probability": round(sets_probability, 3),
        "sets_fair_odds": sets_fair_odds,
        "expected_games": expected_games,
        "games_lean": games_lean,
        "note": "INFO ONLY - not used for TOP selection",
    }


def infer_odds_source(match, odds_data, odds1, odds2):
    odds_source = match.get("odds_source") or odds_data.get("odds_source")

    if odds_source:
        return odds_source

    if odds1 is not None or odds2 is not None:
        return "embedded_match_odds"

    return None


def build_prediction_record(match, surface, elo_prediction, odds_data, form_store):
    player1 = match["player1"]
    player2 = match["player2"]
    tournament = match.get("tournament", "Tennis")

    prob1 = elo_prediction["probability_player1"]
    prob2 = elo_prediction["probability_player2"]

    odds1 = safe_float(match.get("odds_player1"))
    odds2 = safe_float(match.get("odds_player2"))

    if odds1 is None:
        odds1 = safe_float(odds_data.get("odds_player1"))

    if odds2 is None:
        odds2 = safe_float(odds_data.get("odds_player2"))

    odds_source = infer_odds_source(match, odds_data, odds1, odds2)

    form1 = get_player_form(form_store, player1, surface)
    form2 = get_player_form(form_store, player2, surface)

    if prob1 >= prob2:
        pick = player1
        opponent = player2
        base_probability = prob1
        odds = odds1
        elo_player = elo_prediction.get("elo_player1")
        elo_opponent = elo_prediction.get("elo_player2")
        pick_form = form1
        opponent_form = form2
    else:
        pick = player2
        opponent = player1
        base_probability = prob2
        odds = odds2
        elo_player = elo_prediction.get("elo_player2")
        elo_opponent = elo_prediction.get("elo_player1")
        pick_form = form2
        opponent_form = form1

    form_adjustment = calculate_form_adjustment(
        pick_form=pick_form,
        opponent_form=opponent_form,
    )

    adjusted_probability = clamp(
        base_probability + form_adjustment["total_adjustment"],
        0.15,
        0.85,
    )

    alternative_market_info = build_sets_games_info(
        probability=adjusted_probability,
        tournament=tournament,
    )

    return {
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}",
        "pick": pick,
        "opponent": opponent,
        "tournament": tournament,
        "surface": surface,

        "base_probability": round(base_probability, 3),
        "probability": round(adjusted_probability, 3),
        "opponent_probability": round(1 - adjusted_probability, 3),
        "confidence": round(abs(adjusted_probability - 0.5), 3),
        "score": round(adjusted_probability, 3),
        "winner_rank_score": round(adjusted_probability, 3),

        "selection_threshold": MIN_TOP_PROBABILITY,

        "odds": odds,
        "odds_player1": odds1,
        "odds_player2": odds2,
        "odds_source": odds_source,
        "odds_match_score": odds_data.get("match_score"),
        "bookmaker": odds_data.get("bookmaker"),
        "odds_event_id": odds_data.get("event_id"),

        "market_probability": round(1 / odds, 3) if odds else None,
        "bookie_value_edge": None,
        "ev_score": None,
        "ev_percent": None,
        "market_agrees": None,
        "bookie_signal": "NOT_USED",
        "market_warning": "NOT_USED",
        "overround": None,

        "elo_player": round(elo_player, 1) if elo_player is not None else None,
        "elo_opponent": round(elo_opponent, 1) if elo_opponent is not None else None,
        "elo_player1": round(elo_prediction.get("elo_player1"), 1) if elo_prediction.get("elo_player1") is not None else None,
        "elo_player2": round(elo_prediction.get("elo_player2"), 1) if elo_prediction.get("elo_player2") is not None else None,

        "overall_elo_player1": elo_prediction.get("overall_elo_player1"),
        "overall_elo_player2": elo_prediction.get("overall_elo_player2"),
        "surface_elo_player1": elo_prediction.get("surface_elo_player1"),
        "surface_elo_player2": elo_prediction.get("surface_elo_player2"),

        "elo_found_player1": elo_prediction.get("elo_found_player1"),
        "elo_found_player2": elo_prediction.get("elo_found_player2"),
        "elo_matched_key_player1": elo_prediction.get("elo_matched_key_player1"),
        "elo_matched_key_player2": elo_prediction.get("elo_matched_key_player2"),
        "elo_matches_player1": elo_prediction.get("elo_matches_player1"),
        "elo_matches_player2": elo_prediction.get("elo_matches_player2"),
        "surface_matches_player1": elo_prediction.get("surface_matches_player1"),
        "surface_matches_player2": elo_prediction.get("surface_matches_player2"),
        "elo_reliability_player1": elo_prediction.get("elo_reliability_player1"),
        "elo_reliability_player2": elo_prediction.get("elo_reliability_player2"),
        "surface_reliability_player1": elo_prediction.get("surface_reliability_player1"),
        "surface_reliability_player2": elo_prediction.get("surface_reliability_player2"),

        "form_player1": form1,
        "form_player2": form2,
        "form_pick": pick_form,
        "form_opponent": opponent_form,
        "form_adjustment": form_adjustment,

        "model_source": "CUSTOM_ELO_FORM",
        "model_version": f"{elo_prediction.get('model', 'CUSTOM_ELO')}_FORM_V1",
        "bet_tag": None,

        "match_start": match.get("match_start"),
        "match_time_raw": match.get("match_time_raw"),
        "time": match.get("time", "TBD"),

        "short_reason": "Surface-aware calibrated Elo with recent/surface form adjustment. Odds used only as strict TOP filter.",
        "extra_signals": [
            "Custom calibrated Elo",
            "Surface-aware Elo",
            "Recent form adjustment",
            "Surface form adjustment",
            "Reliability penalty",
            "Odds used only as strict TOP filter",
            "No EV",
            "No market edge",
            "No WELO",
            "Sets/games are INFO ONLY",
        ],
        "alternative_market_info": alternative_market_info,
        "alternative_bets": [],
    }


def build_all_predictions():
    raw_matches = get_today_matches()

    print("RAW MATCHES:", len(raw_matches) if raw_matches else 0)

    if not raw_matches:
        print("NO MATCHES FOUND")
        return []

    matches = [normalize_match(m) for m in raw_matches]
    matches = [m for m in matches if m.get("player1") and m.get("player2")]

    print("NORMALIZED MATCHES:", len(matches))

    players = []

    for match in matches:
        if match["player1"] not in players:
            players.append(match["player1"])
        if match["player2"] not in players:
            players.append(match["player2"])

    try:
        stats_map, surface_map = get_stats_context(players, matches)
    except Exception as e:
        print("STATS CONTEXT ERROR:", e)
        surface_map = {}

    elo_store = load()
    form_store = load_form_store()
    odds_matches = fetch_odds()

    print("ELO STORE PLAYERS:", len(elo_store))
    print("FORM STORE PLAYERS:", len(form_store))
    print("ODDS MATCHES RAW:", len(odds_matches))

    all_predictions = []

    for match in matches:
        player1 = match["player1"]
        player2 = match["player2"]

        surface = infer_surface(surface_map, player1, player2)

        elo_prediction = predict(
            player1,
            player2,
            surface,
            elo_store
        )

        odds_data = find_match_odds(player1, player2, odds_matches)

        prediction = build_prediction_record(
            match=match,
            surface=surface,
            elo_prediction=elo_prediction,
            odds_data=odds_data,
            form_store=form_store,
        )

        all_predictions.append(prediction)

    all_predictions.sort(
        key=lambda x: x.get("probability") or 0,
        reverse=True
    )

    print("ALL MATCHES:", len(all_predictions))
    print("WITH ODDS:", sum(1 for p in all_predictions if p.get("odds") is not None))
    print("ELO FOUND BOTH:", sum(1 for p in all_predictions if p.get("elo_found_player1") and p.get("elo_found_player2")))
    print("ELO MISSING:", sum(1 for p in all_predictions if not (p.get("elo_found_player1") and p.get("elo_found_player2"))))
    print("WITH FORM ADJUSTMENT:", sum(1 for p in all_predictions if p.get("form_adjustment")))

    return all_predictions


def get_top_predictions(all_predictions=None):
    if all_predictions is None:
        all_predictions = build_all_predictions()

    eligible = [
        prediction for prediction in all_predictions
        if prediction.get("odds") is not None
        and prediction.get("odds") >= MIN_ODDS
        and prediction.get("probability") is not None
        and prediction.get("probability") >= MIN_TOP_PROBABILITY
        and prediction.get("elo_found_player1")
        and prediction.get("elo_found_player2")
    ]

    eligible.sort(
        key=lambda x: (
            x.get("probability") or 0,
            min(
                x.get("elo_reliability_player1") or 0,
                x.get("elo_reliability_player2") or 0,
            ),
        ),
        reverse=True
    )

    top_predictions = eligible[:TOP_N]

    print("TOP ELIGIBLE:", len(eligible))
    print("TOP COUNT:", len(top_predictions))

    return top_predictions


def get_daily_predictions():
    return get_top_predictions()
