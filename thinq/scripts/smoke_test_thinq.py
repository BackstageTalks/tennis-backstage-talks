"""
THINQ Smoke Test

Run from repository root:
    python thinq/scripts/smoke_test_thinq.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinq.thinq_service import ThinqService


def main() -> None:
    service = ThinqService()
    result = service.build_match_features(
        player1="Jannik Sinner",
        player2="Carlos Alcaraz",
        surface="Grass",
        tour_type="atp",
        best_of=5,
    )
    print(json.dumps({
        "edges": result.get("edges"),
        "confidence": result.get("confidence"),
        "flags": result.get("flags"),
        "match_dynamics": result.get("contexts", {}).get("match_dynamics"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
