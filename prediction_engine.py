from fetch_matches import get_today_matches
from welo import win_probability
from stats_engine import get_stats_context


TOP_N = 7
TARGET_DAILY_BETS = 5
MAX_LOW_CONFIDENCE_FILL = 2


def clamp(value, low, high):
    return max(low, min(high, value))


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
    EV je iba kontrola hodnoty kurzu.
    EV = Win probability * decimal odds - 1
    """
    if odds is None:
        return None

    try:
        return round((float(probability) * float(odds)) - 1, 3)
    except Exception:
        return None


def consensus_probability(our_prob, market_prob):
    """
    Cieľ:
    - ak je náš model plochý okolo 50 %, viac rešpektovať market
    - ak má náš model jasný názor, stále ho zohľadniť
    - pravdepodobnosť používame na winner výber
    """
    if market_prob is None:
        return clamp(our_prob, 0.05, 0.95), "WELO_FALLBACK"

    edge = abs(our_prob - 0.5)

    if edge < 0.03:
        our_weight = 0.25
        market_weight = 0.75
        source = "CONSENSUS_MARKET_HEAVY"
    elif edge < 0.06:
        our_weight = 0.40
        market_weight = 0.60
        source = "CONSENSUS_BALANCED"
    else:
        our_weight = 0.60
        market_weight = 0.40
        source = "CONSENSUS_WELO_LEAN"

    final_prob = (our_prob * our_weight) + (market_prob * market_weight)

    return clamp(final_prob, 0.05, 0.95), source


def classify_bookie_signal(pick, p1, p2, model_prob, odds1, odds2):
    fair1, fair2, overround = fair_market_probs(odds1, odds2)

    if fair1 is None or fair2 is None:
        return {
            "pick_odds": None,
            "market_probability": None,
            "market_agrees": False,
            "bookie_value_edge": None,
            "overround": None,
            "bookie_signal": "NO_ODDS",
            "market_warning": "NO_ODDS",
            "fair1": None,
            "fair2": None,
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
        "market_warning": market_warning,
        "fair1": fair1,
        "fair2": fair2,
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
    """
    Iba informačné signály.
    Nepoužívajú sa na TOP výber.
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
    Staršie alternatívne info.
    Stále iba info.
    """
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


def build_alternative_market_info(probability, bo_format="BO3"):
    """
    Informačný blok pre sety/gemy.
    Nepoužíva sa v TOP výbere ani v bet_tag logike.
    """
    fav_edge = abs(probability - 0.5)

    if bo_format == "BO5":
        over_3_5 = clamp(0.78 - (fav_edge * 0.85), 0.35, 0.82)
        over_4_5 = clamp(0.48 - (fav_edge * 0.70), 0.18, 0.52)

        expected_games = round(clamp(39.5 - (fav_edge * 22.0), 30.0, 45.0), 1)

        games_line = 38.5
        games_prob = clamp(0.50 + ((expected_games - games_line) * 0.035), 0.35, 0.72)

        if games_prob >= 0.5:
            games_lean = "Over 38.5"
            games_fair_odds = round(1 / games_prob, 2)
        else:
            games_lean = "Under 38.5"
            games_fair_odds = round(1 / (1 - games_prob), 2)

        return {
            "bo_format": "BO5",
            "over_2_5_sets_probability": None,
            "under_2_5_sets_probability": None,
            "over_3_5_sets_probability": round(over_3_5, 3),
            "under_3_5_sets_probability": round(1 - over_3_5, 3),
            "over_4_5_sets_probability": round(over_4_5, 3),
            "expected_games": expected_games,
            "games_lean": games_lean,
            "games_fair_odds": games_fair_odds,
            "note": "INFO ONLY - not used in winner selection"
        }

    over_2_5 = clamp(0.62 - (fav_edge * 0.95), 0.32, 0.62)
    under_2_5 = 1 - over_2_5

    expected_games = round(clamp(23.2 - (fav_edge * 12.0), 18.0, 24.5), 1)

    if expected_games >= 22.0:
        games_line = 21.5
    elif expected_games >= 21.0:
        games_line = 20.5
    else:
        games_line = 19.5

    games_prob = clamp(0.50 + ((expected_games - games_line) * 0.055), 0.35, 0.72)

    if games_prob >= 0.5:
        games_lean = f"Over {games_line}"
        games_fair_odds = round(1 / games_prob, 2)
    else:
        games_lean = f"Under {games_line}"
        games_fair_odds = round(1 / (1 - games_prob), 2)

    return {
        "bo_format": "BO3",
        "over_2_5_sets_probability": round(over_2_5, 3),
        "under_2_5_sets_probability": round(under_2_5, 3),
        "over_3_5_sets_probability": None,
        "under_3_5_sets_probability": None,
        "over_4_5_sets_probability": None,
        "expected_games": expected_games,
        "games_lean": games_lean,
        "games_fair_odds": games_fair_odds,
        "note": "INFO ONLY - not used in winner selection"
    }


def data_quality_from_metrics(pick_metrics, opponent_metrics):
    pick_sample = pick_metrics.get("sample", 0) or 0
    opponent_sample = opponent_metrics.get("sample", 0) or 0
    total_sample = pick_sample + opponent_sample

    if pick_sample >= 8 and opponent_sample >= 8:
        return "HIGH"

    if pick_sample >= 4 and opponent_sample >= 4:
        return "MEDIUM"

    if total_sample >= 5:
        return "LOW"

    return "VERY_LOW"


def win_tier(probability):
    if probability >= 0.70:
        return "A++"

    if probability >= 0.65:
        return "A+"

    if probability >= 0.60:
        return "A"

    if probability >= 0.57:
        return "B"

    if probability >= 0.55:
        return "C+"

    if probability >= 0.535:
        return "C"

    if probability >= 0.52:
        return "D"

    return "RISK"


def build_model_flags(probability, odds_info, data_quality, ev_score):
    flags = []

    odds = odds_info.get("pick_odds")
    market_warning = odds_info.get("market_warning")

    if probability >= 0.70:
        flags.append("A_PLUS_PLUS_WIN_PROB")
    elif probability >= 0.65:
        flags.append("A_PLUS_WIN_PROB")
    elif probability >= 0.60:
        flags.append("A_WIN_PROB")
    elif probability >= 0.57:
        flags.append("B_WIN_PROB")
    elif probability >= 0.55:
        flags.append("C_PLUS_WIN_PROB")
    elif probability >= 0.535:
        flags.append("C_WIN_PROB")
    elif probability >= 0.52:
        flags.append("D_WIN_PROB")
    else:
        flags.append("LOW_WIN_EDGE")

    if data_quality == "HIGH":
        flags.append("HIGH_DATA")
    elif data_quality == "MEDIUM":
        flags.append("MEDIUM_DATA")
    elif data_quality == "LOW":
        flags.append("LOW_DATA")
    else:
        flags.append("VERY_LOW_DATA")

    if odds is None:
        flags.append("NO_ODDS")
    elif odds < 1.20:
        flags.append("VERY_LOW_ODDS")
    elif odds < 1.35:
        flags.append("LOW_ODDS")
    elif 1.45 <= odds <= 2.30:
        flags.append("IDEAL_ODDS_RANGE")
    elif odds >= 4.0:
        flags.append("LONGSHOT_ODDS")

    if ev_score is None:
        flags.append("NO_EV")
    elif ev_score >= 0.05:
        flags.append("POSITIVE_EV_TRACK_ONLY")
    elif ev_score < -0.15:
        flags.append("BAD_NEGATIVE_EV")
    elif ev_score < 0:
        flags.append("NEGATIVE_EV_TRACK_ONLY")

    if market_warning:
        flags.append(market_warning)

    return flags


def build_bet_tag(probability, odds, ev_score, model_flags):
    """
    Praktické odporúčanie.

    Zásada:
    - hlavná pracovná kurzová zóna je 1.45–2.30
    - nízke kurzy <1.35 väčšinou nejdú do PLAY
    - EV je brzda proti zlému kurzu
    """

    if probability < 0.535:
        return "❌ NO BET"

    if odds is None:
        if probability >= 0.65:
            return "👀 WATCH / NO ODDS"
        return "❌ NO BET / NO ODDS"

    # tvrdé stopky
    if odds < 1.20:
        return "👀 WATCH / VERY LOW VALUE"

    if odds >= 4.0 and probability < 0.65:
        return "👀 WATCH / LONGSHOT"

    if "EXTREME_MODEL_MARKET_GAP" in model_flags and probability < 0.60:
        return "👀 WATCH / MODEL WARNING"

    # nízke kurzy: nie hlavné bety
    if odds < 1.35:
        if probability >= 0.78 and ev_score is not None and ev_score >= -0.05:
            return "⚠️ PLAY SMALL / LOW ODDS"
        return "👀 WATCH / LOW VALUE"

    # hranično nízke, ale použiteľné len pri silnej šanci
    if 1.35 <= odds < 1.45:
        if probability >= 0.70 and (ev_score is None or ev_score >= -0.10):
            return "⚠️ PLAY SMALL / LOW ODDS"
        if probability >= 0.65 and (ev_score is None or ev_score >= -0.06):
            return "⚠️ PLAY SMALL / LOW ODDS"
        return "👀 WATCH / LOW VALUE"

    # ideálna zóna
    if 1.45 <= odds <= 2.30:
        if probability >= 0.65 and (ev_score is None or ev_score >= -0.08):
            return "🔥 HOT PLAY"

        if probability >= 0.60 and (ev_score is None or ev_score >= -0.10):
            return "✅ STANDARD PLAY"

        if probability >= 0.57 and (ev_score is None or ev_score >= -0.12):
            return "⚠️ PLAY SMALL"

        if probability >= 0.55 and (ev_score is None or ev_score >= -0.15):
            return "⚠️ LOW CONFIDENCE FILL"

        return "👀 WATCH"

    # vyššie kurzy
    if 2.30 < odds <= 3.50:
        if probability >= 0.65 and (ev_score is None or ev_score >= -0.05):
            return "✅ STANDARD PLAY / HIGHER ODDS"

        if probability >= 0.60 and (ev_score is None or ev_score >= -0.10):
            return "⚠️ PLAY SMALL / HIGHER ODDS"

        if probability >= 0.57 and (ev_score is None or ev_score >= -0.05):
            return "⚠️ PLAY SMALL / HIGHER ODDS"

        return "👀 WATCH / HIGHER RISK"

    # longshot safety
    if odds > 3.50:
        if probability >= 0.70 and (ev_score is None or ev_score >= 0):
            return "⚠️ PLAY SMALL / LONGSHOT"
        return "👀 WATCH / LONGSHOT"

    return "❌ NO BET"


def build_short_reason(probability, odds, ev_score, bet_tag, model_flags, probability_source):
    reasons = []

    if probability >= 0.70:
        reasons.append("very strong Win %")
    elif probability >= 0.65:
        reasons.append("strong Win %")
    elif probability >= 0.60:
        reasons.append("good Win %")
    elif probability >= 0.57:
        reasons.append("acceptable Win %")
    elif probability >= 0.55:
        reasons.append("play small range")
    elif probability >= 0.535:
        reasons.append("low confidence fill range")
    else:
        reasons.append("too close to coinflip")

    if odds is None:
        reasons.append("no odds available")
    elif odds < 1.20:
        reasons.append("very low odds")
    elif odds < 1.35:
        reasons.append("low odds / low value")
    elif 1.45 <= odds <= 2.30:
        reasons.append("ideal odds range")
    elif odds > 3.50:
        reasons.append("longshot odds")

    if ev_score is not None:
        if ev_score >= 0.05:
            reasons.append("positive EV tracking")
        elif ev_score < -0.15:
            reasons.append("bad negative EV warning")
        elif ev_score < -0.10:
            reasons.append("negative EV warning")

    if probability_source:
        reasons.append(f"probability source: {probability_source}")

    if "EXTREME_MODEL_MARKET_GAP" in model_flags:
        reasons.append("extreme model-market gap")
    elif "HIGH_MODEL_MARKET_GAP" in model_flags:
        reasons.append("high model-market gap")

    return "; ".join(reasons)


def bet_priority(pred):
    tag = str(pred.get("bet_tag", ""))

    if tag.startswith("🔥 HOT PLAY"):
        return 1

    if tag.startswith("✅ STANDARD PLAY"):
        return 2

    if tag.startswith("⚠️ PLAY SMALL"):
        return 3

    if tag.startswith("⚠️ LOW CONFIDENCE FILL"):
        return 4

    return 99


def is_fill_candidate(pred):
    tag = str(pred.get("bet_tag", ""))
    probability = pred.get("probability", 0)
    odds = pred.get("odds")

    if odds is None:
        return False

    if not tag.startswith("⚠️ LOW CONFIDENCE FILL"):
        return False

    if probability < 0.55:
        return False

    if odds < 1.45 or odds > 2.80:
        return False

    return True


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
            "match_time_raw": match.get("match_time_raw"),
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
        "match_time_raw": None,
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

    all_predictions = []

    for m in matches:
        p1 = m["player1"]
        p2 = m["player2"]
        tournament = m["tournament"]

        odds1 = m.get("odds_player1")
        odds2 = m.get("odds_player2")

        our_prob1 = clamp(win_probability(p1, p2), 0.05, 0.95)
        fair1, fair2, _ = fair_market_probs(odds1, odds2)

        consensus_prob1, probability_source = consensus_probability(our_prob1, fair1)
        consensus_prob2 = 1 - consensus_prob1

        match_key = f"{p1}::{p2}"
        surface = surface_map.get(match_key, "Unknown")

        p1_stats = stats_map.get(p1, {})
        p2_stats = stats_map.get(p2, {})

        p1_metrics = metric_for_surface(p1_stats, surface)
        p2_metrics = metric_for_surface(p2_stats, surface)

        if consensus_prob1 >= consensus_prob2:
            pick = p1
            opponent = p2
            pick_probability = consensus_prob1
            opponent_probability = consensus_prob2
            pick_metrics = p1_metrics
            opponent_metrics = p2_metrics
            pick_our_probability = our_prob1
            pick_market_probability_raw = fair1
        else:
            pick = p2
            opponent = p1
            pick_probability = consensus_prob2
            opponent_probability = consensus_prob1
            pick_metrics = p2_metrics
            opponent_metrics = p1_metrics
            pick_our_probability = 1 - our_prob1
            pick_market_probability_raw = fair2

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
        ev_score = calculate_ev(pick_probability, pick_odds)

        extra_signals = classify_extra_signal(pick_metrics, opponent_metrics)
        alternative_bets = build_alternative_bets(pick, pick_metrics)
        alternative_market_info = build_alternative_market_info(pick_probability, bo_format="BO3")

        data_quality = data_quality_from_metrics(pick_metrics, opponent_metrics)

        model_flags = build_model_flags(
            probability=pick_probability,
            odds_info=odds_info,
            data_quality=data_quality,
            ev_score=ev_score
        )

        bet_tag = build_bet_tag(
            probability=pick_probability,
            odds=pick_odds,
            ev_score=ev_score,
            model_flags=model_flags
        )

        short_reason = build_short_reason(
            probability=pick_probability,
            odds=pick_odds,
            ev_score=ev_score,
            bet_tag=bet_tag,
            model_flags=model_flags,
            probability_source=probability_source
        )

        tier = win_tier(pick_probability)

        score = pick_probability

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

            "score": round(score, 3),
            "winner_rank_score": round(score, 3),

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
            "market_warning": odds_info["market_warning"],

            "ev_score": ev_score,
            "ev_percent": round(ev_score * 100, 1) if ev_score is not None else None,

            "bet_tag": bet_tag,
            "short_reason": short_reason,
            "win_tier": tier,
            "data_quality": data_quality,
            "model_flags": model_flags,

            "model_source": probability_source,
            "our_model_probability": round(pick_our_probability, 3),
            "market_probability_raw": round(pick_market_probability_raw, 3) if pick_market_probability_raw is not None else None,

            "base_probability_player1": round(our_prob1, 3),
            "consensus_probability_player1": round(consensus_prob1, 3),
            "stats_boost_player1": 0.0,

            "match_start": m.get("match_start"),
            "match_time_raw": m.get("match_time_raw"),

            "pick_stats": stats_map.get(pick, {}),
            "opponent_stats": stats_map.get(opponent, {}),
            "pick_metrics": pick_metrics,
            "opponent_metrics": opponent_metrics,
            "extra_signals": extra_signals,
            "alternative_bets": alternative_bets,
            "alternative_market_info": alternative_market_info,
        }

        all_predictions.append(pred)

    # Sort pre TOP/TG logiku:
    # 1. HOT
    # 2. STANDARD
    # 3. PLAY SMALL
    # 4. LOW CONFIDENCE FILL
    all_predictions.sort(
        key=lambda x: (
            bet_priority(x),
            -x.get("probability", 0)
        )
    )

    hot = [
        p for p in all_predictions
        if str(p.get("bet_tag", "")).startswith("🔥 HOT PLAY")
    ]

    standard = [
        p for p in all_predictions
        if str(p.get("bet_tag", "")).startswith("✅ STANDARD PLAY")
    ]

    small = [
        p for p in all_predictions
        if str(p.get("bet_tag", "")).startswith("⚠️ PLAY SMALL")
    ]

    fill = [
        p for p in all_predictions
        if is_fill_candidate(p)
    ]

    final = []

    # 1. HOT PLAY
    for p in hot:
        if len(final) < TOP_N:
            final.append(p)

    # 2. STANDARD PLAY
    for p in standard:
        if len(final) < TOP_N:
            final.append(p)

    # 3. PLAY SMALL len do targetu
    for p in small:
        if len(final) < TARGET_DAILY_BETS:
            final.append(p)

    # 4. LOW CONFIDENCE FILL max 1–2 denne
    low_confidence_added = 0

    for p in fill:
        if len(final) >= TARGET_DAILY_BETS:
            break

        if low_confidence_added >= MAX_LOW_CONFIDENCE_FILL:
            break

        p["bet_tag"] = "⚠️ PLAY SMALL / LOW CONFIDENCE FILL"
        p["short_reason"] = str(p.get("short_reason", "")) + "; selected to reach daily target"

        final.append(p)
        low_confidence_added += 1

    final = final[:TOP_N]

    print("FINAL RECOMMENDED PICKS:", len(final))

    if not final:
        print("NO RECOMMENDED PLAY BETS TODAY")

    for p in final:
        print(
            "PICK:",
            p["pick"],
            "to beat",
            p["opponent"],
            "| prob:",
            p["probability"],
            "| our_prob:",
            p.get("our_model_probability"),
            "| market_prob:",
            p.get("market_probability_raw"),
            "| source:",
            p["model_source"],
            "| tier:",
            p["win_tier"],
            "| odds:",
            p["odds"],
            "| ev:",
            p["ev_score"],
            "| bet_tag:",
            p["bet_tag"],
            "| reason:",
            p["short_reason"]
        )

    return final
