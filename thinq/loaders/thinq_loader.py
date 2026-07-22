"""
THINQ Data Aggregator

This is the single aggregation point for THINQ source data.
CORQ should not call Sackmann, CCV ELO or Tennis Abstract directly.
CORQ should consume normalized THINQ output.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from .sackmann_loader import SackmannLoader
    from .elo_loader import EloLoader
    from .ta_loader import TALoader
except ImportError:
    # Allows direct script execution during local testing.
    from sackmann_loader import SackmannLoader
    from elo_loader import EloLoader
    from ta_loader import TALoader


class ThinqLoader:
    """
    Aggregates HistoryQ, ELOQ and TAQ data for one player.
    """

    def __init__(
        self,
        sackmann_loader: Optional[SackmannLoader] = None,
        elo_loader: Optional[EloLoader] = None,
        ta_loader: Optional[TALoader] = None,
    ) -> None:
        self.sackmann = sackmann_loader or SackmannLoader()
        self.elo = elo_loader or EloLoader()
        self.ta = ta_loader or TALoader()

    def load_player(
        self,
        player_name: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        historyq = self.sackmann.load_player(
            player_name=player_name,
            surface=surface,
            level=level,
        )
        eloq = self.elo.load_player(player_name=player_name)
        taq = self.ta.load_player(
            player_name=player_name,
            tournament_url=tournament_url,
        )

        return {
            "player": player_name,
            "surface": surface,
            "level": level,
            "historyq": historyq,
            "eloq": eloq,
            "taq": taq,
        }

    def load_match(
        self,
        player1: str,
        player2: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "player1": self.load_player(player1, surface, level, tournament_url),
            "player2": self.load_player(player2, surface, level, tournament_url),
            "surface": surface,
            "level": level,
        }
