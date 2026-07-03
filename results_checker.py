import json
import os
import re
import requests
import unicodedata
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


SPORTSCORE_URL = "https://sportscore.com/tennis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

ALL_PICK_HISTORY_DIR = "data/pick_history/all"
TOP5_PICK_HISTORY_DIR = "data/pick_history/top5"
LEGACY_PLAY_HISTORY_DIR = "data/play_history"

RESULTS_DIR = "data/results"
ALL_RESULTS_PATH = "data/results/all_results.json"
TOP5_RESULTS_PATH = "data/results/top5_results.json"
PUBLIC_RESULTS_DATA_PATH = "public/results_data.json"
RESULTS_DEBUG_PATH = "public/results_debug.json"


_DEBUG = {
    "provider": "SportScore",
    "url": SPORTSCORE_URL,
    "http_status": None,
    "fetch_error": None,
    "datasets": {
        "all": {
            "history_files": [],
            "history_items_loaded": 0,
            "resolved_count": 0,
            "pending_count": 0,
            "unknown_count": 0,
        },
        "top5": {
            "history_files": [],
            "history_items_loaded": 0,
            "resolved_count": 0,
            "pending_count": 0,
            "unknown_count": 0,
        },
    },
    "finished_results_found": 0,
    "examples_results": [],
    "examples_resolved": [],
    "examples_unresolved": [],
}


def ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(ALL_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs(TOP5_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs("public", exist_ok=True)


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def betting_day(date_time=None):
    if date_time is None:
        date_time = datetime.now(BRATISLAVA_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=BRATISLAVA_TZ)
    else:
        date_time = date_time.astimezone(BRATISLAVA_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time.strftime("%Y-%m-%d")


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
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

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return default


def normalize(value):
    if value is None:
        return ""

    text = str(value)

    text = unicodedata.normalize("NFKD", text)

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

    text = re.sub(r"[^a-z0-9\s]", " ", text)

    return " ".join(text.split())


def loose_name_keys(name):
    normalized = normalize(name)
    parts = normalized.split()

    keys = set()

    if normalized:
        keys.add(normalized)

    if parts:
        keys.add(parts[-1])

    if len(parts) >= 2:
        keys.add(" ".join(parts[-2:]))

    return keys


def names_match(a, b):
    a_keys = loose_name_keys(a)
    b_keys = loose_name_keys(b)

    if not a_keys or not b_keys:
        return False

    return bool(a_keys.intersection(b_keys))


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None

        return float(value)

    except Exception:
        return None


def load_history_items(dataset, directory):
    ensure_dirs()

    items = []
    files = []

    if not os.path.exists(directory):
        return items

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(directory, filename)
        files.append(path)

        data = load_json(path, [])

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    updated = dict(item)
                    updated["dataset"] = dataset
                    items.append(updated)

    _DEBUG["datasets"][dataset]["history_files"] = files
    _DEBUG["datasets"][dataset]["history_items_loaded"] = len(items)

    return items


def load_dataset_history(dataset):
    if dataset == "all":
        items = load_history_items("all", ALL_PICK_HISTORY_DIR)

        if items:
            return items

        legacy_items = load_history_items("all", LEGACY_PLAY_HISTORY_DIR)

        return legacy_items

    if dataset == "top5":
        return load_history_items("top5", TOP5_PICK_HISTORY_DIR)

    return []


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
    text = finished_text_only(text)

    results = []

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

    return (
        normalize(pick_player) in normalize(pick_match)
        and normalize(opponent) in normalize(pick_match)
        and (
            normalize(r1) in normalize(pick_match)
            or normalize(r2) in normalize(pick_match)
        )
    )


def find_matching_result(pick, results):
    for result in results:
        if match_pick_to_result(pick, result):
            return result

    return None


def calculate_units(status, odds):
    odds_value = safe_float(odds)

    if status == "WON":
        if odds_value is None:
            return 0.0

        return round(odds_value - 1.0, 2)

    if status == "LOST":
        return -1.0

    return 0.0


def evaluate_pick(pick, results, dataset):
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
            _DEBUG["examples_unresolved"].append(
                {
                    "dataset": dataset,
                    "match": pick.get("match"),
                    "pick": pick.get("pick"),
                    "reason": "no_matching_finished_result",
                }
            )

        return updated

    updated = dict(pick)

    if result.get("status") == "VOID":
        status = "VOID"

    else:
        winner = result.get("winner")

        if winner and names_match(pick.get("pick"), winner):
            status = "WON"

        elif winner:
            status = "LOST"

        else:
            status = "UNKNOWN"

    updated["dataset"] = dataset
    updated["result_status"] = status
    updated["winner"] = result.get("winner")
    updated["score"] = result.get("score")
    updated["units"] = calculate_units(
        status,
        updated.get("odds"),
    )
    updated["resolved_at"] = now_utc_iso()
    updated["result_source"] = result.get("source")
    updated["result_match_score"] = result.get("match")

    if len(_DEBUG["examples_resolved"]) < 30:
        _DEBUG["examples_resolved"].append(
            {
                "dataset": dataset,
                "match": updated.get("match"),
                "pick": updated.get("pick"),
                "status": status,
                "winner": updated.get("winner"),
                "score": updated.get("score"),
                "units": updated.get("units"),
            }
        )

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

        summary["units"] += safe_float(item.get("units")) or 0.0

    summary["units"] = round(summary["units"], 2)

    settled = summary["won"] + summary["lost"]

    if settled > 0:
        summary["win_rate"] = round(summary["won"] / settled, 3)
    else:
        summary["win_rate"] = None

    return summary


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def filter_by_days(items, days):
    today_date = parse_date(betting_day())

    if today_date is None:
        today_date = datetime.now(timezone.utc).date()

    cutoff = today_date - timedelta(days=days - 1)

    output = []

    for item in items:
        item_date = parse_date(item.get("date"))

        if item_date and item_date >= cutoff:
            output.append(item)

    return output


def filter_current_month(items):
    today_date = parse_date(betting_day())

    if today_date is None:
        today_date = datetime.now(timezone.utc).date()

    output = []

    for item in items:
        item_date = parse_date(item.get("date"))

        if (
            item_date
            and item_date.year == today_date.year
            and item_date.month == today_date.month
        ):
            output.append(item)

    return output


def sort_items(items):
    return sorted(
        items,
        key=lambda item: (
            item.get("date") or "",
            item.get("rank") or 9999,
            item.get("match") or "",
        ),
        reverse=True,
    )


def build_dataset_payload(dataset, evaluated_items):
    today = betting_day()

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

    return {
        "dataset": dataset,
        "generated_at": now_utc_iso(),
        "today": summarize(today_items),
        "last_7_days": summarize(last_7_items),
        "current_month": summarize(month_items),
        "all_time": summarize(evaluated_items),
        "items": sort_items(evaluated_items),
    }


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


def evaluate_dataset(dataset, finished_results):
    history_items = load_dataset_history(dataset)

    evaluated = []

    for item in history_items:
        evaluated.append(
            evaluate_pick(
                pick=item,
                results=finished_results,
                dataset=dataset,
            )
        )

    _DEBUG["datasets"][dataset]["resolved_count"] = sum(
        1
        for item in evaluated
        if item.get("result_status") in ["WON", "LOST", "VOID"]
    )

    _DEBUG["datasets"][dataset]["pending_count"] = sum(
        1
        for item in evaluated
        if item.get("result_status") == "PENDING"
    )

    _DEBUG["datasets"][dataset]["unknown_count"] = sum(
        1
        for item in evaluated
        if item.get("result_status") == "UNKNOWN"
    )

    return build_dataset_payload(
        dataset=dataset,
        evaluated_items=evaluated,
    )


def empty_dataset_payload(dataset, error=None):
    payload = {
        "dataset": dataset,
        "generated_at": now_utc_iso(),
        "today": summarize([]),
        "last_7_days": summarize([]),
        "current_month": summarize([]),
        "all_time": summarize([]),
        "items": [],
    }

    if error:
        payload["error"] = error

    return payload


def build_public_payload(top5_payload, all_payload, error=None):
    payload = {
        "generated_at": now_utc_iso(),
        "betting_day": betting_day(),
        "top5": top5_payload,
        "all": all_payload,
    }

    if error:
        payload["error"] = error

    return payload


def run():
    ensure_dirs()

    try:
        text = fetch_sportscore_text()

        finished_results = extract_finished_results(
            text,
        )

        top5_payload = evaluate_dataset(
            "top5",
            finished_results,
        )

        all_payload = evaluate_dataset(
            "all",
            finished_results,
        )

        public_payload = build_public_payload(
            top5_payload=top5_payload,
            all_payload=all_payload,
        )

        save_json(
            TOP5_RESULTS_PATH,
            top5_payload,
        )

        save_json(
            ALL_RESULTS_PATH,
            all_payload,
        )

        save_json(
            PUBLIC_RESULTS_DATA_PATH,
            public_payload,
        )

        save_json(
            RESULTS_DEBUG_PATH,
            _DEBUG,
        )

        print(
            "RESULTS CHECKER DONE:",
            "top5_items",
            len(top5_payload.get("items", [])),
            "all_items",
            len(all_payload.get("items", [])),
            "finished_results",
            len(finished_results),
        )

        return public_payload

    except Exception as exc:
        error_text = str(exc)

        _DEBUG["fetch_error"] = error_text

        top5_payload = empty_dataset_payload(
            "top5",
            error=error_text,
        )

        all_payload = empty_dataset_payload(
            "all",
            error=error_text,
        )

        public_payload = build_public_payload(
            top5_payload=top5_payload,
            all_payload=all_payload,
            error=error_text,
        )

        save_json(
            TOP5_RESULTS_PATH,
            top5_payload,
        )

        save_json(
            ALL_RESULTS_PATH,
            all_payload,
        )

        save_json(
            PUBLIC_RESULTS_DATA_PATH,
            public_payload,
        )

        save_json(
            RESULTS_DEBUG_PATH,
            _DEBUG,
        )

        print(
            "RESULTS CHECKER ERROR:",
            error_text,
        )

        return public_payload


if __name__ == "__main__":
    run()
