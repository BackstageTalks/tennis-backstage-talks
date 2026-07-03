
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


SOFASCORE_BASE_URL = "https://api.sofascore.com/api/v1"
SOFASCORE_TENNIS_EVENTS_URL = SOFASCORE_BASE_URL + "/sport/tennis/scheduled-events/{date}"

SPORTSCORE_URL = "https://sportscore.com/tennis/"

BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT_SECONDS = 30
TARGET_CONTEXT_CHARS = 180


DEBUG_TEMPLATE = {
    "generated_at": None,
    "primary_source": "SofaScore",
    "fallback_source": "SportScore",
    "sofascore": {
        "enabled": True,
        "dates_requested": [],
        "http_statuses": {},
        "fetch_errors": {},
        "events_loaded": 0,
        "finished_events": 0,
        "examples": [],
    },
    "sportscore": {
        "enabled": True,
        "http_status": None,
        "fetch_error": None,
        "generic_results_found": 0,
        "targeted_results_found": 0,
        "examples_generic_results": [],
        "examples_targeted_results": [],
        "examples_targeted_contexts": [],
    },
    "combined_results_found": 0,
}


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def betting_day(date_time=None):
    if date_time is None:
        date_time = datetime.now(BRATISLAVA_TZ)

    if isinstance(date_time, str):
        try:
            date_time = datetime.fromisoformat(
                date_time.replace("Z", "+00:00")
            )
        except Exception:
            date_time = datetime.now(BRATISLAVA_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=BRATISLAVA_TZ)
    else:
        date_time = date_time.astimezone(BRATISLAVA_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time.strftime("%Y-%m-%d")


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


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


def name_parts(name):
    normalized = normalize(name)

    return [
        part
        for part in normalized.split()
        if part
    ]


def player_variants(name):
    parts = name_parts(name)
    variants = set()

    if not parts:
        return []

    full = " ".join(parts)
    variants.add(full)

    last = parts[-1]
    variants.add(last)

    if len(parts) >= 2:
        first = parts[0]
        first_initial = first[0]
        variants.add(f"{last} {first_initial}")
        variants.add(f"{first_initial} {last}")
        variants.add(" ".join(parts[-2:]))

    return sorted(
        variants,
        key=len,
        reverse=True,
    )


def loose_name_keys(name):
    parts = name_parts(name)
    keys = set()

    if parts:
        keys.add(" ".join(parts))
        keys.add(parts[-1])

    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        keys.add(" ".join(parts[-2:]))
        keys.add(f"{last} {first[0]}")
        keys.add(f"{first[0]} {last}")

    return keys


def names_match(a, b):
    a_keys = loose_name_keys(a)
    b_keys = loose_name_keys(b)

    if not a_keys or not b_keys:
        return False

    if a_keys.intersection(b_keys):
        return True

    a_norm = normalize(a)
    b_norm = normalize(b)

    if not a_norm or not b_norm:
        return False

    return SequenceMatcher(None, a_norm, b_norm).ratio() >= 0.88


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return None


def event_date_candidates_from_picks(picks):
    dates = set()

    for pick in picks or []:
        if not isinstance(pick, dict):
            continue

        date = pick.get("date")

        if date and re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
            dates.add(str(date))

    today = betting_day()
    dates.add(today)

    try:
        today_date = datetime.strptime(today, "%Y-%m-%d").date()
        dates.add((today_date + timedelta(days=1)).strftime("%Y-%m-%d"))
        dates.add((today_date - timedelta(days=1)).strftime("%Y-%m-%d"))
    except Exception:
        pass

    return sorted(dates)


def http_get_json(url, debug, date):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        debug["sofascore"]["http_statuses"][date] = response.status_code
        response.raise_for_status()

        return response.json()

    except Exception as exc:
        debug["sofascore"]["fetch_errors"][date] = str(exc)
        return None


def get_team_name(team):
    if not isinstance(team, dict):
        return None

    return (
        team.get("name")
        or team.get("shortName")
        or team.get("slug")
    )


def get_status_text(event):
    status = event.get("status") or {}

    if not isinstance(status, dict):
        return ""

    return " ".join(
        str(status.get(key) or "")
        for key in ["type", "description"]
    ).lower()


def is_sofascore_finished(event):
    status = event.get("status") or {}

    if isinstance(status, dict):
        status_type = str(status.get("type") or "").lower()
        status_description = str(status.get("description") or "").lower()
        status_code = status.get("code")

        if status_type == "finished":
            return True

        if status_code in [100, 110, 120]:
            return True

        if "finished" in status_description or "ended" in status_description:
            return True

    if event.get("winnerCode") in [1, 2]:
        return True

    return False


def score_value(score_dict, key):
    if not isinstance(score_dict, dict):
        return None

    return safe_int(score_dict.get(key))


def build_set_score_string(home_score, away_score):
    if not isinstance(home_score, dict) or not isinstance(away_score, dict):
        return None

    set_parts = []

    for index in range(1, 6):
        home_value = score_value(home_score, f"period{index}")
        away_value = score_value(away_score, f"period{index}")

        if home_value is None or away_value is None:
            continue

        set_parts.append(f"{home_value}-{away_value}")

    if set_parts:
        return " ".join(set_parts)

    home_current = score_value(home_score, "current")
    away_current = score_value(away_score, "current")

    if home_current is not None and away_current is not None:
        return f"{home_current}-{away_current}"

    return None


def sofa_winner(event, home_name, away_name):
    winner_code = event.get("winnerCode")

    if winner_code == 1:
        return home_name

    if winner_code == 2:
        return away_name

    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}

    home_current = score_value(home_score, "current")
    away_current = score_value(away_score, "current")

    if home_current is None or away_current is None:
        return None

    if home_current > away_current:
        return home_name

    if away_current > home_current:
        return away_name

    return None


