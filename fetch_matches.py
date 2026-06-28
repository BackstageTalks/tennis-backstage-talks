import re
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

URL = "https://sportscore.com/tennis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

LOCAL_TZ_OFFSET_HOURS = int(os.getenv("LOCAL_TZ_OFFSET_HOURS", "2"))
LOCAL_TZ = timezone(timedelta(hours=LOCAL_TZ_OFFSET_HOURS))

BET_WINDOW_HOURS = int(os.getenv("BET_WINDOW_HOURS", "24"))


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_odd(value):
    try:
        if value in [None, "", "-"]:
            return None
        return float(value)
    except Exception:
        return None


def clean_player_name(name):
    name = clean_text(name)

    name = re.sub(r"^\d{1,2}:\d{2}\s*(AM|PM)?\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(AM|PM)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^TBD\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(\d+\)", "", name)
    name = re.sub(r"\s+[-–]+$", "", name)

    return clean_text(name)


def is_valid_player(name):
    if not name:
        return False

    if len(name) < 3 or len(name) > 55:
        return False

    lower = name.lower()

    blacklist = [
        "tennis", "live", "scores", "fixtures", "results", "scheduled",
        "finished", "upcoming", "winner of", "tbd", "atp", "wta",
        "challenger", "singles", "doubles", "court", "odds", "today",
        "tomorrow", "yesterday", "final", "semifinal", "quarterfinal"
    ]

    if any(bad in lower for bad in blacklist):
        return False

    if "/" in name:
        return False

    if not re.search(r"[A-Za-z]", name):
        return False

    return True


def parse_match_time(time_text):
    time_text = clean_text(time_text)

    now = datetime.now(LOCAL_TZ)
    today = now.date()

    parsed_time = None

    for fmt in ["%I:%M %p", "%H:%M"]:
        try:
            parsed_time = datetime.strptime(time_text.upper(), fmt).time()
            break
        except Exception:
            continue

    if parsed_time is None:
        return None

    candidate = datetime.combine(today, parsed_time, tzinfo=LOCAL_TZ)

    if candidate < now:
        candidate = candidate + timedelta(days=1)

    return candidate


def is_within_next_24h(match_start):
    if match_start is None:
        return False

    now = datetime.now(LOCAL_TZ)
    max_time = now + timedelta(hours=BET_WINDOW_HOURS)

    return now <= match_start <= max_time


def extract_matches_from_text(text):
    text = clean_text(text)

    matches = []
    seen = set()

    pattern = re.compile(
        r"(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM)?)\s+"
        r"(?:TBD\s+)?"
        r"(?P<p1>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,70}?)"
        r"\s+vs\s+"
        r"(?P<p2>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,70}?)"
        r"\s+(?P<odds1>\d+\.\d+|-)\s+(?P<odds2>\d+\.\d+|-)",
        re.IGNORECASE
    )

    now = datetime.now(LOCAL_TZ)
    max_time = now + timedelta(hours=BET_WINDOW_HOURS)

    print("BET WINDOW START:", now.isoformat())
    print("BET WINDOW END:", max_time.isoformat())

    for match in pattern.finditer(text):
        time_text = clean_text(match.group("time"))

        p1 = clean_player_name(match.group("p1"))
        p2 = clean_player_name(match.group("p2"))

        odds1 = parse_odd(match.group("odds1"))
        odds2 = parse_odd(match.group("odds2"))

        match_start = parse_match_time(time_text)

        if not is_within_next_24h(match_start):
            continue

        if not is_valid_player(p1) or not is_valid_player(p2):
            continue

        if p1.lower() == p2.lower():
            continue

        key = f"{p1.lower()}::{p2.lower()}::{match_start.isoformat()}"

        if key in seen:
            continue

        seen.add(key)

        matches.append({
            "player1": p1,
            "player2": p2,
            "tournament": "SportScore Tennis",
            "odds_player1": odds1,
            "odds_player2": odds2,
            "odds_source": "SportScore" if odds1 and odds2 else "missing",
            "match_time_raw": time_text,
            "match_start": match_start.isoformat(),
            "bet_window_hours": BET_WINDOW_HOURS
        })

    return matches


def get_today_matches():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=20)

        print("SPORTSCORE HTTP:", response.status_code)

        if response.status_code != 200:
            print("SPORTSCORE RAW ERROR:", response.text[:500])
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        matches = extract_matches_from_text(text)

        print("REAL TENNIS MATCHES NEXT 24H:", len(matches))
        print("MATCH SAMPLE:", matches[:10])

        return matches[:40]

    except Exception as e:
        print("SPORTSCORE FETCH ERROR:", str(e))
        return []
