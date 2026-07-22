"""
CCV ELO Loader

Purpose:
- Load overall ELO.
- Load surface ELO.
- Load ELO trend signals.
- Provide ELOQ data for THINQ.

THINQ uses ELO as feature/edge input for CORQ.
THINQ does not produce standalone match probability.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class EloQPlayerData:
    player: str

    elo: Optional[float] = None
    hard_elo: Optional[float] = None
    clay_elo: Optional[float] = None
    grass_elo: Optional[float] = None
    indoor_elo: Optional[float] = None

    elo_trend_30d: Optional[float] = None
    elo_trend_90d: Optional[float] = None
    elo_trend_365d: Optional[float] = None

    sample_size_matches: Optional[int] = None
    source: str = "ccv_elo"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EloLoader:
    """
    Loader for CCV ELO data.

    Current version returns a stable schema with None values.
    Next step: point this loader to the actual CCV ELO file or function.
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir

    def load_player(self, player_name: str) -> Dict[str, Any]:
        data = EloQPlayerData(player=player_name)
        return data.to_dict()

    @staticmethod
    def surface_key(surface: Optional[str]) -> Optional[str]:
        if not surface:
            return None
        normalized = surface.strip().lower()
        mapping = {
            "hard": "hard_elo",
            "clay": "clay_elo",
            "grass": "grass_elo",
            "indoor": "indoor_elo",
            "indoor hard": "indoor_elo",
        }
        return mapping.get(normalized)
