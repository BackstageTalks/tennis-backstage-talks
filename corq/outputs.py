from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone
import json

PUBLIC = Path("public")


def stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": stamp(), "data": data} if isinstance(data, list) else data
    path.write_text(json.dumps(payload if not isinstance(data, list) else data, ensure_ascii=False, indent=2), encoding="utf-8")


def publish_outputs(all_predictions: List[Dict[str, Any]], ranked: List[Dict[str, Any]], top7: List[Dict[str, Any]]) -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    write_json(PUBLIC / "all_predictions_latest.json", all_predictions)
    write_json(PUBLIC / "corq_predictions_latest.json", ranked)
    write_json(PUBLIC / "top7_predictions_latest.json", top7)
