from __future__ import annotations
from typing import Any, Dict, List

MIN_ODDS = 1.40
LOW_ODDS_THRESHOLD = 1.60


def to_float(value: Any, default=None):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def is_eligible_for_corq(match: Dict[str, Any]) -> tuple[bool, List[str]]:
    reasons = []
    if match.get("is_doubles"):
        reasons.append("DOUBLES_EXCLUDED")
    if not match.get("pick") or not match.get("opponent"):
        reasons.append("MISSING_PLAYERS")
    odds = to_float(match.get("pick_odds") or match.get("odds"))
    if odds is None:
        reasons.append("MISSING_PICK_ODDS")
    elif odds < MIN_ODDS:
        reasons.append("ODDS_BELOW_MIN")
    if match.get("surface") in (None, "", "Unknown"):
        reasons.append("SURFACE_UNKNOWN")
    return len(reasons) == 0, reasons


def risk_penalty(match: Dict[str, Any], probability: float) -> tuple[float, List[str]]:
    flags = []
    penalty = 0.0
    odds = to_float(match.get("pick_odds") or match.get("odds"))
    if odds is not None and odds < LOW_ODDS_THRESHOLD and probability >= 0.75:
        penalty += 0.04
        flags.append("LOW_ODDS_OVERCONFIDENCE_GUARD")
    if match.get("thinq_confidence") is not None and to_float(match.get("thinq_confidence"), 0.0) < 0.25:
        penalty += 0.02
        flags.append("LOW_THINQ_CONFIDENCE")
    return penalty, flags
