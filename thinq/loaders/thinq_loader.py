"""
THINQ Data Aggregator

This is the single aggregation point for THINQ source data.
CORQ should not call Sackmann, CCV ELO, Tennis Abstract or H2H directly.
CORQ should consume normalized THINQ output.

Layers:
- HistoryQ: historical form from Sackmann
- ELOQ: CCV ELO layer
- TAQ: Tennis Abstract reference layer
- H2HQ: head-to-head context layer
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from .sackmann_loader import SackmannLoader
    from .elo_loader import EloLoader
    from .ta_loader import TALoader
    from .h2h_loader import H2HLoader
except ImportError:
    # Allows direct script execution during local testing.
    from sackmann_loader import SackmannLoader
    from elo_loader import EloLoader
    from ta_loader import TALoader
    from h2h_loader import H2HLoader


class ThinqLoader:
    """
    Aggregates all THINQ source layers.

    Important:
    - This class only gathers normalized data.
    - Feature edge formulas belong in ThinqService or dedicated feature modules.
    - Final probability still belongs to CORQ.
    """

    def __init__(
        self,
        sackmann_loader: Optional[SackmannLoader] = None,
        elo_loader: Optional[EloLoader] = None,
        ta_loader: Optional[TALoader] = None,
        h2h_loader: Optional[H2HLoader] = None,
    ) -> None:
        self.sackmann = sackmann_loader or SackmannLoader()
        self.elo = elo_loader or EloLoader()
        self.ta = ta_loader or TALoader()
        self.h2h = h2h_loader or H2HLoader()

    def load_player(
        self,
        player_name: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        historyq = self.sackmann.load_player(
            player_name=player_name,
            surface=surface,
            level=level,
            as_of_date=as_of_date,
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
        tour_type: Optional[str] = None,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        player1_data = self.load_player(
            player_name=player1,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
            as_of_date=as_of_date,
        )
        player2_data = self.load_player(
            player_name=player2,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
            as_of_date=as_of_date,
        )
        h2hq = self.h2h.load_h2h(
            player1=player1,
            player2=player2,
            surface=surface,
            tour_type=tour_type,
        )

        return {
            "player1": player1_data,
            "player2": player2_data,
            "surface": surface,
            "level": level,
            "h2hq": h2hq,
        }
