import csv
import json
import logging
import os
import unicodedata
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from tennisapi_client import TennisApiClient

logger = logging.getLogger(__name__)

_H2H_CACHE: Dict[str, Dict[str, Any]] = {}
_EVENT_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
_SACKMANN_CSV_CACHE: Dict[str, List[Dict[str, Any]]] = {}

H2H_DATA_DIR = Path(os.getenv("H2H_DATA_DIR", "thinq/data/h2h"))
H2H_NORMALIZED_DIR = H2H_DATA_DIR / "normalized"
H2H_RAW_API_DIR = H2H_DATA_DIR / "raw" / "api"
H2H_RAW_SACKMANN_DIR = H2H_DATA_DIR / "raw" / "sackmann"
LOCAL_SACKMANN_CACHE_DIR = Path(os.getenv("SACKMANN_H2H_CACHE_DIR", str(H2H_DATA_DIR / "sackmann_csv")))
SACKMANN_H2H_YEARS = int(os.getenv("SACKMANN_H2H_YEARS", "12"))
SACKMANN_H2H_ENABLED = os.getenv("SACKMANN_H2H_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
H2H_PERSIST_ENABLED = os.getenv("H2H_PERSIST_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}

SACKMANN_SOURCES = [
    ("atp_main", "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{year}.csv"),
    ("atp_qual_chall", "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_qual_chall_{year}.csv"),
    ("wta_main", "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{year}.csv"),
]


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
    if not ta or not tb:
        return False
    if ta & tb:
        return True
    a_parts = na.split()
    b_parts = nb.split()
    return bool(a_parts and b_parts and a_parts[-1] == b_parts[-1])


def _team_name(team: Any) -> str:
    if isinstance(team, dict):
        for key in ("name", "shortName", "fullName", "displayName", "slug"):
            value = team.get(key)
            if value:
                return str(value)
    return str(team or "")


def _extract_event(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        event = payload.get("event")
        if isinstance(event, dict):
            return event
        data = payload.get("data")
        if isinstance(data, dict):
            nested = data.get("event")
            if isinstance(nested, dict):
                return nested
            if data.get("homeTeam") or data.get("awayTeam"):
                return data
        if payload.get("homeTeam") or payload.get("awayTeam"):
            return payload
    return None


def _extract_events(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("events", "h2h", "data", "items", "results", "matches"):
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
    if "hard" in text or "indoor" in text:
        return "hard"
    return ""


def _safe_slug(value: Any, max_len: int = 80) -> str:
    text = _normalize_name(value).replace(" ", "-")
    text = "".join(ch for ch in text if ch.isalnum() or ch == "-")
    text = text.strip("-")
    return (text[:max_len] or "unknown")


def _h2h_match_slug(event_id: Optional[Any], player1: str, player2: str) -> str:
    event_part = str(event_id) if event_id not in [None, ""] else "noevent"
    return f"{event_part}__{_safe_slug(player1)}__vs__{_safe_slug(player2)}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _write_json(path: Path, payload: Any) -> None:
    if not H2H_PERSIST_ENABLED:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:
        logger.debug("H2H persist failed path=%s error=%s", path, exc)


def _persist_h2h_artifacts(
    event_id: Optional[Any],
    player1: str,
    player2: str,
    pick: str,
    surface: Optional[str],
    result: Dict[str, Any],
    api_events: List[Dict[str, Any]],
    sackmann_events: List[Dict[str, Any]],
    combined_events: List[Dict[str, Any]],
    api_payload: Any = None,
    api_endpoint_path: Optional[str] = None,
) -> None:
    if not H2H_PERSIST_ENABLED:
        return

    slug = _h2h_match_slug(event_id, player1, player2)
    persisted_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    normalized_payload = {
        "schema_version": "h2h_context_v1",
        "persisted_at_utc": persisted_at,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "pick": pick,
        "surface": surface,
        "result": result,
        "events": combined_events,
    }
    _write_json(H2H_NORMALIZED_DIR / f"{slug}.json", normalized_payload)
    if event_id not in [None, ""]:
        _write_json(H2H_NORMALIZED_DIR / "by_event" / f"{event_id}.json", normalized_payload)

    raw_index = {
        "schema_version": "h2h_raw_index_v1",
        "persisted_at_utc": persisted_at,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "api_endpoint_path": api_endpoint_path,
        "api_events_count": len(api_events),
        "sackmann_events_count": len(sackmann_events),
    }
    _write_json(H2H_DATA_DIR / "index" / f"{slug}.json", raw_index)

    if api_payload is not None:
        _write_json(H2H_RAW_API_DIR / f"{slug}.json", {"endpoint_path": api_endpoint_path, "payload": api_payload})
    if sackmann_events:
        _write_json(H2H_RAW_SACKMANN_DIR / f"{slug}.json", {"events": sackmann_events})


def _event_players(event: Dict[str, Any]) -> Tuple[str, str]:
    home = _team_name(event.get("homeTeam") or event.get("home") or event.get("participant1"))
    away = _team_name(event.get("awayTeam") or event.get("away") or event.get("participant2"))
    return home, away


def _pick_result_for_event(event: Dict[str, Any], pick: str) -> Optional[bool]:
    # Sackmann normalized pseudo-events carry this directly.
    if isinstance(event.get("pick_won"), bool):
        return bool(event.get("pick_won"))

    home, away = _event_players(event)
    winner_code = event.get("winnerCode")
    try:
        winner_code = int(winner_code)
    except Exception:
        winner_code = None
    if winner_code in (1, 2):
        if _same_player(pick, home):
            return winner_code == 1
        if _same_player(pick, away):
            return winner_code == 2

    winner_team = event.get("winnerTeam") or event.get("winner")
    winner_name = _team_name(winner_team)
    if winner_name:
        return _same_player(pick, winner_name)
    return None


def _valid_h2h_event(event: Dict[str, Any], player1: str, player2: str) -> bool:
    home, away = _event_players(event)
    direct = _same_player(player1, home) and _same_player(player2, away)
    reverse = _same_player(player1, away) and _same_player(player2, home)
    return direct or reverse


def _score_summary(event: Dict[str, Any]) -> str:
    if event.get("score_summary"):
        return str(event.get("score_summary"))
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


def _event_surface(event: Dict[str, Any]) -> str:
    direct = event.get("groundType") or event.get("surface")
    if direct:
        return _surface_key(direct)
    tournament = event.get("tournament")
    if isinstance(tournament, dict):
        unique = tournament.get("uniqueTournament")
        if isinstance(unique, dict):
            value = unique.get("groundType") or unique.get("surface")
            if value:
                return _surface_key(value)
        value = tournament.get("groundType") or tournament.get("surface")
        if value:
            return _surface_key(value)
    return ""


def _empty_h2h(event_id: Optional[Any] = None, reason: str = "No H2H data") -> Dict[str, Any]:
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
        "h2h_adjustment_pct": 0.0,
        "h2h_component_pct": 0.0,
        "thinq_h2h_pct": 0.0,
        "h2h_reason": reason,
        "h2h_recent_result": None,
        "h2h_raw_count": 0,
        "h2h_endpoint_path": None,
        "h2h_source": "none",
        "h2h_api_total_matches": 0,
        "h2h_sackmann_total_matches": 0,
    }


def _compute_adjustment_pct(total: int, pick_wins: int, same_surface_total: int = 0, same_surface_pick_wins: int = 0) -> float:
    if total <= 0:
        return 0.0
    opponent_wins = total - pick_wins
    pick_win_pct = pick_wins / total
    sample_weight = min(total / 4.0, 1.0)
    adjustment = (pick_win_pct - 0.5) * 8.0 * sample_weight
    if same_surface_total > 0:
        same_surface_pct = same_surface_pick_wins / same_surface_total
        surface_weight = min(same_surface_total / 3.0, 1.0)
        adjustment += (same_surface_pct - 0.5) * 3.0 * surface_weight
    adjustment = max(-5.0, min(5.0, adjustment))
    if pick_wins == opponent_wins and same_surface_total == 0:
        adjustment = 0.0
    return round(adjustment, 1)


def fetch_event_details(event_id: Any, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    if not event_id:
        return None
    key = str(event_id)
    if key in _EVENT_CACHE and not force_refresh:
        return _EVENT_CACHE[key]
    client = TennisApiClient()
    try:
        payload = client.get_match_details(int(event_id))
        event = _extract_event(payload)
        _EVENT_CACHE[key] = event
        return event
    except Exception as exc:
        logger.debug("H2H event details failed. event_id=%s error=%s", event_id, exc)
        _EVENT_CACHE[key] = None
        return None


def fetch_h2h_history_payload(event_id: Any, force_refresh: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not event_id:
        return None, None
    key = f"history:{event_id}"
    if key in _H2H_CACHE and not force_refresh:
        cached = _H2H_CACHE[key]
        return cached.get("payload"), cached.get("path")
    client = TennisApiClient()
    paths = [
        f"/api/tennis/event/{event_id}/h2h/events",
        f"/api/tennis/event/{event_id}/h2h/history",
        f"/api/tennis/event/{event_id}/head-to-head/history",
        f"/api/tennis/event/{event_id}/head-to-head/events",
        f"/api/tennis/event/{event_id}/headtohead/history",
        f"/api/tennis/event/{event_id}/h2h",
        f"/api/tennis/event/{event_id}/head-to-head",
        f"/api/tennis/match/{event_id}/h2h/events",
        f"/api/tennis/match/{event_id}/h2h/history",
    ]
    for path in paths:
        try:
            payload = client._request_json("GET", path)
            events = _extract_events(payload)
            if events:
                _H2H_CACHE[key] = {"payload": payload, "path": path}
                print(f"H2H DEBUG: api history ok event_id={event_id} path={path} events={len(events)}")
                return payload, path
        except Exception as exc:
            logger.debug("H2H history candidate failed. path=%s error=%s", path, exc)
    print(f"H2H DEBUG: api history missing event_id={event_id}")
    _H2H_CACHE[key] = {"payload": None, "path": None}
    return None, None


def fetch_h2h_summary_payload(event_id: Any, force_refresh: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not event_id:
        return None, None
    key = f"summary:{event_id}"
    if key in _H2H_CACHE and not force_refresh:
        cached = _H2H_CACHE[key]
        return cached.get("payload"), cached.get("path")
    client = TennisApiClient()
    paths = [
        f"/api/tennis/event/{event_id}/h2h/summary",
        f"/api/tennis/event/{event_id}/head-to-head/summary",
        f"/api/tennis/event/{event_id}/headtohead/summary",
        f"/api/tennis/match/{event_id}/h2h/summary",
    ]
    for path in paths:
        try:
            payload = client._request_json("GET", path)
            if isinstance(payload, dict) and payload:
                keys = set(payload.keys()) | set(payload.get("data", {}).keys() if isinstance(payload.get("data"), dict) else [])
                if keys & {"homeWins", "awayWins", "player1Wins", "player2Wins", "homeTeamWins", "awayTeamWins", "h2h"}:
                    _H2H_CACHE[key] = {"payload": payload, "path": path}
                    print(f"H2H DEBUG: api summary ok event_id={event_id} path={path}")
                    return payload, path
        except Exception as exc:
            logger.debug("H2H summary candidate failed. path=%s error=%s", path, exc)
    _H2H_CACHE[key] = {"payload": None, "path": None}
    return None, None


def _summary_counts(payload: Dict[str, Any], current_event: Optional[Dict[str, Any]], pick: str) -> Optional[Tuple[int, int]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        return None
    home_wins = data.get("homeWins") or data.get("homeTeamWins")
    away_wins = data.get("awayWins") or data.get("awayTeamWins")
    p1_wins = data.get("player1Wins") or data.get("player1AllWins")
    p2_wins = data.get("player2Wins") or data.get("player2AllWins")

    def to_int(value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except Exception:
            return None

    home_wins_i = to_int(home_wins)
    away_wins_i = to_int(away_wins)
    if current_event and home_wins_i is not None and away_wins_i is not None:
        home, away = _event_players(current_event)
        if _same_player(pick, home):
            return home_wins_i, away_wins_i
        if _same_player(pick, away):
            return away_wins_i, home_wins_i

    p1_wins_i = to_int(p1_wins)
    p2_wins_i = to_int(p2_wins)
    if p1_wins_i is not None and p2_wins_i is not None:
        if current_event:
            home, away = _event_players(current_event)
            if _same_player(pick, home):
                return p1_wins_i, p2_wins_i
            if _same_player(pick, away):
                return p2_wins_i, p1_wins_i
        return p1_wins_i, p2_wins_i
    return None


def _read_remote_csv(url: str, cache_path: Path, force_refresh: bool = False) -> List[Dict[str, Any]]:
    cache_key = str(cache_path)
    if cache_key in _SACKMANN_CSV_CACHE and not force_refresh:
        return _SACKMANN_CSV_CACHE[cache_key]

    text = None
    if cache_path.exists() and not force_refresh:
        try:
            text = cache_path.read_text(encoding="utf-8")
        except Exception:
            text = None

    if text is None:
        try:
            response = requests.get(url, timeout=25)
            if response.status_code != 200 or "," not in response.text:
                _SACKMANN_CSV_CACHE[cache_key] = []
                return []
            text = response.text
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")
        except Exception as exc:
            logger.debug("Sackmann H2H CSV fetch failed url=%s error=%s", url, exc)
            _SACKMANN_CSV_CACHE[cache_key] = []
            return []

    try:
        rows = list(csv.DictReader(StringIO(text)))
    except Exception as exc:
        logger.debug("Sackmann H2H CSV parse failed path=%s error=%s", cache_path, exc)
        rows = []
    _SACKMANN_CSV_CACHE[cache_key] = rows
    return rows


def _sackmann_years() -> List[int]:
    current_year = datetime.utcnow().year
    return list(range(current_year, current_year - SACKMANN_H2H_YEARS, -1))


def _sackmann_event_from_row(row: Dict[str, Any], player1: str, player2: str, pick: str, source_label: str) -> Optional[Dict[str, Any]]:
    winner = row.get("winner_name") or row.get("winner")
    loser = row.get("loser_name") or row.get("loser")
    if not winner or not loser:
        return None

    direct = _same_player(player1, winner) and _same_player(player2, loser)
    reverse = _same_player(player1, loser) and _same_player(player2, winner)
    if not direct and not reverse:
        return None

    pick_won = _same_player(pick, winner)
    score = row.get("score") or ""
    tourney_date = row.get("tourney_date") or row.get("date") or ""
    surface = row.get("surface") or ""
    tourney = row.get("tourney_name") or row.get("tournament") or ""
    winner_rank = row.get("winner_rank") or ""
    loser_rank = row.get("loser_rank") or ""

    return {
        "homeTeam": {"name": str(winner)},
        "awayTeam": {"name": str(loser)},
        "winnerCode": 1,
        "winnerTeam": {"name": str(winner)},
        "pick_won": pick_won,
        "surface": surface,
        "groundType": surface,
        "tournament": {"name": tourney, "surface": surface},
        "startDate": tourney_date,
        "tourney_date": tourney_date,
        "score": score,
        "score_summary": f"{winner} def. {loser} {score}".strip(),
        "h2h_source": f"sackmann:{source_label}",
        "winner_rank": winner_rank,
        "loser_rank": loser_rank,
    }


def fetch_sackmann_h2h_events(
    player1: str,
    player2: str,
    pick: str,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    if not SACKMANN_H2H_ENABLED:
        return []

    cache_key = f"sackmann:{_normalize_name(player1)}:{_normalize_name(player2)}"
    if cache_key in _H2H_CACHE and not force_refresh:
        cached = _H2H_CACHE[cache_key].get("events")
        return cached if isinstance(cached, list) else []

    output: List[Dict[str, Any]] = []
    for year in _sackmann_years():
        for label, template in SACKMANN_SOURCES:
            url = template.format(year=year)
            path = LOCAL_SACKMANN_CACHE_DIR / label / f"{year}.csv"
            rows = _read_remote_csv(url, path, force_refresh=force_refresh)
            if not rows:
                continue
            for row in rows:
                event = _sackmann_event_from_row(row, player1, player2, pick, label)
                if event:
                    output.append(event)

    _H2H_CACHE[cache_key] = {"events": output}
    if output:
        print(f"H2H DEBUG: sackmann ok {player1} vs {player2} events={len(output)}")
    return output


def _event_key(event: Dict[str, Any]) -> str:
    home, away = _event_players(event)
    names = sorted([_normalize_name(home), _normalize_name(away)])
    date = str(event.get("startDate") or event.get("tourney_date") or event.get("startTimestamp") or "")
    score = str(event.get("score") or event.get("score_summary") or "")
    return "|".join(names + [date, score])


def _usable_api_events(events: List[Dict[str, Any]], player1: str, player2: str, pick: str) -> List[Dict[str, Any]]:
    output = []
    for event in events:
        if not _valid_h2h_event(event, player1, player2):
            continue
        if _pick_result_for_event(event, pick) is None:
            continue
        output.append(event)
    return output


def _merge_events(api_events: List[Dict[str, Any]], sackmann_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []
    for event in api_events + sackmann_events:
        key = _event_key(event)
        if key in seen:
            continue
        seen.add(key)
        output.append(event)
    return output


def _source_label(api_count: int, sackmann_count: int) -> str:
    if api_count > 0 and sackmann_count > 0:
        return "api+sackmann"
    if api_count > 0:
        return "api"
    if sackmann_count > 0:
        return "sackmann"
    return "none"


def build_h2h_context(
    event_id: Optional[Any],
    player1: str,
    player2: str,
    pick: str,
    surface: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    current_event = fetch_event_details(event_id, force_refresh=force_refresh) if event_id else None
    current_surface_key = _surface_key(surface) or _event_surface(current_event or {})

    history_payload, history_path = fetch_h2h_history_payload(event_id, force_refresh=force_refresh) if event_id else (None, None)
    api_raw_events = _extract_events(history_payload) if history_payload else []
    api_events = _usable_api_events(api_raw_events, player1, player2, pick)

    endpoint_path = history_path
    summary_counts: Optional[Tuple[int, int]] = None

    if not api_events and event_id:
        summary_payload, summary_path = fetch_h2h_summary_payload(event_id, force_refresh=force_refresh)
        endpoint_path = summary_path or endpoint_path
        if summary_payload:
            summary_counts = _summary_counts(summary_payload, current_event, pick)

    sackmann_events = fetch_sackmann_h2h_events(player1, player2, pick, force_refresh=force_refresh)
    events = _merge_events(api_events, sackmann_events)

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
        event_surface_key = _event_surface(event)
        if current_surface_key and event_surface_key and current_surface_key == event_surface_key:
            same_surface_total += 1
            if pick_won:
                same_surface_pick_wins += 1

    # If event history has no usable events but summary has totals, use summary as API source.
    if total <= 0 and summary_counts:
        pick_wins, opponent_wins = summary_counts
        total = pick_wins + opponent_wins
        same_surface_total = 0
        same_surface_pick_wins = 0
    else:
        opponent_wins = total - pick_wins

    api_count = len(api_events) if api_events else (total if summary_counts and total > 0 and not events else 0)
    sackmann_count = len(sackmann_events)
    source = _source_label(api_count, sackmann_count)

    if total <= 0:
        result = _empty_h2h(event_id, reason="No usable H2H events")
        result["h2h_raw_count"] = len(api_raw_events) + sackmann_count
        result["h2h_endpoint_path"] = endpoint_path
        result["h2h_source"] = source
        result["h2h_api_total_matches"] = api_count
        result["h2h_sackmann_total_matches"] = sackmann_count
        _persist_h2h_artifacts(
            event_id=event_id,
            player1=player1,
            player2=player2,
            pick=pick,
            surface=surface,
            result=result,
            api_events=api_events,
            sackmann_events=sackmann_events,
            combined_events=events,
            api_payload=history_payload,
            api_endpoint_path=endpoint_path,
        )
        return result

    opponent_wins = total - pick_wins
    pick_win_pct = pick_wins / total
    same_surface_pick_win_pct = (same_surface_pick_wins / same_surface_total) if same_surface_total > 0 else None

    if pick_wins > opponent_wins:
        signal = "SUPPORT"
        reason = f"Pick leads H2H {pick_wins}-{opponent_wins}"
    elif pick_wins < opponent_wins:
        signal = "AGAINST"
        reason = f"Pick trails H2H {pick_wins}-{opponent_wins}"
    else:
        signal = "NEUTRAL"
        reason = f"H2H balanced {pick_wins}-{opponent_wins}"

    adjustment_pct = _compute_adjustment_pct(total, pick_wins, same_surface_total, same_surface_pick_wins)

    result = {
        "h2h_event_id": event_id,
        "h2h_total_matches": total,
        "h2h_pick_wins": pick_wins,
        "h2h_opponent_wins": opponent_wins,
        "h2h_pick_win_pct": round(pick_win_pct, 4),
        "h2h_same_surface_matches": same_surface_total,
        "h2h_same_surface_pick_wins": same_surface_pick_wins,
        "h2h_same_surface_pick_win_pct": round(same_surface_pick_win_pct, 4) if same_surface_pick_win_pct is not None else None,
        "h2h_signal": signal,
        "h2h_adjustment": round(adjustment_pct / 100.0, 4),
        "h2h_adjustment_pct": adjustment_pct,
        "h2h_component_pct": adjustment_pct,
        "thinq_h2h_pct": adjustment_pct,
        "h2h_reason": reason,
        "h2h_recent_result": recent_result,
        "h2h_raw_count": len(api_raw_events) + sackmann_count,
        "h2h_endpoint_path": endpoint_path,
        "h2h_source": source,
        "h2h_api_total_matches": api_count,
        "h2h_sackmann_total_matches": sackmann_count,
    }
    _persist_h2h_artifacts(
        event_id=event_id,
        player1=player1,
        player2=player2,
        pick=pick,
        surface=surface,
        result=result,
        api_events=api_events,
        sackmann_events=sackmann_events,
        combined_events=events,
        api_payload=history_payload,
        api_endpoint_path=endpoint_path,
    )
    return result
