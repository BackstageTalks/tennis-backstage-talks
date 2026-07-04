from dataclasses import dataclass


@dataclass
class MarqInput:
    opening_odds: float
    current_odds: float


@dataclass
class MarqOutput:
    probability: float
    move_pct: float
    signal: str
