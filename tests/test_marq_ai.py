from src.marq_ai import build_marq_ai


def main():

    marq = build_marq_ai(
        opening_odds=2.10,
        current_odds=1.85,
        movement_history=[
            {
                "odds": 2.10,
                "timestamp": 1,
            },
            {
                "odds": 2.05,
                "timestamp": 2,
            },
            {
                "odds": 2.00,
                "timestamp": 3,
            },
            {
                "odds": 1.95,
                "timestamp": 4,
            },
            {
                "odds": 1.90,
                "timestamp": 5,
            },
            {
                "odds": 1.85,
                "timestamp": 6,
            },
        ],
    )

    print()
    print("================================")
    print("         MARQ AI TEST")
    print("================================")
    print()

    print(f"Score       : {marq.score}")
    print(f"Signal      : {marq.signal}")
    print(f"Direction   : {marq.direction}")
    print(f"Strength    : {marq.strength}")
    print(f"Consistency : {marq.consistency}")

    print()
    print("================================")
    print()


if __name__ == "__main__":
    main()
