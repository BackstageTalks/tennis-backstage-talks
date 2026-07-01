import json
import os
import re
import unicodedata

DATA_PATH = "data/elo_ratings.json"

DEFAULT_ELO = 1500


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


def expected(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))


def dynamic_k(matches):
    if matches < 30:
        return 40

    if matches < 100:
        return 32

    return 24


def get_recency_weight(date):
    try:
        year = int(str(date)[:4])
        return max(0.75, 1.0 + ((year - 2018) * 0.03))
    except Exception:
        return 1.0


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
    w = normalize(winner)

    s_key = surface_key(surface)

    score1 = 1 if w == p1 else 0
    score2 = 1 - score1

    k1 = dynamic_k(store[p1]["matches"])
    k2 = dynamic_k(store[p2]["matches"])

    weight = get_recency_weight(date)

    # surface Elo update
    r1 = store[p1][s_key]
    r2 = store[p2][s_key]

    exp1 = expected(r1, r2)
    exp2 = expected(r2, r1)

    store[p1][s_key] = r1 + k1 * weight * (score1 - exp1)
    store[p2][s_key] = r2 + k2 * weight * (score2 - exp2)

    # overall Elo update
    o1 = store[p1]["Elo"]
    o2 = store[p2]["Elo"]

    o_exp1 = expected(o1, o2)
    o_exp2 = expected(o2, o1)

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

    # surname bonus
    if player_parts[-1] == candidate_parts[-1]:
        score += 0.25

    # reversed name bonus
    if len(player_parts) >= 2 and " ".join(reversed(player_parts)) == candidate_key:
        score += 0.25

    return min(score, 1.0)


def find_player_key(store, player):
    if not player:
        return None

    key = normalize(player)

    if key in store:
        return key

    variants = name_variants(player)

    for variant in variants:
        if variant in store:
            return variant

    best_key = None
    best_score = 0.0

    for candidate_key in store.keys():
        score = candidate_score(player, candidate_key)

        if score > best_score:
            best_score = score
            best_key = candidate_key

    if best_score >= 0.55:
        return best_key

    return None


def get_raw_elo(store, player, surface):
    player_key = find_player_key(store, player)

    if not player_key:
        return DEFAULT_ELO, False, None

    record = store[player_key]

    s_key = surface_key(surface)

    surface_elo = record.get(s_key)
    overall_elo = record.get("Elo")

    if surface_elo is None:
        surface_elo = overall_elo

    if overall_elo is None:
        overall_elo = DEFAULT_ELO

    # hybrid Elo: surface + overall
    final_elo = 0.7 * surface_elo + 0.3 * overall_elo

    return final_elo, True, player_key


def predict(player1, player2, surface, store):
    elo1, found1, matched_key1 = get_raw_elo(store, player1, surface)
    elo2, found2, matched_key2 = get_raw_elo(store, player2, surface)

    probability1 = expected(elo1, elo2)

    return {
        "available": True,
        "player1": player1,
        "player2": player2,
        "probability_player1": probability1,
        "probability_player2": 1 - probability1,
        "elo_player1": elo1,
        "elo_player2": elo2,
        "elo_found_player1": found1,
        "elo_found_player2": found2,
        "elo_matched_key_player1": matched_key1,
        "elo_matched_key_player2": matched_key2,
        "model": "CUSTOM_ELO_V3",
    }
