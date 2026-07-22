# THINQ Full Integration Update

This update puts the current THINQ architecture together before connecting THINQ into CORQ.

## Project target architecture

```text
CORQ = CORE output model
THINQ = intelligence layer / brain
CLOQ = close-odds specialist
```

## THINQ layers included in the integrated flow

```text
History
ELO
TA
H2H
Player Resolver
Data Quality
Schedule / Fatigue
Surface Transition
Level Context
Status Risk
Match Dynamics
Snapshot Builder
```

## Files in this update

```text
thinq/loaders/thinq_loader.py
thinq/features/__init__.py
thinq/thinq_service.py
thinq/build_thinq_snapshot.py
thinq/scripts/smoke_test_thinq.py
thinq/README_FULL_INTEGRATION.md
```

## Why this update exists

Previous updates added separate layers. This update ensures:

- `ThinqLoader` passes `tour_type` into ELO lookup.
- `ThinqService` includes all current contexts and edges.
- `build_thinq_snapshot.py` supports `best_of` for Match Dynamics.
- Smoke test is available before CORQ integration.

## Quick tests

```bash
python -m py_compile thinq/loaders/thinq_loader.py
python -m py_compile thinq/thinq_service.py
python -m py_compile thinq/build_thinq_snapshot.py
python -m py_compile thinq/features/match_dynamics.py
python thinq/scripts/smoke_test_thinq.py
```

## Snapshot input example

```json
[
  {
    "player1": "Jannik Sinner",
    "player2": "Carlos Alcaraz",
    "surface": "Grass",
    "tour_type": "atp",
    "best_of": 5
  }
]
```

Build snapshot:

```bash
python -m thinq.build_thinq_snapshot --input daily_matches.json --output thinq/outputs/thinq_snapshot.json
```

CORQ should later read `thinq/outputs/thinq_snapshot.json` or call `ThinqService.build_match_features()` directly.
