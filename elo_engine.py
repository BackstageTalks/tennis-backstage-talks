import json
import os
import re
import unicodedata

DATA_PATH = "data/elo_ratings.json"

DEFAULT_ELO = 1500

# Rating update scale nechávame klasický.
RATING_UPDATE_SCALE = 400

# Prediction scale je jemnejší, aby percentá neboli prehnané.
PREDICTION_SCALE = 520

# Probability cap - ochrana proti nereálnym extrémom.
MIN_PROBABILITY = 0.15
MAX_PROBABILITY = 0.85

# Hybrid váhy.
SURFACE_WEIGHT = 0.55
OVERALL_WEIGHT = 0.45

# Čím vyššie číslo, tým viac ťaháme hráčov s malou vzorkou späť k 1500.
RELIABILITY_MATCHES_DENOMINATOR = 50


def clamp(value, low, high):
    return max(low, min(high, value))


def normalize(name):
    if not name:
        return ""

    text = str(name)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def name_tokens(name):
    key = normalize(name)

    if not key:
        return []

    return key.split()


def name_variants(name):
    key = normalize(name)

    if not key:
        return set()

    parts = key.split()
    variants = set()

    variants.add(key)

    if len(parts) >= 2:
        variants.add(" ".join(reversed(parts)))
        variants.add(parts[-1])
        variants.add(parts[0] + " " + parts[-1])
        variants.add(parts[-1] + " " + parts[0])

    if len(parts) >= 3:
        variants.add(parts[-2] + " " + parts[-1])
        variants.add(parts[0] + " " + parts[-2] + " " + parts[-1])
        variants.add(parts[-1] + " " + parts[-2] + " " + parts[0])
        variants.add(parts[0] + " " + parts[1])

    return variants


def surface_key(surface):
    s = normalize(surface)

    if "grass" in s:
        return "gElo"

    if "clay" in s:
        return "cElo"

    if "hard" in s:
        return "hElo"

    return "Elo"


def expected_rating_update(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / RATING_UPDATE_SCALE))


def expected_prediction(r1, r2):
    raw_probability = 1 / (1 + 10 ** ((r2 - r1) / PREDICTION_SCALE))
    return clamp(raw_probability, MIN_PROBABILITY, MAX_PROBABILITY)


def dynamic_k(matches):
    if matches < 30:
        return 32

    if matches < 100:
        return 26

    return 20


def get_recency_weight(date):
    """
    Jemnejší recency weight.
    Nechceme, aby novšie zápasy rozstrelili Elo extrémne rýchlo.
    """
    try:
        year = int(str(date)[:4])
        return clamp(1.0 + ((year - 2018) * 0.015), 0.85, 1.12)
    except Exception:
        return 1.0


def reliability_from_matches(matches):
    try:
        m = float(matches or 0)
    except Exception:
        m = 0.0

    return clamp(
        m / (m + RELIABILITY_MATCHES_DENOMINATOR),
        0.0,
        1.0
    )


def regress_to_default(raw_elo, matches):
    reliability = reliability_from_matches(matches)
    return DEFAULT_ELO + (raw_elo - DEFAULT_ELO) * reliability


def ensure(store, player):
    key = normalize(player)

    if key not in store:
        store[key] = {
            "player": player,
            "Elo": DEFAULT_ELO,
            "hElo": DEFAULT_ELO,
            "cElo": DEFAULT_ELO,
            "gElo": DEFAULT_ELO,
            "matches": 0,
        }

    return key


def update_match(store, player1, player2, winner, surface, date=None):
    p1 = ensure(store, player1)
    p2 = ensure(store, player2)
    winner_key = normalize(winner)

    s_key = surface_key(surface)

    score1 = 1 if winner_key == p1 else 0
    score2 = 1 - score1

    k1 = dynamic_k(store[p1]["matches"])
    k2 = dynamic_k(store[p2]["matches"])

    weight = get_recency_weight(date)

    # Surface Elo update
    r1 = store[p1][s_key]
    r2 = store[p2][s_key]

    exp1 = expected_rating_update(r1, r2)
    exp2 = expected_rating_update(r2, r1)

    store[p1][s_key] = r1 + k1 * weight * (score1 - exp1)
    store[p2][s_key] = r2 + k2 * weight * (score2 - exp2)

    # Overall Elo update
    o1 = store[p1]["Elo"]
    o2 = store[p2]["Elo"]

    o_exp1 = expected_rating_update(o1, o2)
    o_exp2 = expected_rating_update(o2, o1)

    store[p1]["Elo"] = o1 + k1 * weight * (score1 - o_exp1)
    store[p2]["Elo"] = o2 + k2 * weight * (score2 - o_exp2)

    store[p1]["matches"] += 1
    store[p2]["matches"] += 1


def build_elo(matches):
    store = {}

    for match in matches:
        try:
            update_match(
                store=store,
                player1=match["player1"],
                player2=match["player2"],
                winner=match["winner"],
                surface=match.get("surface", "Hard"),
                date=match.get("date"),
            )
        except Exception:
            continue

    return store


def save(store):
    os.makedirs("data", exist_ok=True)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def load():
    if not os.path.exists(DATA_PATH):
        return {}

    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_and_save(matches):
    print("BUILDING ELO...")

    store = build_elo(matches)

    save(store)

    print("ELO PLAYERS:", len(store))

    return store


