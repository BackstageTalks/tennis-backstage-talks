import re
import unicodedata
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


SPORTSCORE_URL = "https://sportscore.com/tennis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


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

    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]

        if first and last:
            keys.add(
                f"{first[0]} {last}"
            )
            keys.add(
                f"{last} {first[0]}"
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


def fetch_sportscore_text():
    response = requests.get(
        SPORTSCORE_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    return soup.get_text(
        " ",
        strip=True,
    )


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
        index = lower.find(marker)

        if index != -1:
            start_index = index
            break

    if start_index == -1:
        return text

    return text[start_index:]


def parse_score_sets(score_text):
    if not score_text:
        return None

    score_text = clean_text(score_text)
    upper = score_text.upper()

    if any(
        token in upper
        for token in ["W/O", "WO", "RET", "ABN", "DEF"]
    ):
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

    winner_side = (
        "player1"
        if p1_sets > p2_sets
        else "player2"
    )

    return {
        "status": "FINISHED",
        "winner_side": winner_side,
        "score": score_text,
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
    }


def extract_generic_vs_results(text):
    text = finished_text_only(text)

    results = []

    pattern = re.compile(
        r"(?P<p1>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+vs\s+"
        r"(?P<p2>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+(?P<score>(?:\d{1,2}-\d{1,2}(?:\(\d+\))?\s*){2,5}|W/O|WO|RET|DEF|ABN)",
        re.IGNORECASE,
    )

    for match in pattern.finditer(text):
        p1 = clean_text(
            match.group("p1")
        )
        p2 = clean_text(
            match.group("p2")
        )
        score = clean_text(
            match.group("score")
        )

        parsed = parse_score_sets(
            score,
        )

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

        results.append(
            {
                "player1": p1,
                "player2": p2,
                "match": f"{p1} vs {p2}",
                "winner": winner,
                "score": score,
                "status": status,
                "source": "SportScore:generic",
            }
        )

    return results


def find_name_position(text_normalized, name):
    keys = sorted(
        loose_name_keys(name),
        key=len,
        reverse=True,
    )

    for key in keys:
        key = normalize(key)

        if not key:
            continue

        index = text_normalized.find(key)

        if index != -1:
            return index, key

    return -1, None


def compact_score_from_tail(tail):
    """
    SportScore text sometimes contains compact result blocks:
    Player A Player B 3 1 6 4 7 6 ...

    This tries to read the first two small integers after both names
    as set count. It is intentionally conservative.
    """

    tail = clean_text(tail)

    numbers = re.findall(
        r"\b([0-5])\b",
        tail,
    )

    if len(numbers) < 2:
        return None

    try:
        p1_sets = int(numbers[0])
        p2_sets = int(numbers[1])
    except Exception:
        return None

    if p1_sets == p2_sets:
        return None

    if max(p1_sets, p2_sets) not in [2, 3]:
        return None

    if min(p1_sets, p2_sets) < 0:
        return None

    winner_side = (
        "player1"
        if p1_sets > p2_sets
        else "player2"
    )

    return {
        "status": "FINISHED",
        "winner_side": winner_side,
        "score": f"{p1_sets}-{p2_sets}",
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
    }


def extract_targeted_result_for_pick(text, pick):
    finished_text = finished_text_only(text)
    normalized_text = normalize(finished_text)

    pick_name = pick.get("pick")
    opponent_name = pick.get("opponent")

    if not pick_name or not opponent_name:
        return None

    pick_pos, pick_key = find_name_position(
        normalized_text,
        pick_name,
    )

    opponent_pos, opponent_key = find_name_position(
        normalized_text,
        opponent_name,
    )

    if pick_pos == -1 or opponent_pos == -1:
        return None

    first_pos = min(
        pick_pos,
        opponent_pos,
    )

    second_pos = max(
        pick_pos,
        opponent_pos,
    )

    if second_pos - first_pos > 250:
        return None

    if pick_pos < opponent_pos:
        player1 = pick_name
        player2 = opponent_name

    else:
        player1 = opponent_name
        player2 = pick_name

    snippet = normalized_text[
        max(0, first_pos - 80):
        min(len(normalized_text), second_pos + 220)
    ]

    parsed = compact_score_from_tail(
        snippet,
    )

    if not parsed:
        return None

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
        "source": "SportScore:targeted",
        "snippet": snippet[:260],
        "pick_key": pick_key,
        "opponent_key": opponent_key,
    }


def deduplicate_results(results):
    seen = set()
    output = []

    for result in results:
        key = (
            normalize(result.get("player1")),
            normalize(result.get("player2")),
            normalize(result.get("score")),
            normalize(result.get("source")),
        )

        reverse_key = (
            normalize(result.get("player2")),
            normalize(result.get("player1")),
            normalize(result.get("score")),
            normalize(result.get("source")),
        )

        if key in seen or reverse_key in seen:
            continue

        seen.add(key)
        output.append(result)

    return output


def fetch_finished_results(picks=None):
    """
    Returns normalized finished tennis results.

    Current source:
    - SportScore HTML text

    Strategy:
    1. Generic parser for "Player A vs Player B 6-4 6-3"
    2. Targeted parser around our saved picks
    """

    picks = picks or []

    debug = {
        "source": "SportScore",
        "url": SPORTSCORE_URL,
        "generated_at": now_utc_iso(),
        "generic_results": 0,
        "targeted_results": 0,
        "examples": [],
        "error": None,
    }

    text = fetch_sportscore_text()

    generic_results = extract_generic_vs_results(
        text,
    )

    targeted_results = []

    for pick in picks:
        result = extract_targeted_result_for_pick(
            text,
            pick,
        )

        if result:
            targeted_results.append(result)

    results = deduplicate_results(
        generic_results + targeted_results
    )

    debug["generic_results"] = len(generic_results)
    debug["targeted_results"] = len(targeted_results)
    debug["total_results"] = len(results)
    debug["examples"] = results[:30]

    return results, debug
