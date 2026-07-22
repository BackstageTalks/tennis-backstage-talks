"""
THINQ Loaders Package

Loaders are responsible only for collecting and normalizing source data.
They should not calculate final predictions.
"""

from .sackmann_loader import SackmannLoader
from .elo_loader import EloLoader
from .ta_loader import TALoader
from .thinq_loader import ThinqLoader

__all__ = [
    "SackmannLoader",
    "EloLoader",
    "TALoader",
    "ThinqLoader",
]
