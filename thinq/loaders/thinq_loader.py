"""
THINQ Data Aggregator

Single aggregation point for THINQ source data.
CORQ should consume normalized THINQ output and should not call data sources directly.

Project architecture:
- CORQ = CORE output model
- THINQ = intelligence layer / brain
- CLOQ = close-odds specialist

THINQ layers:
- History
- ELO
- TA
- H2H
- Player Resolver
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from .sackmann_loader import SackmannLoader
    from .elo_loader import EloLoader
    from .ta_loader import TALoader
    from .h2h_loader import H2HLoader
    from .player_resolver import PlayerResolver
except ImportError:
    from sackmann_loader import SackmannLoader
    from elo_loader import EloLoader
    from ta_loader import TALoader
    from h2h_loader import H2HLoader
    from player_resolver import PlayerResolver


class ThinqLoader:
    """
    Aggregates all THINQ source layers.

    Important:
    - This class gathers normalized data.
    - Feature edge formulas belong in ThinqService or feature modules.
    - Final probability belongs to CORQ.
    """

    def __init__(
        self,
        sackmann_loader: Optional[SackmannLoader] = None,
        elo_loader: Optional[EloLoader] = None,
        ta_loader: Optional[TALoader] = None,
        h2h_loader: Optional[H2HLoader] = None,
        player_resolver: Optional[PlayerResolver] = None,
    ) -> None:
        self.resolver = player_resolver or PlayerResolver()
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
        tour_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        identity = self.resolver.resolve(player_name, tour=tour_type)
        canonical_name = identity.get("canonical_name") or player_name

        history = self.sackmann.load_player(
            player_name=canonical_name,
            surface=surface,
            level=level,
            as_of_date=as_of_date,
        )
        # ELO loader supports tour-aware lookup. This prevents ATP/WTA name collisions.
        elo = self.elo.load_player(player_name=canonical_name, tour=tour_type)
        ta = self.ta.load_player(
            player_name=canonical_name,
            tournament_url=tournament_url,
        )

        return {
            "player": canonical_name,
            "input_player": player_name,
            "identity": identity,
            "surface": surface,
            "level": level,
            "history": history,
            "elo": elo,
            "ta": ta,
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
        event_id: Optional[Any] = None,
        player1_id: Optional[Any] = None,
        player2_id: Optional[Any] = None,
        tournament_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        player1_data = self.load_player(
            player_name=player1,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
            as_of_date=as_of_date,
            tour_type=tour_type,
        )
        player2_data = self.load_player(
            player_name=player2,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
            as_of_date=as_of_date,
            tour_type=tour_type,
        )

        p1_id = player1_id or player1_data.get("identity", {}).get("rapidapi_id")
        p2_id = player2_id or player2_data.get("identity", {}).get("rapidapi_id")

        h2h = self.h2h.load_h2h(
            player1=player1_data.get("player") or player1,
            player2=player2_data.get("player") or player2,
            surface=surface,
            tour_type=tour_type,
            event_id=event_id,
            player1_id=p1_id,
            player2_id=p2_id,
            tournament_id=tournament_id,
        )

        return {
            "player1": player1_data,
            "player2": player2_data,
            "surface": surface,
            "level": level,
            "h2h": h2h,
        }
