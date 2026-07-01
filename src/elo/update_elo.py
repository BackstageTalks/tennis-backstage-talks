from .fetch import fetch_all
from .clean import clean_elo
from .store import save_latest, append_history


def run():

    data = fetch_all()

    for name, df in data.items():

        clean_df = clean_elo(df)

        save_latest(name, clean_df)

        append_history(name, clean_df)


if __name__ == "__main__":
    run()
