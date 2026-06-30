import json
import os

DATA_PATH = "data/elo_ratings.json"

DEFAULT_ELO = 1500
K = 32


def normalize(name):
    return name.lower().strip()


def ensure(store, p):
    if p not in store:
        store[p] = {
            "Elo": DEFAULT_ELO,
            "hElo": DEFAULT_ELO,
            "cElo": DEFAULT_ELO,
            "gElo": DEFAULT_ELO
        }


def expected(r1, r2):
    return 1 / (1 + 10 ** ((r2 - r1) / 400))


def update_rating(r1, r2, score):
    exp = expected(r1, r2)
    return r1 + K * (score - exp)


def surface_key(surface):
    s = surface.lower()
    if "grass" in s:
        return "gElo"
    if "clay" in s:
        return "cElo"
    if "hard" in s:
        return "hElo"
    return "Elo"


def update_match(store, p1, p2, winner, surface):
    p1 = normalize(p1)
    p2 = normalize(p2)

    ensure(store, p1)
    ensure(store, p2)

    key = surface_key(surface)

    r1 = store[p1][key]
    r2 = store[p2][key]

    s1 = 1 if normalize(winner) == p1 else 0
    s2 = 1 - s1

    store[p1][key] = update_rating(r1, r2, s1)
    store[p2][key] = update_rating(r2, r1, s2)

    # overall
    o1 = store[p1]["Elo"]
    o2 = store[p2]["Elo"]

    store[p1]["Elo"] = update_rating(o1, o2, s1)
    store[p2]["Elo"] = update_rating(o2, o1, s2)


def build_elo(matches):
    store = {}

    for m in matches:
        update_match(
            store,
            m["player1"],
            m["player2"],
            m["winner"],
            m["surface"]
        )

    return store


def save(store):
    os.makedirs("data", exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(store, f)


def load():
    if not os.path.exists(DATA_PATH):
        return {}
    return json.load(open(DATA_PATH))


def build_and_save(matches):
    store = build_elo(matches)
    save(store)
    print("ELO PLAYERS:", len(store))
    return store


def get_elo(store, player, surface):
    player = normalize(player)

    if player not in store:
        return DEFAULT_ELO

    key = surface_key(surface)

    return store[player].get(key) or store[player]["Elo"]


def predict(p1, p2, surface, store):
    r1 = get_elo(store, p1, surface)
    r2 = get_elo(store, p2, surface)

    p = expected(r1, r2)

    return {
        "available": True,
        "probability_player1": p,
        "probability_player2": 1 - p,
        "elo_player1": r1,
        "elo_player2": r2
    }
``
