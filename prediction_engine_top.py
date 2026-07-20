import os
from typing import Any, Dict, List, Optional, Tuple

from prediction_engine_core import build_all_predictions as build_core_all_predictions


TOP_N = int(os.getenv("TOP_N", "7"))
TOP_MIN_ODDS = float(os.getenv("TOP_MIN_ODDS", "1.40"))
TOP_MAX_ODDS = float(os.getenv("TOP_MAX_ODDS", "3.00"))
TOP_MIN_CORQ_Q = float(os.getenv("TOP_MIN_CORQ_Q", "0.55"))
TOP_MIN_THINQ_Q = float(os.getenv("TOP_MIN_THINQ_Q", "0.55"))
TOP_MAX_MODEL_GAP = float(os.getenv("TOP_MAX_MODEL_GAP", "0.15"))
TOP_MIN_AI_MATCH = float(os.getenv("TOP_MIN_AI_MATCH", "0.0"))

# Cloq = close-odds model. Defaults are intentionally conservative and can be tuned by env.
CLOQ_MIN_ODDS = float(os.getenv("CLOQ_MIN_ODDS", "1.60"))
CLOQ_MAX_ODDS = float(os.getenv("CLOQ_MAX_ODDS", "4.20"))
CLOQ_TARGET_ODDS = float(os.getenv("CLOQ_TARGET_ODDS", "1.85"))
CLOQ_MIN_CONSENSUS = float(os.getenv("CLOQ_MIN_CONSENSUS", "0.55"))
CLOQ_MAX_MODEL_GAP = float(os.getenv("CLOQ_MAX_MODEL_GAP", str(TOP_MAX_MODEL_GAP)))
CLOQ_MIN_AI_MATCH = float(os.getenv("CLOQ_MIN_AI_MATCH", str(TOP_MIN_AI_MATCH)))


MODEL_CORQ = "corq"
MODEL_THINQ = "thinq"
MODEL_CLOQ = "cloq"


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
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )


def get_thinq_probability(prediction: Dict[str, Any]) -> Optional[float]:
    return normalize_probability_decimal(
        prediction.get("bst_ai_probability")
        or prediction.get("thinq_ai_probability")
        or prediction.get("thinq_display_probability")
    )


def get_ai_match(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("ai_match"))


def get_pick_odds(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("odds"))


def has_both_model_outputs(prediction: Dict[str, Any]) -> bool:
    """
    Production TOP rule:
    - Corq probability must exist.
    - Thinq probability must exist.
    - AI Match must exist.

    Historical bst_ai_status is intentionally NOT used as a hard filter.
    """
    if get_corq_probability(prediction) is None:
        return False
    if get_thinq_probability(prediction) is None:
        return False
    if get_ai_match(prediction) is None:
        return False
    return True


def calculate_cross_influence_scores(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)
    ai_match = get_ai_match(prediction)

    if corq is None or thinq is None or ai_match is None:
        return None

    # Requested experiment:
    # - Corq stays as it was: 80% Corq + 20% Thinq.
    # - Thinq changes to 50% Thinq + 50% Corq.
    corq_q = 0.80 * corq + 0.20 * thinq
    thinq_q = 0.50 * thinq + 0.50 * corq

    model_gap = abs(corq - thinq)
    q_model_gap = abs(corq_q - thinq_q)
    consensus_score = (corq_q + thinq_q) / 2.0

    odds_value = get_pick_odds(prediction) or 0.0
    market_break_even = (1.0 / odds_value) if odds_value > 0 else 0.0
    model_edge = consensus_score - market_break_even if market_break_even > 0 else 0.0

    # Cloq probability is a close-odds consensus view. It is still explainable and not a black box.
    # The page/RSS can display this as cloq_ai_probability.
    cloq_q = consensus_score

    return {
        "corq": corq,
        "thinq": thinq,
        "corq_q": corq_q,
        "thinq_q": thinq_q,
        "cloq_q": cloq_q,
        "model_gap": model_gap,
        "q_model_gap": q_model_gap,
        "consensus_score": consensus_score,
        "market_break_even": market_break_even,
        "model_edge": model_edge,
        "ai_match": ai_match,
    }


