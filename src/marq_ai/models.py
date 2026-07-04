from dataclasses import dataclass
from typing import List


@dataclass
class MovementPoint:
    odds: float
    timestamp: int


@dataclass
class MarqInput:
    opening_odds: float
    current_odds: float
    movement_history: List[MovementPoint]


@dataclass
class MarqOutput:
    score: float
    direction: float
    strength: float
    consistency: float
    signal: str
