from src.elo.store import load_history


def main():

    df = load_history()

    print(df.head())

    print()
    print("Rows:", len(df))


if __name__ == "__main__":
    main()