def consensus_status(model_gap: Optional[float]) -> str:
    if model_gap is None:
        return "NO_CONSENSUS_DATA"
    if model_gap <= 0.07:
        return "STRONG_CONSENSUS"
    if model_gap <= 0.15:
        return "CONSENSUS"
    if model_gap <= 0.22:
        return "MODEL_GAP"
    return "MODEL_CONFLICT"


def has_valid_top_odds(prediction: Dict[str, Any]) -> bool:
    odds = get_pick_odds(prediction)
    return odds is not None and TOP_MIN_ODDS <= odds <= TOP_MAX_ODDS


def has_valid_cloq_odds(prediction: Dict[str, Any]) -> bool:
    odds = get_pick_odds(prediction)
    return odds is not None and CLOQ_MIN_ODDS <= odds <= CLOQ_MAX_ODDS


def eligible_top7(prediction: Dict[str, Any]) -> bool:
    if not has_both_model_outputs(prediction):
        return False
    if not has_valid_top_odds(prediction):
        return False

    scores = calculate_cross_influence_scores(prediction)
    if not scores:
        return False

    if scores["corq_q"] < TOP_MIN_CORQ_Q:
        return False
    if scores["thinq_q"] < TOP_MIN_THINQ_Q:
        return False
    if scores["model_gap"] > TOP_MAX_MODEL_GAP:
        return False
    if scores["ai_match"] < TOP_MIN_AI_MATCH:
        return False

    return True


def eligible_model_top7(prediction: Dict[str, Any], model: str) -> bool:
    if model == MODEL_CLOQ:
        return eligible_cloq_top7(prediction)
    return eligible_top7(prediction)


def eligible_cloq_top7(prediction: Dict[str, Any]) -> bool:
    if not has_both_model_outputs(prediction):
        return False
    if not has_valid_cloq_odds(prediction):
        return False

    scores = calculate_cross_influence_scores(prediction)
    if not scores:
        return False

    if scores["consensus_score"] < CLOQ_MIN_CONSENSUS:
        return False
    if scores["model_gap"] > CLOQ_MAX_MODEL_GAP:
        return False
    if scores["ai_match"] < CLOQ_MIN_AI_MATCH:
        return False

    return True


def top7_score(prediction: Dict[str, Any]) -> Tuple[float, float, float]:
    scores = calculate_cross_influence_scores(prediction)
    if not scores:
        return (0.0, 0.0, 0.0)
    return (
        scores["consensus_score"],
        scores["corq_q"],
        scores["ai_match"],
    )


def model_top7_score(prediction: Dict[str, Any], model: str) -> Tuple[float, float, float, float]:
    scores = calculate_cross_influence_scores(prediction)
    if not scores:
        return (0.0, 0.0, 0.0, 0.0)

    odds_value = get_pick_odds(prediction) or 0.0

    if model == MODEL_THINQ:
        return (
            scores["thinq_q"],
            scores["consensus_score"],
            scores["ai_match"],
            odds_value,
        )

    if model == MODEL_CLOQ:
        # Close-odds ranking:
        # 1) positive model edge over market break-even,
        # 2) closeness to target odds, default 1.85,
        # 3) consensus score,
        # 4) AI Match.
        target_distance = abs(odds_value - CLOQ_TARGET_ODDS) if odds_value else 99.0
        closeness_score = -target_distance
        return (
            scores["model_edge"],
            closeness_score,
            scores["consensus_score"],
            scores["ai_match"],
        )

    # Default Corq ranking.
    return (
        scores["corq_q"],
        scores["consensus_score"],
        scores["ai_match"],
        odds_value,
    )


