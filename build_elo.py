from sackmann_loader import load_all_matches
from elo_engine import build_and_save


def run():
    print("LOADING MATCHES...")
    matches = load_all_matches(2015, 2030)

    print("BUILDING ELO...")
    build_and_save(matches)


if __name__ == "__main__":
    run()
``
