import time
import requests
from typing import Any, Dict, List, Optional
from config import API_BASE_URL, API_TOKEN

HEADERS = {
    "Authorization": f"Token {API_TOKEN}"
}

def safe_request(url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params or {}, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            time.sleep(1)
    return {}

def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    return safe_request(url, params)

def get_matches(date: str) -> List[Dict[str, Any]]:
    return _get("/matches/", {"date_from": date, "date_to": date}) or []

def get_match_detail(match_id: int) -> Dict[str, Any]:
    return _get(f"/matches/{match_id}/") or {}

def get_match_h2h(match_id: int) -> Dict[str, Any]:
    return _get(f"/matches/{match_id}/h2h/") or {}

def get_match_odds(match_id: int) -> Dict[str, Any]:
    return _get(f"/matches/{match_id}/odds/") or {}

def get_rankings(type_: str = "ATP") -> List[Dict[str, Any]]:
    return _get("/rankings/", {"type": type_}) or []