def apply_top7_metadata(prediction: Dict[str, Any], model: str = MODEL_CORQ) -> Dict[str, Any]:
    item = dict(prediction)
    scores = calculate_cross_influence_scores(item)

    if not scores:
        item["top_mode"] = "NO_DUAL_MODEL_OUTPUT"
        item["top_reason"] = "Missing Corq, Thinq or AI Match output"
        item["model_view"] = model
        return item

    item["corq_raw_probability"] = round(scores["corq"], 4)
    item["thinq_raw_probability"] = round(scores["thinq"], 4)
    item["corq_q_probability"] = round(scores["corq_q"], 4)
    item["thinq_q_probability"] = round(scores["thinq_q"], 4)
    item["cloq_ai_probability"] = round(scores["cloq_q"], 4)
    item["model_gap"] = round(scores["model_gap"], 4)
    item["q_model_gap"] = round(scores["q_model_gap"], 4)
    item["consensus_score"] = round(scores["consensus_score"], 4)
    item["market_break_even"] = round(scores["market_break_even"], 4)
    item["model_edge"] = round(scores["model_edge"], 4)
    item["consensus_status"] = consensus_status(scores["model_gap"])
    item["model_view"] = model

    if model == MODEL_THINQ:
        item["probability"] = round(scores["thinq_q"], 4)
        item["top_mode"] = "TOP7_THINQ_50_50"
        item["top_reason"] = "TOP7 Thinq: ThinqQ = 50% Thinq + 50% Corq, odds filter, model_gap filter, both probabilities required"
    elif model == MODEL_CLOQ:
        item["probability"] = round(scores["cloq_q"], 4)
        item["top_mode"] = "TOP7_CLOQ_CLOSE_ODDS"
        item["top_reason"] = (
            f"TOP7 Cloq: close odds {CLOQ_MIN_ODDS:.2f}-{CLOQ_MAX_ODDS:.2f}, "
            "ranked by model edge, target odds closeness, consensus and AI Match"
        )
    else:
        item["probability"] = round(scores["corq_q"], 4)
        item["top_mode"] = "TOP7_CORQ_80_20"
        item["top_reason"] = "TOP7 Corq: CorqQ = 80% Corq + 20% Thinq, odds filter, model_gap filter, both probabilities required"

    return item


def unique_key(prediction: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(prediction.get("match_id") or prediction.get("event_id") or ""),
        str(prediction.get("match") or ""),
        str(prediction.get("pick") or ""),
    )


def deduplicate_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []
    for prediction in predictions:
        key = unique_key(prediction)
        if key in seen:
            continue
        seen.add(key)
        output.append(prediction)
    return output


def build_all_predictions() -> List[Dict[str, Any]]:
    return build_core_all_predictions()


def get_model_top_predictions(
    model: str = MODEL_CORQ,
    all_predictions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    if all_predictions is None:
        all_predictions = build_all_predictions()

    model = str(model or MODEL_CORQ).lower()
    if model not in {MODEL_CORQ, MODEL_THINQ, MODEL_CLOQ}:
        model = MODEL_CORQ

    eligible = [
        apply_top7_metadata(prediction, model=model)
        for prediction in all_predictions
        if eligible_model_top7(prediction, model=model)
    ]
    eligible = deduplicate_predictions(eligible)
    eligible.sort(key=lambda item: model_top7_score(item, model=model), reverse=True)
    selected = eligible[:TOP_N]

    print(f"TOP7 {model.upper()} COUNT:", len(selected))
    print(f"TOP7 {model.upper()} MIN ODDS:", CLOQ_MIN_ODDS if model == MODEL_CLOQ else TOP_MIN_ODDS)
    print(f"TOP7 {model.upper()} MAX MODEL GAP:", CLOQ_MAX_MODEL_GAP if model == MODEL_CLOQ else TOP_MAX_MODEL_GAP)

    for idx, item in enumerate(selected, start=1):
        print(
            f"TOP7 {model.upper()} PICK:",
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "odds=", item.get("odds"),
            "prob=", item.get("probability"),
            "corq_q=", item.get("corq_q_probability"),
            "thinq_q=", item.get("thinq_q_probability"),
            "cloq=", item.get("cloq_ai_probability"),
            "edge=", item.get("model_edge"),
            "gap=", item.get("model_gap"),
            "consensus=", item.get("consensus_score"),
            "status=", item.get("consensus_status"),
        )

    return selected


def get_corq_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return get_model_top_predictions(MODEL_CORQ, all_predictions=all_predictions)


def get_thinq_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return get_model_top_predictions(MODEL_THINQ, all_predictions=all_predictions)


def get_cloq_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return get_model_top_predictions(MODEL_CLOQ, all_predictions=all_predictions)


def get_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    # Backward-compatible default: original caller gets Corq TOP7.
    return get_corq_top_predictions(all_predictions=all_predictions)


def get_daily_predictions() -> List[Dict[str, Any]]:
    # Backward-compatible default for existing workflows.
    return get_top_predictions()
