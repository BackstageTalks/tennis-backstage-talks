import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    from results_fetcher import fetch_finished_results as _external_fetch_finished_results
except Exception:
    _external_fetch_finished_results = None


BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

ALL_PICK_HISTORY_DIR = "data/pick_history/all"
TOP5_PICK_HISTORY_DIR = "data/pick_history/top5"
LEGACY_PLAY_HISTORY_DIR = "data/play_history"

RESULTS_DIR = "data/results"
ALL_RESULTS_PATH = "data/results/all_results.json"
TOP5_RESULTS_PATH = "data/results/top5_results.json"
PUBLIC_RESULTS_DATA_PATH = "public/results_data.json"
RESULTS_DEBUG_PATH = "public/results_debug.json"

FINISHED_STATUSES = {
    "FINISHED",
    "COMPLETED",
    "ENDED",
    "END",
    "FT",
    "AFTER_EXTRA_TIME",
}

VOID_STATUSES = {
    "VOID",
    "CANCELLED",
    "CANCELED",
    "POSTPONED",
    "WALKOVER",
    "W/O",
    "WO",
    "RETIRED",
    "RETIREMENT",
    "ABANDONED",
    "WITHDRAWN",
    "WITHDRAWAL",
    "DEFAULT",
    "NOT_PLAYED",
    "NOT PLAYED",
}

PENDING_STATUSES = {
    "SCHEDULED",
    "NOT_STARTED",
    "NOT STARTED",
    "DELAYED",
    "SUSPENDED",
    "INTERRUPTED",
    "LIVE",
    "IN_PROGRESS",
    "IN PROGRESS",
    "ONGOING",
    "PAUSED",
    "UNKNOWN",
    "",
}

_DEBUG = {
    "provider": "results_fetcher",
    "fetch_error": None,
    "fetch_debug": {},
    "datasets": {
        "all": {"history_files": [], "history_items_loaded": 0, "resolved_count": 0, "pending_count": 0, "unknown_count": 0},
        "top5": {"history_files": [], "history_items_loaded": 0, "resolved_count": 0, "pending_count": 0, "unknown_count": 0},
    },
    "finished_results_found": 0,
    "examples_results": [],
    "examples_resolved": [],
    "examples_unresolved": [],
    "examples_date_rejected": [],
    "examples_pending_matched": [],
    "examples_void": [],
}


def ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(ALL_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs(TOP5_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs(LEGACY_PLAY_HISTORY_DIR, exist_ok=True)
    os.makedirs("public", exist_ok=True)


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def betting_day(date_time=None):
    if date_time is None:
        date_time = datetime.now(BRATISLAVA_TZ)
    if isinstance(date_time, str):
        try:
            date_time = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
        except Exception:
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
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        print("RESULTS CHECKER JSON LOAD ERROR:", path, str(exc))
        return default


def snapshot_items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["items", "picks", "matches", "results"]:
            items = data.get(key)
            if isinstance(items, list):
                return items
    return []


def normalize(value):
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = text.replace("-", " ").replace(".", " ").replace(",", " ")
    text = text.replace("'", "").replace("’", "").replace("`", "")
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
        first = parts[0]
        last = parts[-1]
        if first and last:
            keys.add(f"{first[0]} {last}")
            keys.add(f"{last} {first[0]}")
    return keys


def names_match(a, b):
    a_keys = loose_name_keys(a)
    b_keys = loose_name_keys(b)
    if not a_keys or not b_keys:
        return False
    return bool(a_keys.intersection(b_keys))


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None
        return float(value)
    except Exception:
        return None


def parse_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def ids_match(pick, result):
    pick_id = pick.get("match_id") or pick.get("event_id") or pick.get("id")
    result_id = result.get("match_id") or result.get("event_id") or result.get("id")
    if pick_id and result_id and str(pick_id) == str(result_id):
        return True
    return False


def dates_compatible(pick, result):
    pick_date = pick.get("date")
    result_date = result.get("date")

    # Safety guard: do not name-match if either side has no date.
    # Better to keep a pick PENDING than to attach a wrong result from another day.
    if not pick_date or not result_date:
        return False

    return str(pick_date) == str(result_date)


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
        for item in snapshot_items(data):
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
        return load_history_items("all", LEGACY_PLAY_HISTORY_DIR)
    if dataset == "top5":
        return load_history_items("top5", TOP5_PICK_HISTORY_DIR)
    return []


def item_key(item):
    return "|".join([
        str(item.get("date") or ""),
        normalize(item.get("match") or ""),
        normalize(item.get("pick") or ""),
        normalize(item.get("opponent") or ""),
    ])


def load_previous_items(dataset):
    path = TOP5_RESULTS_PATH if dataset == "top5" else ALL_RESULTS_PATH
    data = load_json(path, {})
    items = snapshot_items(data)
    return {item_key(item): item for item in items if isinstance(item, dict)}


def parse_score_sets(score):
    if not score:
        return []
    sets = []
    for part in str(score).replace(",", " ").split():
        match = re.match(r"^(\d+)\s*-\s*(\d+)", part)
        if not match:
            continue
        try:
            sets.append((int(match.group(1)), int(match.group(2))))
        except Exception:
            pass
    return sets


def is_completed_set(a, b):
    high = max(a, b)
    low = min(a, b)
    if high >= 6 and high - low >= 2:
        return True
    if high == 7 and low in [5, 6]:
        return True
    return False


def completed_match_winner_from_score(score, best_of=None):
    sets = parse_score_sets(score)
    if not sets:
        return None
    p1_sets = 0
    p2_sets = 0
    for a, b in sets:
        if not is_completed_set(a, b):
            continue
        if a > b:
            p1_sets += 1
        elif b > a:
            p2_sets += 1
    try:
        best_of_int = int(best_of) if best_of else None
    except Exception:
        best_of_int = None
    sets_needed = 3 if best_of_int == 5 else 2
    if p1_sets >= sets_needed:
        return "player1"
    if p2_sets >= sets_needed:
        return "player2"
    return None


def score_is_incomplete_text(score, best_of=None):
    if not score:
        return False
    return completed_match_winner_from_score(score, best_of=best_of) is None


def raw_status_blob(result):
    raw = result.get("raw") if isinstance(result.get("raw"), dict) else result
    values = []
    for source in [result, raw]:
        if not isinstance(source, dict):
            continue
        for key in [
            "status", "result_status", "status_type", "match_status", "event_status",
            "reason", "winner_type", "result_type", "type", "note", "description", "raw_status"
        ]:
            if source.get(key) is not None:
                values.append(str(source.get(key)))
    return " | ".join(values).upper()


def has_void_keyword(value):
    text = str(value or "").upper()
    return any(keyword in text for keyword in [
        "VOID", "RETIRED", "RETIREMENT", "RET", "WALKOVER", "W/O", "WO",
        "WITHDRAWN", "WITHDRAWAL", "ABANDONED", "CANCELLED", "CANCELED",
        "DEFAULT", "NOT_PLAYED", "NOT PLAYED"
    ])


def status_contains_any(raw_status, candidates):
    text = str(raw_status or "").upper().strip()
    if text in candidates:
        return True
    return any(candidate and candidate in text for candidate in candidates)


def score_looks_incomplete_for_resolved_result(result):
    winner = result.get("winner")
    score = result.get("score")
    if not winner or not score:
        return False
    raw = result.get("raw") if isinstance(result.get("raw"), dict) else {}
    best_of = result.get("best_of") or raw.get("best_of")
    return score_is_incomplete_text(score, best_of=best_of)


def is_void_match(result):
    if not isinstance(result, dict):
        return False
    if has_void_keyword(raw_status_blob(result)):
        return True
    if has_void_keyword(result.get("score")):
        return True
    if score_looks_incomplete_for_resolved_result(result):
        return True
    return False


def void_reason(result):
    if has_void_keyword(raw_status_blob(result)):
        return f"api_status:{raw_status_blob(result)}"
    score = result.get("score")
    if has_void_keyword(score):
        return f"score_text:{score}"
    if score_looks_incomplete_for_resolved_result(result):
        return f"incomplete_score_with_winner:{score}"
    return "void"


def coerce_void_after_evaluation(item):
    if not isinstance(item, dict):
        return item
    status = str(item.get("result_status") or "").upper()
    if status not in ["WON", "LOST"]:
        return item
    if item.get("winner") and item.get("score") and score_is_incomplete_text(item.get("score"), best_of=item.get("best_of")):
        updated = dict(item)
        updated["result_status"] = "VOID"
        updated["units"] = 0.0
        updated["result_void_reason"] = f"incomplete_score_with_winner:{item.get('score')}"
        updated["resolved_at"] = now_utc_iso()
        if len(_DEBUG.get("examples_void", [])) < 30:
            _DEBUG.setdefault("examples_void", []).append({
                "dataset": updated.get("dataset"),
                "date": updated.get("date"),
                "match": updated.get("match"),
                "pick": updated.get("pick"),
                "score": updated.get("score"),
                "winner": updated.get("winner"),
                "reason": updated.get("result_void_reason"),
            })
        return updated
    return item


def merge_previous_status(pick, previous_by_key):
    previous = previous_by_key.get(item_key(pick))
    if not previous:
        return pick

    previous_status = str(previous.get("result_status") or "").upper()
    if previous_status not in ["WON", "LOST", "VOID", "UNKNOWN"]:
        return pick

    def clear_previous_result_fields(source):
        merged = dict(source)
        for key in [
            "result_status", "winner", "score", "units", "resolved_at", "result_source",
            "result_match_score", "result_date", "result_void_reason", "result_raw_status"
        ]:
            merged.pop(key, None)
        return merged

    # Always recalc today's card and any old WON/LOST with incomplete score.
    if str(pick.get("date") or "") == betting_day():
        return clear_previous_result_fields(pick)

    previous_score = previous.get("score") or pick.get("score")
    previous_winner = previous.get("winner") or pick.get("winner")
    previous_best_of = previous.get("best_of") or pick.get("best_of")
    if previous_status in ["WON", "LOST"] and previous_winner and previous_score and score_is_incomplete_text(previous_score, best_of=previous_best_of):
        return clear_previous_result_fields(pick)

    # Recheck recent resolved items because API statuses can mature from winner-only to retired/void info.
    try:
        pick_date = parse_date(pick.get("date"))
        today_date = parse_date(betting_day())
        recheck_days = int(os.getenv("RESULTS_RECHECK_DAYS", "14"))
        if pick_date and today_date and (today_date - pick_date).days <= recheck_days and previous_status in ["WON", "LOST", "UNKNOWN"]:
            return clear_previous_result_fields(pick)
    except Exception:
        pass

    merged = dict(pick)
    for key in [
        "result_status", "winner", "score", "units", "resolved_at", "result_source",
        "result_match_score", "result_date", "result_void_reason", "result_raw_status"
    ]:
        if key in previous:
            merged[key] = previous.get(key)
    return merged


def result_score(result):
    if result.get("score"):
        return result.get("score")
    h = result.get("home_score_current")
    a = result.get("away_score_current")
    if h is not None and a is not None:
        return f"{h}-{a}"
    return None


def normalize_finished_result(result):
    if not isinstance(result, dict):
        return None

    player1 = result.get("player1") or result.get("home") or result.get("homeTeam") or result.get("home_player")
    player2 = result.get("player2") or result.get("away") or result.get("awayTeam") or result.get("away_player")
    winner = result.get("winner") or result.get("winner_name")

    raw_status = str(
        result.get("status")
        or result.get("result_status")
        or result.get("match_status")
        or result.get("event_status")
        or ""
    ).upper().strip()

    raw_blob = raw_status_blob(result)

    if has_void_keyword(raw_blob) or status_contains_any(raw_status, VOID_STATUSES):
        normalized_status = "VOID"
    elif status_contains_any(raw_status, FINISHED_STATUSES):
        normalized_status = "FINISHED"
    else:
        # Critical fix: unknown, scheduled, delayed, live, suspended, or missing statuses are PENDING.
        # Never treat an unrecognized status as FINISHED.
        normalized_status = "PENDING"

    if not player1 or not player2:
        return None

    score = result_score(result)

    return {
        "match_id": result.get("match_id"),
        "event_id": result.get("event_id") or result.get("match_id"),
        "date": result.get("date"),
        "player1": player1,
        "player2": player2,
        "winner": winner,
        "score": score,
        "status": normalized_status,
        "source": result.get("source") or result.get("result_source") or "results_fetcher",
        "match": result.get("match") or f"{player1} vs {player2}",
        "raw": result,
        "raw_status": raw_status,
    }


def fetch_finished_results_safe():
    if _external_fetch_finished_results is None:
        _DEBUG["fetch_error"] = "results_fetcher.fetch_finished_results is not available"
        return []
    try:
        raw_results = _external_fetch_finished_results()
        if raw_results is None:
            raw_results = []
        normalized = []
        for result in raw_results:
            item = normalize_finished_result(result)
            if item:
                normalized.append(item)
        _DEBUG["finished_results_found"] = len(normalized)
        _DEBUG["examples_results"] = normalized[:10]
        return normalized
    except Exception as exc:
        _DEBUG["fetch_error"] = str(exc)
        print("RESULTS CHECKER FETCH ERROR:", str(exc))
        return []


def match_pick_to_result(pick, result):
    # Strong match: same TennisApi event id.
    if ids_match(pick, result):
        return True

    # Safety guard: never match same player names across different dates.
    if not dates_compatible(pick, result):
        if len(_DEBUG["examples_date_rejected"]) < 30:
            _DEBUG["examples_date_rejected"].append({
                "pick_date": pick.get("date"),
                "result_date": result.get("date"),
                "pick": pick.get("pick"),
                "match": pick.get("match"),
                "result_match": result.get("match"),
                "result_status": result.get("status"),
            })
        return False

    pick_match = pick.get("match") or ""
    pick_player = pick.get("pick") or ""
    opponent = pick.get("opponent") or ""
    r1 = result.get("player1") or ""
    r2 = result.get("player2") or ""

    direct = names_match(pick_player, r1) and names_match(opponent, r2)
    reversed_match = names_match(pick_player, r2) and names_match(opponent, r1)

    if direct or reversed_match:
        return True

    normalized_pick_match = normalize(pick_match)
    return (
        normalize(pick_player) in normalized_pick_match
        and normalize(opponent) in normalized_pick_match
        and (normalize(r1) in normalized_pick_match or normalize(r2) in normalized_pick_match)
    )


def find_matching_result(pick, results):
    # Prefer exact id matches first.
    for result in results:
        if ids_match(pick, result):
            return result

    # Then date-safe name matching.
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
        if odds_value is None:
            return 0.0
        return -1.0
    return 0.0


def evaluate_pick(pick, results, dataset):
    result = find_matching_result(pick, results)
    if not result:
        updated = dict(pick)
        existing_status = str(updated.get("result_status") or "PENDING").upper()
        if existing_status in ["WON", "LOST", "VOID"] and str(updated.get("date") or "") != betting_day():
            updated["dataset"] = dataset
            return coerce_void_after_evaluation(updated)
        updated["dataset"] = dataset
        updated["result_status"] = "PENDING"
        updated["units"] = 0.0
        updated.pop("winner", None)
        updated.pop("score", None)
        if len(_DEBUG["examples_unresolved"]) < 30:
            _DEBUG["examples_unresolved"].append({
                "dataset": dataset,
                "date": pick.get("date"),
                "match": pick.get("match"),
                "pick": pick.get("pick"),
                "reason": "no_date_safe_matching_finished_result",
            })
        return updated

    updated = dict(pick)
    result_status = str(result.get("status") or "PENDING").upper()

    if result_status == "VOID" or is_void_match(result):
        status = "VOID"
    elif result_status != "FINISHED":
        status = "PENDING"
    else:
        winner = result.get("winner")
        score = result.get("score")

        # Critical fix: no final score means no settlement.
        # Some APIs can expose/guess winner-like fields before the match is truly finished.
        if not winner or not score:
            status = "PENDING"
        elif score_is_incomplete_text(score, best_of=updated.get("best_of")):
            status = "PENDING"
        elif names_match(pick.get("pick"), winner):
            status = "WON"
        else:
            status = "LOST"

    updated["dataset"] = dataset
    updated["result_status"] = status
    updated["units"] = calculate_units(status, updated.get("odds"))
    updated["result_source"] = result.get("source")
    updated["result_match_score"] = result.get("match")
    updated["result_date"] = result.get("date")
    updated["result_raw_status"] = result.get("raw_status") or raw_status_blob(result)

    if status in ["WON", "LOST", "VOID"]:
        updated["winner"] = result.get("winner")
        updated["score"] = result.get("score")
        updated["resolved_at"] = now_utc_iso()
        if status == "VOID":
            updated["result_void_reason"] = void_reason(result)
    else:
        updated["winner"] = result.get("winner")
        updated["score"] = result.get("score")
        updated["resolved_at"] = None
        if len(_DEBUG["examples_pending_matched"]) < 30:
            _DEBUG["examples_pending_matched"].append({
                "dataset": dataset,
                "date": updated.get("date"),
                "match": updated.get("match"),
                "pick": updated.get("pick"),
                "result_status": result_status,
                "winner": result.get("winner"),
                "score": result.get("score"),
                "raw_status": updated.get("result_raw_status"),
            })

    if len(_DEBUG["examples_resolved"]) < 30 and status in ["WON", "LOST", "VOID", "UNKNOWN"]:
        _DEBUG["examples_resolved"].append({
            "dataset": dataset,
            "date": updated.get("date"),
            "match": updated.get("match"),
            "pick": updated.get("pick"),
            "status": status,
            "winner": updated.get("winner"),
            "score": updated.get("score"),
            "units": updated.get("units"),
            "result_date": result.get("date"),
            "raw_status": updated.get("result_raw_status"),
        })
    return updated


def summarize(items):
    summary = {"picks": len(items), "won": 0, "lost": 0, "void": 0, "pending": 0, "unknown": 0, "units": 0.0}
    for item in items:
        status = str(item.get("result_status") or "PENDING").upper()
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
    summary["win_rate"] = round(summary["won"] / settled, 3) if settled > 0 else None
    return summary


def filter_by_days(items, days):
    today_date = parse_date(betting_day()) or datetime.now(timezone.utc).date()
    cutoff = today_date - timedelta(days=days - 1)
    output = []
    for item in items:
        item_date = parse_date(item.get("date"))
        if item_date and item_date >= cutoff:
            output.append(item)
    return output


def filter_current_month(items):
    today_date = parse_date(betting_day()) or datetime.now(timezone.utc).date()
    output = []
    for item in items:
        item_date = parse_date(item.get("date"))
        if item_date and item_date.year == today_date.year and item_date.month == today_date.month:
            output.append(item)
    return output


def sort_items(items):
    return sorted(items, key=lambda item: (item.get("date") or "", -(item.get("rank") or 9999), item.get("match") or ""), reverse=True)


def build_dataset_payload(dataset, evaluated_items):
    today = betting_day()
    sorted_all = sort_items(evaluated_items)
    today_items = [item for item in evaluated_items if item.get("date") == today]
    last_7_items = filter_by_days(evaluated_items, 7)
    month_items = filter_current_month(evaluated_items)
    return {
        "dataset": dataset,
        "updated_at": now_utc_iso(),
        "betting_day": today,
        "summary": summarize(evaluated_items),
        "cards": {
            "today": summarize(today_items),
            "last_7_days": summarize(last_7_items),
            "current_month": summarize(month_items),
            "all_time": summarize(evaluated_items),
        },
        "today": summarize(today_items),
        "last_7_days": summarize(last_7_items),
        "current_month": summarize(month_items),
        "all_time": summarize(evaluated_items),
        "items": sorted_all,
        "results": sorted_all,
    }


def evaluate_dataset(dataset, finished_results):
    history_items = load_dataset_history(dataset)
    previous_by_key = load_previous_items(dataset)
    prepared_items = [merge_previous_status(item, previous_by_key) for item in history_items]
    evaluated_items = [evaluate_pick(item, finished_results, dataset) for item in prepared_items]
    evaluated_items = [coerce_void_after_evaluation(item) for item in evaluated_items]

    resolved = 0
    pending = 0
    unknown = 0
    for item in evaluated_items:
        status = str(item.get("result_status") or "PENDING").upper()
        if status in ["WON", "LOST", "VOID"]:
            resolved += 1
        elif status == "UNKNOWN":
            unknown += 1
        else:
            pending += 1
    _DEBUG["datasets"][dataset]["resolved_count"] = resolved
    _DEBUG["datasets"][dataset]["pending_count"] = pending
    _DEBUG["datasets"][dataset]["unknown_count"] = unknown
    return build_dataset_payload(dataset, evaluated_items)


def main():
    ensure_dirs()
    finished_results = fetch_finished_results_safe()
    all_payload = evaluate_dataset("all", finished_results)
    top5_payload = evaluate_dataset("top5", finished_results)
    combined_public_payload = {
        "updated_at": now_utc_iso(),
        "betting_day": betting_day(),
        "all": all_payload,
        "top5": top5_payload,
        "datasets": {"all": all_payload, "top5": top5_payload},
    }
    save_json(ALL_RESULTS_PATH, all_payload)
    save_json(TOP5_RESULTS_PATH, top5_payload)
    save_json(PUBLIC_RESULTS_DATA_PATH, combined_public_payload)
    save_json(RESULTS_DEBUG_PATH, _DEBUG)
    print("Results checker completed")
    print("ALL picks:", all_payload["summary"]["picks"])
    print("TOP5 picks:", top5_payload["summary"]["picks"])
    print("Finished results found:", len(finished_results))
    if _DEBUG.get("fetch_error"):
        print("Fetch warning:", _DEBUG["fetch_error"])


if __name__ == "__main__":
    main()
