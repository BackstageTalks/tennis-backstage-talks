from sackmann_loader import load_all_matches
from elo_engine import build_elo_from_matches


def run():
    print("LOADING MATCHES...")
    matches = load_all_matches(2005, 2030)

    print("BUILDING ELO...")
    store = build_elo_from_matches(matches)

    print("ELO BUILD COMPLETE:", len(store))


if __name__ == "__main__":
    run()
