from __future__ import annotations
from typing import Any, Dict
import re

def first_value(mapping: Dict[str, Any], keys, default=None):
    for key in keys:
        if key in mapping and mapping.get(key) not in (None, ""):
            return mapping.get(key)
    return default

def dig(mapping: Dict[str, Any], *path, default=None):
    cur = mapping
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur

def normalize_name(value: Any) -> str:
    return " ".join(str(value or "").replace("_", " ").split()).strip()

def normalize_surface_string(value: Any) -> str:
    raw = str(value or "").strip()
    text = raw.lower()
    if not text or text in {"unknown", "none", "null", "-"}:
        return "Unknown"
    if "clay" in text:
        return "Clay"
    if "grass" in text:
        return "Grass"
    if "carpet" in text:
        return "Carpet"
    if "hard" in text:
        return "Hard"
    return "Unknown"

def is_doubles_match(match: Dict[str, Any]) -> bool:
    text = " ".join(str(match.get(k, "")) for k in ["match", "player1", "player2", "tournament", "competitionName", "match_type", "matchType"])
    return "/" in text or bool(re.search(r"\bdoubles?\b", text, re.I))

def extract_players(raw: Dict[str, Any]) -> tuple[str, str]:
    player1 = first_value(raw, ["player1", "home", "home_name", "homeTeam", "player_one", "p1"])
    player2 = first_value(raw, ["player2", "away", "away_name", "awayTeam", "player_two", "p2"])
    if isinstance(player1, dict):
        player1 = first_value(player1, ["name", "shortName", "fullName"])
    if isinstance(player2, dict):
        player2 = first_value(player2, ["name", "shortName", "fullName"])
    player1 = player1 or dig(raw, "homeTeam", "name") or dig(raw, "home", "name")
    player2 = player2 or dig(raw, "awayTeam", "name") or dig(raw, "away", "name")
    match_name = str(raw.get("match") or raw.get("event_name") or "")
    if (not player1 or not player2) and " vs " in match_name.lower():
        parts = re.split(r"\s+vs\s+", match_name, flags=re.I)
        if len(parts) == 2:
            player1 = player1 or parts[0]
            player2 = player2 or parts[1]
    return normalize_name(player1), normalize_name(player2)

def normalize_match(raw: Dict[str, Any]) -> Dict[str, Any]:
    raw = dict(raw or {})
    player1, player2 = extract_players(raw)
    tournament = normalize_name(first_value(raw, ["tournament", "tourney_name", "competitionName", "league", "category_name"], ""))
    tournament_id = first_value(raw, ["tournament_id", "tournamentId", "competition_id", "competitionId"]) or dig(raw, "tournament", "id") or dig(raw, "competition", "id")
    unique_tournament_id = first_value(raw, ["unique_tournament_id", "uniqueTournamentId"]) or dig(raw, "uniqueTournament", "id") or dig(raw, "tournament", "uniqueTournament", "id")
    surface_raw = first_value(raw, ["surface_raw", "surfaceType", "surface", "court", "Court"], None)
    surface = normalize_surface_string(surface_raw)
    event_id = first_value(raw, ["event_id", "eventId", "id", "match_id", "matchId"])
    best_of = first_value(raw, ["best_of", "bestOf"], 3)
    output = {
        "event_id": event_id,
        "eventId": event_id,
        "tournament_id": tournament_id,
        "tournamentId": tournament_id,
        "unique_tournament_id": unique_tournament_id,
        "uniqueTournamentId": unique_tournament_id,
        "player1": player1,
        "player2": player2,
        "pick": raw.get("pick") or player1,
        "opponent": raw.get("opponent") or player2,
        "match": f"{player1} vs {player2}" if player1 and player2 else raw.get("match", ""),
        "tournament": tournament,
        "gender": first_value(raw, ["gender", "tour", "category"], None),
        "surface": surface,
        "surface_raw": surface_raw,
        "surface_source": raw.get("surface_source") or ("raw_event" if surface != "Unknown" else "unknown"),
        "best_of": int(best_of or 3) if str(best_of or "").isdigit() else 3,
        "time": first_value(raw, ["time", "match_time", "start_time", "startTime", "scheduled_time", "datetime"], None),
        "raw": raw,
    }
    for key in ["pick_odds", "opponent_odds", "odds", "odds_player1", "odds_player2", "p1_odds", "p2_odds", "home_odds", "away_odds"]:
        if key in raw:
            output[key] = raw.get(key)
    output["is_doubles"] = is_doubles_match(output)
    return output
