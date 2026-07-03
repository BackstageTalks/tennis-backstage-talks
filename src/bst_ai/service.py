import json
from functools import lru_cache
from pathlib import Path

from src.bst_ai.matching import (
    normalize_name,
    normalize_tour,
    surface_key,
)

from src.bst_ai.probability import elo_probability

from src.bst_ai.rules import (
    build_ai_match_result,
    no_data_result,
)


DATA_FILE = Path("data/bst_ai/players.json")


@lru_cache(maxsize=1)
def load_bst_ai_players():
    if not DATA_FILE.exists():
        return {
            "status": "NO_DATA",
            "players": [],
            "by_key": {},
            "by_tour_name": {},
        }

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except Exception:
        return {
            "status": "NO_DATA",
            "players": [],
            "by_key": {},
            "by_tour_name": {},
        }

    players = data.get("players", [])

    by_key = {}
    by_tour_name = {}

    for player in players:
        player_key = player.get("player_key")
        tour = player.get("tour")
        name_key = player.get("player_name_key")

        if player_key:
            by_key[player_key] = player

        if tour and name_key:
            by_tour_name[f"{tour}:{name_key}"] = player

    return {
        "status": data.get("status", "OK"),
        "players": players,
        "by_key": by_key,
        "by_tour_name": by_tour_name,
    }


def find_player(player_name, tour=None):
    data = load_bst_ai_players()

    if data.get("status") != "OK":
        return None

    name_key = normalize_name(player_name)

    if not name_key:
        return None

    normalized_tour = normalize_tour(tour)

    if normalized_tour:
        player = data["by_tour_name"].get(
            f"{normalized_tour}:{name_key}"
        )

        if player:
            return player

    for fallback_tour in ["ATP", "WTA"]:
        player = data["by_tour_name"].get(
            f"{fallback_tour}:{name_key}"
        )

        if player:
            return player

    return None


def get_pair_ratings(player_a, player_b, surface):
    key = surface_key(surface)

    if key:
        rating_a = (
            player_a.get("surface_elo", {})
            .get(key)
        )

        rating_b = (
            player_b.get("surface_elo", {})
            .get(key)
        )

        if rating_a is not None and rating_b is not None:
            return rating_a, rating_b, f"{key}_elo"

    rating_a = player_a.get("elo")
    rating_b = player_b.get("elo")

    if rating_a is not None and rating_b is not None:
        return rating_a, rating_b, "elo"

    rating_a = player_a.get("yelo")
    rating_b = player_b.get("yelo")

    if rating_a is not None and rating_b is not None:
        return rating_a, rating_b, "yelo"

    return None, None, None


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

    player1_data = find_player(
        player1,
        tour=tour,
    )

    player2_data = find_player(
        player2,
        tour=tour,
    )

    if not player1_data or not player2_data:
        return {
            "status": "PLAYER_NOT_FOUND",
            "reason": "One or both players were not found in BsT AI data.",
            "probability": None,
            "rating_type": None,
            "player1_found": bool(player1_data),
            "player2_found": bool(player2_data),
        }

    rating1, rating2, rating_type = get_pair_ratings(
        player1_data,
        player2_data,
        surface,
    )

    if rating1 is None or rating2 is None or not rating_type:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Players found, but no complete real rating pair is available.",
            "probability": None,
            "rating_type": None,
            "player1_found": True,
            "player2_found": True,
        }

    probability_player1 = elo_probability(
        rating1,
        rating2,
    )

    if probability_player1 is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Could not calculate BsT AI probability from real ratings.",
            "probability": None,
            "rating_type": rating_type,
            "player1_found": True,
            "player2_found": True,
        }

    if pick == player1:
        pick_probability = probability_player1

    elif pick == player2:
        pick_probability = 1.0 - probability_player1

    else:
        return {
            "status": "PLAYER_NOT_FOUND",
            "reason": "Pick player does not match player1 or player2.",
            "probability": None,
            "rating_type": rating_type,
            "player1_found": True,
            "player2_found": True,
        }

    return {
        "status": "OK",
        "reason": "OK",
        "probability": round(pick_probability, 3),
        "rating_type": rating_type,
        "player1_found": True,
        "player2_found": True,
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

        return result

    result = build_ai_match_result(
        corq_probability=corq_probability,
        bst_probability=bst_result.get("probability"),
    )

    result["bst_ai_rating_type"] = bst_result.get("rating_type")
    result["bst_player1_found"] = bst_result.get("player1_found")
    result["bst_player2_found"] = bst_result.get("player2_found")

    return result
