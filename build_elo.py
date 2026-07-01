from datetime import datetime
from zoneinfo import ZoneInfo

from sackmann_loader import load_all_matches
from elo_engine import build_and_save
from form_engine import build_and_save_form


LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def today_cutoff_yyyymmdd():
    return datetime.now(LOCAL_TZ).strftime("%Y%m%d")


def filter_matches_before_today(matches):
    cutoff = today_cutoff_yyyymmdd()

    filtered = []

    for match in matches:
        date = str(match.get("date") or "0")

        if date != "0" and date < cutoff:
            filtered.append(match)

    print("TODAY CUTOFF:", cutoff)
    print("MATCHES BEFORE TODAY:", len(filtered))

    return filtered


def run():
    print("LOADING MATCHES FOR ADVANCED ELO + FORM...")

    matches = load_all_matches(2018, 2030)

    if not matches:
        raise Exception("NO MATCHES LOADED FOR ELO")

    print("MATCHES LOADED:", len(matches))

    historical_matches = filter_matches_before_today(matches)

    if len(historical_matches) < 1000:
        raise Exception(
            f"TOO FEW HISTORICAL MATCHES LOADED: {len(historical_matches)}"
        )

    print("BUILDING ADVANCED ELO STORE...")
    elo_store = build_and_save(historical_matches)

    print("ELO STORE PLAYERS:", len(elo_store))

    if len(elo_store) < 200:
        raise Exception(f"TOO FEW ELO PLAYERS: {len(elo_store)}")

    print("BUILDING FORM STORE...")
    form_store = build_and_save_form(historical_matches)

    print("FORM STORE PLAYERS:", len(form_store))

    if len(form_store) < 200:
        raise Exception(f"TOO FEW FORM PLAYERS: {len(form_store)}")

    print("ADVANCED ELO + FORM BUILD DONE")


if __name__ == "__main__":
    run()
