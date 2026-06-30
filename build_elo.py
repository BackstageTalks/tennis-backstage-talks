from sackmann_loader import load_all_matches
from elo_engine import build_and_save


def run():
    print("LOADING MATCHES...")
    
    # načítame posledné roky (rýchlejšie)
    matches = load_all_matches(2018, 2030)

    print("BUILDING ELO...")
    
    build_and_save(matches)

    print("ELO BUILD DONE ✅")


if __name__ == "__main__":
    run()