def candidate_score(player_name, candidate_key):
    player_parts = name_tokens(player_name)
    candidate_parts = name_tokens(candidate_key)

    if not player_parts or not candidate_parts:
        return 0.0

    player_set = set(player_parts)
    candidate_set = set(candidate_parts)

    overlap = len(player_set.intersection(candidate_set))
    total = max(len(player_set), len(candidate_set))

    score = overlap / total

    if player_parts[-1] == candidate_parts[-1]:
        score += 0.30

    if len(player_parts) >= 2:
        reversed_player = " ".join(reversed(player_parts))
        if reversed_player == candidate_key:
            score += 0.30

    if len(player_parts) >= 3 and len(candidate_parts) >= 3:
        if player_parts[-1] == candidate_parts[-1]:
            score += 0.15
        if player_parts[-2] == candidate_parts[-2]:
            score += 0.10

    return min(score, 1.0)


def find_player_key(store, player):
    if not player:
        return None

    direct_key = normalize(player)

    if direct_key in store:
        return direct_key

    player_variants = name_variants(player)

    for variant in player_variants:
        if variant in store:
            return variant

    for candidate_key in store.keys():
        candidate_variants = name_variants(candidate_key)

        if player_variants.intersection(candidate_variants):
            return candidate_key

    best_key = None
    best_score = 0.0

    for candidate_key in store.keys():
        score = candidate_score(player, candidate_key)

        if score > best_score:
            best_score = score
            best_key = candidate_key

    if best_score >= 0.50:
        return best_key

    return None


def get_raw_elo_components(store, player, surface):
    player_key = find_player_key(store, player)

    if not player_key:
        return {
            "found": False,
            "matched_key": None,
            "raw_surface_elo": DEFAULT_ELO,
            "raw_overall_elo": DEFAULT_ELO,
            "adjusted_surface_elo": DEFAULT_ELO,
            "adjusted_overall_elo": DEFAULT_ELO,
            "final_elo": DEFAULT_ELO,
            "matches": 0,
            "reliability": 0.0,
        }

    record = store[player_key]

    s_key = surface_key(surface)

    raw_surface_elo = record.get(s_key)
    raw_overall_elo = record.get("Elo")
    matches = record.get("matches", 0)

    if raw_surface_elo is None:
        raw_surface_elo = raw_overall_elo

    if raw_overall_elo is None:
        raw_overall_elo = DEFAULT_ELO

    reliability = reliability_from_matches(matches)

    adjusted_surface_elo = regress_to_default(raw_surface_elo, matches)
    adjusted_overall_elo = regress_to_default(raw_overall_elo, matches)

    final_elo = (
        SURFACE_WEIGHT * adjusted_surface_elo
        + OVERALL_WEIGHT * adjusted_overall_elo
    )

    return {
        "found": True,
        "matched_key": player_key,
        "raw_surface_elo": raw_surface_elo,
        "raw_overall_elo": raw_overall_elo,
        "adjusted_surface_elo": adjusted_surface_elo,
        "adjusted_overall_elo": adjusted_overall_elo,
        "final_elo": final_elo,
        "matches": matches,
        "reliability": reliability,
    }


def predict(player1, player2, surface, store):
    p1 = get_raw_elo_components(store, player1, surface)
    p2 = get_raw_elo_components(store, player2, surface)

    probability1 = expected_prediction(
        p1["final_elo"],
        p2["final_elo"]
    )

    return {
        "available": True,
        "player1": player1,
        "player2": player2,

        "probability_player1": probability1,
        "probability_player2": 1 - probability1,

        "elo_player1": p1["final_elo"],
        "elo_player2": p2["final_elo"],

        "elo_raw_surface_player1": p1["raw_surface_elo"],
        "elo_raw_surface_player2": p2["raw_surface_elo"],
        "elo_raw_overall_player1": p1["raw_overall_elo"],
        "elo_raw_overall_player2": p2["raw_overall_elo"],

        "elo_adjusted_surface_player1": p1["adjusted_surface_elo"],
        "elo_adjusted_surface_player2": p2["adjusted_surface_elo"],
        "elo_adjusted_overall_player1": p1["adjusted_overall_elo"],
        "elo_adjusted_overall_player2": p2["adjusted_overall_elo"],

        "elo_found_player1": p1["found"],
        "elo_found_player2": p2["found"],
        "elo_matched_key_player1": p1["matched_key"],
        "elo_matched_key_player2": p2["matched_key"],

        "elo_matches_player1": p1["matches"],
        "elo_matches_player2": p2["matches"],
        "elo_reliability_player1": round(p1["reliability"], 3),
        "elo_reliability_player2": round(p2["reliability"], 3),

        "model": "CUSTOM_ELO_V4_CALIBRATED",
        "calibration": {
            "surface_weight": SURFACE_WEIGHT,
            "overall_weight": OVERALL_WEIGHT,
            "prediction_scale": PREDICTION_SCALE,
            "min_probability": MIN_PROBABILITY,
            "max_probability": MAX_PROBABILITY,
            "reliability_denominator": RELIABILITY_MATCHES_DENOMINATOR,
        },
    }
