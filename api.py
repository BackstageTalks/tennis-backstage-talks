# api.py
import requests
from typing import Any, Dict, List, Optional
from config import API_BASE_URL

def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    resp = requests.get(url, params=params or {})
    resp.raise_for_status()
    return resp.json()

def get_matches(date: str) -> List[Dict[str, Any]]:
    return _get("/matches/", {"date_from": date, "date_to": date})

def get_match_detail(match_id: int) -> Dict[str, Any]:
    return _get(f"/matches/{match_id}/")

def get_match_h2h(match_id: int) -> Dict[str, Any]:
    return _get(f"/matches/{match_id}/h2h/")

def get_match_odds(match_id: int) -> Dict[str, Any]:
    return _get(f"/matches/{match_id}/odds/")

def get_rankings(type_: str = "ATP") -> List[Dict[str, Any]]:
    return _get("/rankings/", {"type": type_})
