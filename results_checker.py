import json
import os
import re
import requests
import unicodedata
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta


SPORTSCORE_URL = "https://sportscore.com/tennis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PLAY_HISTORY_DIR = "data/play_history"
RESULTS_DATA_PATH = "data/play_results.json"
PUBLIC_RESULTS_DATA_PATH = "public/results_data.json"
RESULTS_DEBUG_PATH = "public/results_debug.json"


_DEBUG = {
    "provider": "SportScore",
    "url": SPORTSCORE_URL,
    "http_status": None,
    "fetch_error": None,
    "history_files": [],
    "history_items_loaded": 0,
    "finished_results_found": 0,
    "resolved_count": 0,
    "pending_count": 0,
    "unknown_count": 0,
    "examples_results": [],
    "examples_resolved": [],
    "examples_unresolved": [],
}


def ensure_dirs():
    os.makedirs(
        "data",
        exist_ok=True,
    )

    os.makedirs(
        PLAY_HISTORY_DIR,
        exist_ok=True,
    )

    os.makedirs(
        "public",
        exist_ok=True,
    )


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception:
        return default


def normalize(value):
    if value is None:
        return ""

    text = str(value)

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace(".", " ")
    text = text.replace(",", " ")
    text = text.replace("'", "")
    text = text.replace("’", "")
    text = text.replace("`", "")

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def loose_name_keys(name):
    normalized = normalize(name)
    parts = normalized.split()

    keys = set()

    if normalized:
        keys.add(normalized)

    if parts:
        keys.add(parts[-1])

    if len(parts) >= 2:
        keys.add(
            " ".join(parts[-2:])
        )

    return keys


def names_match(a, b):
    a_keys = loose_name_keys(a)
    b_keys = loose_name_keys(b)

    if not a_keys or not b_keys:
        return False

    return bool(
        a_keys.intersection(b_keys)
    )


def clean_text(value):
    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None

        return float(value)

    except Exception:
        return None


