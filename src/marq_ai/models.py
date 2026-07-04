from dataclasses import dataclass


@dataclass
class MovementPoint:
    odds: float
    timestamp: int


@dataclass
class MarqInput:
    opening_odds: float
    current_odds: float
    movement_history: list[MovementPoint]


@dataclass
class MarqOutput:
    score: float
    direction: str
    strength: float
    consistency: float
    signal: str
