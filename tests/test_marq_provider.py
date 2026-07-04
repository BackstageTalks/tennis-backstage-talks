from src.marq_ai import (
    fetch_marq_market_data,
)


def main():

    result = fetch_marq_market_data(
        player1="Daniil Medvedev",
        player2="Kamil Majchrzak",
        date_only="2026-06-13",
    )

    print()
    print("========== MARQ PROVIDER ==========")
    print(result)
    print("===================================")
    print()


if __name__ == "__main__":
    main()