def sofa_event_to_result(event, date):
    home_name = get_team_name(event.get("homeTeam"))
    away_name = get_team_name(event.get("awayTeam"))

    if not home_name or not away_name:
        return None

    if not is_sofascore_finished(event):
        return None

    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}
    score = build_set_score_string(home_score, away_score)

    winner = sofa_winner(event, home_name, away_name)

    if not winner:
        return None

    tournament = event.get("tournament") or {}
    unique_tournament = event.get("season") or {}

    tournament_name = None

    if isinstance(tournament, dict):
        tournament_name = tournament.get("name")

    if not tournament_name and isinstance(unique_tournament, dict):
        tournament_name = unique_tournament.get("name")

    return {
        "player1": home_name,
        "player2": away_name,
        "match": f"{home_name} vs {away_name}",
        "winner": winner,
        "score": score or "",
        "status": "FINISHED",
        "source": "SofaScore",
        "method": "sofascore_scheduled_events",
        "event_id": event.get("id"),
        "date": date,
        "tournament": tournament_name,
        "start_timestamp": event.get("startTimestamp"),
    }


def fetch_sofascore_results_for_date(date, debug):
    url = SOFASCORE_TENNIS_EVENTS_URL.format(date=date)

    debug["sofascore"]["dates_requested"].append(date)

    data = http_get_json(url, debug, date)

    if not data:
        return []

    events = data.get("events")

    if not isinstance(events, list):
        return []

    debug["sofascore"]["events_loaded"] += len(events)

    results = []

    for event in events:
        if not isinstance(event, dict):
            continue

        result = sofa_event_to_result(event, date)

        if not result:
            continue

        results.append(result)

        if len(debug["sofascore"]["examples"]) < 30:
            debug["sofascore"]["examples"].append(result)

    debug["sofascore"]["finished_events"] += len(results)

    return results


def fetch_sofascore_results(picks, debug):
    all_results = []

    for date in event_date_candidates_from_picks(picks):
        all_results.extend(
            fetch_sofascore_results_for_date(date, debug)
        )

    return all_results


def parse_score_sets(score_text):
    if not score_text:
        return None

    score_text = clean_text(score_text)
    upper = score_text.upper()

    if any(token in upper for token in ["W/O", "WO", "RET", "ABN", "DEF"]):
        return {
            "status": "VOID",
            "winner_side": None,
            "score": score_text,
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
        a = safe_int(a_text)
        b = safe_int(b_text)

        if a is None or b is None:
            continue

        if a > b:
            p1_sets += 1
        elif b > a:
            p2_sets += 1

    if p1_sets == p2_sets:
        return None

    return {
        "status": "FINISHED",
        "winner_side": "player1" if p1_sets > p2_sets else "player2",
        "score": score_text,
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
    }


def parse_scoreboard_numbers(after_text):
    after_text = clean_text(after_text)
    numbers = re.findall(r"\d{1,3}", after_text)

    if len(numbers) < 2:
        return None

    p1_sets = safe_int(numbers[0])
    p2_sets = safe_int(numbers[1])

    if p1_sets is None or p2_sets is None:
        return None

    if p1_sets == p2_sets:
        return None

    if max(p1_sets, p2_sets) > 3:
        return None

    if min(p1_sets, p2_sets) > 2:
        return None

    if max(p1_sets, p2_sets) < 2:
        return None

    score_preview = " ".join(numbers[:10])

    return {
        "status": "FINISHED",
        "winner_side": "player1" if p1_sets > p2_sets else "player2",
        "score": score_preview,
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
    }


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


def extract_generic_vs_results(text, debug):
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
            "score": parsed.get("score") or score,
            "status": status,
            "source": "SportScore",
            "method": "generic_vs_score",
        }

        results.append(result)

        if len(debug["sportscore"]["examples_generic_results"]) < 30:
            debug["sportscore"]["examples_generic_results"].append(result)

    debug["sportscore"]["generic_results_found"] = len(results)

    return results


