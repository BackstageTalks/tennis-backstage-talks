import os
import re
from typing import Any, Dict, List, Optional, Tuple


TOP_N = int(os.getenv("TOP_N", "7"))
TOP_MIN_ODDS = float(os.getenv("TOP_MIN_ODDS", "1.40"))
TOP_MAX_ODDS = float(os.getenv("TOP_MAX_ODDS", "5.00"))

CORQ_SELECTOR_MIN_ODDS = float(os.getenv("CORQ_SELECTOR_MIN_ODDS", str(TOP_MIN_ODDS)))
CORQ_SELECTOR_MAX_ODDS = float(os.getenv("CORQ_SELECTOR_MAX_ODDS", str(TOP_MAX_ODDS)))

THINQ_MIN_ODDS = float(os.getenv("THINQ_MIN_ODDS", "1.60"))
THINQ_MAX_ODDS = float(os.getenv("THINQ_MAX_ODDS", str(TOP_MAX_ODDS)))

CLOQ_MIN_ODDS = float(os.getenv("CLOQ_MIN_ODDS", "1.60"))
CLOQ_MAX_ODDS = float(os.getenv("CLOQ_MAX_ODDS", "4.20"))
CLOQ_MAX_MARKET_GAP = float(os.getenv("CLOQ_MAX_MARKET_GAP", "0.15"))
CLOQ_CORQ_WEIGHT = float(os.getenv("CLOQ_CORQ_WEIGHT", "0.60"))
CLOQ_THINQ_WEIGHT = float(os.getenv("CLOQ_THINQ_WEIGHT", "0.40"))

CORQ_EDGE_BONUS_WEIGHT = float(os.getenv("CORQ_EDGE_BONUS_WEIGHT", "0.25"))
CORQ_EDGE_BONUS_CAP = float(os.getenv("CORQ_EDGE_BONUS_CAP", "0.02"))
CORQ_LOW_ODDS_GUARD_MAX_ODDS = float(os.getenv("CORQ_LOW_ODDS_GUARD_MAX_ODDS", "1.60"))
CORQ_LOW_ODDS_GUARD_MIN_Q = float(os.getenv("CORQ_LOW_ODDS_GUARD_MIN_Q", "0.75"))
CORQ_LOW_ODDS_GUARD_MIN_EDGE = float(os.getenv("CORQ_LOW_ODDS_GUARD_MIN_EDGE", "0.12"))
CORQ_LOW_ODDS_GUARD_PENALTY = float(os.getenv("CORQ_LOW_ODDS_GUARD_PENALTY", "0.06"))
CORQ_LOW_ODDS_EXTREME_EDGE = float(os.getenv("CORQ_LOW_ODDS_EXTREME_EDGE", "0.14"))
CORQ_LOW_ODDS_ELITE_AI_MATCH = float(os.getenv("CORQ_LOW_ODDS_ELITE_AI_MATCH", "95.0"))
CORQ_LOW_ODDS_EXTREME_PENALTY = float(os.getenv("CORQ_LOW_ODDS_EXTREME_PENALTY", "0.04"))

MODEL_CORQ = "corq"
MODEL_THINQ = "thinq"
MODEL_CLOQ = "cloq"

CORQ_RANKING_SCORE_KEYS = [
    "corq_adjusted_score",
    "corq_top_score",
    "corq_q_probability",
    "corq_thinq_adjusted_probability",
    "corq_ai_probability",
    "probability",
]


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def normalize_probability_decimal(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number > 1.0:
        return number / 100.0
    return number


def get_corq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("corq_q_probability")
        or prediction.get("corq_thinq_adjusted_probability")
        or prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )


def get_thinq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("bst_ai_probability")
        or prediction.get("thinq_ai_probability")
        or prediction.get("thinq_display_probability")
        or prediction.get("thinq_q_probability")
    )


def get_cloq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("cloq_probability")
        or prediction.get("cloq_ai_probability")
        or prediction.get("cloq_display_probability")
        or prediction.get("blend_ai_probability")
        or prediction.get("blenq_ai_probability")
    )


def get_ai_match(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("ai_match"))


