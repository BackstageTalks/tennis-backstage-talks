# THINQ_H2H_LAYER_VERSION = thinq_h2h_clean_v1
"""
THINQ / H2HQ Loader

Role in project:
- H2HQ is a standalone THINQ layer for head-to-head context.
- H2HQ does not create final match probability.
- H2HQ returns H2H feature/edge/confidence data for CORQ.

Primary source:
- Tennis API - ATP WTA ITF via RapidAPI
- Host: tennis-api-atp-wta-itf.p.rapidapi.com
- Name-based endpoints:
  - /tennis/v2/ms-api/h2h/playerType/{player}
  - /tennis/v2/ms-api/h2h/{tourType}/{player1}/{player2}/{limit}

Fallback source:
- SackmannLoader.load_matches() from thinq/loaders/sackmann_loader.py

Recommended location:
- thinq/loaders/h2h_loader.py

Environment variables:
- RAPIDAPI_KEY is preferred
- TENNIS_API_KEY is accepted as fallback

Important:
- H2H edge is intentionally capped because H2H usually has small sample size.
- H2HQ is a context signal, not a standalone model.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

try:
    from .sackmann_loader import SackmannLoader
except ImportError:
    # Allows direct local execution from thinq/loaders.
    from sackmann_loader import SackmannLoader


RAPIDAPI_HOST = "tennis-api-atp-wta-itf.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def normalize_player_name(name: Any) -> str:
    if name is None:
        return ""
    text = str(name).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_surface(surface: Optional[str]) -> Optional[str]:
    if surface is None:
        return None

    value = str(surface).strip().lower()
    if not value:
        return None

    mapping = {
        "hard": "hard",
        "clay": "clay",
        "grass": "grass",
        "carpet": "carpet",
        "i.hard": "indoor hard",
        "ihard": "indoor hard",
        "indoor": "indoor hard",
        "indoor hard": "indoor hard",
        "indoor_hard": "indoor hard",
    }
    return mapping.get(value, value)


def surface_to_api(surface: Optional[str]) -> Optional[str]:
    normalized = normalize_surface(surface)
    if normalized in ["hard", "clay", "grass", "carpet"]:
        return normalized
    if normalized == "indoor hard":
        # The public H2H matches endpoint accepts hard/clay/grass/carpet.
        # Indoor hard may still appear in response surfaceData, but query filter uses hard.
        return "hard"
    return None


def parse_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        try:
            return int(float(str(value).strip()))
        except Exception:
            return default


def parse_date_key(value: Any) -> str:
    if not value:
        return "0"
    text = str(value).strip()
    if re.match(r"^\d{8}$", text):
        return text
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            return datetime.fromisoformat(text[:10]).strftime("%Y%m%d")
    except Exception:
        pass
    return "0"


# -----------------------------------------------------------------------------
# Data schema
# -----------------------------------------------------------------------------


@dataclass
class H2HQData:
    player1: str
    player2: str
    surface: Optional[str] = None

    h2h_total_matches: int = 0
    h2h_player1_wins: int = 0
    h2h_player2_wins: int = 0

    h2h_surface_matches: int = 0
    h2h_surface_player1_wins: int = 0
    h2h_surface_player2_wins: int = 0

    h2h_recent_matches: int = 0
    h2h_recent_player1_wins: int = 0
    h2h_recent_player2_wins: int = 0
    h2h_recent_winner: Optional[str] = None

    h2h_edge: float = 0.0
    h2h_confidence: float = 0.0

    source: str = "none"
    api_status: str = "not_used"
    fallback_used: bool = False
    error: Optional[str] = None

    raw_api: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# -----------------------------------------------------------------------------
# Loader
# -----------------------------------------------------------------------------


class H2HLoader:
    """
    Standalone H2HQ loader for THINQ.

    Load order:
    1. Tennis API name-based H2H profile endpoint.
    2. Sackmann fallback from historical match cache.

    Returned edge is from player1 perspective:
    - positive h2h_edge means H2H favors player1
    - negative h2h_edge means H2H favors player2
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[str] = None,
        use_api: bool = True,
        use_cache: bool = True,
        use_sackmann_fallback: bool = True,
        timeout: int = 25,
        sackmann_loader: Optional[SackmannLoader] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY") or os.getenv("TENNIS_API_KEY")
        self.cache_dir = Path(cache_dir) if cache_dir else Path("thinq/data/h2h")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.use_api = use_api
        self.use_cache = use_cache
        self.use_sackmann_fallback = use_sackmann_fallback
        self.timeout = timeout
        self.sackmann_loader = sackmann_loader

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_h2h(
        self,
        player1: str,
        player2: str,
        surface: Optional[str] = None,
        tour_type: Optional[str] = None,
        limit: bool = False,
        include_all: bool = False,
    ) -> Dict[str, Any]:
        """
        Main method used by THINQ.

        Args:
            player1: First player display name.
            player2: Second player display name.
            surface: Optional current match surface.
            tour_type: Optional atp/wta. If missing, loader tries playerType endpoint.
            limit: Passed to profile endpoint as true/false string.
            include_all: Query parameter for profile endpoint.
        """
        cache_key = self._cache_key(player1, player2, surface, tour_type, limit, include_all)

        if self.use_cache:
            cached = self._read_cache(cache_key)
            if cached:
                return cached

        result: Optional[Dict[str, Any]] = None
        api_error: Optional[str] = None

        if self.use_api and self.api_key:
            try:
                result = self._load_from_api(
                    player1=player1,
                    player2=player2,
                    surface=surface,
                    tour_type=tour_type,
                    limit=limit,
                    include_all=include_all,
                )
            except Exception as exc:
                api_error = str(exc)

        if not result and self.use_sackmann_fallback:
            result = self._load_from_sackmann(
                player1=player1,
                player2=player2,
                surface=surface,
                api_error=api_error,
            )

        if not result:
            data = H2HQData(
                player1=player1,
                player2=player2,
                surface=surface,
                source="none",
                api_status="failed" if api_error else "not_used",
                error=api_error,
            )
            result = data.to_dict()

        if self.use_cache:
            self._write_cache(cache_key, result)

        return result

    # Compatibility alias.
    def load_match(
        self,
        player1: str,
        player2: str,
        surface: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.load_h2h(player1=player1, player2=player2, surface=surface, **kwargs)

    # ------------------------------------------------------------------
    # Tennis API source
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "X-RapidAPI-Key": self.api_key or "",
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }

    def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{RAPIDAPI_BASE_URL}{path}"
        response = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)
        if response.status_code == 204:
            return None
        if response.status_code != 200:
            raise RuntimeError(f"API HTTP {response.status_code}: {url} :: {response.text[:300]}")
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"API JSON decode failed: {url} :: {exc}")

    def get_player_type(self, player_name: str) -> Optional[str]:
        encoded = quote(player_name.strip())
        data = self._get_json(f"/tennis/v2/ms-api/h2h/playerType/{encoded}")
        if not isinstance(data, dict):
            return None
        value = data.get("type")
        if not value:
            return None
        value = str(value).strip().lower()
        if value in ["atp", "wta"]:
            return value
        return None

    def _resolve_tour_type(self, player1: str, player2: str, tour_type: Optional[str]) -> Optional[str]:
        if tour_type:
            value = str(tour_type).strip().lower()
            if value in ["atp", "wta"]:
                return value

        p1_type = self.get_player_type(player1)
        if p1_type in ["atp", "wta"]:
            return p1_type

        p2_type = self.get_player_type(player2)
        if p2_type in ["atp", "wta"]:
            return p2_type

        return None

    def _load_from_api(
        self,
        player1: str,
        player2: str,
        surface: Optional[str],
        tour_type: Optional[str],
        limit: bool,
        include_all: bool,
    ) -> Optional[Dict[str, Any]]:
        resolved_tour = self._resolve_tour_type(player1, player2, tour_type)
        if not resolved_tour:
            raise RuntimeError("Could not resolve tour_type for H2H API")

        encoded_p1 = quote(player1.strip())
        encoded_p2 = quote(player2.strip())
        limit_text = "true" if limit else "false"
        include_all_text = "true" if include_all else "false"

        path = f"/tennis/v2/ms-api/h2h/{resolved_tour}/{encoded_p1}/{encoded_p2}/{limit_text}"
        raw = self._get_json(path, params={"includeAll": include_all_text})

        if not isinstance(raw, dict):
            return None

        parsed = self._parse_api_profile(
            raw=raw,
            player1=player1,
            player2=player2,
            surface=surface,
        )
        parsed["api_status"] = "ok"
        parsed["source"] = "tennis_api_h2h"
        parsed["fallback_used"] = False
        parsed["raw_api"] = raw
        return parsed

    def _parse_api_profile(
        self,
        raw: Dict[str, Any],
        player1: str,
        player2: str,
        surface: Optional[str],
    ) -> Dict[str, Any]:
        surface_data = raw.get("surfaceData") if isinstance(raw.get("surfaceData"), dict) else {}

        total_p1, total_p2 = self._extract_api_total_wins(raw, surface_data)
        surface_p1, surface_p2 = self._extract_api_surface_wins(surface_data, surface)

        recent_p1, recent_p2, recent_winner, recent_total = self._extract_recent_from_api(raw)

        total_matches = total_p1 + total_p2
        surface_matches = surface_p1 + surface_p2

        edge = self._calculate_edge(
            p1_wins=total_p1,
            p2_wins=total_p2,
            surface_p1_wins=surface_p1,
            surface_p2_wins=surface_p2,
            recent_p1_wins=recent_p1,
            recent_p2_wins=recent_p2,
        )
        confidence = self._calculate_confidence(
            total_matches=total_matches,
            surface_matches=surface_matches,
            recent_matches=recent_total,
        )

        data = H2HQData(
            player1=player1,
            player2=player2,
            surface=surface,
            h2h_total_matches=total_matches,
            h2h_player1_wins=total_p1,
            h2h_player2_wins=total_p2,
            h2h_surface_matches=surface_matches,
            h2h_surface_player1_wins=surface_p1,
            h2h_surface_player2_wins=surface_p2,
            h2h_recent_matches=recent_total,
            h2h_recent_player1_wins=recent_p1,
            h2h_recent_player2_wins=recent_p2,
            h2h_recent_winner=recent_winner,
            h2h_edge=edge,
            h2h_confidence=confidence,
            source="tennis_api_h2h",
            api_status="ok",
        )
        return data.to_dict()

    def _extract_api_total_wins(self, raw: Dict[str, Any], surface_data: Dict[str, Any]) -> Tuple[int, int]:
        # Advanced profile usually has surfaceData.total1 / total2.
        p1 = parse_int(surface_data.get("total1"), 0)
        p2 = parse_int(surface_data.get("total2"), 0)
        if p1 or p2:
            return p1, p2

        # Other API responses may expose direct all-wins fields.
        p1 = parse_int(raw.get("player1AllWins"), 0)
        p2 = parse_int(raw.get("player2AllWins"), 0)
        if p1 or p2:
            return p1, p2

        p1 = parse_int(raw.get("player1Wins"), 0)
        p2 = parse_int(raw.get("player2Wins"), 0)
        return p1, p2

    def _extract_api_surface_wins(self, surface_data: Dict[str, Any], surface: Optional[str]) -> Tuple[int, int]:
        normalized = normalize_surface(surface)
        if not normalized or not surface_data:
            return 0, 0

        key_map = {
            "hard": ("hard1", "hard2"),
            "indoor hard": ("iHard1", "iHard2"),
            "clay": ("clay1", "clay2"),
            "grass": ("grass1", "grass2"),
            "carpet": ("carpet1", "carpet2"),
        }
        keys = key_map.get(normalized)
        if not keys:
            return 0, 0
        return parse_int(surface_data.get(keys[0]), 0), parse_int(surface_data.get(keys[1]), 0)

    def _extract_recent_from_api(self, raw: Dict[str, Any]) -> Tuple[int, int, Optional[str], int]:
        # The advanced profile exposes recentGames per player, but those are general recent games,
        # not necessarily direct H2H matches. Therefore we do not convert those into H2H edge.
        # Keep this as neutral until a full matches endpoint parser is added.
        return 0, 0, None, 0

    # ------------------------------------------------------------------
    # Sackmann fallback source
    # ------------------------------------------------------------------

    def _load_from_sackmann(
        self,
        player1: str,
        player2: str,
        surface: Optional[str],
        api_error: Optional[str] = None,
    ) -> Dict[str, Any]:
        loader = self.sackmann_loader or SackmannLoader()
        matches = loader.load_matches()

        p1_key = normalize_player_name(player1)
        p2_key = normalize_player_name(player2)
        surface_key = normalize_surface(surface)

        h2h_matches: List[Dict[str, Any]] = []
        surface_matches: List[Dict[str, Any]] = []

        for match in matches:
            m_p1 = normalize_player_name(match.get("player1"))
            m_p2 = normalize_player_name(match.get("player2"))
            players = {m_p1, m_p2}
            if players != {p1_key, p2_key}:
                continue

            h2h_matches.append(match)

            match_surface = normalize_surface(match.get("surface"))
            if surface_key and match_surface == surface_key:
                surface_matches.append(match)

        h2h_matches.sort(key=lambda item: parse_date_key(item.get("date")), reverse=True)
        surface_matches.sort(key=lambda item: parse_date_key(item.get("date")), reverse=True)

        total_p1 = self._count_wins(h2h_matches, p1_key)
        total_p2 = self._count_wins(h2h_matches, p2_key)
        surface_p1 = self._count_wins(surface_matches, p1_key)
        surface_p2 = self._count_wins(surface_matches, p2_key)

        recent_matches = h2h_matches[:3]
        recent_p1 = self._count_wins(recent_matches, p1_key)
        recent_p2 = self._count_wins(recent_matches, p2_key)
        recent_winner = None
        if recent_matches:
            winner_key = normalize_player_name(recent_matches[0].get("winner"))
            if winner_key == p1_key:
                recent_winner = "player1"
            elif winner_key == p2_key:
                recent_winner = "player2"

        edge = self._calculate_edge(
            p1_wins=total_p1,
            p2_wins=total_p2,
            surface_p1_wins=surface_p1,
            surface_p2_wins=surface_p2,
            recent_p1_wins=recent_p1,
            recent_p2_wins=recent_p2,
        )
        confidence = self._calculate_confidence(
            total_matches=len(h2h_matches),
            surface_matches=len(surface_matches),
            recent_matches=len(recent_matches),
        )

        data = H2HQData(
            player1=player1,
            player2=player2,
            surface=surface,
            h2h_total_matches=len(h2h_matches),
            h2h_player1_wins=total_p1,
            h2h_player2_wins=total_p2,
            h2h_surface_matches=len(surface_matches),
            h2h_surface_player1_wins=surface_p1,
            h2h_surface_player2_wins=surface_p2,
            h2h_recent_matches=len(recent_matches),
            h2h_recent_player1_wins=recent_p1,
            h2h_recent_player2_wins=recent_p2,
            h2h_recent_winner=recent_winner,
            h2h_edge=edge,
            h2h_confidence=confidence,
            source="sackmann_h2h_fallback",
            api_status="failed" if api_error else "not_used",
            fallback_used=True,
            error=api_error,
        )
        return data.to_dict()

    @staticmethod
    def _count_wins(matches: List[Dict[str, Any]], player_key: str) -> int:
        return sum(1 for match in matches if normalize_player_name(match.get("winner")) == player_key)

    # ------------------------------------------------------------------
    # Edge/confidence formulas
    # ------------------------------------------------------------------

    def _calculate_edge(
        self,
        p1_wins: int,
        p2_wins: int,
        surface_p1_wins: int = 0,
        surface_p2_wins: int = 0,
        recent_p1_wins: int = 0,
        recent_p2_wins: int = 0,
    ) -> float:
        """
        Conservative H2H edge from player1 perspective.

        Caps:
        - 0 matches: 0.00
        - 1 match: +/-0.02
        - 2-3 matches: +/-0.04
        - 4+ matches: +/-0.06

        Surface/recent components only influence available H2H sample.
        """
        total = p1_wins + p2_wins
        if total <= 0:
            return 0.0

        total_diff = (p1_wins - p2_wins) / total

        surface_total = surface_p1_wins + surface_p2_wins
        if surface_total > 0:
            surface_diff = (surface_p1_wins - surface_p2_wins) / surface_total
        else:
            surface_diff = 0.0

        recent_total = recent_p1_wins + recent_p2_wins
        if recent_total > 0:
            recent_diff = (recent_p1_wins - recent_p2_wins) / recent_total
        else:
            recent_diff = 0.0

        weighted = (0.60 * total_diff) + (0.25 * surface_diff) + (0.15 * recent_diff)

        if total == 1:
            cap = 0.02
        elif total <= 3:
            cap = 0.04
        else:
            cap = 0.06

        edge = max(min(weighted * cap, cap), -cap)
        return round(edge, 4)

    @staticmethod
    def _calculate_confidence(total_matches: int, surface_matches: int, recent_matches: int) -> float:
        if total_matches <= 0:
            return 0.0

        total_score = min(total_matches / 5, 1.0)
        surface_score = min(surface_matches / 3, 1.0)
        recent_score = min(recent_matches / 3, 1.0)

        confidence = (0.60 * total_score) + (0.25 * surface_score) + (0.15 * recent_score)
        return round(confidence, 4)

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _cache_key(
        self,
        player1: str,
        player2: str,
        surface: Optional[str],
        tour_type: Optional[str],
        limit: bool,
        include_all: bool,
    ) -> str:
        p1 = normalize_player_name(player1).replace(" ", "_")
        p2 = normalize_player_name(player2).replace(" ", "_")
        s = (normalize_surface(surface) or "all").replace(" ", "_")
        t = (tour_type or "auto").lower()
        l = "limited" if limit else "full"
        ia = "all" if include_all else "default"
        ordered = sorted([p1, p2])
        return f"{ordered[0]}__{ordered[1]}__{s}__{t}__{l}__{ia}.json"

    def _read_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        path = self.cache_dir / cache_key
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    def _write_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        path = self.cache_dir / cache_key
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            print("H2H CACHE WRITE ERROR:", exc)


if __name__ == "__main__":
    loader = H2HLoader(use_api=False, use_sackmann_fallback=True)
    sample = loader.load_h2h("Novak Djokovic", "Carlos Alcaraz", surface="Grass")
    print(json.dumps(sample, ensure_ascii=False, indent=2))
