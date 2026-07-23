"""Clean CORQ engine.

This module intentionally does not call legacy prediction_engine_* files.
It uses fetch_matches.py only as the current match source until a clean source module is introduced.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List
import importlib

from match_normalizer import normalize_match
from .model import CorqModel
from .ranking import rank_predictions, top_n_from_ranked
from .outputs import publish_outputs


def _extract_match_list(data: Any) -> List[Dict[str, Any]] | None:
    """Extract a match list from common return payload shapes."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["matches", "events", "data", "fixtures", "items"]:
            value = data.get(key)
            if isinstance(value, list):
                return value
    return None


def load_raw_matches() -> List[Dict[str, Any]]:
    """Load raw matches from the current fetch_matches.py source.

    Existing project naming uses get_today_matches() / get_matches_for_date().
    The clean runtime now supports both old and clean source function names.
    """
    fetch = importlib.import_module("fetch_matches")

    # Most likely existing project entrypoints first.
    for name in [
        "get_today_matches",
        "fetch_matches",
        "get_matches",
        "load_matches",
        "main",
    ]:
        func = getattr(fetch, name, None)
        if not callable(func):
            continue
        data = func()
        matches = _extract_match_list(data)
        if matches is not None:
            return matches

    # Optional date-based loader fallback. It may require betting_day() from same module.
    get_for_date = getattr(fetch, "get_matches_for_date", None)
    if callable(get_for_date):
        target_date = None
        betting_day = getattr(fetch, "betting_day", None)
        if callable(betting_day):
            try:
                target_date = betting_day()
            except Exception:
                target_date = None
        if target_date is not None:
            data = get_for_date(target_date)
            matches = _extract_match_list(data)
            if matches is not None:
                return matches

    available = [name for name in ["get_today_matches", "fetch_matches", "get_matches", "load_matches", "main", "get_matches_for_date"] if callable(getattr(fetch, name, None))]
    raise RuntimeError(
        "fetch_matches.py does not expose a supported match loading function returning matches. "
        f"Callable candidates found: {available}"
    )


def build_thinq(match: Dict[str, Any]) -> Dict[str, Any]:
    """Call THINQ and never let THINQ errors kill the CORQ build."""
    try:
        from thinq.service import ThinqService
        return ThinqService().analyse_match(match)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "confidence": 0.0,
            "surface": {
                "surface": match.get("surface") or "Unknown",
                "surface_raw": match.get("surface_raw") or match.get("surface"),
                "surface_source": "thinq_runtime_error_fallback",
                "surface_model_bucket": "Overall",
                "thinq_selected_elo_type": "overall_elo",
            },
            "edges": {},
            "h2h": {
                "status": "ERROR_NON_BLOCKING",
                "edge": 0.0,
                "confidence": 0.0,
                "reason": str(exc),
                "flags": ["H2H_SKIPPED_THINQ_RUNTIME_ERROR"],
            },
            "flags": ["THINQ_RUNTIME_ERROR"],
        }


def build_predictions(raw_matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    model = CorqModel()
    predictions: List[Dict[str, Any]] = []
    for raw in raw_matches:
        match = normalize_match(raw)
        thinq = build_thinq(match)
        match["thinq"] = thinq

        # Flatten critical audit fields for JSON/search/UI convenience.
        surface = thinq.get("surface") or {}
        match["surface"] = surface.get("surface") or match.get("surface") or "Unknown"
        match["surface_raw"] = surface.get("surface_raw")
        match["surface_source"] = surface.get("surface_source")
        match["surface_model_bucket"] = surface.get("surface_model_bucket")
        match["thinq_selected_elo_type"] = surface.get("thinq_selected_elo_type")
        match["thinq_available"] = bool(thinq.get("available"))
        match["thinq_error"] = thinq.get("error")
        match["thinq_confidence"] = thinq.get("confidence")
        match["thinq_edges"] = thinq.get("edges") or {}
        h2h = thinq.get("h2h") or {}
        match["thinq_h2h_status"] = h2h.get("status")
        match["thinq_h2h_edge"] = h2h.get("edge")
        match["thinq_h2h_source"] = h2h.get("source")
        match["thinq_h2h_confidence"] = h2h.get("confidence")

        predictions.append(model.score(match, thinq))
    return predictions


def main() -> None:
    raw_matches = load_raw_matches()
    all_predictions = build_predictions(raw_matches)
    ranked = rank_predictions(all_predictions)
    top7 = top_n_from_ranked(ranked, 7)
    publish_outputs(all_predictions, ranked, top7)
    try:
        from web.render import render_all_pages
        render_all_pages(all_predictions=all_predictions, corq_predictions=ranked, top7=top7)
    except Exception as exc:
        print(f"WEB_RENDER_NON_BLOCKING_ERROR: {exc}")
    print(f"CORQ CLEAN RUNTIME OK: all={len(all_predictions)} ranked={len(ranked)} top7={len(top7)}")


if __name__ == "__main__":
    main()
