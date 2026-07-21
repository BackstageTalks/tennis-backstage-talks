import copy
import glob
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from render_site import write_page, write_rss


BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"
SITE_TITLE = "BackstageTalks Statistic Model"

TOP_N = int(os.getenv("TOP_N", "7"))
TOP_MIN_ODDS = float(os.getenv("TOP_MIN_ODDS", "1.40"))
TOP_MAX_ODDS = float(os.getenv("TOP_MAX_ODDS", "5.00"))
CORQ_MIN_ODDS = float(os.getenv("CORQ_MIN_ODDS", str(TOP_MIN_ODDS)))
CORQ_MAX_ODDS = float(os.getenv("CORQ_MAX_ODDS", str(TOP_MAX_ODDS)))
THINQ_MIN_ODDS = float(os.getenv("THINQ_MIN_ODDS", "1.60"))
THINQ_MAX_ODDS = float(os.getenv("THINQ_MAX_ODDS", str(TOP_MAX_ODDS)))
THINQ_MIN_Q = float(os.getenv("THINQ_MIN_Q", "0.62"))
THINQ_MIN_EDGE = float(os.getenv("THINQ_MIN_EDGE", "0.02"))
THINQ_MAX_MODEL_GAP = float(os.getenv("THINQ_MAX_MODEL_GAP", "0.10"))
THINQ_MIN_AI_MATCH = float(os.getenv("THINQ_MIN_AI_MATCH", "94.0"))
THINQ_MIN_CORQ_RAW = float(os.getenv("THINQ_MIN_CORQ_RAW", "0.55"))
THINQ_MIN_THINQ_RAW = float(os.getenv("THINQ_MIN_THINQ_RAW", "0.55"))
THINQ_MIN_CORQ_EDGE = float(os.getenv("THINQ_MIN_CORQ_EDGE", "-0.01"))
THINQ_MIN_RAW_EDGE = float(os.getenv("THINQ_MIN_RAW_EDGE", "0.02"))
THINQ_MAX_EDGE_WITHOUT_ELITE_MATCH = float(os.getenv("THINQ_MAX_EDGE_WITHOUT_ELITE_MATCH", "0.14"))
THINQ_ELITE_AI_MATCH = float(os.getenv("THINQ_ELITE_AI_MATCH", "95.0"))
TOP_MIN_CORQ_Q = float(os.getenv("TOP_MIN_CORQ_Q", "0.55"))
TOP_MIN_THINQ_Q = float(os.getenv("TOP_MIN_THINQ_Q", "0.55"))
TOP_MAX_MODEL_GAP = float(os.getenv("TOP_MAX_MODEL_GAP", "0.15"))
TOP_MIN_AI_MATCH = float(os.getenv("TOP_MIN_AI_MATCH", "0.0"))

# Cloq = close-odds / market-edge model.
# Main close-market rule: normalized market gap <= 15 percentage points.
# Strong close market: <= 10 pp. Close market: <= 15 pp.
# New requested odds window: 1.60 - 4.20.
CLOQ_MIN_PICK_ODDS = float(os.getenv("CLOQ_MIN_PICK_ODDS", os.getenv("CLOQ_MIN_ODDS", "1.60")))
CLOQ_MAX_PICK_ODDS = float(os.getenv("CLOQ_MAX_PICK_ODDS", os.getenv("CLOQ_MAX_ODDS", "4.20")))
CLOQ_STRONG_MARKET_GAP = float(os.getenv("CLOQ_STRONG_MARKET_GAP", "0.10"))
CLOQ_MAX_MARKET_GAP = float(os.getenv("CLOQ_MAX_MARKET_GAP", "0.15"))
CLOQ_MIN_CORQ = float(os.getenv("CLOQ_MIN_CORQ", "0.50"))
CLOQ_MIN_THINQ = float(os.getenv("CLOQ_MIN_THINQ", "0.50"))
CLOQ_MIN_PROBABILITY = float(os.getenv("CLOQ_MIN_PROBABILITY", "0.55"))
CLOQ_MIN_AI_MATCH = float(os.getenv("CLOQ_MIN_AI_MATCH", "0.0"))
CLOQ_MIN_EDGE = float(os.getenv("CLOQ_MIN_EDGE", "0.02"))
CLOQ_THIN_MIN_CONSENSUS = float(os.getenv("CLOQ_THIN_MIN_CONSENSUS", "0.62"))
CLOQ_THIN_MIN_EDGE = float(os.getenv("CLOQ_THIN_MIN_EDGE", "0.05"))
CLOQ_THIN_MAX_MODEL_GAP = float(os.getenv("CLOQ_THIN_MAX_MODEL_GAP", "0.07"))
CLOQ_THIN_MIN_AI_MATCH = float(os.getenv("CLOQ_THIN_MIN_AI_MATCH", "94.0"))
CLOQ_MAX_MODEL_GAP = float(os.getenv("CLOQ_MAX_MODEL_GAP", "0.15"))
CLOQ_BANNED_MARKET_SIGNALS = {"CAUTION", "BEARISH"}


