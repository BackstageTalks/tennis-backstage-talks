from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone
import json

PUBLIC_DIR = Path("public")

def write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def publish_outputs(all_predictions: List[Dict[str, Any]], ranked: List[Dict[str, Any]], top7: List[Dict[str, Any]]) -> None:
    PUBLIC_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    write_json(PUBLIC_DIR / "all_predictions_latest.json", all_predictions)
    write_json(PUBLIC_DIR / f"all_predictions_{stamp}.json", all_predictions)
    write_json(PUBLIC_DIR / "corq_predictions_latest.json", ranked)
    write_json(PUBLIC_DIR / "top7_predictions_latest.json", top7)
    write_json(PUBLIC_DIR / "runtime_meta.json", {"generated_at": datetime.now(timezone.utc).isoformat(), "runtime": "clean_corq"})
