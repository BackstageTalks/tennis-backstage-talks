import os
import re
import json
import datetime
import requests
from bs4 import BeautifulSoup
from datetime import timezone, timedelta

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"
SPORTSCORE_URL = "https://sportscore.com/tennis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

LOCAL_TZ_OFFSET_HOURS = int(os.getenv("LOCAL_TZ_OFFSET_HOURS", "2"))
LOCAL_TZ = timezone(timedelta(hours=LOCAL_TZ_OFFSET_HOURS))


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_name(value):
    value = clean_text(value)
    value = value.lower()
    value = re.sub(r"[^a-zà-ž0-9]+", " ", value)
    return clean_text(value)


def pct(value):
    try:
        return round(float(value) * 100, 1)
    except Exception:
        return 0


def odds_to_float(value):
    try:
        if value in [None, "", "-", "None"]:
            return None
        return float(value)
    except Exception:
        return None


def units_for_result(status, odds):
    odd_value = odds_to_float(odds)

    if status == "WON":
        if odd_value is None:
            return 0.0
        return round(odd_value - 1.0, 2)

    if status == "LOST":
        return -1.0

    return 0.0


def candidate_prediction_dates(days_back=7):
    now = datetime.datetime.now(LOCAL_TZ).date()

    return [
        (now - datetime.timedelta(days=i)).isoformat()
        for i in range(1, days_back + 1)
    ]


def fetch_json_url(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)

        print("FETCH JSON:", url, response.status_code)

        if response.status_code != 200:
            return None

        return response.json()

    except Exception as e:
        print("FETCH JSON ERROR:", url, str(e))
        return None


def load_previous_predictions():
    """
    Workflow maže public folder, preto berieme predchádzajúce TOP7 predikcie
    z už publikovanej GitHub Pages URL.

    Hľadáme posledný dostupný predictions_YYYY-MM-DD.json.
    """
    for date_value in candidate_prediction_dates():
        url = f"{BASE}predictions_{date_value}.json?v=results-check"

        data = fetch_json_url(url)

        if isinstance(data, list):
            print("PREVIOUS PREDICTIONS FOUND:", date_value, len(data))
            return date_value, data

    print("NO PREVIOUS PREDICTIONS FOUND")
    return None, []


def fetch_sportscore_text():
    try:
        response = requests.get(SPORTSCORE_URL, headers=HEADERS, timeout=25)

        print("SPORTSCORE RESULTS HTTP:", response.status_code)

        if response.status_code != 200:
            print("SPORTSCORE RESULTS RAW ERROR:", response.text[:500])
            return ""

        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(" ", strip=True)

    except Exception as e:
        print("SPORTSCORE RESULTS FETCH ERROR:", str(e))
        return ""


def finished_text_only(text):
    text = clean_text(text)

    lower = text.lower()

    markers = [
        "finished results",
        "finished matches",
        "finished",
    ]

    start_index = -1

    for marker in markers:
        idx = lower.find(marker)

        if idx != -1:
            start_index = idx
            break

    if start_index == -1:
        return text

    return clean_text(text[start_index:])


def score_from_tokens(tokens):
    """
    SportScore finished text býva napríklad:
    Player A 6 3 1 6 6 3 Player B

    Interpretácia:
    6-3, 1-6, 6-3
    """
    numbers = []

    for token in tokens:
        if token.isdigit():
            numbers.append(int(token))

    if len(numbers) < 2 or len(numbers) % 2 != 0:
        return None

    sets = []

    for i in range(0, len(numbers), 2):
        sets.append((numbers[i], numbers[i + 1]))

    return sets


def format_sets(sets):
    if not sets:
        return ""

    return " ".join(f"{a}-{b}" for a, b in sets)


def winner_from_sets(sets, first_player, second_player):
    if not sets:
        return None

    first_sets = 0
    second_sets = 0

    for a, b in sets:
        if a > b:
            first_sets += 1
        elif b > a:
            second_sets += 1

    if first_sets > second_sets:
        return first_player

    if second_sets > first_sets:
        return second_player

    return None


