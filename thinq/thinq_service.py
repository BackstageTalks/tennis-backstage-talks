"""
THINQ Intelligence Layer

THINQ is the brain/intelligence layer for CORQ.
THINQ does not create final predictions.
THINQ returns features, edges, flags and confidence signals.
CORQ remains the CORE model for final probability, ranking and TOP7 output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from .loaders.thinq_loader import ThinqLoader
except ImportError:
    from loaders.thinq_loader import ThinqLoader


class ThinqService:
    """
    Public entry point for CORQ.

    CORQ should call this service instead of calling individual data sources.
    """

    def __init__(self, loader: Optional[ThinqLoader] = None) -> None:
        self.loader = loader or ThinqLoader()

    def get_player_data(
        self,
        player_name: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.loader.load_player(
            player_name=player_name,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
        )

    def build_match_features(
        self,
        player1: str,
        player2: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw = self.loader.load_match(
            player1=player1,
            player2=player2,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
        )

        edges = self._calculate_placeholder_edges(raw)
        flags = self._build_placeholder_flags(edges)

        return {
            "player1": player1,
            "player2": player2,
            "surface": surface,
            "level": level,
            "raw": raw,
            "edges": edges,
            "flags": flags,
            "confidence": edges.get("confidence"),
            "thinq_role": "intelligence_layer",
        }

    def _calculate_placeholder_edges(self, raw: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """
        Placeholder edge schema.

        Real edge formulas will be added after connecting:
        - Sackmann/HistoryQ
        - CCV ELO
        - Tennis Abstract
        """
        return {
            "surface_form_edge": None,
            "recent_form_edge": None,
            "elo_edge": None,
            "opponent_quality_edge": None,
            "ta_forecast_edge": None,
            "confidence": None,
        }

    def _build_placeholder_flags(self, edges: Dict[str, Optional[float]]) -> List[str]:
        return []
