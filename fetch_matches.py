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

# Pre naše výstupy labelujeme čas ako CET.
# Technicky v lete môže byť offset +2, preto nechávame nastaviteľné cez env.
LOCAL_TZ_OFFSET_HOURS = int(os.getenv("LOCAL_TZ_OFFSET_HOURS", "2"))
LOCAL_TZ = timezone(timedelta(hours=LOCAL_TZ_OFFSET_HOURS))

# Denné okno:
# dnes 06:00 CET -> zajtra 06:00 CET
BET_WINDOW_START_HOUR = int(os.getenv("BET_WINDOW_START_HOUR", "6"))
BET_WINDOW_END_NEXT_DAY_HOUR = int(os.getenv("BET_WINDOW_END_NEXT_DAY_HOUR", "6"))


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

    # odstráň čas alebo AM/PM na začiatku
    name = re.sub(r"^\d{1,2}:\d{2}\s*(AM|PM)?\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(AM|PM)\s+", "", name, flags=re.IGNORECASE)

    # odstráň TBD pred menom
    name = re.sub(r"^TBD\s+", "", name, flags=re.IGNORECASE)

    # odstráň seed/brackets
    name = re.sub(r"\(\d+\)", "", name)

    # odstráň pomlčky na konci
    name = re.sub(r"\s+[-–]+$", "", name)

    return clean_text(name)


def is_valid_player(name):
    if not name:
        return False

    if len(name) < 3 or len(name) > 60:
        return False

    lower = name.lower()

    blacklist = [
        "tennis",
        "live",
        "scores",
        "fixtures",
        "results",
        "scheduled",
        "finished",
        "upcoming",
        "winner of",
        "tbd",
        "atp",
        "wta",
        "challenger",
        "singles",
        "doubles",
        "court",
        "odds",
        "today",
        "tomorrow",
        "yesterday",
        "final",
        "semifinal",
        "quarterfinal",
    ]

    if any(bad in lower for bad in blacklist):
        return False

    # nechceme doubles páry
    if "/" in name:
        return False

    if not re.search(r"[A-Za-z]", name):
        return False

    return True


def bet_window_start():
    """
    Začiatok okna = dnes 06:00 CET.
    Ak workflow beží pred 06:00, stále berieme okno začaté včera 06:00,
    aby ranné zápasy do 06:00 ešte patrili do predchádzajúceho okna.
    """
    now = datetime.now(LOCAL_TZ)

    today_start = datetime.combine(
        now.date(),
        datetime.min.time(),
        tzinfo=LOCAL_TZ
    ) + timedelta(hours=BET_WINDOW_START_HOUR)

    if now < today_start:
        return today_start - timedelta(days=1)

    return today_start


def bet_window_end():
    """
    Koniec okna = začiatok okna + 24h.
    Prakticky:
    dnes 06:00 CET -> zajtra 06:00 CET
    """
    return bet_window_start() + timedelta(days=1)


def parse_match_time(time_text):
    """
    Prevedie čas zo SportScore ako '1:00 AM' alebo '13:30'
    na lokálny datetime.

    Keďže SportScore text často neobsahuje dátum, testujeme kandidátov:
    - včera
    - dnes
    - zajtra
    a vyberieme toho, ktorý spadá do denného okna 06:00 -> 06:00.
    """
    time_text = clean_text(time_text)

    parsed_time = None

    for fmt in ["%I:%M %p", "%H:%M"]:
        try:
            parsed_time = datetime.strptime(time_text.upper(), fmt).time()
            break
        except Exception:
            continue

    if parsed_time is None:
        return None

    now = datetime.now(LOCAL_TZ)

    candidate_dates = [
        now.date() - timedelta(days=1),
        now.date(),
        now.date() + timedelta(days=1),
    ]

    start = bet_window_start()
    end = bet_window_end()

    for candidate_date in candidate_dates:
        candidate = datetime.combine(candidate_date, parsed_time, tzinfo=LOCAL_TZ)

        if start <= candidate <= end:
            return candidate

    # fallback: dnešný čas, ak nič nesedí
    candidate = datetime.combine(now.date(), parsed_time, tzinfo=LOCAL_TZ)

    if candidate < start:
        candidate = candidate + timedelta(days=1)

    return candidate


def is_within_bet_window(match_start):
    """
    Povolené okno:
    06:00 CET aktuálny deň -> 06:00 CET nasledujúci deň
    """
    if match_start is None:
        return False

    return bet_window_start() <= match_start <= bet_window_end()


def scheduled_text_only(text):
    """
    Snaží sa obmedziť parsing hlavne na scheduled fixtures,
    aby sme nebrali finished/live zápasy ako budúce.

    Ak marker nenájde, fallback je celý text.
    """
    text = clean_text(text)

    lower = text.lower()

    start_markers = [
        "scheduled fixtures",
        "scheduled",
    ]

    start_index = -1

    for marker in start_markers:
        idx = lower.find(marker)

        if idx != -1:
            start_index = idx
            break

    if start_index == -1:
        return text

    sliced = text[start_index:]

    lower_sliced = sliced.lower()

    end_markers = [
        "finished matches",
        "finished",
    ]

    end_index = -1

    for marker in end_markers:
        idx = lower_sliced.find(marker)

        if idx > 0:
            end_index = idx
            break

    if end_index > 0:
        sliced = sliced[:end_index]

    return clean_text(sliced)


def extract_matches_from_text(text):
    text = scheduled_text_only(text)

    matches = []
    seen = set()

    # Zachytáva napr:
    # 1:00 AM Filippo Romano vs Marco Cecchinato 2.20 1.61
    # 3:10 AM TBD Mili Poljicak vs Alejo Sanchez Quilez 1.61 2.20
    pattern = re.compile(
        r"(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM)?)\s+"
        r"(?:TBD\s+)?"
        r"(?P<p1>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+vs\s+"
        r"(?P<p2>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+(?P<odds1>\d+\.\d+|-)\s+(?P<odds2>\d+\.\d+|-)",
        re.IGNORECASE
    )

    start = bet_window_start()
    end = bet_window_end()

    print("BET WINDOW START CET:", start.isoformat())
    print("BET WINDOW END CET:", end.isoformat())

    for match in pattern.finditer(text):
        time_text = clean_text(match.group("time"))

        p1 = clean_player_name(match.group("p1"))
        p2 = clean_player_name(match.group("p2"))

        odds1 = parse_odd(match.group("odds1"))
        odds2 = parse_odd(match.group("odds2"))

        match_start = parse_match_time(time_text)

        if not is_within_bet_window(match_start):
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

            # Reálny turnaj zatiaľ nepoznáme, preto prázdne.
            "tournament": "",

            "data_source": "SportScore",
            "odds_player1": odds1,
            "odds_player2": odds2,
            "odds_source": "SportScore" if odds1 and odds2 else "missing",

            "match_time_raw": time_text,
            "match_start": match_start.isoformat(),

            "bet_window_start": start.isoformat(),
            "bet_window_end": end.isoformat(),
            "bet_window_start_hour": BET_WINDOW_START_HOUR,
            "bet_window_end_next_day_hour": BET_WINDOW_END_NEXT_DAY_HOUR,
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

        print("REAL TENNIS MATCHES IN 06-06 CET WINDOW:", len(matches))
        print("MATCH SAMPLE:", matches[:10])

        return matches[:40]

    except Exception as e:
        print("SPORTSCORE FETCH ERROR:", str(e))
        return []
