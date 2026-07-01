from sackmann_loader import load_all_matches
from elo_engine import build_and_save


def run():
    print("LOADING MATCHES FOR ELO...")

    matches = load_all_matches(2018, 2030)

    if not matches:
        raise Exception("NO MATCHES LOADED FOR ELO")

    print("MATCHES LOADED:", len(matches))

    if len(matches) < 1000:
        raise Exception(f"TOO FEW MATCHES LOADED FOR ELO: {len(matches)}")

    print("BUILDING ELO STORE...")

    store = build_and_save(matches)

    print("ELO STORE PLAYERS:", len(store))

    if len(store) < 200:
        raise Exception(f"TOO FEW ELO PLAYERS: {len(store)}")

    print("ELO BUILD DONE")


if __name__ == "__main__":
    run()
