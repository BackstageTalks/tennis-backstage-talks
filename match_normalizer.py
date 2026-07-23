"""Match normalizer for clean CORQ runtime.

This module normalizes raw match dictionaries from the existing fetch_matches.py.
It intentionally never defaults surface to Hard. Unknown surface stays Unknown.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import re
import unicodedata


def first_value(source: Dict[str, Any], keys: list[str], default: Any = None) -> Any:
    for key in keys:
        if key in source and source.get(key) not in (None, ""):
            return source.get(key)
    return default


def norm_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def recursive_find_id(obj: Any, key_names: set[str]) -> Optional[Any]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in key_names and value not in (None, ""):
                return value
        for value in obj.values():
            found = recursive_find_id(value, key_names)
            if found not in (None, ""):
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = recursive_find_id(value, key_names)
            if found not in (None, ""):
                return found
    return None


def is_doubles_match(match: Dict[str, Any]) -> bool:
    fields = [
        match.get("match_type"), match.get("matchType"), match.get("type"),
        match.get("competitionName"), match.get("tournament"), match.get("match"),
        match.get("player1"), match.get("player2"),
    ]
    text = " ".join(str(x or "") for x in fields).lower()
    if "doubles" in text or " double" in text:
        return True
    return any("/" in str(match.get(k) or "") for k in ["player1", "player2", "pick", "opponent"])


def to_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def normalize_match(raw: Dict[str, Any]) -> Dict[str, Any]:
    raw = raw or {}
    player1 = norm_name(first_value(raw, ["player1", "home", "home_name", "player_one", "p1", "competitor1"]))
    player2 = norm_name(first_value(raw, ["player2", "away", "away_name", "player_two", "p2", "competitor2"]))

    # If match field contains "A vs B", use it as fallback.
    match_name = first_value(raw, ["match", "name", "event_name"])
    if (not player1 or not player2) and isinstance(match_name, str) and " vs " in match_name.lower():
        parts = re.split(r"\s+vs\s+", match_name, flags=re.I)
        if len(parts) >= 2:
            player1 = player1 or norm_name(parts[0])
            player2 = player2 or norm_name(parts[1])

    pick = norm_name(first_value(raw, ["pick", "prediction_pick", "winner_pick"], player1))
    opponent = norm_name(first_value(raw, ["opponent"], player2 if pick == player1 else player1))

    odds1 = to_float(first_value(raw, ["odds_player1", "p1_odds", "home_odds", "odds1", "price1"]))
    odds2 = to_float(first_value(raw, ["odds_player2", "p2_odds", "away_odds", "odds2", "price2"]))
    pick_odds = to_float(first_value(raw, ["pick_odds", "odds", "marq_current_pick_odds", "marq_initial_pick_odds"]))
    opponent_odds = to_float(first_value(raw, ["opponent_odds", "marq_current_opponent_odds", "marq_initial_opponent_odds"]))

    if pick_odds is None:
        if pick and player1 and pick.lower() == player1.lower():
            pick_odds = odds1
            opponent_odds = opponent_odds if opponent_odds is not None else odds2
        elif pick and player2 and pick.lower() == player2.lower():
            pick_odds = odds2
            opponent_odds = opponent_odds if opponent_odds is not None else odds1
    if opponent_odds is None:
        if pick and player1 and pick.lower() == player1.lower():
            opponent_odds = odds2
        elif pick and player2 and pick.lower() == player2.lower():
            opponent_odds = odds1

    tournament_id = first_value(raw, ["tournament_id", "tournamentId", "competition_id", "competitionId"])
    if tournament_id in (None, ""):
        tournament_id = recursive_find_id(raw.get("raw") or raw, {"tournamentId", "tournament_id", "competitionId", "competition_id"})
    unique_tournament_id = first_value(raw, ["unique_tournament_id", "uniqueTournamentId"])
    if unique_tournament_id in (None, ""):
        unique_tournament_id = recursive_find_id(raw.get("raw") or raw, {"uniqueTournamentId", "unique_tournament_id"})

    surface = first_value(raw, ["surface"])
    surface_raw = first_value(raw, ["surface_raw", "surfaceType"], surface)
    if not surface:
        surface = "Unknown"

    normalized = {
        **raw,
        "event_id": first_value(raw, ["event_id", "eventId", "id"]),
        "eventId": first_value(raw, ["event_id", "eventId", "id"]),
        "player1": player1,
        "player2": player2,
        "pick": pick,
        "opponent": opponent,
        "match": match_name or f"{player1} vs {player2}",
        "tournament": first_value(raw, ["tournament", "competition", "competitionName", "league", "category"], "-"),
        "tournament_id": tournament_id,
        "tournamentId": tournament_id,
        "unique_tournament_id": unique_tournament_id,
        "uniqueTournamentId": unique_tournament_id,
        "gender": first_value(raw, ["gender", "tour", "category_gender"], None),
        "surface": surface,
        "surface_raw": surface_raw,
        "best_of": int(first_value(raw, ["best_of", "bestOf"], 3) or 3),
        "odds_player1": odds1,
        "odds_player2": odds2,
        "pick_odds": pick_odds,
        "opponent_odds": opponent_odds,
        "odds_pair_available": pick_odds is not None and opponent_odds is not None,
        "is_doubles": bool(raw.get("is_doubles")) or is_doubles_match(raw),
        "raw": raw.get("raw") or raw,
    }
    if pick_odds is not None and opponent_odds is not None:
        try:
            normalized["odds_gap_abs"] = abs(pick_odds - opponent_odds)
            normalized["odds_gap_pct"] = abs(pick_odds - opponent_odds) / min(pick_odds, opponent_odds)
        except Exception:
            pass
    return normalized
