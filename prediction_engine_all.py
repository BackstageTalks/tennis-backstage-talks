from prediction_engine_core import (
    TOP_N,
    MIN_ODDS,
    MIN_TOP_PROBABILITY,
    build_all_predictions,
    get_top_predictions,
    get_daily_predictions,
)


def get_all_predictions():
    return build_all_predictions()
