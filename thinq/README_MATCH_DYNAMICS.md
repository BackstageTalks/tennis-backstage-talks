# THINQ Match Dynamics Update

Adds Match Dynamics as a THINQ intelligence layer.

## Purpose

Match Dynamics provides context for:

- projected sets
- straight-sets probability
- decider probability
- projected games
- tiebreak probability
- sets edge
- games edge
- tiebreak edge
- decider edge

This is not a standalone model. CORQ remains the CORE output model.

## Files to copy

```text
thinq/features/match_dynamics.py
thinq/features/__init__.py
thinq/thinq_service.py
```

## New context output

```json
{
  "contexts": {
    "match_dynamics": {
      "projected_sets": 2.39,
      "straight_sets_probability": 0.61,
      "decider_probability": 0.39,
      "projected_games": 22.6,
      "tiebreak_probability": 0.33,
      "confidence": 0.71
    }
  }
}
```

## New edges

```json
{
  "sets_edge": 0.01,
  "games_edge": 0.02,
  "tiebreak_edge": 0.01,
  "decider_edge": 0.01
}
```

Positive values are context support for player1 or longer/volatile match context depending on how CORQ consumes them. Negative values indicate the opposite.