def build_result(status, pick, winner, result_score, note=""):
    if status == "VOID":
        final_status = "VOID"
    elif winner is None:
        final_status = "UNKNOWN"
    elif normalize_name(winner) == normalize_name(pick):
        final_status = "WON"
    else:
        final_status = "LOST"

    return {
        "status": final_status,
        "winner": winner,
        "result_score": result_score,
        "note": note,
    }


def find_match_result(prediction, finished_text):
    """
    Konzervatívne párovanie:
    - hľadáme len vo finished sekcii
    - musia sedieť obe mená hráčov
    - cancelled / walkover / retired dávame ako VOID
    """
    player1 = str(prediction.get("player1", ""))
    player2 = str(prediction.get("player2", ""))
    pick = str(prediction.get("pick", player1))

    if not player1 or not player2:
        return {
            "status": "UNKNOWN",
            "winner": None,
            "result_score": "",
            "note": "Missing player names in prediction",
        }

    text = finished_text

    status_pattern = r"(?P<status>FT|Canc|Cancelled|RET|Ret|WO|W/O|Walkover)"
    score_pattern = r"(?P<score>(?:\d+|-)\s+(?:\d+|-)(?:\s+(?:\d+|-)\s+(?:\d+|-)){0,4})"

    patterns = [
        {
            "first": player1,
            "second": player2,
            "regex": re.compile(
                status_pattern
                + r"\s+"
                + re.escape(player1)
                + r"\s+"
                + score_pattern
                + r"\s+"
                + re.escape(player2),
                re.IGNORECASE,
            ),
        },
        {
            "first": player2,
            "second": player1,
            "regex": re.compile(
                status_pattern
                + r"\s+"
                + re.escape(player2)
                + r"\s+"
                + score_pattern
                + r"\s+"
                + re.escape(player1),
                re.IGNORECASE,
            ),
        },
    ]

    for item in patterns:
        match = item["regex"].search(text)

        if not match:
            continue

        raw_status = clean_text(match.group("status"))
        score_text = clean_text(match.group("score"))

        if raw_status.lower() in [
            "canc",
            "cancelled",
            "wo",
            "w/o",
            "walkover",
            "ret",
            "retired",
        ]:
            return build_result(
                status="VOID",
                pick=pick,
                winner=None,
                result_score=score_text,
                note=f"Match status: {raw_status}",
            )

        tokens = score_text.split()
        sets = score_from_tokens(tokens)
        result_score = format_sets(sets)

        winner = winner_from_sets(
            sets=sets,
            first_player=item["first"],
            second_player=item["second"],
        )

        return build_result(
            status="DONE",
            pick=pick,
            winner=winner,
            result_score=result_score,
            note="Matched from SportScore finished results",
        )

    return {
        "status": "PENDING",
        "winner": None,
        "result_score": "",
        "note": "Result not found in current SportScore finished section",
    }


def summarize(results):
    summary = {
        "total": len(results),
        "won": 0,
        "lost": 0,
        "void": 0,
        "pending": 0,
        "unknown": 0,
        "hit_rate": None,
        "units": 0.0,
    }

    for item in results:
        status = item.get("status")
        units = float(item.get("units", 0) or 0)

        summary["units"] += units

        if status == "WON":
            summary["won"] += 1
        elif status == "LOST":
            summary["lost"] += 1
        elif status == "VOID":
            summary["void"] += 1
        elif status == "PENDING":
            summary["pending"] += 1
        else:
            summary["unknown"] += 1

    decided = summary["won"] + summary["lost"]

    if decided > 0:
        summary["hit_rate"] = round(summary["won"] / decided * 100, 1)

    summary["units"] = round(summary["units"], 2)

    return summary


def run():
    os.makedirs("public", exist_ok=True)

    prediction_date, predictions = load_previous_predictions()

    finished_text = finished_text_only(fetch_sportscore_text())

    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    results = []

    for prediction in predictions[:7]:
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

