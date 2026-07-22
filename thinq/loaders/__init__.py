"""
THINQ Loaders Package

Loaders collect and normalize source data for THINQ.
They must not calculate final CORQ predictions.
"""

from .sackmann_loader import SackmannLoader
from .elo_loader import EloLoader
from .ta_loader import TALoader
from .h2h_loader import H2HLoader
from .player_resolver import PlayerResolver
from .thinq_loader import ThinqLoader

__all__ = [
    "SackmannLoader",
    "EloLoader",
    "TALoader",
    "H2HLoader",
    "PlayerResolver",
    "ThinqLoader",
]
