from src.elo.fetch import fetch_all
from src.elo.clean import clean_elo
from src.elo.store import save_latest, append_history


def run():

    data = fetch_all()

    for name, df in data.items():

        cleaned = clean_elo(df)

        save_latest(
            name=name,
            df=cleaned
        )

        append_history(
            name=name,
            df=cleaned
        )

    print("ELO database updated")


if __name__ == "__main__":
    run()
