# THINQ

THINQ is the intelligence layer for the tennis project.

## Role

- CORQ is the CORE model and produces final outputs.
- THINQ is the data and logic brain.
- THINQ prepares feature and edge data for CORQ.
- THINQ does not act as a standalone prediction model.

## Main input layers

- HistoryQ / Sackmann historical data
- CCV ELO
- Tennis Abstract data
- H2H later
- Surface and level trends

## Main output for CORQ

Typical THINQ output should look like this:

```json
{
  "surface_form_edge": 0.08,
  "recent_form_edge": 0.05,
  "elo_edge": 0.09,
  "opponent_quality_edge": 0.02,
  "ta_forecast_edge": 0.04,
  "confidence": 0.84
}
```

## Folder structure

```text
thinq/
├── data/
│   ├── historyq/
│   ├── elo/
│   ├── tennisabstract/
│   ├── cache/
│   └── snapshots/
├── loaders/
├── features/
├── outputs/
└── thinq_service.py
```
