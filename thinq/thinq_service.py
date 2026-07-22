"""
THINQ Intelligence Layer

THINQ is the brain/intelligence layer for CORQ.
THINQ does not create final match probability.
THINQ returns feature, edge, flag and confidence signals.
CORQ remains the CORE model for final probability, ranking and TOP7 output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .loaders.thinq_loader import ThinqLoader
except ImportError:
    from loaders.thinq_loader import ThinqLoader


class ThinqService:
    """
    Public entry point for CORQ.

    CORQ should call this service instead of calling individual data sources.
    """

    def __init__(
        self,
        loader: Optional[ThinqLoader] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        self.loader = loader or ThinqLoader()
        self.output_dir = Path(output_dir) if output_dir else Path("thinq/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_player_data(
        self,
        player_name: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.loader.load_player(
            player_name=player_name,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
            as_of_date=as_of_date,
        )

    def build_match_features(
        self,
        player1: str,
        player2: str,
        surface: Optional[str] = None,
        level: Optional[str] = None,
        tournament_url: Optional[str] = None,
        tour_type: Optional[str] = None,
        as_of_date: Optional[str] = None,
        save_snapshot: bool = False,
    ) -> Dict[str, Any]:
        """
        Build THINQ intelligence output for one match.

        Edge direction:
        - positive edge favors player1
        - negative edge favors player2

        CORQ can then decide how much weight each THINQ edge receives.
        """
        raw = self.loader.load_match(
            player1=player1,
            player2=player2,
            surface=surface,
            level=level,
            tournament_url=tournament_url,
            tour_type=tour_type,
            as_of_date=as_of_date,
        )

        edges = self._calculate_edges(raw)
        confidence = self._calculate_total_confidence(raw, edges)
        flags = self._build_flags(raw, edges, confidence)

        output = {
            "player1": player1,
            "player2": player2,
            "surface": surface,
            "level": level,
            "thinq_role": "intelligence_layer",
            "edges": edges,
            "confidence": confidence,
            "flags": flags,
            "raw": raw,
        }

        if save_snapshot:
            self.save_match_snapshot(output)

        return output

    def save_match_snapshot(self, output: Dict[str, Any]) -> Path:
        player1 = self._safe_name(output.get("player1"))
        player2 = self._safe_name(output.get("player2"))
        surface = self._safe_name(output.get("surface") or "all")
        path = self.output_dir / f"thinq_{player1}_vs_{player2}_{surface}.json"
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Edge calculation
    # ------------------------------------------------------------------

    def _calculate_edges(self, raw: Dict[str, Any]) -> Dict[str, Optional[float]]:
        p1 = raw.get("player1", {})
        p2 = raw.get("player2", {})
        p1_history = p1.get("historyq", {}) if isinstance(p1, dict) else {}
        p2_history = p2.get("historyq", {}) if isinstance(p2, dict) else {}
        p1_elo = p1.get("eloq", {}) if isinstance(p1, dict) else {}
        p2_elo = p2.get("eloq", {}) if isinstance(p2, dict) else {}
        p1_ta = p1.get("taq", {}) if isinstance(p1, dict) else {}
        p2_ta = p2.get("taq", {}) if isinstance(p2, dict) else {}
        h2hq = raw.get("h2hq", {}) if isinstance(raw.get("h2hq"), dict) else {}

        return {
            "surface_form_edge": self._edge_from_percent_diff(
                p1_history.get("surface_win_pct_52w"),
                p2_history.get("surface_win_pct_52w"),
                cap=0.12,
            ),
            "recent_form_edge": self._edge_from_percent_diff(
                p1_history.get("last10_win_pct"),
                p2_history.get("last10_win_pct"),
                cap=0.10,
            ),
            "level_form_edge": self._edge_from_percent_diff(
                p1_history.get("level_win_pct"),
                p2_history.get("level_win_pct"),
                cap=0.08,
            ),
            "elo_edge": self._edge_from_elo(p1_elo, p2_elo, raw.get("surface")),
            "opponent_quality_edge": None,
            "ta_forecast_edge": self._edge_from_ta(p1_ta, p2_ta),
            "h2h_edge": self._to_float_or_none(h2hq.get("h2h_edge")),
        }

    @staticmethod
    def _edge_from_percent_diff(
        p1_value: Any,
        p2_value: Any,
        cap: float,
    ) -> Optional[float]:
        p1_float = ThinqService._to_float_or_none(p1_value)
        p2_float = ThinqService._to_float_or_none(p2_value)
        if p1_float is None or p2_float is None:
            return None
        raw = p1_float - p2_float
        raw = max(min(raw, cap), -cap)
        return round(raw, 4)

    @staticmethod
    def _edge_from_elo(
        p1_elo: Dict[str, Any],
        p2_elo: Dict[str, Any],
        surface: Optional[str],
    ) -> Optional[float]:
        surface_key = ThinqService._surface_elo_key(surface)
        p1_value = None
        p2_value = None

        if surface_key:
            p1_value = ThinqService._to_float_or_none(p1_elo.get(surface_key))
            p2_value = ThinqService._to_float_or_none(p2_elo.get(surface_key))

        if p1_value is None or p2_value is None:
            p1_value = ThinqService._to_float_or_none(p1_elo.get("elo"))
            p2_value = ThinqService._to_float_or_none(p2_elo.get("elo"))

        if p1_value is None or p2_value is None:
            return None

        diff = p1_value - p2_value
        # Conservative edge cap: 200 ELO diff roughly maps to max +/-0.10 feature edge.
        edge = max(min(diff / 2000, 0.10), -0.10)
        return round(edge, 4)

    @staticmethod
    def _edge_from_ta(p1_ta: Dict[str, Any], p2_ta: Dict[str, Any]) -> Optional[float]:
        p1_forecast = ThinqService._to_float_or_none(p1_ta.get("ta_forecast"))
        p2_forecast = ThinqService._to_float_or_none(p2_ta.get("ta_forecast"))
        if p1_forecast is None or p2_forecast is None:
            return None

        # If TA forecast is stored as 0-100, normalize to 0-1.
        if p1_forecast > 1:
            p1_forecast = p1_forecast / 100
        if p2_forecast > 1:
            p2_forecast = p2_forecast / 100

        raw = p1_forecast - p2_forecast
        raw = max(min(raw, 0.08), -0.08)
        return round(raw, 4)

    # ------------------------------------------------------------------
    # Confidence and flags
    # ------------------------------------------------------------------

    def _calculate_total_confidence(
        self,
        raw: Dict[str, Any],
        edges: Dict[str, Optional[float]],
    ) -> float:
        p1 = raw.get("player1", {})
        p2 = raw.get("player2", {})
        p1_history = p1.get("historyq", {}) if isinstance(p1, dict) else {}
        p2_history = p2.get("historyq", {}) if isinstance(p2, dict) else {}
        h2hq = raw.get("h2hq", {}) if isinstance(raw.get("h2hq"), dict) else {}

        history_conf = self._avg_present([
            p1_history.get("data_confidence"),
            p2_history.get("data_confidence"),
        ])
        h2h_conf = self._to_float_or_none(h2hq.get("h2h_confidence"))
        edge_coverage = self._edge_coverage(edges)

        parts = []
        weights = []

        if history_conf is not None:
            parts.append(history_conf)
            weights.append(0.45)

        if h2h_conf is not None:
            parts.append(h2h_conf)
            weights.append(0.15)

        parts.append(edge_coverage)
        weights.append(0.40)

        if not parts:
            return 0.0

        total_weight = sum(weights)
        confidence = sum(value * weight for value, weight in zip(parts, weights)) / total_weight
        return round(max(min(confidence, 1.0), 0.0), 4)

    @staticmethod
    def _build_flags(
        raw: Dict[str, Any],
        edges: Dict[str, Optional[float]],
        confidence: float,
    ) -> List[str]:
        flags: List[str] = []

        h2h_edge = edges.get("h2h_edge")
        if h2h_edge is not None:
            if h2h_edge >= 0.04:
                flags.append("H2H_STRONG_PLAYER1")
            elif h2h_edge <= -0.04:
                flags.append("H2H_STRONG_PLAYER2")

        surface_edge = edges.get("surface_form_edge")
        if surface_edge is not None:
            if surface_edge >= 0.08:
                flags.append("SURFACE_FORM_STRONG_PLAYER1")
            elif surface_edge <= -0.08:
                flags.append("SURFACE_FORM_STRONG_PLAYER2")

        recent_edge = edges.get("recent_form_edge")
        if recent_edge is not None:
            if recent_edge >= 0.07:
                flags.append("RECENT_FORM_STRONG_PLAYER1")
            elif recent_edge <= -0.07:
                flags.append("RECENT_FORM_STRONG_PLAYER2")

        if confidence < 0.35:
            flags.append("THINQ_LOW_DATA_CONFIDENCE")

        available_edges = [value for value in edges.values() if value is not None]
        if len(available_edges) <= 2:
            flags.append("THINQ_THIN_FEATURE_COVERAGE")

        return flags

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_float_or_none(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _avg_present(values: List[Any]) -> Optional[float]:
        parsed = [ThinqService._to_float_or_none(value) for value in values]
        parsed = [value for value in parsed if value is not None]
        if not parsed:
            return None
        return sum(parsed) / len(parsed)

    @staticmethod
    def _edge_coverage(edges: Dict[str, Optional[float]]) -> float:
        if not edges:
            return 0.0
        available = sum(1 for value in edges.values() if value is not None)
        return round(available / len(edges), 4)

    @staticmethod
    def _surface_elo_key(surface: Optional[str]) -> Optional[str]:
        if not surface:
            return None
        value = str(surface).strip().lower()
        mapping = {
            "hard": "hard_elo",
            "clay": "clay_elo",
            "grass": "grass_elo",
            "indoor": "indoor_elo",
            "indoor hard": "indoor_elo",
            "i.hard": "indoor_elo",
        }
        return mapping.get(value)

    @staticmethod
    def _safe_name(value: Any) -> str:
        text = str(value or "unknown").strip().lower()
        keep = []
        for char in text:
            if char.isalnum():
                keep.append(char)
            elif char in [" ", "-", "_"]:
                keep.append("_")
        text = "".join(keep)
        while "__" in text:
            text = text.replace("__", "_")
        return text.strip("_") or "unknown"
