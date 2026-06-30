from prediction_engine import build_all_predictions


def get_all_daily_predictions():
    """
    ALL stránka:
    - všetky zápasy
    - každý zápas má ELO+ predikciu víťaza
    - žiadny filter podľa kurzu
    - kompatibilné s update.py, ktorý importuje get_all_daily_predictions
    """
    predictions = build_all_predictions()

    print("ALL ELO+ PREDICTIONS:", len(predictions))

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
            "| base_elo:",
            p.get("base_elo_probability"),
            "| adj:",
            p.get("elo_stats_adjustment"),
            "| sets:",
            alt.get("most_likely_sets"),
            "| expected_games:",
            alt.get("expected_games"),
            "| games_lean:",
            alt.get("games_lean")
        )

    return predictions


def get_all_predictions():
    """
    Alias pre prípad, že niektorý iný súbor volá get_all_predictions().
    """
    return get_all_daily_predictions()


def get_daily_predictions():
    """
    Compatibility alias pre staršie volania.
    """
    return get_all_daily_predictions()
