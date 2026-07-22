# THINQ Intelligence Layers Update

This update adds the practical THINQ layers discussed for the tennis project.

## Architecture

```text
CORQ = CORE output model
THINQ = intelligence layer / brain
CLOQ = close-odds specialist

THINQ contains:
- History
- ELO
- TA
- H2H
- Player Resolver
- Data Quality
- Schedule / Fatigue
- Surface Transition
- Status Risk
- Level Context
- Snapshot Builder
```

## Files included

```text
thinq/loaders/player_resolver.py
thinq/loaders/thinq_loader.py
thinq/loaders/__init__.py
thinq/features/__init__.py
thinq/features/data_quality.py
thinq/features/schedule_fatigue.py
thinq/features/surface_transition.py
thinq/features/level_context.py
thinq/features/status_risk.py
thinq/thinq_service.py
thinq/build_thinq_snapshot.py
thinq/data/players/.gitkeep
thinq/data/snapshots/.gitkeep
thinq/outputs/.gitkeep
```

## Output edges

THINQ now returns additional edges:

```json
{
  "surface_form_edge": 0.0,
  "recent_form_edge": 0.0,
  "level_form_edge": 0.0,
  "elo_edge": 0.0,
  "opponent_quality_edge": null,
  "ta_edge": null,
  "h2h_edge": 0.0,
  "fatigue_edge": 0.0,
  "surface_transition_edge": 0.0,
  "level_context_edge": 0.0,
  "status_risk_edge": 0.0
}
```

Positive edge favors player1. Negative edge favors player2.

THINQ still does not create final prediction probability. CORQ remains the CORE output model.
