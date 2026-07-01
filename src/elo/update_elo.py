from src.elo.fetch import fetch_all


def run():

    data = fetch_all()

    for name, df in data.items():

        print("\n====================")
        print(name)
        print("====================")

        print(df.columns.tolist())

    print("DONE")


if __name__ == "__main__":
    run()
