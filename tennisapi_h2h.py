import logging
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from tennisapi_client import TennisApiClient

logger = logging.getLogger(__name__)

_H2H_CACHE: Dict[str, Dict[str, Any]] = {}


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for ch in [".", ",", "'", "`", "’", "-", "_", "(", ")", "[", "]"]:
        text = text.replace(ch, " ")
    return " ".join(text.split())


def _tokens(value: Any) -> set[str]:
    return set(_normalize_name(value).split())


def _same_player(a: Any, b: Any) -> bool:
    na = _normalize_name(a)
    nb = _normalize_name(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    ta = _tokens(na)
    tb = _tokens(nb)
    return bool(ta & tb)


def _team_name(team: Any) -> str:
    if isinstance(team, dict):
        for key in ("name", "shortName", "fullName", "displayName", "slug"):
            value = team.get(key)
            if value:
                return str(value)
    return str(team or "")


def _extract_events(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("events", "h2h", "data", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = _extract_events(value)
                if nested:
                    return nested
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _surface_key(value: Any) -> str:
    text = str(value or "").lower()
    if "clay" in text:
        return "clay"
    if "grass" in text:
        return "grass"
    if "hard" in text:
        return "hard"
    if "indoor" in text:
        return "hard"
    return ""


def _event_players(event: Dict[str, Any]) -> Tuple[str, str]:
    home = _team_name(event.get("homeTeam") or event.get("home") or event.get("participant1"))
    away = _team_name(event.get("awayTeam") or event.get("away") or event.get("participant2"))
    return home, away


def _pick_result_for_event(event: Dict[str, Any], pick: str) -> Optional[bool]:
    home, away = _event_players(event)
    winner_code = event.get("winnerCode")
    try:
        winner_code = int(winner_code)
    except Exception:
        winner_code = None

    if not winner_code:
        return None

    if _same_player(pick, home):
        return winner_code == 1
    if _same_player(pick, away):
        return winner_code == 2
    return None


def _valid_h2h_event(event: Dict[str, Any], player1: str, player2: str) -> bool:
    home, away = _event_players(event)
    direct = _same_player(player1, home) and _same_player(player2, away)
    reverse = _same_player(player1, away) and _same_player(player2, home)
    return direct or reverse


def _score_summary(event: Dict[str, Any]) -> str:
    home, away = _event_players(event)
    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}
    if not isinstance(home_score, dict) or not isinstance(away_score, dict):
        return ""
    home_sets = home_score.get("current") or home_score.get("display")
    away_sets = away_score.get("current") or away_score.get("display")
    if home and away and home_sets is not None and away_sets is not None:
        return f"{home} {home_sets}-{away_sets} {away}"
    return ""


def _empty_h2h(event_id: Optional[Any] = None) -> Dict[str, Any]:
    return {
        "h2h_event_id": event_id,
        "h2h_total_matches": 0,
        "h2h_pick_wins": 0,
        "h2h_opponent_wins": 0,
        "h2h_pick_win_pct": None,
        "h2h_same_surface_matches": 0,
        "h2h_same_surface_pick_wins": 0,
        "h2h_same_surface_pick_win_pct": None,
        "h2h_signal": "NO_DATA",
        "h2h_adjustment": 0.0,
        "h2h_reason": "No H2H data",
        "h2h_recent_result": None,
        "h2h_raw_count": 0,
    }


def fetch_h2h_payload(event_id: Any, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    if not event_id:
        return None
    event_id = str(event_id)
    if event_id in _H2H_CACHE and not force_refresh:
        cached = _H2H_CACHE[event_id].get("payload")
        return cached if isinstance(cached, dict) else None

    client = TennisApiClient()
    paths = [
        f"/api/tennis/event/{event_id}/h2h/events",
        f"/api/tennis/event/{event_id}/h2h",
        f"/api/tennis/event/{event_id}/head-to-head/history",
        f"/api/tennis/event/{event_id}/head-to-head",
        f"/api/tennis/match/{event_id}/h2h/events",
    ]

    for path in paths:
        try:
            payload = client._request_json("GET", path)
            events = _extract_events(payload)
            if events:
                _H2H_CACHE[event_id] = {"payload": payload, "path": path}
                print(f"H2H DEBUG: ok event_id={event_id} path={path} events={len(events)}")
                return payload
        except Exception as exc:
            logger.debug("H2H endpoint failed. path=%s error=%s", path, exc)

    print(f"H2H DEBUG: missing event_id={event_id}")
    _H2H_CACHE[event_id] = {"payload": None, "path": None}
    return None


def build_h2h_context(
    event_id: Optional[Any],
    player1: str,
    player2: str,
    pick: str,
    surface: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    if not event_id:
        return _empty_h2h(event_id)

    payload = fetch_h2h_payload(event_id, force_refresh=force_refresh)
    if not payload:
        return _empty_h2h(event_id)

    events = [event for event in _extract_events(payload) if _valid_h2h_event(event, player1, player2)]
    if not events:
        result = _empty_h2h(event_id)
        result["h2h_raw_count"] = len(_extract_events(payload))
        return result

    current_surface_key = _surface_key(surface)
    total = 0
    pick_wins = 0
    same_surface_total = 0
    same_surface_pick_wins = 0
    recent_result = None

    for event in events:
        pick_won = _pick_result_for_event(event, pick)
        if pick_won is None:
            continue
        total += 1
        if pick_won:
            pick_wins += 1
        if recent_result is None:
            recent_result = _score_summary(event) or None

        event_surface_key = _surface_key(event.get("groundType") or event.get("surface") or event.get("tournament", {}).get("groundType") if isinstance(event.get("tournament"), dict) else None)
        if current_surface_key and event_surface_key and current_surface_key == event_surface_key:
            same_surface_total += 1
            if pick_won:
                same_surface_pick_wins += 1

    if total <= 0:
        result = _empty_h2h(event_id)
        result["h2h_raw_count"] = len(events)
        return result

    opponent_wins = total - pick_wins
    pick_win_pct = pick_wins / total
    same_surface_pick_win_pct = (same_surface_pick_wins / same_surface_total) if same_surface_total > 0 else None

    if total < 2:
        signal = "NO_DATA"
    elif pick_win_pct >= 0.67:
        signal = "SUPPORT"
    elif pick_win_pct <= 0.33:
        signal = "AGAINST"
    else:
        signal = "NEUTRAL"

    if signal == "SUPPORT":
        reason = f"Pick leads H2H {pick_wins}-{opponent_wins}"
    elif signal == "AGAINST":
        reason = f"Pick trails H2H {pick_wins}-{opponent_wins}"
    elif signal == "NEUTRAL":
        reason = f"H2H balanced {pick_wins}-{opponent_wins}"
    else:
        reason = "Insufficient H2H sample"

    return {
        "h2h_event_id": event_id,
        "h2h_total_matches": total,
        "h2h_pick_wins": pick_wins,
        "h2h_opponent_wins": opponent_wins,
        "h2h_pick_win_pct": round(pick_win_pct, 4),
        "h2h_same_surface_matches": same_surface_total,
        "h2h_same_surface_pick_wins": same_surface_pick_wins,
        "h2h_same_surface_pick_win_pct": round(same_surface_pick_win_pct, 4) if same_surface_pick_win_pct is not None else None,
        "h2h_signal": signal,
        "h2h_adjustment": 0.0,
        "h2h_reason": reason,
        "h2h_recent_result": recent_result,
        "h2h_raw_count": len(events),
    }