def find_variant_positions(text, variants):
    positions = []

    for variant in variants:
        if not variant:
            continue

        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(variant) + r"(?![a-z0-9])")

        for match in pattern.finditer(text):
            positions.append(
                {
                    "variant": variant,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    positions.sort(key=lambda item: item["start"])

    return positions


def build_targeted_result_from_context(pick, text):
    pick_name = pick.get("pick") or ""
    opponent_name = pick.get("opponent") or ""

    if not pick_name or not opponent_name:
        return None

    normalized_text = normalize(text)
    pick_variants = player_variants(pick_name)
    opponent_variants = player_variants(opponent_name)

    pick_positions = find_variant_positions(normalized_text, pick_variants)
    opponent_positions = find_variant_positions(normalized_text, opponent_variants)

    best_candidate = None
    best_distance = None

    for pick_pos in pick_positions:
        for opponent_pos in opponent_positions:
            if pick_pos["start"] == opponent_pos["start"]:
                continue

            left = min(pick_pos, opponent_pos, key=lambda item: item["start"])
            right = max(pick_pos, opponent_pos, key=lambda item: item["start"])
            distance = right["start"] - left["end"]

            if distance < 0 or distance > TARGET_CONTEXT_CHARS:
                continue

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_candidate = {
                    "left": left,
                    "right": right,
                    "pick_first": pick_pos["start"] < opponent_pos["start"],
                }

    if not best_candidate:
        return None

    right = best_candidate["right"]
    after = normalized_text[right["end"]: right["end"] + TARGET_CONTEXT_CHARS]
    parsed = parse_scoreboard_numbers(after)

    if not parsed:
        return None

    pick_first = best_candidate["pick_first"]

    player1 = pick_name if pick_first else opponent_name
    player2 = opponent_name if pick_first else pick_name

    if parsed["status"] == "VOID":
        winner = None
        status = "VOID"
    elif parsed["winner_side"] == "player1":
        winner = player1
        status = "FINISHED"
    else:
        winner = player2
        status = "FINISHED"

    return {
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}",
        "winner": winner,
        "score": parsed.get("score"),
        "status": status,
        "source": "SportScore",
        "method": "targeted_pick_context",
        "context": after[:120],
        "pick_id": pick.get("id"),
        "pick_match": pick.get("match"),
    }


def fetch_sportscore_text(debug):
    try:
        response = requests.get(
            SPORTSCORE_URL,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        debug["sportscore"]["http_status"] = response.status_code
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        return soup.get_text(
            " ",
            strip=True,
        )

    except Exception as exc:
        debug["sportscore"]["fetch_error"] = str(exc)
        return ""


def fetch_sportscore_results(picks, debug):
    text = fetch_sportscore_text(debug)

    if not text:
        return []

    text = finished_text_only(text)
    generic_results = extract_generic_vs_results(text, debug)

    targeted_results = []
    seen = set()

    for pick in picks or []:
        if not isinstance(pick, dict):
            continue

        result = build_targeted_result_from_context(pick, text)

        if not result:
            continue

        key = result_key(result)

        if key in seen:
            continue

        seen.add(key)
        targeted_results.append(result)

        if len(debug["sportscore"]["examples_targeted_results"]) < 30:
            debug["sportscore"]["examples_targeted_results"].append(
                {
                    key: value
                    for key, value in result.items()
                    if key != "context"
                }
            )

        if len(debug["sportscore"]["examples_targeted_contexts"]) < 30:
            debug["sportscore"]["examples_targeted_contexts"].append(
                {
                    "match": result.get("pick_match"),
                    "context": result.get("context"),
                    "winner": result.get("winner"),
                    "score": result.get("score"),
                }
            )

    debug["sportscore"]["targeted_results_found"] = len(targeted_results)

    return targeted_results + generic_results


def result_key(result):
    return "::".join(
        sorted([
            normalize(result.get("player1")),
            normalize(result.get("player2")),
        ])
    )


def combine_results(*result_groups):
    output = []
    seen = set()

    for group in result_groups:
        for result in group or []:
            key = result_key(result)

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)
            output.append(result)

    return output


def fetch_finished_results(picks=None):
    picks = picks or []
    debug = json.loads(json.dumps(DEBUG_TEMPLATE))
    debug["generated_at"] = now_utc_iso()
    debug["picks_received"] = len(picks)

    sofascore_results = fetch_sofascore_results(picks, debug)
    sportscore_results = fetch_sportscore_results(picks, debug)

    combined = combine_results(
        sofascore_results,
        sportscore_results,
    )

    debug["combined_results_found"] = len(combined)

    return combined, debug