def extract_date_from_filename(path: str) -> str:
    filename = os.path.basename(path or "")
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else ""


def sorted_files_newest_first(pattern: str) -> List[str]:
    files = glob.glob(pattern)
    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )
    return files


def load_json(path: str, default: Any):
    try:
        if not path or not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        print("BUILD PAGES JSON LOAD ERROR:", path, str(exc))
        return default


def save_json(path: str, data: Any) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def find_latest_non_empty_file(pattern: str, label: str) -> Optional[str]:
    for path in sorted_files_newest_first(pattern):
        data = load_json(path, [])
        if isinstance(data, list) and data:
            print("BUILD PAGES SOURCE:", label, path, len(data))
            return path
    print("BUILD PAGES SOURCE MISSING:", label, pattern)
    return None


def ensure_public_dirs() -> None:
    os.makedirs("public", exist_ok=True)
    os.makedirs("public/all", exist_ok=True)
    os.makedirs("public/BsT", exist_ok=True)
    os.makedirs("public/cloq", exist_ok=True)
    os.makedirs("public/Cloq", exist_ok=True)


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


def get_prediction_odds(prediction: Dict[str, Any]) -> Optional[float]:
    return safe_float(prediction.get("odds"))


def get_first_float(prediction: Dict[str, Any], keys: List[str]) -> Optional[float]:
    for key in keys:
        value = safe_float(prediction.get(key))
        if value is not None:
            return value
    return None


def get_odds_player1(prediction: Dict[str, Any]) -> Optional[float]:
    return get_first_float(
        prediction,
        ["odds_player1", "p1_odds", "home_odds", "odds1", "price1"],
    )


def get_odds_player2(prediction: Dict[str, Any]) -> Optional[float]:
    return get_first_float(
        prediction,
        ["odds_player2", "p2_odds", "away_odds", "odds2", "price2"],
    )


def has_both_model_outputs(prediction: Dict[str, Any]) -> bool:
    """
    Production pages rule:
    - Corq probability required.
    - Thinq probability required.
    - AI Match required.

    Historical bst_ai_status is intentionally not used as a hard filter.
    ALL page remains audit/debug and can show missing model data.
    """
    if get_corq_probability(prediction) is None:
        return False
    if get_thinq_probability(prediction) is None:
        return False
    if get_ai_match(prediction) is None:
        return False
    return True


