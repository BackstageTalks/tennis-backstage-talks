# THINQ H2HQ update

This update adds the H2HQ layer to THINQ.

## Files to copy

```text
thinq/loaders/__init__.py
thinq/loaders/thinq_loader.py
thinq/thinq_service.py
thinq/data/h2h/.gitkeep
```

Also keep the previously generated file:

```text
thinq/loaders/h2h_loader.py
```

## Output edge added

```json
{
  "h2h_edge": 0.03
}
```

`h2h_edge` is from player1 perspective:

- positive means H2H favors player1
- negative means H2H favors player2

THINQ still does not create final predictions. CORQ remains the CORE output model.
