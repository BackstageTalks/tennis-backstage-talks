"""
THINQ Offline Smoke Test

Purpose:
- Test THINQ service, edges, confidence and Match Dynamics without heavy network calls.
- Avoid automatic Sackmann/TML loading during GitHub Actions smoke tests.
- This is a structural test, not a data freshness test.

Run from repository root:
    python thinq/scripts/smoke_test_thinq.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinq.thinq_service import ThinqService


class OfflineThinqLoader:
    """
    Minimal loader used only for smoke testing.

    It intentionally avoids Sackmann, H2H API, Tennis Abstract fetches and any remote source.
    """

    def load_player(
        self,
        player_name: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
        as_of_date: Optional[str] = None,
        tour_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        profiles = {
            "jannik sinner": {
                "elo": 2331.9,
                "hard_elo": 2269.3,
                "clay_elo": 2221.8,
                "grass_elo": 2135.5,
                "season_yelo": 2323.0,
            },
            "carlos alcaraz": {
                "elo": 2156.8,
                "hard_elo": 2083.3,
                "clay_elo": 2096.6,
                "grass_elo": 2024.2,
                "season_yelo": 2132.7,
            },
            "iga swiatek": {
                "elo": 1960.8,
                "hard_elo": 1905.0,
                "clay_elo": 2050.0,
                "grass_elo": 1810.0,
                "season_yelo": 1960.8,
            },
            "aryna sabalenka": {
                "elo": 2123.0,
                "hard_elo": 2110.0,
                "clay_elo": 2020.0,
                "grass_elo": 1900.0,
                "season_yelo": 2123.0,
            },
        }
        key = player_name.strip().lower()
        elo = profiles.get(key, {"elo": None, "hard_elo": None, "clay_elo": None, "grass_elo": None, "season_yelo": None})

        # Small but realistic synthetic History block for structural test only.
        if key in ["jannik sinner", "iga swiatek"]:
            history = {
                "player": player_name,
                "last10_win_pct": 0.80,
                "surface_win_pct_52w": 0.78,
                "level_win_pct": 0.74,
                "sample_size_matches": 35,
                "surface_sample_size_52w": 14,
                "data_confidence": 0.86,
            }
        else:
            history = {
                "player": player_name,
                "last10_win_pct": 0.70,
                "surface_win_pct_52w": 0.70,
                "level_win_pct": 0.68,
                "sample_size_matches": 32,
                "surface_sample_size_52w": 12,
                "data_confidence": 0.82,
            }

        return {
            "player": player_name,
            "input_player": player_name,
            "identity": {
                "input_name": player_name,
                "canonical_name": player_name,
                "normalized_name": key,
                "tour": tour_type,
            },
            "surface": surface,
            "level": level,
            "history": history,
            "elo": {
                "player": player_name,
                "tour": tour_type,
                "elo": elo.get("elo"),
                "hard_elo": elo.get("hard_elo"),
                "clay_elo": elo.get("clay_elo"),
                "grass_elo": elo.get("grass_elo"),
                "season_yelo": elo.get("season_yelo"),
                "missing": elo.get("elo") is None,
                "flags": [] if elo.get("elo") is not None else ["MISSING_ELO"],
            },
            "ta": {
                "player": player_name,
                "ta_forecast": None,
            },
        }

    def load_match(
        self,
        player1: str,
        player2: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
        tour_type: Optional[str] = None,
        as_of_date: Optional[str] = None,
        event_id: Optional[Any] = None,
        player1_id: Optional[Any] = None,
        player2_id: Optional[Any] = None,
        tournament_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return {
            "player1": self.load_player(player1, surface, level, tournament_url, as_of_date, tour_type),
            "player2": self.load_player(player2, surface, level, tournament_url, as_of_date, tour_type),
            "surface": surface,
            "level": level,
            "h2h": {
                "player1": player1,
                "player2": player2,
                "surface": surface,
                "h2h_total_matches": 5,
                "h2h_player1_wins": 3,
                "h2h_player2_wins": 2,
                "h2h_surface_matches": 2,
                "h2h_surface_player1_wins": 1,
                "h2h_surface_player2_wins": 1,
                "h2h_edge": 0.012,
                "h2h_confidence": 0.75,
                "source": "offline_smoke_test",
                "fallback_used": False,
                "flags": [],
            },
        }


def build_case(service: ThinqService, player1: str, player2: str, surface: str, tour_type: str, best_of: int) -> Dict[str, Any]:
    result = service.build_match_features(
        player1=player1,
        player2=player2,
        surface=surface,
        tour_type=tour_type,
        best_of=best_of,
    )

    assert "edges" in result, "Missing edges block"
    assert "contexts" in result, "Missing contexts block"
    assert "match_dynamics" in result["contexts"], "Missing match_dynamics context"
    assert "elo_edge" in result["edges"], "Missing elo_edge"
    assert "sets_edge" in result["edges"], "Missing sets_edge"
    assert "games_edge" in result["edges"], "Missing games_edge"
    assert "tiebreak_edge" in result["edges"], "Missing tiebreak_edge"
    assert "decider_edge" in result["edges"], "Missing decider_edge"
    assert result["contexts"]["match_dynamics"].get("projected_games") is not None, "Missing projected_games"
    assert result["confidence"] is not None, "Missing confidence"

    return result


def main() -> None:
    service = ThinqService(loader=OfflineThinqLoader())

    matches = [
        build_case(service, "Jannik Sinner", "Carlos Alcaraz", "Grass", "atp", 5),
        build_case(service, "Iga Swiatek", "Aryna Sabalenka", "Clay", "wta", 3),
    ]

    snapshot = {
        "generated_by": "thinq/scripts/smoke_test_thinq.py",
        "mode": "offline_structural_smoke_test",
        "count": len(matches),
        "matches": matches,
    }

    output_path = ROOT / "thinq" / "outputs" / "thinq_smoke_snapshot.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "mode": "offline_structural_smoke_test",
        "count": len(matches),
        "output": str(output_path),
        "first_edges": matches[0].get("edges"),
        "first_match_dynamics": matches[0].get("contexts", {}).get("match_dynamics"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
