import os
import json
import datetime

from results_checker import (
    BASE,
    HEADERS,
    LOCAL_TZ,
    fetch_json_url,
    fetch_sportscore_text,
    finished_text_only,
    find_match_result,
    units_for_result,
    summarize,
)


def candidate_prediction_dates(days_back=7):
    now = datetime.datetime.now(LOCAL_TZ).date()

    return [
        (now - datetime.timedelta(days=i)).isoformat()
        for i in range(1, days_back + 1)
    ]


def load_previous_all_predictions():
    """
    Loads previous ALL predictions from published GitHub Pages.
    """
    for date_value in candidate_prediction_dates():
        url = f"{BASE}all_predictions_{date_value}.json?v=all-results-check"

        data = fetch_json_url(url)

        if isinstance(data, list):
            print("PREVIOUS ALL PREDICTIONS FOUND:", date_value, len(data))
            return date_value, data

    print("NO PREVIOUS ALL PREDICTIONS FOUND")
    return None, []


def run():
    os.makedirs("public", exist_ok=True)

    prediction_date, predictions = load_previous_all_predictions()

    finished_text = finished_text_only(fetch_sportscore_text())

    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    results = []

    for prediction in predictions:
        match_result = find_match_result(prediction, finished_text)

        pick = str(prediction.get("pick", prediction.get("player1", "Unknown")))
        opponent = str(prediction.get("opponent", prediction.get("player2", "Unknown")))
        odds = prediction.get("odds")

        status = match_result.get("status")
        units = units_for_result(status, odds)

        output = {
            "prediction_date": prediction_date,
            "generated_at_utc": generated_at,

            "pick": pick,
            "opponent": opponent,
            "player1": prediction.get("player1"),
            "player2": prediction.get("player2"),

            "match_start": prediction.get("match_start"),
            "odds": odds,
            "probability": prediction.get("probability"),

            "status": status,
            "winner": match_result.get("winner"),
            "result_score": match_result.get("result_score"),
            "units": units,
            "note": match_result.get("note"),

            "source_results": "SportScore",
        }

        results.append(output)

    summary = summarize(results)

    payload = {
        "type": "ALL_RESULTS",
        "prediction_date": prediction_date,
        "generated_at_utc": generated_at,
        "summary": summary,
        "results": results,
    }

    result_date = prediction_date or datetime.date.today().isoformat()
    path = f"public/all_results_{result_date}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    print("ALL RESULTS GENERATED:", path)
    print("SUMMARY:", summary)
    print("RESULTS SAMPLE:", results[:3])


if __name__ == "__main__":
    run()