def get_pick_odds(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("pick_odds") or prediction.get("odds"))


def get_odds_player1(prediction: Dict[str, Any]) -> Optional[float]:
    for key in ["odds_player1", "p1_odds", "home_odds", "odds1", "price1"]:
        value = safe_float(prediction.get(key))
        if value is not None:
            return value
    return None


def get_odds_player2(prediction: Dict[str, Any]) -> Optional[float]:
    for key in ["odds_player2", "p2_odds", "away_odds", "odds2", "price2"]:
        value = safe_float(prediction.get(key))
        if value is not None:
            return value
    return None


def normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def is_doubles_side(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = text.lower()
    return any(separator in lowered for separator in [" / ", " & ", " + ", " and "])


def is_doubles_prediction(prediction: Dict[str, Any]) -> bool:
    event_type = str(prediction.get("match_type") or prediction.get("event_type") or "").lower()
    if event_type == "doubles" or "doubles" in str(prediction.get("tournament") or "").lower():
        return True
    for key in ["player1", "player2", "pick", "opponent"]:
        if is_doubles_side(prediction.get(key)):
            return True
    match_text = str(prediction.get("match") or "")
    return " / " in match_text and " vs " in match_text.lower()


def has_required_dual_model_outputs(prediction: Dict[str, Any]) -> bool:
    return (
        get_corq_probability(prediction) is not None
        and get_thinq_probability(prediction) is not None
        and get_ai_match(prediction) is not None
    )


def has_valid_odds(prediction: Dict[str, Any], min_odds: float, max_odds: float) -> bool:
    odds = get_pick_odds(prediction)
    return odds is not None and min_odds <= odds <= max_odds


def market_break_even(odds: Optional[float]) -> Optional[float]:
    if odds is None or odds <= 1.0:
        return None
    return 1.0 / odds


def market_fair_probabilities(odds1: Optional[float], odds2: Optional[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if odds1 is None or odds2 is None or odds1 <= 1.0 or odds2 <= 1.0:
        return None, None, None
    implied1 = 1.0 / odds1
    implied2 = 1.0 / odds2
    total = implied1 + implied2
    if total <= 0:
        return None, None, None
    fair1 = implied1 / total
    fair2 = implied2 / total
    return fair1, fair2, abs(fair1 - fair2)


def get_existing_corq_score(prediction: Dict[str, Any]) -> Optional[float]:
    for key in CORQ_RANKING_SCORE_KEYS:
        value = safe_float(prediction.get(key))
        if value is not None:
            return value
    return None


def compute_corq_q(prediction: Dict[str, Any]) -> Optional[float]:
    explicit = normalize_probability_decimal(prediction.get("corq_q_probability"))
    if explicit is not None:
        return explicit
    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)
    if corq is None:
        return None
    if thinq is None:
        return corq
    return 0.80 * corq + 0.20 * thinq


def compute_corq_adjusted_score(prediction: Dict[str, Any], corq_q: float) -> Tuple[float, float, float, List[str]]:
    odds = get_pick_odds(prediction)
    break_even = market_break_even(odds)
    edge = corq_q - break_even if break_even is not None else 0.0
    ai_match = get_ai_match(prediction)

    bonus = min(max(edge, 0.0) * CORQ_EDGE_BONUS_WEIGHT, CORQ_EDGE_BONUS_CAP)
    penalty = 0.0
    flags: List[str] = []

    existing_flags = prediction.get("corq_risk_flags")
    if isinstance(existing_flags, list):
        flags.extend(str(flag) for flag in existing_flags)

    if odds is not None and odds < CORQ_LOW_ODDS_GUARD_MAX_ODDS and corq_q >= CORQ_LOW_ODDS_GUARD_MIN_Q and edge >= CORQ_LOW_ODDS_GUARD_MIN_EDGE:
        penalty += CORQ_LOW_ODDS_GUARD_PENALTY
        flags.append("LOW_ODDS_OVERCONFIDENCE")
        if edge >= CORQ_LOW_ODDS_EXTREME_EDGE and (ai_match is None or ai_match < CORQ_LOW_ODDS_ELITE_AI_MATCH):
            penalty += CORQ_LOW_ODDS_EXTREME_PENALTY
            flags.append("LOW_ODDS_EXTREME_EDGE_NOT_ELITE_AI_MATCH")

    score = corq_q + bonus - penalty
    return score, edge, bonus, flags


def build_corq_ranked_record(prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if is_doubles_prediction(prediction):
        return None
    if not has_required_dual_model_outputs(prediction):
        return None
    if not has_valid_odds(prediction, CORQ_SELECTOR_MIN_ODDS, CORQ_SELECTOR_MAX_ODDS):
        return None

    item = dict(prediction)
    corq_q = compute_corq_q(item)
    if corq_q is None:
        return None

    existing_score = safe_float(item.get("corq_adjusted_score") or item.get("corq_top_score"))
    score, edge, bonus, flags = compute_corq_adjusted_score(item, corq_q)
    if existing_score is not None:
        score = existing_score

    item["probability"] = round(corq_q, 4)
    item["corq_q_probability"] = round(corq_q, 4)
    item["corq_q_edge"] = round(edge, 4)
    item["corq_edge_bonus"] = round(safe_float(item.get("corq_edge_bonus")) if item.get("corq_edge_bonus") is not None else bonus, 4)
    item["corq_bonus"] = item["corq_edge_bonus"]
    item["corq_risk_penalty"] = round(safe_float(item.get("corq_risk_penalty")) or 0.0, 4)
    item["corq_risk_flags"] = flags
    item["corq_adjusted_score"] = round(score, 4)
    item["corq_top_score"] = round(score, 4)
    item["model_view"] = MODEL_CORQ
    item["top_mode"] = "CORQ_RANKED_TOP7"
    item["top_reason"] = "CORQ ranked eligible singles by finalized CORQ score; TOP7 is only the first TOP_N records."
    return item


def corq_rank_tuple(prediction: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return (
        safe_float(prediction.get("corq_adjusted_score")) or 0.0,
        safe_float(prediction.get("corq_q_probability")) or 0.0,
        safe_float(prediction.get("corq_q_edge")) or 0.0,
        safe_float(prediction.get("ai_match")) or 0.0,
    )


def thinq_ranked_record(prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if is_doubles_prediction(prediction):
        return None
    if not has_required_dual_model_outputs(prediction):
        return None
    if not has_valid_odds(prediction, THINQ_MIN_ODDS, THINQ_MAX_ODDS):
        return None
    thinq = get_thinq_probability(prediction)
    corq = get_corq_probability(prediction)
    if thinq is None or corq is None:
        return None
    item = dict(prediction)
    thinq_q = safe_float(item.get("thinq_q_probability"))
    if thinq_q is None:
        thinq_q = 0.80 * thinq + 0.20 * corq
    item["probability"] = round(thinq_q, 4)
    item["thinq_q_probability"] = round(thinq_q, 4)
    item["model_view"] = MODEL_THINQ
    item["top_mode"] = "THINQ_VIEW"
    item["top_reason"] = "Thinq page view: both Corq and Thinq outputs required; doubles excluded."
    return item


def cloq_ranked_record(prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if is_doubles_prediction(prediction):
        return None
    if not has_required_dual_model_outputs(prediction):
        return None
    if not has_valid_odds(prediction, CLOQ_MIN_ODDS, CLOQ_MAX_ODDS):
        return None

    odds1 = get_odds_player1(prediction)
    odds2 = get_odds_player2(prediction)
    _, _, market_gap = market_fair_probabilities(odds1, odds2)
    if market_gap is None or market_gap > CLOQ_MAX_MARKET_GAP:
        return None

    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)
    if corq is None or thinq is None:
        return None

    cloq_probability = get_cloq_probability(prediction)
    if cloq_probability is None:
        cloq_probability = CLOQ_CORQ_WEIGHT * corq + CLOQ_THINQ_WEIGHT * thinq

    odds = get_pick_odds(prediction)
    break_even = market_break_even(odds)
    edge = cloq_probability - break_even if break_even is not None else 0.0

    item = dict(prediction)
    item["probability"] = round(cloq_probability, 4)
    item["cloq_probability"] = round(cloq_probability, 4)
    item["cloq_ai_probability"] = round(cloq_probability, 4)
    item["cloq_score"] = round(cloq_probability + max(edge, 0.0), 4)
    item["edge_pp"] = round(edge, 4)
    item["market_gap"] = round(market_gap, 4)
    item["model_view"] = MODEL_CLOQ
    item["top_mode"] = "CLOQ_CLOSE_ODDS_VIEW"
    item["top_reason"] = "Cloq close-odds view: both Corq and Thinq outputs required; doubles excluded."
    return item


def unique_key(prediction: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(prediction.get("match_id") or prediction.get("event_id") or ""),
        str(prediction.get("match") or ""),
        str(prediction.get("pick") or ""),
    )


def deduplicate_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output: List[Dict[str, Any]] = []
    for prediction in predictions:
        key = unique_key(prediction)
        if key in seen:
            continue
        seen.add(key)
        output.append(prediction)
    return output


def build_all_predictions() -> List[Dict[str, Any]]:
    # Lazy import so build_pages can import this module even when it only needs
    # selectors over an already-loaded ALL snapshot.
    from prediction_engine_core import build_all_predictions as build_core_all_predictions
    return build_core_all_predictions()


def get_model_top_predictions(model: str = MODEL_CORQ, all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if all_predictions is None:
        all_predictions = build_all_predictions()
    model = str(model or MODEL_CORQ).lower()

    rejected_doubles = 0
    rejected_missing_dual = 0
    selected_candidates: List[Dict[str, Any]] = []

    for prediction in all_predictions:
        if is_doubles_prediction(prediction):
            rejected_doubles += 1
            continue
        if not has_required_dual_model_outputs(prediction):
            rejected_missing_dual += 1
            continue

        if model == MODEL_THINQ:
            item = thinq_ranked_record(prediction)
        elif model == MODEL_CLOQ:
            item = cloq_ranked_record(prediction)
        else:
            item = build_corq_ranked_record(prediction)

        if item:
            selected_candidates.append(item)

    selected_candidates = deduplicate_predictions(selected_candidates)

    if model == MODEL_THINQ:
        selected_candidates.sort(
            key=lambda item: (
                safe_float(item.get("thinq_q_probability")) or 0.0,
                safe_float(item.get("ai_match")) or 0.0,
                safe_float(item.get("odds")) or 0.0,
            ),
            reverse=True,
        )
    elif model == MODEL_CLOQ:
        selected_candidates.sort(
            key=lambda item: (
                safe_float(item.get("cloq_score")) or 0.0,
                safe_float(item.get("edge_pp")) or 0.0,
                -(safe_float(item.get("market_gap")) or 99.0),
            ),
            reverse=True,
        )
    else:
        selected_candidates.sort(key=corq_rank_tuple, reverse=True)

    selected = selected_candidates[:TOP_N]

    print(f"{model.upper()} RANKED CANDIDATES:", len(selected_candidates))
    print(f"{model.upper()} REJECTED DOUBLES:", rejected_doubles)
    print(f"{model.upper()} REJECTED MISSING DUAL OUTPUTS:", rejected_missing_dual)
    print(f"{model.upper()} TOP COUNT:", len(selected))
    for idx, item in enumerate(selected, start=1):
        print(
            f"{model.upper()} TOP PICK:",
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "odds=", item.get("odds"),
            "prob=", item.get("probability"),
            "corq_score=", item.get("corq_adjusted_score"),
            "flags=", item.get("corq_risk_flags"),
        )

    return selected


def get_corq_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return get_model_top_predictions(MODEL_CORQ, all_predictions=all_predictions)


def get_thinq_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return get_model_top_predictions(MODEL_THINQ, all_predictions=all_predictions)


def get_cloq_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return get_model_top_predictions(MODEL_CLOQ, all_predictions=all_predictions)


def get_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return get_corq_top_predictions(all_predictions=all_predictions)


def get_daily_predictions() -> List[Dict[str, Any]]:
    return get_top_predictions()