def load_all_history_items():
    ensure_dirs()

    items = []
    files = []

    for filename in sorted(os.listdir(PLAY_HISTORY_DIR)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(
            PLAY_HISTORY_DIR,
            filename,
        )

        files.append(path)

        data = load_json(
            path,
            [],
        )

        if isinstance(data, list):
            items.extend(data)

    _DEBUG["history_files"] = files
    _DEBUG["history_items_loaded"] = len(items)

    return items


def finished_text_only(text):
    text = clean_text(text)
    lower = text.lower()

    markers = [
        "finished matches",
        "finished results",
        "finished",
        "results",
    ]

    start_index = -1

    for marker in markers:
        idx = lower.find(marker)

        if idx != -1:
            start_index = idx
            break

    if start_index == -1:
        return text

    return text[start_index:]


def parse_score_sets(score_text):
    """
    Skúsi určiť sety z textu typu:
    6-4 4-6 6-3
    """

    if not score_text:
        return None

    upper = score_text.upper()

    if any(token in upper for token in ["W/O", "WO", "RET", "ABN", "DEF"]):
        return {
            "status": "VOID",
            "winner_side": None,
            "score": clean_text(score_text),
        }

    chunks = re.findall(
        r"(\d{1,2})-(\d{1,2})",
        score_text,
    )

    if not chunks:
        return None

    p1_sets = 0
    p2_sets = 0

    for a_text, b_text in chunks:
        try:
            a = int(a_text)
            b = int(b_text)
        except Exception:
            continue

        if a > b:
            p1_sets += 1

        elif b > a:
            p2_sets += 1

    if p1_sets == p2_sets:
        return None

    winner_side = "player1" if p1_sets > p2_sets else "player2"

    return {
        "status": "FINISHED",
        "winner_side": winner_side,
        "score": clean_text(score_text),
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
    }


def extract_finished_results(text):
    """
    Best-effort parser.

    SportScore text sa môže meniť, preto parser nikdy nesmie zhodiť workflow.
    Ak výsledok nevie spoľahlivo určiť, pick ostane PENDING alebo UNKNOWN.
    """

    text = finished_text_only(text)

    results = []

    # Pattern:
    # Player One vs Player Two 6-4 4-6 6-3
    pattern_vs_score = re.compile(
        r"(?P<p1>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+vs\s+"
        r"(?P<p2>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+(?P<score>(?:\d{1,2}-\d{1,2}(?:\(\d+\))?\s*){2,5}|W/O|WO|RET|DEF|ABN)",
        re.IGNORECASE,
    )

    for match in pattern_vs_score.finditer(text):
        p1 = clean_text(match.group("p1"))
        p2 = clean_text(match.group("p2"))
        score = clean_text(match.group("score"))

        parsed = parse_score_sets(score)

        if not parsed:
            continue

        if parsed["status"] == "VOID":
            winner = None
            status = "VOID"

        elif parsed["winner_side"] == "player1":
            winner = p1
            status = "FINISHED"

        else:
            winner = p2
            status = "FINISHED"

        result = {
            "player1": p1,
            "player2": p2,
            "match": f"{p1} vs {p2}",
            "winner": winner,
            "score": score,
            "status": status,
            "source": "SportScore",
        }

        results.append(result)

        if len(_DEBUG["examples_results"]) < 30:
            _DEBUG["examples_results"].append(result)

    # Pattern fallback:
    # Player One Player Two 6-4 6-4
    # Bez "vs" je menej spoľahlivý, preto ho zatiaľ nepoužívame na WON/LOST.

    _DEBUG["finished_results_found"] = len(results)

    return results


def match_pick_to_result(pick, result):
    pick_match = pick.get("match") or ""

    pick_player = pick.get("pick") or ""
    opponent = pick.get("opponent") or ""

    r1 = result.get("player1") or ""
    r2 = result.get("player2") or ""

    direct = (
        names_match(pick_player, r1)
        and names_match(opponent, r2)
    )

    reversed_match = (
        names_match(pick_player, r2)
        and names_match(opponent, r1)
    )

    if direct or reversed_match:
        return True

    # fallback cez match string
    return (
        names_match(pick_player, r1)
        and names_match(opponent, r2)
    ) or (
        names_match(pick_player, r2)
        and names_match(opponent, r1)
    ) or (
        normalize(pick_player) in normalize(pick_match)
        and normalize(opponent) in normalize(pick_match)
        and (
            normalize(r1) in normalize(pick_match)
            or normalize(r2) in normalize(pick_match)
        )
    )


def find_matching_result(pick, results):
    for result in results:
        if match_pick_to_result(
            pick,
            result,
        ):
            return result

    return None


def calculate_units(status, odds):
    odds_value = safe_float(odds)

    if status == "WON":
        if odds_value is None:
            return 0.0

        return round(
            odds_value - 1.0,
            2,
        )

    if status == "LOST":
        return -1.0

    return 0.0


def evaluate_pick(pick, results):
    result = find_matching_result(
        pick,
        results,
    )

    if not result:
        updated = dict(pick)

        if updated.get("result_status") in ["WON", "LOST", "VOID"]:
            return updated

        updated["result_status"] = "PENDING"
        updated["units"] = 0.0

        if len(_DEBUG["examples_unresolved"]) < 30:
            _DEBUG["examples_unresolved"].append({
                "match": pick.get("match"),
                "pick": pick.get("pick"),
                "reason": "no_matching_finished_result",
            })

        return updated

    updated = dict(pick)

    if result.get("status") == "VOID":
        status = "VOID"

    else:
        winner = result.get("winner")

        if winner and names_match(
            pick.get("pick"),
            winner,
        ):
            status = "WON"

        elif winner:
            status = "LOST"

        else:
            status = "UNKNOWN"

    updated["result_status"] = status
    updated["winner"] = result.get("winner")
    updated["score"] = result.get("score")
    updated["units"] = calculate_units(
        status,
        updated.get("odds"),
    )
    updated["resolved_at"] = datetime.now(
        timezone.utc,
    ).isoformat()
    updated["result_source"] = result.get("source")
    updated["result_match_score"] = result.get("match")

    if len(_DEBUG["examples_resolved"]) < 30:
        _DEBUG["examples_resolved"].append({
            "match": updated.get("match"),
            "pick": updated.get("pick"),
            "status": status,
            "winner": updated.get("winner"),
            "score": updated.get("score"),
            "units": updated.get("units"),
        })

    return updated


def summarize(items):
    summary = {
        "picks": len(items),
        "won": 0,
        "lost": 0,
        "void": 0,
        "pending": 0,
        "unknown": 0,
        "units": 0.0,
    }

    for item in items:
        status = str(
            item.get("result_status") or "PENDING"
        ).upper()

        if status == "WON":
            summary["won"] += 1

        elif status == "LOST":
            summary["lost"] += 1

        elif status == "VOID":
            summary["void"] += 1

        elif status == "UNKNOWN":
            summary["unknown"] += 1

        else:
            summary["pending"] += 1

        summary["units"] += safe_float(
            item.get("units")
        ) or 0.0

    summary["units"] = round(
        summary["units"],
        2,
    )

    settled = (
        summary["won"]
        + summary["lost"]
    )

    if settled > 0:
        summary["win_rate"] = round(
            summary["won"] / settled,
            3,
        )

    else:
        summary["win_rate"] = None

    return summary


def filter_by_days(items, days):
    cutoff = datetime.now(
        timezone.utc,
    ).date() - timedelta(days=days - 1)

    output = []

    for item in items:
        date_text = item.get("date")

        try:
            item_date = datetime.strptime(
                date_text,
                "%Y-%m-%d",
            ).date()

        except Exception:
            continue

        if item_date >= cutoff:
            output.append(item)

    return output


def filter_current_month(items):
    now = datetime.now(
        timezone.utc,
    )

    output = []

    for item in items:
        date_text = item.get("date")

        try:
            item_date = datetime.strptime(
                date_text,
                "%Y-%m-%d",
            )

        except Exception:
            continue

        if (
            item_date.year == now.year
            and item_date.month == now.month
        ):
            output.append(item)

    return output


def build_results_payload(evaluated_items):
    today = datetime.now(
        timezone.utc,
    ).strftime("%Y-%m-%d")

    today_items = [
        item
        for item in evaluated_items
        if item.get("date") == today
    ]

    last_7_items = filter_by_days(
        evaluated_items,
        7,
    )

    month_items = filter_current_month(
        evaluated_items,
    )

    payload = {
        "generated_at": datetime.now(
            timezone.utc,
        ).isoformat(),

        "today": summarize(today_items),
        "last_7_days": summarize(last_7_items),
        "current_month": summarize(month_items),
        "all_time": summarize(evaluated_items),

        "items": sorted(
            evaluated_items,
            key=lambda item: (
                item.get("date") or "",
                item.get("rank") or 9999,
                item.get("match") or "",
            ),
            reverse=True,
        ),
    }

    return payload


def fetch_sportscore_text():
    response = requests.get(
        SPORTSCORE_URL,
        headers=HEADERS,
        timeout=30,
    )

    _DEBUG["http_status"] = response.status_code

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    return soup.get_text(
        " ",
        strip=True,
    )


def run():
    ensure_dirs()

    try:
        history_items = load_all_history_items()

        text = fetch_sportscore_text()

        finished_results = extract_finished_results(
            text,
        )

        evaluated = []

        for item in history_items:
            evaluated.append(
                evaluate_pick(
                    item,
                    finished_results,
                )
            )

        _DEBUG["resolved_count"] = sum(
            1
            for item in evaluated
            if item.get("result_status") in ["WON", "LOST", "VOID"]
        )

        _DEBUG["pending_count"] = sum(
            1
            for item in evaluated
            if item.get("result_status") == "PENDING"
        )

        _DEBUG["unknown_count"] = sum(
            1
            for item in evaluated
            if item.get("result_status") == "UNKNOWN"
        )

        payload = build_results_payload(
            evaluated,
        )

        save_json(
            RESULTS_DATA_PATH,
            payload,
        )

        save_json(
            PUBLIC_RESULTS_DATA_PATH,
            payload,
        )

        save_json(
            RESULTS_DEBUG_PATH,
            _DEBUG,
        )

        print(
            "RESULTS CHECKER DONE:",
            "items",
            len(evaluated),
            "finished_results",
            len(finished_results),
        )

        return payload

    except Exception as exc:
        _DEBUG["fetch_error"] = str(exc)

        save_json(
            RESULTS_DEBUG_PATH,
            _DEBUG,
        )

        print(
            "RESULTS CHECKER ERROR:",
            str(exc),
        )

        fallback = {
            "generated_at": datetime.now(
                timezone.utc,
            ).isoformat(),
            "today": summarize([]),
            "last_7_days": summarize([]),
            "current_month": summarize([]),
            "all_time": summarize([]),
            "items": [],
            "error": str(exc),
        }

        save_json(
            RESULTS_DATA_PATH,
            fallback,
        )

        save_json(
            PUBLIC_RESULTS_DATA_PATH,
            fallback,
        )

        return fallback


if __name__ == "__main__":
    run()