def calculate_quality_scores(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    corq = get_corq_probability(prediction)
    thinq = get_thinq_probability(prediction)
    ai_match = get_ai_match(prediction)
    if corq is None or thinq is None or ai_match is None:
        return None

    # Requested experiment:
    # CorqQ remains 80% Corq + 20% Thinq.
    # ThinqQ changes to 50% Thinq + 50% Corq.
    corq_q = 0.80 * corq + 0.20 * thinq
    thinq_q = 0.50 * thinq + 0.50 * corq
    model_gap = abs(corq - thinq)
    q_model_gap = abs(corq_q - thinq_q)
    consensus_score = (corq_q + thinq_q) / 2.0

    odds = get_prediction_odds(prediction)
    market_break_even = 1.0 / odds if odds and odds > 1.0 else None
    market_probability = get_pick_market_probability(prediction)
    comparison_probability = market_probability if market_probability is not None else market_break_even

    model_edge = consensus_score - comparison_probability if comparison_probability is not None else None
    corq_edge = corq - comparison_probability if comparison_probability is not None else None
    thinq_edge = thinq - comparison_probability if comparison_probability is not None else None
    thinq_q_edge = thinq_q - comparison_probability if comparison_probability is not None else None
    dynamic_min_edge = dynamic_thinq_min_edge(odds)

    return {
        "corq_probability": corq,
        "thinq_probability": thinq,
        "corq_q_probability": corq_q,
        "thinq_q_probability": thinq_q,
        "model_gap": model_gap,
        "q_model_gap": q_model_gap,
        "consensus_score": consensus_score,
        "market_break_even": market_break_even or 0.0,
        "market_probability": comparison_probability or 0.0,
        "model_edge": model_edge or 0.0,
        "corq_edge": corq_edge or 0.0,
        "thinq_edge": thinq_edge or 0.0,
        "thinq_q_edge": thinq_q_edge or 0.0,
        "dynamic_min_edge": dynamic_min_edge,
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


def has_required_top_odds(prediction: Dict[str, Any]) -> bool:
    odds = get_prediction_odds(prediction)
    return odds is not None and TOP_MIN_ODDS <= odds <= TOP_MAX_ODDS


def has_required_corq_odds(prediction: Dict[str, Any]) -> bool:
    odds = get_prediction_odds(prediction)
    return odds is not None and CORQ_MIN_ODDS <= odds <= CORQ_MAX_ODDS


def has_required_thinq_odds(prediction: Dict[str, Any]) -> bool:
    odds = get_prediction_odds(prediction)
    return odds is not None and THINQ_MIN_ODDS <= odds <= THINQ_MAX_ODDS


def is_thin_market(prediction: Dict[str, Any]) -> bool:
    values = [
        prediction.get("marq_ai_signal"),
        prediction.get("marq_quality_signal"),
        prediction.get("marq_sharp_signal"),
        prediction.get("cloq_risk"),
    ]
    text = " ".join(str(value or "").upper() for value in values)
    return "THIN" in text or "NO SHARP DATA" in text


def calculate_market_fair_probabilities(
    odds_player1: Optional[float],
    odds_player2: Optional[float],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if odds_player1 is None or odds_player2 is None:
        return None, None, None
    if odds_player1 <= 1.0 or odds_player2 <= 1.0:
        return None, None, None
    implied1 = 1.0 / odds_player1
    implied2 = 1.0 / odds_player2
    total = implied1 + implied2
    if total <= 0:
        return None, None, None
    fair1 = implied1 / total
    fair2 = implied2 / total
    market_gap = abs(fair1 - fair2)
    return fair1, fair2, market_gap


def calculate_pick_market_fair(
    prediction: Dict[str, Any],
    fair_1: Optional[float],
    fair_2: Optional[float],
) -> Optional[float]:
    pick = str(prediction.get("pick") or "").strip().lower()
    player1 = str(prediction.get("player1") or "").strip().lower()
    player2 = str(prediction.get("player2") or "").strip().lower()
    if fair_1 is None or fair_2 is None:
        return None
    if pick == player1:
        return fair_1
    if pick == player2:
        return fair_2
    return None


def get_pick_market_probability(prediction: Dict[str, Any]) -> Optional[float]:
    odds = get_prediction_odds(prediction)
    odds1 = get_odds_player1(prediction)
    odds2 = get_odds_player2(prediction)

    fair1, fair2, _market_gap = calculate_market_fair_probabilities(odds1, odds2)
    fair_pick = calculate_pick_market_fair(prediction, fair1, fair2)
    if fair_pick is not None:
        return fair_pick

    if odds is not None and odds > 1.0:
        return 1.0 / odds
    return None


def dynamic_thinq_min_edge(odds: Optional[float]) -> float:
    if odds is None:
        return THINQ_MIN_EDGE
    if odds < 1.80:
        return max(THINQ_MIN_EDGE, 0.025)
    if odds < 2.20:
        return max(THINQ_MIN_EDGE, 0.035)
    if odds < 3.00:
        return max(THINQ_MIN_EDGE, 0.050)
    return max(THINQ_MIN_EDGE, 0.070)


def calculate_cloq_market_quality(market_gap: Optional[float]) -> str:
    if market_gap is None:
        return "NO_MARKET_GAP"
    if market_gap <= CLOQ_STRONG_MARKET_GAP:
        return "STRONG_CLOSE"
    if market_gap <= CLOQ_MAX_MARKET_GAP:
        return "CLOSE"
    return "NOT_CLOQ"


def calculate_cloq_tier(
    cloq_probability: float,
    edge_pp: float,
    ai_match: float,
    marq_signal: Any,
) -> str:
    signal = str(marq_signal or "").upper().strip()
    negative_market = signal in {"CAUTION", "BEARISH"}
    if cloq_probability >= 0.62 and edge_pp >= 0.05 and ai_match >= 92 and not negative_market:
        return "CLOQ_A"
    if cloq_probability >= 0.60 and edge_pp >= 0.03 and ai_match >= 90:
        return "CLOQ_B"
    return "CLOQ_WATCH"


def calculate_cloq_risk(
    prediction: Dict[str, Any],
    market_gap: Optional[float],
    edge_pp: Optional[float],
    ai_match: Optional[float],
    model_gap: Optional[float],
) -> str:
    notes = []
    signal = str(prediction.get("marq_ai_signal") or "").upper().strip()
    if signal == "THIN MARKET":
        notes.append("THIN_MARKET")
    if signal in {"CAUTION", "BEARISH"}:
        notes.append("NEGATIVE_MARKET")
    if edge_pp is not None and edge_pp < 0.03:
        notes.append("LOW_EDGE")
    if ai_match is not None and ai_match < 90:
        notes.append("LOW_AI_MATCH")
    if model_gap is not None and model_gap > CLOQ_MAX_MODEL_GAP:
        notes.append("MODEL_GAP")
    if market_gap is not None and market_gap > CLOQ_STRONG_MARKET_GAP:
        notes.append("WIDER_CLOSE_MARKET")
    return ",".join(notes) if notes else "OK"


def clone_prediction(prediction: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(prediction)


def unique_key(prediction: Dict[str, Any]) -> Tuple[str, str]:
    return (
        str(prediction.get("match_id") or prediction.get("event_id") or prediction.get("match") or ""),
        str(prediction.get("pick") or ""),
    )


def dedupe_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected = []
    seen = set()
    for prediction in predictions:
        key = unique_key(prediction)
        if key in seen:
            continue
        seen.add(key)
        selected.append(prediction)
    return selected


def apply_consensus_metadata(
    prediction: Dict[str, Any],
    display_probability: float,
    view_name: str,
    reason: str,
) -> Dict[str, Any]:
    updated = clone_prediction(prediction)
    scores = calculate_quality_scores(updated) or {}
    model_gap = scores.get("model_gap")
    q_model_gap = scores.get("q_model_gap")
    updated["probability"] = round(display_probability, 4)
    updated["corq_raw_probability"] = round(scores.get("corq_probability", 0.0), 4)
    updated["thinq_raw_probability"] = round(scores.get("thinq_probability", 0.0), 4)
    updated["corq_q_probability"] = round(scores.get("corq_q_probability", 0.0), 4)
    updated["thinq_q_probability"] = round(scores.get("thinq_q_probability", 0.0), 4)
    updated["cloq_ai_probability"] = round(scores.get("consensus_score", 0.0), 4)
    updated["model_gap"] = round(model_gap, 4) if model_gap is not None else None
    updated["q_model_gap"] = round(q_model_gap, 4) if q_model_gap is not None else None
    updated["consensus_score"] = round(scores.get("consensus_score", 0.0), 4)
    updated["market_break_even"] = round(scores.get("market_break_even", 0.0), 4)
    updated["market_probability"] = round(scores.get("market_probability", 0.0), 4)
    updated["model_edge"] = round(scores.get("model_edge", 0.0), 4)
    updated["corq_edge"] = round(scores.get("corq_edge", 0.0), 4)
    updated["thinq_edge"] = round(scores.get("thinq_edge", 0.0), 4)
    updated["thinq_q_edge"] = round(scores.get("thinq_q_edge", 0.0), 4)
    updated["dynamic_min_edge"] = round(scores.get("dynamic_min_edge", 0.0), 4)
    updated["consensus_status"] = consensus_status(model_gap)
    updated["top_mode"] = view_name
    updated["top_reason"] = reason
    return updated


def mark_cloq_view(
    prediction: Dict[str, Any],
    cloq_probability: float,
    scores: Dict[str, float],
) -> Dict[str, Any]:
    updated = apply_consensus_metadata(
        prediction,
        cloq_probability,
        "CLOQ_CLOSE_ODDS_EDGE",
        "Cloq close-odds market-edge model with both Corq and Thinq outputs required.",
    )
    odds = get_prediction_odds(prediction)
    odds1 = get_odds_player1(prediction)
    odds2 = get_odds_player2(prediction)
    fair1, fair2, market_gap = calculate_market_fair_probabilities(odds1, odds2)
    market_fair_pick = calculate_pick_market_fair(prediction, fair1, fair2)
    market_implied_pick = 1.0 / odds if odds and odds > 1.0 else None
    edge_pp = cloq_probability - market_implied_pick if market_implied_pick is not None else None
    ai_match = scores.get("ai_match")
    model_gap = scores.get("model_gap")
    updated["cloq_probability"] = round(cloq_probability, 4)
    updated["cloq_ai_probability"] = round(cloq_probability, 4)
    updated["market_fair_player1"] = round(fair1, 4) if fair1 is not None else None
    updated["market_fair_player2"] = round(fair2, 4) if fair2 is not None else None
    updated["market_gap"] = round(market_gap, 4) if market_gap is not None else None
    updated["cloq_market_quality"] = calculate_cloq_market_quality(market_gap)
    updated["market_fair_pick"] = round(market_fair_pick, 4) if market_fair_pick is not None else None
    updated["market_implied_pick"] = round(market_implied_pick, 4) if market_implied_pick is not None else None
    updated["edge_pp"] = round(edge_pp, 4) if edge_pp is not None else None
    updated["cloq_tier"] = calculate_cloq_tier(cloq_probability, edge_pp or 0.0, ai_match or 0.0, prediction.get("marq_ai_signal"))
    updated["cloq_risk"] = calculate_cloq_risk(prediction, market_gap, edge_pp, ai_match, model_gap)
    return updated


def eligible_common_top(prediction: Dict[str, Any], model: str = "corq") -> Optional[Dict[str, float]]:
    if not has_both_model_outputs(prediction):
        return None

    model_key = str(model or "corq").lower()
    if model_key == "thinq":
        if not has_required_thinq_odds(prediction):
            return None
    elif model_key == "corq":
        if not has_required_corq_odds(prediction):
            return None
    else:
        if not has_required_top_odds(prediction):
            return None

    scores = calculate_quality_scores(prediction)
    if not scores:
        return None

    if model_key == "thinq":
        thinq_edge = scores["thinq_q_probability"] - scores["market_break_even"]

        if scores["corq_probability"] < THINQ_MIN_CORQ_RAW:
            return None
        if scores["thinq_probability"] < THINQ_MIN_THINQ_RAW:
            return None
        if scores["thinq_q_probability"] < THINQ_MIN_Q:
            return None
        if thinq_edge < THINQ_MIN_EDGE:
            return None
        if scores["model_gap"] > THINQ_MAX_MODEL_GAP:
            return None
        if scores["ai_match"] < THINQ_MIN_AI_MATCH:
            return None


        scores["thinq_edge"] = thinq_edge
        return scores

    if scores["corq_q_probability"] < TOP_MIN_CORQ_Q:
        return None
    if scores["thinq_q_probability"] < TOP_MIN_THINQ_Q:
        return None
    if scores["model_gap"] > TOP_MAX_MODEL_GAP:
        return None
    if scores["ai_match"] < TOP_MIN_AI_MATCH:
        return None
    return scores


def derive_corq_predictions(all_predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = []
    for prediction in all_predictions:
        scores = eligible_common_top(prediction, model="corq")
        if not scores:
            continue
        eligible.append(
            apply_consensus_metadata(
                prediction,
                scores["corq_q_probability"],
                "CORQ_TOP7_CONSENSUS",
                "CorqQ = 80% Corq + 20% Thinq; both model probabilities required; model_gap <= 15%; odds >= Corq min odds.",
            )
        )
    eligible = dedupe_predictions(eligible)
    eligible.sort(
        key=lambda item: (
            safe_float(item.get("corq_q_probability")) or 0.0,
            safe_float(item.get("consensus_score")) or 0.0,
            safe_float(item.get("ai_match")) or 0.0,
        ),
        reverse=True,
    )
    return eligible[:TOP_N]


def derive_thinq_predictions(all_predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = []
    for prediction in all_predictions:
        scores = eligible_common_top(prediction, model="thinq")
        if not scores:
            continue
        updated = apply_consensus_metadata(
            prediction,
            scores["thinq_q_probability"],
            "THINQ_TOP7_50_50",
            "ThinqQ = 50% Thinq + 50% Corq; both model probabilities required; model_gap <= 15%; odds >= Thinq min odds.",
        )
        updated["bst_ai_probability"] = round(scores["thinq_q_probability"], 4)
        updated["thinq_ai_probability"] = round(scores["thinq_q_probability"], 4)
        updated["thinq_edge"] = round(scores.get("thinq_edge", 0.0), 4)
        updated["thinq_quality_gate"] = "STRICT_EDGE"
        updated["thinq_q_edge"] = round(scores.get("thinq_q_edge", 0.0), 4)
        updated["dynamic_min_edge"] = round(scores.get("dynamic_min_edge", 0.0), 4)
        eligible.append(updated)
    eligible = dedupe_predictions(eligible)
    eligible.sort(
        key=lambda item: (
            safe_float(item.get("thinq_q_edge")) or 0.0,
            safe_float(item.get("ai_match")) or 0.0,
            -(safe_float(item.get("model_gap")) or 0.0),
            safe_float(item.get("thinq_q_probability")) or 0.0,
        ),
        reverse=True,
    )
    return eligible[:TOP_N]


def eligible_cloq(prediction: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not has_both_model_outputs(prediction):
        return None
    scores = calculate_quality_scores(prediction)
    if not scores:
        return None

    odds = get_prediction_odds(prediction)
    odds1 = get_odds_player1(prediction)
    odds2 = get_odds_player2(prediction)
    if odds is None or odds < CLOQ_MIN_PICK_ODDS or odds > CLOQ_MAX_PICK_ODDS:
        return None
    if odds1 is None or odds2 is None:
        return None
    if scores["corq_probability"] < CLOQ_MIN_CORQ:
        return None
    if scores["thinq_probability"] < CLOQ_MIN_THINQ:
        return None
    if scores["consensus_score"] < CLOQ_MIN_PROBABILITY:
        return None
    if scores["ai_match"] < CLOQ_MIN_AI_MATCH:
        return None
    if scores["model_gap"] > CLOQ_MAX_MODEL_GAP:
        return None

    market_signal = str(prediction.get("marq_ai_signal") or prediction.get("marq_move_signal") or "").upper().strip()
    if market_signal in CLOQ_BANNED_MARKET_SIGNALS:
        return None

    fair1, fair2, market_gap = calculate_market_fair_probabilities(odds1, odds2)
    if market_gap is None or market_gap > CLOQ_MAX_MARKET_GAP:
        return None

    market_implied_pick = 1.0 / odds if odds and odds > 1.0 else None
    edge_pp = scores["consensus_score"] - market_implied_pick if market_implied_pick is not None else None
    if edge_pp is None or edge_pp < CLOQ_MIN_EDGE:
        return None

    if is_thin_market(prediction):
        if scores["consensus_score"] < CLOQ_THIN_MIN_CONSENSUS:
            return None
        if edge_pp < CLOQ_THIN_MIN_EDGE:
            return None
        if scores["model_gap"] > CLOQ_THIN_MAX_MODEL_GAP:
            return None
        if scores["ai_match"] < CLOQ_THIN_MIN_AI_MATCH:
            return None

    return scores


def derive_cloq_predictions(all_predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    eligible = []
    for prediction in all_predictions:
        scores = eligible_cloq(prediction)
        if not scores:
            continue
        eligible.append(mark_cloq_view(prediction, scores["consensus_score"], scores))
    eligible = dedupe_predictions(eligible)
    eligible.sort(
        key=lambda item: (
            safe_float(item.get("edge_pp")) or 0.0,
            safe_float(item.get("cloq_probability")) or 0.0,
            safe_float(item.get("ai_match")) or 0.0,
            safe_float(item.get("odds")) or 0.0,
        ),
        reverse=True,
    )
    return eligible[:TOP_N]


def print_prediction_sample(label: str, predictions: List[Dict[str, Any]]) -> None:
    print("")
    print(f"=== {label} SAMPLE ===")
    print("COUNT:", len(predictions))
    for idx, item in enumerate(predictions[:10], start=1):
        print(
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "prob=", item.get("probability"),
            "odds=", item.get("odds"),
            "corq_q=", item.get("corq_q_probability"),
            "thinq_q=", item.get("thinq_q_probability"),
            "cloq=", item.get("cloq_ai_probability"),
            "edge=", item.get("edge_pp") or item.get("model_edge"),
            "gap=", item.get("model_gap"),
            "consensus=", item.get("consensus_score"),
            "mode=", item.get("top_mode"),
        )


def validate_predictions(all_predictions: List[Dict[str, Any]]) -> None:
    if not all_predictions:
        raise ValueError("ALL predictions are empty. Refusing to deploy empty ALL page.")


def load_all_predictions_for_pages() -> List[Dict[str, Any]]:
    source = find_latest_non_empty_file("public/all_predictions_*.json", "public all predictions")
    if not source:
        source = find_latest_non_empty_file("data/pick_history/all/*.json", "all snapshot")
    if not source:
        raise FileNotFoundError("No non-empty ALL predictions JSON found.")
    data = load_json(source, [])
    if not isinstance(data, list):
        raise ValueError(f"ALL predictions source is not a list: {source}")
    return data


def build_pages() -> None:
    ensure_public_dirs()
    all_predictions = load_all_predictions_for_pages()
    validate_predictions(all_predictions)

    corq_predictions = derive_corq_predictions(all_predictions)
    thinq_predictions = derive_thinq_predictions(all_predictions)
    cloq_predictions = derive_cloq_predictions(all_predictions)

    print("TOP_N:", TOP_N)
    print("TOP MIN ODDS:", TOP_MIN_ODDS)
    print("CORQ ODDS RANGE:", CORQ_MIN_ODDS, CORQ_MAX_ODDS)
    print("THINQ ODDS RANGE:", THINQ_MIN_ODDS, THINQ_MAX_ODDS)
    print("THINQ STRICT GATE:", "min_q", THINQ_MIN_Q, "base_edge", THINQ_MIN_EDGE, "gap", THINQ_MAX_MODEL_GAP, "ai", THINQ_MIN_AI_MATCH)
    print("THINQ EDGE GATE:", "corq_edge", THINQ_MIN_CORQ_EDGE, "raw_thinq_edge", THINQ_MIN_RAW_EDGE, "max_edge_without_elite", THINQ_MAX_EDGE_WITHOUT_ELITE_MATCH, "elite_ai", THINQ_ELITE_AI_MATCH)
    print("TOP MAX MODEL GAP:", TOP_MAX_MODEL_GAP)
    print("CLOQ ODDS RANGE:", CLOQ_MIN_PICK_ODDS, CLOQ_MAX_PICK_ODDS)
    print("CLOQ MAX MARKET GAP:", CLOQ_MAX_MARKET_GAP)
    print("CORQ TOP7 COUNT:", len(corq_predictions))
    print("THINQ TOP7 COUNT:", len(thinq_predictions))
    print("CLOQ TOP7 COUNT:", len(cloq_predictions))

    print_prediction_sample("CORQ TOP7", corq_predictions)
    print_prediction_sample("THINQ TOP7", thinq_predictions)
    print_prediction_sample("CLOQ TOP7", cloq_predictions)

    save_json("public/all_predictions_latest.json", all_predictions)
    save_json("public/corq_predictions_latest.json", corq_predictions)
    save_json("public/thinq_predictions_latest.json", thinq_predictions)
    save_json("public/cloq_predictions_latest.json", cloq_predictions)

    write_page(corq_predictions, SITE_TITLE, "Corq TOP7 dual-model consensus", "public/index.html")
    write_rss(corq_predictions, f"{SITE_TITLE} - Corq", f"{BASE_URL}/", "public/tennis.xml")

    write_page(thinq_predictions, SITE_TITLE, "Thinq TOP7 dual-model consensus", "public/BsT/index.html")
    write_rss(thinq_predictions, f"{SITE_TITLE} - Thinq", f"{BASE_URL}/BsT/", "public/tennis_bst.xml")

    write_page(cloq_predictions, SITE_TITLE, "Cloq close-odds market-edge predictions", "public/cloq/index.html")
    write_page(cloq_predictions, SITE_TITLE, "Cloq close-odds market-edge predictions", "public/Cloq/index.html")
    write_rss(cloq_predictions, f"{SITE_TITLE} - Cloq", f"{BASE_URL}/Cloq/", "public/tennis_cloq.xml")

    write_page(all_predictions, SITE_TITLE, "ALL audit predictions", "public/all/index.html")
    write_rss(all_predictions, f"{SITE_TITLE} - ALL", f"{BASE_URL}/all/", "public/tennis_all.xml")

    print("BUILD PAGES DONE")


if __name__ == "__main__":
    build_pages()
