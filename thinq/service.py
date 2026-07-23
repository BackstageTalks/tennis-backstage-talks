"""THINQ service: intelligence layer for CORQ."""
from __future__ import annotations
from typing import Any, Dict

try:
    from thinq.loaders.surface_loader import SurfaceResolver
except Exception:
    SurfaceResolver = None
try:
    from thinq.loaders.h2h_loader import H2HLoader, empty_h2h
except Exception:
    H2HLoader = None
    def empty_h2h(reason="H2H loader unavailable", status="NO_DATA"):
        return {"status": status, "source": "none", "edge": 0.0, "confidence": 0.0, "reason": reason, "flags": [status]}
try:
    from thinq.loaders.elo_loader import EloLoader
except Exception:
    EloLoader = None


def as_float(value, default=None):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class ThinqService:
    def __init__(self):
        self.surface_resolver = SurfaceResolver() if SurfaceResolver else None
        self.h2h_loader = H2HLoader() if H2HLoader else None
        self.elo_loader = EloLoader() if EloLoader else None

    def _load_elo(self, player: str, tour: str | None = None) -> Dict[str, Any]:
        if not self.elo_loader:
            return {"missing": True, "flags": ["ELO_LOADER_UNAVAILABLE"]}
        for call in [
            lambda: self.elo_loader.load_player(player, tour=tour),
            lambda: self.elo_loader.load_player(player, tour),
            lambda: self.elo_loader.load_player(player),
        ]:
            try:
                value = call()
                if isinstance(value, dict):
                    return value
            except Exception:
                continue
        return {"missing": True, "flags": ["ELO_LOOKUP_FAILED"]}

    def _select_elo(self, elo: Dict[str, Any], elo_type: str) -> float | None:
        keys = {
            "hard_elo": ["hard_elo", "h_elo", "hElo"],
            "clay_elo": ["clay_elo", "c_elo", "cElo"],
            "grass_elo": ["grass_elo", "g_elo", "gElo"],
            "overall_elo": ["elo", "overall_elo", "ta_elo"],
        }.get(elo_type, ["elo", "overall_elo", "ta_elo"])
        for key in keys + ["elo", "overall_elo", "ta_elo"]:
            val = as_float(elo.get(key))
            if val is not None:
                return val
        return None

    def analyse_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        flags = []
        surface = self.surface_resolver.resolve(match) if self.surface_resolver else {"surface": match.get("surface") or "Unknown", "surface_model_bucket": "Overall", "thinq_selected_elo_type": "overall_elo", "surface_flags": ["SURFACE_RESOLVER_UNAVAILABLE"]}
        flags.extend(surface.get("surface_flags") or [])
        tour = match.get("gender") or match.get("tour")
        player1 = match.get("player1")
        player2 = match.get("player2")
        pick = match.get("pick") or player1
        opponent = match.get("opponent") or player2

        p1_elo = self._load_elo(player1, tour=tour)
        p2_elo = self._load_elo(player2, tour=tour)
        elo_type = surface.get("thinq_selected_elo_type") or "overall_elo"
        p1_val = self._select_elo(p1_elo, elo_type)
        p2_val = self._select_elo(p2_elo, elo_type)
        elo_edge_p1 = 0.0
        elo_status = "NO_DATA"
        if p1_val is not None and p2_val is not None:
            elo_edge_p1 = clamp((p1_val - p2_val) / 2000.0, -0.10, 0.10)
            elo_status = "OK"
        else:
            flags.append("MISSING_ELO")

        pick_is_player2 = str(pick or "").strip().lower() == str(player2 or "").strip().lower()
        elo_edge_pick = -elo_edge_p1 if pick_is_player2 else elo_edge_p1

        if self.h2h_loader:
            h2h = self.h2h_loader.load_h2h(
                player1=player1,
                player2=player2,
                pick=pick,
                opponent=opponent,
                surface=surface.get("surface"),
                event_id=match.get("event_id") or match.get("eventId"),
                tournament_id=match.get("tournament_id") or match.get("tournamentId"),
            )
        else:
            h2h = empty_h2h("H2H loader unavailable")
        h2h_edge = as_float(h2h.get("edge"), 0.0) or 0.0

        edges = {
            "elo_edge": round(elo_edge_pick, 4),
            "h2h_edge": round(h2h_edge, 4) if h2h.get("status") == "AVAILABLE" else 0.0,
        }
        confidence = 0.0
        if elo_status == "OK":
            confidence += 0.55
        if h2h.get("status") == "AVAILABLE":
            confidence += min(as_float(h2h.get("confidence"), 0.0) or 0.0, 0.25)
        if surface.get("surface") != "Unknown":
            confidence += 0.15
        confidence = round(clamp(confidence, 0.0, 1.0), 4)
        available = True
        return {
            "available": available,
            "error": None,
            "confidence": confidence,
            "surface": surface,
            "elo": {"status": elo_status, "selected_elo_type": elo_type, "player1_elo": p1_val, "player2_elo": p2_val, "pick_elo_edge": round(elo_edge_pick, 4)},
            "h2h": h2h,
            "edges": edges,
            "flags": sorted(set(flags + (h2h.get("flags") or []))),
        }

    def build_match_features(self, player1: str, player2: str, **kwargs) -> Dict[str, Any]:
        match = dict(kwargs)
        match["player1"] = player1
        match["player2"] = player2
        match.setdefault("pick", kwargs.get("pick") or player1)
        match.setdefault("opponent", kwargs.get("opponent") or player2)
        return self.analyse_match(match)
