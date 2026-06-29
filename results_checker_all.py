from results_checker import build_results_payload


def run():
    build_results_payload(
        prefix="all_predictions_",
        result_prefix="all_results_",
        result_type="ALL_RESULTS",
        max_items=None,
    )


if __name__ == "__main__":
    run()
