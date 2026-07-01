import json
import os

from elo_engine import normalize, find_player_key

DATA_PATH = "data/form_stats.json"


def surface_key(surface):
    s = normalize(surface)

    if "grass" in s:
        return "grass"

    if "clay" in s:
        return "clay"

    if "hard" in s:
        return "hard"

    return "unknown"


def ensure_player(store, player):
    key = normalize(player)

    if key not in store:
        store[key] = {
            "player": player,
            "overall_results": [],
            "surface_results": {
                "hard": [],
                "clay": [],
                "grass": [],
                "unknown": [],
            },
            "matches": 0,
        }

    return key


def trim_results(results, keep=50):
    if len(results) <= keep:
        return results

    return results[-keep:]


def add_match(store, player, surface, won):
    key = ensure_player(store, player)
    s_key = surface_key(surface)

    result = 1 if won else 0

    store[key]["overall_results"].append(result)
    store[key]["overall_results"] = trim_results(store[key]["overall_results"])

    if s_key not in store[key]["surface_results"]:
        store[key]["surface_results"][s_key] = []

    store[key]["surface_results"][s_key].append(result)
    store[key]["surface_results"][s_key] = trim_results(
        store[key]["surface_results"][s_key]
    )

    store[key]["matches"] += 1


def build_form_store(matches):
    store = {}

    sorted_matches = sorted(
        matches,
        key=lambda x: str(x.get("date") or "0")
    )

    for match in sorted_matches:
        try:
            player1 = match["player1"]
            player2 = match["player2"]
            winner = match["winner"]
            surface = match.get("surface", "Hard")

            winner_key = normalize(winner)
            p1_key = normalize(player1)
            p2_key = normalize(player2)

            add_match(
                store=store,
                player=player1,
                surface=surface,
                won=(winner_key == p1_key),
            )

            add_match(
                store=store,
                player=player2,
                surface=surface,
                won=(winner_key == p2_key),
            )

        except Exception:
            continue

    return store


def save_form_store(store):
    os.makedirs("data", exist_ok=True)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def load_form_store():
    if not os.path.exists(DATA_PATH):
        return {}

    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_and_save_form(matches):
    print("BUILDING FORM STORE...")

    store = build_form_store(matches)

    save_form_store(store)

    print("FORM PLAYERS:", len(store))

    return store


def rate(results, n):
    if not results:
        return None

    subset = results[-n:]

    if not subset:
        return None

    return sum(subset) / len(subset)


def safe_rate(value):
    if value is None:
        return None

    try:
        return round(float(value), 3)
    except Exception:
        return None


def get_player_form(store, player, surface):
    player_key = find_player_key(store, player)

    if not player_key:
        return {
            "found": False,
            "matched_key": None,
            "last_5": None,
            "last_10": None,
            "surface_last_5": None,
            "surface_last_10": None,
            "matches": 0,
            "surface_matches": 0,
        }

    record = store[player_key]
    s_key = surface_key(surface)

    overall_results = record.get("overall_results", [])
    surface_results = record.get("surface_results", {}).get(s_key, [])

    return {
        "found": True,
        "matched_key": player_key,
        "last_5": safe_rate(rate(overall_results, 5)),
        "last_10": safe_rate(rate(overall_results, 10)),
        "surface_last_5": safe_rate(rate(surface_results, 5)),
        "surface_last_10": safe_rate(rate(surface_results, 10)),
        "matches": len(overall_results),
        "surface_matches": len(surface_results),
    }


def usable_rate(value):
    if value is None:
        return 0.5

    try:
        return float(value)
    except Exception:
        return 0.5


def clamp(value, low, high):
    return max(low, min(high, value))


def calculate_form_adjustment(pick_form, opponent_form):
    """
    Small correction only.
    ELO remains the main model.

    Max total adjustment: +/- 3.5 percentage points.
    """

    pick_last10 = usable_rate(pick_form.get("last_10"))
    opp_last10 = usable_rate(opponent_form.get("last_10"))

    recent_diff = pick_last10 - opp_last10

    recent_adjustment = clamp(
        recent_diff * 0.05,
        -0.025,
        0.025
    )

    surface_adjustment = 0.0

    pick_surface_matches = pick_form.get("surface_matches") or 0
    opp_surface_matches = opponent_form.get("surface_matches") or 0

    if pick_surface_matches >= 3 and opp_surface_matches >= 3:
        pick_surface = usable_rate(pick_form.get("surface_last_10"))
        opp_surface = usable_rate(opponent_form.get("surface_last_10"))

        surface_diff = pick_surface - opp_surface

        surface_adjustment = clamp(
            surface_diff * 0.035,
            -0.015,
            0.015
        )

    total_adjustment = clamp(
        recent_adjustment + surface_adjustment,
        -0.035,
        0.035
    )

    return {
        "recent_adjustment": round(recent_adjustment, 3),
        "surface_adjustment": round(surface_adjustment, 3),
        "total_adjustment": round(total_adjustment, 3),
    }
