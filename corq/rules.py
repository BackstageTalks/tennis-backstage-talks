from __future__ import annotations
from typing import Any, Dict, List
from match_normalizer import is_doubles_match
from .schema import to_float

MIN_PICK_ODDS = 1.40

def pick_odds(prediction: Dict[str, Any]):
    for key in ["pick_odds", "odds", "marq_current_pick_odds", "marq_initial_pick_odds"]:
        value = to_float(prediction.get(key))
        if value is not None:
            return value
    return None

def eligible_for_corq(prediction: Dict[str, Any]) -> tuple[bool, List[str]]:
    reasons = []
    if is_doubles_match(prediction):
        reasons.append("DOUBLES_EXCLUDED")
    odds = pick_odds(prediction)
    if odds is None:
        reasons.append("MISSING_PICK_ODDS")
    elif odds < MIN_PICK_ODDS:
        reasons.append("LOW_ODDS_BELOW_MIN")
    if not prediction.get("pick"):
        reasons.append("MISSING_PICK")
    if not prediction.get("opponent"):
        reasons.append("MISSING_OPPONENT")
    return (len(reasons) == 0), reasons
