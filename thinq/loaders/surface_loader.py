"""
THINQ Surface Loader / Resolver

Purpose:
- Resolve tournament surface from TennisApi PRO tournament metadata.
- Normalize API surfaceType values such as "Hardcourt outdoor", "Hardcourt indoor", "Clay".
- Persist raw and normalized surface data under thinq/data/surfaces/.
- Provide model-friendly surface bucket for ELO selection.

Principles:
- Never default unknown surface to Hard.
- If raw surface contains "hard", model surface is Hard.
- If raw surface is Carpet and no carpet ELO exists, use hard_elo fallback with audit flag.
- Preserve surface_raw and surface_environment for audit/debug.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

DEFAULT_HOST = os.getenv("TENNISAPI_PRO_HOST", "tennisapi1.p.rapidapi.com")
DEFAULT_BASE_URL = os.getenv("TENNISAPI_PRO_BASE_URL", "https://tennisapi1.p.rapidapi.com")
DEFAULT_DATA_DIR = Path(os.getenv("THINQ_SURFACE_DATA_DIR", "thinq/data/surfaces"))
CACHE_FILE = DEFAULT_DATA_DIR / "tournament_surface_cache.json"
RAW_DIR = DEFAULT_DATA_DIR / "raw" / "tennisapi_tournament_metadata"
UNKNOWN_SURFACE = "Unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def normalize_surface_type(surface_type: Any) -> Dict[str, Any]:
    """
    Normalize TennisApi surfaceType to model-friendly fields.

    Examples:
    - Clay -> Clay
    - Hardcourt outdoor -> Hard / Outdoor
    - Hardcourt indoor -> Hard / Indoor
    - Indoor hard -> Hard / Indoor
    - Carpet indoor -> Carpet / Indoor / model bucket Hard fallback
    """
    raw = str(surface_type or "").strip()
    text = raw.lower()

    environment: Optional[str] = None
    if "indoor" in text:
        environment = "Indoor"
    elif "outdoor" in text:
        environment = "Outdoor"

    flags = []
    confidence = "HIGH" if raw else "LOW"

    if "clay" in text:
        surface = "Clay"
        model_bucket = "Clay"
        elo_type = "clay_elo"
    elif "grass" in text:
        surface = "Grass"
        model_bucket = "Grass"
        elo_type = "grass_elo"
    elif "carpet" in text:
        surface = "Carpet"
        model_bucket = "Hard"
        elo_type = "hard_elo"
        confidence = "MEDIUM"
        flags.append("CARPET_AS_HARD_FALLBACK")
    elif "hard" in text:
        surface = "Hard"
        model_bucket = "Hard"
        elo_type = "hard_elo"
    elif raw:
        surface = UNKNOWN_SURFACE
        model_bucket = UNKNOWN_SURFACE
        elo_type = "overall_elo"
        confidence = "LOW"
        flags.append("UNKNOWN_SURFACE_TYPE")
    else:
        surface = UNKNOWN_SURFACE
        model_bucket = UNKNOWN_SURFACE
        elo_type = "overall_elo"
        confidence = "LOW"
        flags.append("MISSING_SURFACE_TYPE")

    return {
        "surface": surface,
        "surface_raw": raw or None,
        "surface_environment": environment,
        "surface_model_bucket": model_bucket,
        "surface_confidence": confidence,
        "thinq_selected_elo_type": elo_type,
        "surface_flags": flags,
    }


def _load_cache(cache_file: Path = CACHE_FILE) -> Dict[str, Any]:
    try:
        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"generated_at": None, "source": "tennisapi_getTournamentInfoMetadata", "items": {}}


def _save_cache(cache: Dict[str, Any], cache_file: Path = CACHE_FILE) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache["generated_at"] = utc_now_iso()
    tmp = cache_file.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.replace(cache_file)


def _extract_surface_type(payload: Dict[str, Any]) -> Optional[str]:
    meta = payload.get("meta") if isinstance(payload, dict) else None
    if not isinstance(meta, dict):
        return None

    # TennisApi example: meta.playingMonths[0].surfaceType
    months = meta.get("playingMonths")
    if isinstance(months, list):
        for item in months:
            if isinstance(item, dict) and item.get("surfaceType"):
                return str(item.get("surfaceType"))

    # Defensive fallbacks for possible response variants
    for key in ("surfaceType", "surface", "courtSurface"):
        if meta.get(key):
            return str(meta.get(key))

    return None


def _extract_meta_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    meta = payload.get("meta") if isinstance(payload, dict) else None
    if not isinstance(meta, dict):
        meta = {}
    unique = meta.get("uniqueTournament") if isinstance(meta.get("uniqueTournament"), dict) else {}
    category = meta.get("category") if isinstance(meta.get("category"), dict) else {}
    return {
        "competition_name": meta.get("competitionName"),
        "city_name": meta.get("cityName"),
        "match_type": meta.get("matchType"),
        "unique_tournament_name": unique.get("name"),
        "unique_tournament_slug": unique.get("slug"),
        "category_name": category.get("name"),
        "category_slug": category.get("slug"),
    }


def fetch_tournament_metadata(tournament_id: Any, timeout: int = 20) -> Dict[str, Any]:
    """Fetch TennisApi PRO tournament info metadata from RapidAPI."""
    if requests is None:
        raise RuntimeError("requests is not installed")
    api_key = os.getenv("RAPIDAPI_KEY") or os.getenv("X_RAPIDAPI_KEY")
    if not api_key:
        raise RuntimeError("Missing RAPIDAPI_KEY")

    url = f"{DEFAULT_BASE_URL.rstrip('/')}/api/tennis/tournament/{tournament_id}/info"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": DEFAULT_HOST,
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def resolve_tournament_surface(
    tournament_id: Any = None,
    tournament_name: Any = None,
    match: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Resolve and normalize tournament surface.

    Returns a dict with:
    - surface
    - surface_raw
    - surface_environment
    - surface_model_bucket
    - thinq_selected_elo_type
    - surface_source
    - surface_confidence
    - surface_flags
    """
    match = match or {}
    tid = tournament_id or match.get("tournament_id") or match.get("tournamentId") or match.get("unique_tournament_id")
    name = tournament_name or match.get("tournament") or match.get("competitionName") or match.get("event_name")
    cache_key = str(tid) if tid not in (None, "") else _safe_key(name)

    cache = _load_cache()
    items = cache.setdefault("items", {})
    if not force_refresh and cache_key in items:
        cached = dict(items[cache_key])
        cached["cache_used"] = True
        return cached

    # First trust explicit surfaceType-like fields in the match if present.
    explicit_raw = (
        match.get("surfaceType")
        or match.get("surface_raw")
        or match.get("surfaceRaw")
        or match.get("courtSurface")
    )
    if explicit_raw:
        normalized = normalize_surface_type(explicit_raw)
        normalized.update({
            "surface_source": "match_surface_type",
            "tournament_id": tid,
            "tournament_name": name,
            "cache_key": cache_key,
            "cache_used": False,
        })
        if persist:
            items[cache_key] = normalized
            _save_cache(cache)
        return normalized

    raw_payload = None
    fetch_error = None
    if tid not in (None, ""):
        try:
            raw_payload = fetch_tournament_metadata(tid)
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            raw_path = RAW_DIR / f"{_safe_key(tid)}.json"
            with raw_path.open("w", encoding="utf-8") as f:
                json.dump(raw_payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception as exc:
            fetch_error = str(exc)

    surface_type = _extract_surface_type(raw_payload or {}) if raw_payload else None
    if surface_type:
        normalized = normalize_surface_type(surface_type)
        normalized.update(_extract_meta_fields(raw_payload or {}))
        normalized.update({
            "surface_source": "tennisapi_getTournamentInfoMetadata",
            "tournament_id": tid,
            "tournament_name": name,
            "cache_key": cache_key,
            "cache_used": False,
            "fetch_error": None,
        })
    else:
        # Do not default to Hard. Unknown means overall_elo.
        normalized = normalize_surface_type(None)
        normalized.update({
            "surface_source": "unknown",
            "tournament_id": tid,
            "tournament_name": name,
            "cache_key": cache_key,
            "cache_used": False,
            "fetch_error": fetch_error,
        })

    if persist:
        items[cache_key] = normalized
        _save_cache(cache)
    return normalized


def select_elo_value(player_elo: Dict[str, Any], surface_info: Dict[str, Any]) -> Dict[str, Any]:
    """Select the best available ELO value for resolved surface."""
    elo_type = surface_info.get("thinq_selected_elo_type") or "overall_elo"
    keys_by_type = {
        "hard_elo": ["hard_elo", "h_elo", "hElo"],
        "clay_elo": ["clay_elo", "c_elo", "cElo"],
        "grass_elo": ["grass_elo", "g_elo", "gElo"],
        "carpet_elo": ["carpet_elo"],
        "overall_elo": ["elo", "overall_elo", "ta_elo"],
    }
    fallback_keys = ["elo", "overall_elo", "ta_elo"]
    flags = list(surface_info.get("surface_flags") or [])

    value = None
    selected_key = None
    for key in keys_by_type.get(elo_type, []):
        if player_elo.get(key) not in (None, ""):
            value = player_elo.get(key)
            selected_key = key
            break

    if value is None:
        for key in fallback_keys:
            if player_elo.get(key) not in (None, ""):
                value = player_elo.get(key)
                selected_key = key
                flags.append("SURFACE_ELO_MISSING_USED_OVERALL")
                break

    return {
        "selected_elo": value,
        "selected_elo_type": elo_type,
        "selected_elo_key": selected_key,
        "selected_elo_flags": flags,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Resolve TennisApi tournament surface for THINQ.")
    parser.add_argument("--tournament-id", dest="tournament_id", required=False)
    parser.add_argument("--surface-type", dest="surface_type", required=False)
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()

    if args.surface_type:
        print(json.dumps(normalize_surface_type(args.surface_type), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(resolve_tournament_surface(args.tournament_id, force_refresh=args.force_refresh), ensure_ascii=False, indent=2))
