import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.bst_ai.matching import (
    normalize_name,
    normalize_name_spaced,
    normalize_tour,
    surface_key,
)
from src.bst_ai.probability import elo_probability
from src.bst_ai.rules import (
    build_ai_match_result,
    no_data_result,
)

DATA_FILE = Path("data/bst_ai/players.json")
ELO_DIR = Path("data/elo")
PLAYER_ALIASES_FILE = Path("data/player_aliases.json")

ELO_CANDIDATES = {
    "ATP": {
        "elo": [
            ELO_DIR / "atp_elo_latest.csv",
            ELO_DIR / "atp_elo.csv",
        ],
        "yelo": [
            ELO_DIR / "atp_yelo_latest.csv",
            ELO_DIR / "atp_yelo.csv",
        ],
    },
    "WTA": {
        "elo": [
            ELO_DIR / "wta_elo_latest.csv",
            ELO_DIR / "wta_elo.csv",
        ],
        "yelo": [
            ELO_DIR / "wta_yelo_latest.csv",
            ELO_DIR / "wta_yelo.csv",
        ],
    },
}


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        text = str(value).replace(",", "").strip()
        if not text or text.lower() in {"nan", "none", "null", "-"}:
            return None
        return float(text)
    except Exception:
        return None


def _first_value(row: Dict[str, Any], candidates: List[str]) -> Any:
    if not row:
        return None
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in candidates:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _first_existing(paths: List[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def _load_aliases() -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    if not PLAYER_ALIASES_FILE.exists():
        return aliases
    try:
        with PLAYER_ALIASES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return aliases

    if not isinstance(data, dict):
        return aliases

    for canonical, raw_aliases in data.items():
        canonical_key = normalize_name(canonical)
        if not canonical_key:
            continue
        aliases[canonical_key] = canonical_key
        if isinstance(raw_aliases, list):
            for alias in raw_aliases:
                alias_key = normalize_name(alias)
                if alias_key:
                    aliases[alias_key] = canonical_key
        elif isinstance(raw_aliases, str):
            alias_key = normalize_name(raw_aliases)
            if alias_key:
                aliases[alias_key] = canonical_key
                aliases[canonical_key] = alias_key
    return aliases


def _index_player(index: Dict[str, Any], player: Dict[str, Any]) -> None:
    player_key = player.get("player_key")
    tour = player.get("tour")
    name_key = player.get("player_name_key")
    player_name = player.get("player_name") or player.get("name")

    if not name_key and player_name:
        name_key = normalize_name(player_name)
        player["player_name_key"] = name_key

    if not player_key and tour and name_key:
        player_key = f"{tour}:{name_key}"
        player["player_key"] = player_key

    if player_key:
        index["by_key"][player_key] = player
    if tour and name_key:
        index["by_tour_name"][f"{tour}:{name_key}"] = player
        index["by_name"].setdefault(name_key, player)


def _merge_player(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if value is None:
            continue
        if key == "surface_elo":
            surf = dict(merged.get("surface_elo") or {})
            surf.update(value or {})
            merged[key] = surf
        elif merged.get(key) in (None, "", {}, []):
            merged[key] = value
        elif key in {"elo", "yelo"}:
            merged[key] = value
    return merged


def _read_elo_csv(path: Path, tour: str, rating_kind: str) -> List[Dict[str, Any]]:
    players: List[Dict[str, Any]] = []
    if not path or not path.exists():
        return players
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = _first_value(row, ["Player", "player", "name", "player_name"])
                if not name:
                    continue
                name = str(name).replace("\xa0", " ").strip()
                name_key = normalize_name(name)
                if not name_key:
                    continue

                elo = _float_or_none(_first_value(row, ["Elo", "elo", "rating"]))
                yelo = _float_or_none(_first_value(row, ["yElo", "yelo", "Yelo", "season_yelo"]))
                hard = _float_or_none(_first_value(row, ["hElo", "helo", "hard_elo", "hard"] ))
                clay = _float_or_none(_first_value(row, ["cElo", "celo", "clay_elo", "clay"] ))
                grass = _float_or_none(_first_value(row, ["gElo", "gelo", "grass_elo", "grass"] ))

                player: Dict[str, Any] = {
                    "player_key": f"{tour}:{name_key}",
                    "player_name": name,
                    "player_name_key": name_key,
                    "tour": tour,
                    "source": str(path),
                    "surface_elo": {},
                }

                if rating_kind == "yelo":
                    player["yelo"] = yelo if yelo is not None else elo
                else:
                    player["elo"] = elo
                    if hard is not None:
                        player["surface_elo"]["hard"] = hard
                    if clay is not None:
                        player["surface_elo"]["clay"] = clay
                    if grass is not None:
                        player["surface_elo"]["grass"] = grass

                players.append(player)
    except Exception:
        return players
    return players


def _load_elo_csv_players() -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for tour, groups in ELO_CANDIDATES.items():
        for rating_kind, paths in groups.items():
            path = _first_existing(paths)
            if not path:
                continue
            for player in _read_elo_csv(path, tour, rating_kind):
                key = player.get("player_key")
                if not key:
                    continue
                merged[key] = _merge_player(merged.get(key, {}), player)
    return list(merged.values())


@lru_cache(maxsize=1)
def load_bst_ai_players():
    players: List[Dict[str, Any]] = []
    status = "OK"

    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                players.extend(data.get("players", []) or [])
                status = data.get("status", "OK")
        except Exception:
            status = "NO_DATA"

    # Critical fallback: if data/bst_ai/players.json is stale or incomplete,
    # supplement it from the maintained Tennis Abstract ELO CSV store.
    players.extend(_load_elo_csv_players())

    by_key: Dict[str, Dict[str, Any]] = {}
    by_tour_name: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}

    index = {
        "by_key": by_key,
        "by_tour_name": by_tour_name,
        "by_name": by_name,
    }

    merged_by_key: Dict[str, Dict[str, Any]] = {}
    for player in players:
        if not isinstance(player, dict):
            continue
        player_name = player.get("player_name") or player.get("name") or player.get("player")
        tour = normalize_tour(player.get("tour")) or player.get("tour")
        if not player_name or not tour:
            continue
        name_key = player.get("player_name_key") or normalize_name(player_name)
        player["player_name"] = player_name
        player["player_name_key"] = name_key
        player["tour"] = tour
        player["player_key"] = player.get("player_key") or f"{tour}:{name_key}"
        key = player["player_key"]
        merged_by_key[key] = _merge_player(merged_by_key.get(key, {}), player)

    for player in merged_by_key.values():
        _index_player(index, player)

    return {
        "status": "OK" if by_tour_name else status,
        "players": list(merged_by_key.values()),
        "by_key": by_key,
        "by_tour_name": by_tour_name,
        "by_name": by_name,
        "aliases": _load_aliases(),
    }


def _alias_candidates(name_key: str, aliases: Dict[str, str]) -> List[str]:
    candidates = [name_key]
    aliased = aliases.get(name_key)
    if aliased and aliased not in candidates:
        candidates.append(aliased)
    return candidates


def find_player(player_name, tour=None):
    data = load_bst_ai_players()
    if data.get("status") != "OK":
        return None
    name_key = normalize_name(player_name)
    if not name_key:
        return None

    aliases = data.get("aliases") or {}
    name_candidates = _alias_candidates(name_key, aliases)
    normalized_tour = normalize_tour(tour)

    if normalized_tour:
        for candidate in name_candidates:
            player = data["by_tour_name"].get(f"{normalized_tour}:{candidate}")
            if player:
                return player

    for fallback_tour in ["ATP", "WTA"]:
        for candidate in name_candidates:
            player = data["by_tour_name"].get(f"{fallback_tour}:{candidate}")
            if player:
                return player

    for candidate in name_candidates:
        player = data.get("by_name", {}).get(candidate)
        if player:
            return player

    # Last lightweight fallback: compare spaced normalized names to make some
    # generated CSV variants more tolerant while avoiding heavy fuzzy matching.
    wanted_spaced = normalize_name_spaced(player_name)
    if wanted_spaced:
        wanted_compact = normalize_name(wanted_spaced)
        for player in data.get("players", []):
            candidate_key = player.get("player_name_key") or normalize_name(player.get("player_name"))
            if candidate_key == wanted_compact:
                return player
    return None


def get_pair_ratings(player_a, player_b, surface):
    key = surface_key(surface)
    if key:
        rating_a = (player_a.get("surface_elo", {}) or {}).get(key)
        rating_b = (player_b.get("surface_elo", {}) or {}).get(key)
        if rating_a is not None and rating_b is not None:
            return rating_a, rating_b, f"{key}_elo"

    # Prefer season/current yELO if both players have it, then overall Elo.
    rating_a = player_a.get("yelo")
    rating_b = player_b.get("yelo")
    if rating_a is not None and rating_b is not None:
        return rating_a, rating_b, "yelo"

    rating_a = player_a.get("elo")
    rating_b = player_b.get("elo")
    if rating_a is not None and rating_b is not None:
        return rating_a, rating_b, "elo"

    # Partial fallback: if one side has surface/yelo only and the other has Elo,
    # use the best available rating instead of returning No data.
    rating_a = player_a.get("elo") or player_a.get("yelo")
    rating_b = player_b.get("elo") or player_b.get("yelo")
    if rating_a is not None and rating_b is not None:
        return rating_a, rating_b, "mixed_elo"

    return None, None, None


def _names_equal(a: Any, b: Any) -> bool:
    return normalize_name(a) == normalize_name(b)


def _build_missing_player_context(
    player1: Any,
    player2: Any,
    player1_data: Optional[Dict[str, Any]],
    player2_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a clear, UI-friendly diagnostic when Thinq/BsT cannot find players.

    The model logic intentionally remains strict: no probability is calculated unless
    both players are found. This helper only improves explainability for ALL/debug UI.
    """
    player1_found = bool(player1_data)
    player2_found = bool(player2_data)

    missing_players: List[str] = []
    missing_side: Optional[str] = None
    reason = "One or both players were not found in BsT AI data."

    if not player1_found:
        missing_players.append(str(player1))
    if not player2_found:
        missing_players.append(str(player2))

    if not player1_found and not player2_found:
        missing_side = "both"
        reason = "Both players missing in ELO"
    elif not player1_found:
        missing_side = "player"
        reason = "Player missing in ELO"
    elif not player2_found:
        missing_side = "opponent"
        reason = "Opponent missing in ELO"

    return {
        "status": "PLAYER_NOT_FOUND",
        "reason": reason,
        "probability": None,
        "rating_type": None,
        "player1_found": player1_found,
        "player2_found": player2_found,
        "player1_key": normalize_name(player1),
        "player2_key": normalize_name(player2),
        "missing_side": missing_side,
        "missing_players": missing_players,
        "missing_player": missing_players[0] if len(missing_players) == 1 else None,
        "thinq_reason": reason,
        "thinq_missing_side": missing_side,
        "thinq_missing_players": missing_players,
        "thinq_missing_player": missing_players[0] if len(missing_players) == 1 else None,
    }


def build_bst_ai_probability(
    player1,
    player2,
    pick,
    surface=None,
    tour=None,
):
    data = load_bst_ai_players()
    if data.get("status") != "OK":
        return {
            "status": "NO_DATA",
            "reason": "BsT AI data file is missing or unavailable.",
            "probability": None,
            "rating_type": None,
            "player1_found": False,
            "player2_found": False,
        }

    player1_data = find_player(player1, tour=tour)
    player2_data = find_player(player2, tour=tour)

    if not player1_data or not player2_data:
        return _build_missing_player_context(
            player1=player1,
            player2=player2,
            player1_data=player1_data,
            player2_data=player2_data,
        )

    rating1, rating2, rating_type = get_pair_ratings(player1_data, player2_data, surface)

    if rating1 is None or rating2 is None or not rating_type:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Ratings incomplete",
            "detail": "Players found, but no complete real rating pair is available.",
            "probability": None,
            "rating_type": None,
            "player1_found": True,
            "player2_found": True,
            "thinq_reason": "Ratings incomplete",
            "thinq_detail": "Players found, but no complete real rating pair is available.",
        }

    probability_player1 = elo_probability(rating1, rating2)
    if probability_player1 is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Could not calculate BsT AI probability from real ratings.",
            "probability": None,
            "rating_type": rating_type,
            "player1_found": True,
            "player2_found": True,
            "thinq_reason": "Could not calculate BsT AI probability from real ratings.",
        }

    if _names_equal(pick, player1):
        pick_probability = probability_player1
    elif _names_equal(pick, player2):
        pick_probability = 1.0 - probability_player1
    else:
        return {
            "status": "PLAYER_NOT_FOUND",
            "reason": "Pick player does not match player1 or player2.",
            "probability": None,
            "rating_type": rating_type,
            "player1_found": True,
            "player2_found": True,
            "thinq_reason": "Pick player does not match player1 or player2.",
        }

    return {
        "status": "OK",
        "reason": "OK",
        "probability": round(pick_probability, 3),
        "rating_type": rating_type,
        "player1_found": True,
        "player2_found": True,
        "player1_rating": rating1,
        "player2_rating": rating2,
    }


def build_bst_ai_comparison(
    player1,
    player2,
    pick,
    surface,
    corq_probability,
    tour=None,
):
    bst_result = build_bst_ai_probability(
        player1=player1,
        player2=player2,
        pick=pick,
        surface=surface,
        tour=tour,
    )

    if bst_result.get("status") != "OK":
        result = no_data_result(
            status=bst_result.get("status", "NO_DATA"),
            reason=bst_result.get("reason"),
        )
        result["corq_ai_probability"] = (
            round(corq_probability, 3)
            if corq_probability is not None
            else None
        )
        result["bst_ai_rating_type"] = bst_result.get("rating_type")
        result["bst_player1_found"] = bst_result.get("player1_found")
        result["bst_player2_found"] = bst_result.get("player2_found")
        result["bst_player1_key"] = bst_result.get("player1_key")
        result["bst_player2_key"] = bst_result.get("player2_key")
        result["bst_missing_side"] = bst_result.get("missing_side")
        result["bst_missing_player"] = bst_result.get("missing_player")
        result["bst_missing_players"] = bst_result.get("missing_players")
        result["thinq_reason"] = bst_result.get("thinq_reason") or bst_result.get("reason")
        result["thinq_detail"] = bst_result.get("thinq_detail") or bst_result.get("detail")
        result["thinq_missing_side"] = bst_result.get("thinq_missing_side")
        result["thinq_missing_player"] = bst_result.get("thinq_missing_player")
        result["thinq_missing_players"] = bst_result.get("thinq_missing_players")
        return result

    result = build_ai_match_result(
        corq_probability=corq_probability,
        bst_probability=bst_result.get("probability"),
    )
    result["bst_ai_rating_type"] = bst_result.get("rating_type")
    result["bst_player1_found"] = bst_result.get("player1_found")
    result["bst_player2_found"] = bst_result.get("player2_found")
    result["bst_player1_rating"] = bst_result.get("player1_rating")
    result["bst_player2_rating"] = bst_result.get("player2_rating")
    return result
