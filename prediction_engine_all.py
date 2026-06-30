from prediction_engine import build_all_predictions


def get_all_daily_predictions():
    predictions = build_all_predictions()

    print("ALL STANDARD ELO PREDICTIONS:", len(predictions))

    for p in predictions:
        alt = p.get("alternative_market_info", {})

        print(
            "ALL:",
            p.get("pick"),
            "to beat",
            p.get("opponent"),
            "| prob:",
            p.get("probability"),
            "| odds:",
            p.get("odds"),
            "| source:",
            p.get("model_source"),
            "| elo:",
            p.get("elo_player"),
            "vs",
            p.get("elo_opponent"),
            "| sets:",
            alt.get("most_likely_sets"),
            "| expected_games:",
            alt.get("expected_games")
        )

    return predictions


def get_all_predictions():
    return get_all_daily_predictions()


def get_daily_predictions():
    return get_all_daily_predictions()
