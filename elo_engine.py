import json
import os

DATA_PATH = "data/elo_ratings.json"

DEFAULT_ELO = 1500


def normalize(name):
    return name.lower().strip()


def ensure(store, p):
    if p not in store:
        store[p] = {
            "Elo": DEFAULT_ELO,
            "hElo": DEFAULT_ELO,
            "cElo": DEFAULT_ELO,
            "gElo": DEFAULT_ELO,
            "matches": 0
        }


def expected(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))


def dynamic_k(matches):
    if matches < 30:
        return 40
    elif matches < 100:
        return 32
    else:
        return 24


def surface_key(surface):
    s = str(surface).lower()

    if "grass" in s:
        return "gElo"
    if "clay" in s:
        return "cElo"
    if "hard" in s:
        return "hElo"

    return "Elo"


def get_recency_weight(date):
    try:
        year = int(str(date)[:4])
        return 1.0 + ((year - 2018) * 0.05)
    except:
        return 1.0


def update_match(store, p1, p2, winner, surface, date=None):
    p1 = normalize(p1)
    p2 = normalize(p2)
    winner = normalize(winner)

    ensure(store, p1)
    ensure(store, p2)

    key = surface_key(surface)

    r1 = store[p1][key]
    r2 = store[p2][key]

    s1 = 1 if winner == p1 else 0
    s2 = 1 - s1

    k1 = dynamic_k(store[p1]["matches"])
    k2 = dynamic_k(store[p2]["matches"])

    weight = get_recency_weight(date)

    # ✅ surface Elo
    store[p1][key] = r1 + k1 * weight * (s1 - expected(r1, r2))
    store[p2][key] = r2 + k2 * weight * (s2 - expected(r2, r1))

    # ✅ overall Elo
    o1 = store[p1]["Elo"]
    o2 = store[p2]["Elo"]

    store[p1]["Elo"] = o1 + k1 * weight * (s1 - expected(o1, o2))
    store[p2]["Elo"] = o2 + k2 * weight * (s2 - expected(o2, o1))

    store[p1]["matches"] += 1
    store[p2]["matches"] += 1


def build_elo(matches):
    store = {}

    for m in matches:
        update_match(
            store,
            m["player1"],
            m["player2"],
            m["winner"],
            m["surface"],
            m.get("date")
        )

    return store


def save(store):
    os.makedirs("data", exist_ok=True)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f)


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


def get_elo(store, player, surface):
    player = normalize(player)

    if player not in store:
        return DEFAULT_ELO

    key = surface_key(surface)

    surface_elo = store[player].get(key)
    overall_elo = store[player].get("Elo")

    if surface_elo is None:
        surface_elo = overall_elo

    # ✅ HYBRID
    return 0.7 * surface_elo + 0.3 * overall_elo


def predict(p1, p2, surface, store):
    r1 = get_elo(store, p1, surface)
    r2 = get_elo(store, p2, surface)

    prob1 = expected(r1, r2)

    return {
        "available": True,
        "probability_player1": prob1,
        "probability_player2": 1 - prob1,
        "elo_player1": r1,
        "elo_player2": r2,
        "model": "CUSTOM_ELO_V2"
    }
