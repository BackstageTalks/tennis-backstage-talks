from __future__ import annotations
from typing import Any, Dict, Iterable, List
import importlib
from match_normalizer import normalize_match
from .model import CorqModel
from .ranking import rank_predictions, top_n_from_ranked
from .outputs import publish_outputs

def load_raw_matches() -> List[Dict[str, Any]]:
    fetch = importlib.import_module("fetch_matches")
    for name in ["fetch_matches", "get_matches", "main", "load_matches"]:
        func = getattr(fetch, name, None)
        if callable(func):
            data = func()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ["matches", "events", "data"]:
                    if isinstance(data.get(key), list):
                        return data.get(key)
    raise RuntimeError("fetch_matches.py does not expose a supported match loading function")

def build_thinq(match: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from thinq.service import ThinqService
        return ThinqService().analyse_match(match)
    except Exception as exc:
        return {"available": False, "error": str(exc), "confidence": 0.0, "edges": {}, "flags": ["THINQ_RUNTIME_ERROR"], "h2h": {"status": "ERROR_NON_BLOCKING", "edge": 0.0, "confidence": 0.0, "reason": str(exc)}}

def build_predictions(raw_matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    model = CorqModel()
    predictions = []
    for raw in raw_matches:
        match = normalize_match(raw)
        thinq = build_thinq(match)
        match["thinq"] = thinq
        match["thinq_available"] = bool(thinq.get("available"))
        match["thinq_error"] = thinq.get("error")
        match["thinq_confidence"] = thinq.get("confidence")
        match["thinq_edges"] = thinq.get("edges")
        match["thinq_h2h_status"] = (thinq.get("h2h") or {}).get("status")
        match["thinq_h2h_edge"] = (thinq.get("h2h") or {}).get("edge")
        predictions.append(model.score(match, thinq))
    return predictions

def main() -> None:
    raw_matches = load_raw_matches()
    all_predictions = build_predictions(raw_matches)
    ranked = rank_predictions(all_predictions)
    top7 = top_n_from_ranked(ranked, 7)
    publish_outputs(all_predictions, ranked, top7)
    try:
        from site.render import render_all_pages
        render_all_pages(all_predictions=all_predictions, corq_predictions=ranked, top7=top7)
    except Exception as exc:
        print(f"SITE_RENDER_NON_BLOCKING_ERROR: {exc}")
    print(f"CORQ CLEAN RUNTIME OK: all={len(all_predictions)} ranked={len(ranked)} top7={len(top7)}")
