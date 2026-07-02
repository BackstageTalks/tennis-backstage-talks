import re
import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone


URL = "https://sportscore.com/tennis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DEBUG_PATH = "public/sportscore_debug.json"

# Pre naše výstupy labelujeme čas ako CET.
# Technicky v lete používame offset +2, preto je nastaviteľné cez env.
LOCAL_TZ_OFFSET_HOURS = int(os.getenv("LOCAL_TZ_OFFSET_HOURS", "2"))
LOCAL_TZ = timezone(timedelta(hours=LOCAL_TZ_OFFSET_HOURS))

# SportScore raw time považujeme za UTC.
SPORTSCORE_TZ = timezone.utc

# Denné okno:
# dnes 06:00 lokálny čas -> zajtra 06:00 lokálny čas
BET_WINDOW_START_HOUR = int(os.getenv("BET_WINDOW_START_HOUR", "6"))
BET_WINDOW_END_NEXT_DAY_HOUR = int(os.getenv("BET_WINDOW_END_NEXT_DAY_HOUR", "6"))


GRAND_SLAM_NAMES = [
    "wimbledon",
    "australian open",
    "french open",
    "roland garros",
    "us open",
]


TOURNAMENT_MARKERS = [
    ("wimbledon men singles", "Wimbledon Men Singles"),
    ("wimbledon women singles", "Wimbledon Women Singles"),
    ("atp wimbledon", "ATP Wimbledon"),
    ("wta wimbledon", "WTA Wimbledon"),

    ("australian open men singles", "Australian Open Men Singles"),
    ("australian open women singles", "Australian Open Women Singles"),
    ("atp australian open", "ATP Australian Open"),
    ("wta australian open", "WTA Australian Open"),

    ("french open men singles", "French Open Men Singles"),
    ("french open women singles", "French Open Women Singles"),
    ("roland garros men singles", "Roland Garros Men Singles"),
    ("roland garros women singles", "Roland Garros Women Singles"),
    ("atp french open", "ATP French Open"),
    ("wta french open", "WTA French Open"),
    ("atp roland garros", "ATP Roland Garros"),
    ("wta roland garros", "WTA Roland Garros"),

    ("us open men singles", "US Open Men Singles"),
    ("us open women singles", "US Open Women Singles"),
    ("atp us open", "ATP US Open"),
    ("wta us open", "WTA US Open"),

    ("atp challenger", "ATP Challenger"),
    ("wta ", "WTA"),
    ("atp ", "ATP"),
]


_DEBUG = {
    "provider": "SportScore",
    "url": URL,
    "http_status": None,
    "fetch_error": None,

    "local_tz_offset_hours": LOCAL_TZ_OFFSET_HOURS,
    "bet_window_start_hour": BET_WINDOW_START_HOUR,
    "bet_window_end_next_day_hour": BET_WINDOW_END_NEXT_DAY_HOUR,

    "now_local": None,
    "bet_window_start": None,
    "bet_window_end": None,

    "raw_text_length": 0,
    "scheduled_text_length": 0,

    "tournament_markers_found": [],
    "matches_found": 0,
    "matches_returned": 0,

    "examples_matches": [],
    "examples_skipped": [],
    "text_preview": "",
}


def write_debug():
    try:
        os.makedirs(
            "public",
            exist_ok=True,
        )

        with open(
            DEBUG_PATH,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                _DEBUG,
                file,
                indent=2,
                ensure_ascii=False,
            )

    except Exception as exc:
        print("SPORTSCORE DEBUG WRITE ERROR:", str(exc))


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
    name = re.sub(
        r"^\d{1,2}:\d{2}\s*(AM|PM)?\s+",
        "",
        name,
        flags=re.IGNORECASE,
    )

    name = re.sub(
        r"^(AM|PM)\s+",
        "",
        name,
        flags=re.IGNORECASE,
    )

    # odstráň TBD pred menom
    name = re.sub(
        r"^TBD\s+",
        "",
        name,
        flags=re.IGNORECASE,
    )

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
    Začiatok okna = 06:00 lokálny čas.

    Ak workflow beží pred 06:00, berieme okno začaté včera 06:00,
    aby ranné zápasy do 06:00 ešte patrili do predchádzajúceho okna.
    """
    now = datetime.now(LOCAL_TZ)

    today_start = (
        datetime.combine(
            now.date(),
            datetime.min.time(),
            tzinfo=LOCAL_TZ,
        )
        + timedelta(hours=BET_WINDOW_START_HOUR)
    )

    if now < today_start:
        return today_start - timedelta(days=1)

    return today_start


def bet_window_end():
    """
    Koniec okna = začiatok okna + 24h.

    Prakticky:
    dnes 06:00 lokálny čas -> zajtra 06:00 lokálny čas
    """
    return bet_window_start() + timedelta(days=1)


def parse_time_text_to_time(time_text):
    """
    Prevedie text ako '1:00 AM' alebo '13:30' na time().
    """
    time_text = clean_text(time_text)

    for fmt in ["%I:%M %p", "%H:%M"]:
        try:
            return datetime.strptime(
                time_text.upper(),
                fmt,
            ).time()

        except Exception:
            continue

    return None


def parse_match_time(time_text):
    """
    Prevedie čas zo SportScore na lokálny datetime.

    Dôležitá oprava:
    - SportScore raw čas berieme ako UTC.
    - Potom ho konvertujeme do LOCAL_TZ, teda Bratislava offset +2.
    """
    parsed_time = parse_time_text_to_time(time_text)

    if parsed_time is None:
        return None

    now_local = datetime.now(LOCAL_TZ)
    now_utc = now_local.astimezone(timezone.utc)

    start = bet_window_start()
    end = bet_window_end()

    candidates = []

    for day_offset in [-1, 0, 1, 2]:
        candidate_utc_date = now_utc.date() + timedelta(days=day_offset)

        candidate_utc = datetime.combine(
            candidate_utc_date,
            parsed_time,
            tzinfo=SPORTSCORE_TZ,
        )

        candidate_local = candidate_utc.astimezone(
            LOCAL_TZ,
        )

        if (
            now_local <= candidate_local <= end
            and start <= candidate_local <= end
        ):
            candidates.append(candidate_local)

    if not candidates:
        return None

    return sorted(candidates)[0]


def is_within_bet_window(match_start):
    """
    Povolené okno:
    06:00 lokálny čas aktuálny deň -> 06:00 lokálny čas nasledujúci deň

    Navyše:
    - zápas musí byť v budúcnosti vzhľadom na aktuálny run.
    """
    if match_start is None:
        return False

    now = datetime.now(LOCAL_TZ)

    return now <= match_start <= bet_window_end()


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
        "finished results",
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


def find_tournament_markers_in_text(text):
    found = []
    lower = str(text or "").lower()

    for marker, label in TOURNAMENT_MARKERS:
        position = lower.find(marker)

        if position != -1:
            found.append({
                "marker": marker,
                "label": label,
                "position": position,
            })

    found.sort(
        key=lambda item: item.get("position", 0),
    )

    return found


def infer_tournament_from_context(text, match_start_index):
    """
    Pokúsi sa nájsť najbližší turnajový header pred zápasom.

    Nepoužíva HTML selektory, aby sme neriskovali rozbitie parsera,
    keďže aktuálny parser pracuje s textom zo soup.get_text().
    """
    if not text:
        return ""

    context_start = max(0, match_start_index - 3000)
    context = text[context_start:match_start_index]
    context_lower = context.lower()

    best_position = -1
    best_label = ""

    for marker, label in TOURNAMENT_MARKERS:
        position = context_lower.rfind(marker)

        if position > best_position:
            best_position = position
            best_label = label

    if best_label:
        return best_label

    # Fallback pre texty typu:
    # "Wimbledon ... Men Singles"
    for slam in GRAND_SLAM_NAMES:
        slam_position = context_lower.rfind(slam)

        if slam_position == -1:
            continue

        after_slam = context_lower[slam_position:slam_position + 250]

        if "men singles" in after_slam:
            if slam == "roland garros":
                return "Roland Garros Men Singles"

            return f"{slam.title()} Men Singles"

        if "women singles" in after_slam:
            if slam == "roland garros":
                return "Roland Garros Women Singles"

            return f"{slam.title()} Women Singles"

    return ""


def get_context_before_match(text, match_start_index):
    context_start = max(0, match_start_index - 500)
    context = text[context_start:match_start_index]

    return clean_text(context)[-500:]


def infer_gender(tournament):
    text = str(tournament or "").lower()

    if "women" in text or "wta" in text:
        return "women"

    if "men" in text or "atp" in text:
        return "men"

    return "unknown"


def infer_best_of(tournament):
    text = str(tournament or "").lower()
    gender = infer_gender(tournament)

    is_slam = any(
        slam in text
        for slam in GRAND_SLAM_NAMES
    )

    if is_slam and gender == "men":
        return 5

    return 3


def infer_surface_from_tournament(tournament):
    text = str(tournament or "").lower()

    if "wimbledon" in text:
        return "Grass"

    if "french open" in text or "roland garros" in text:
        return "Clay"

    if "us open" in text:
        return "Hard"

    if "australian open" in text:
        return "Hard"

    return None


def extract_matches_from_text(text):
    scheduled_text = scheduled_text_only(text)

    _DEBUG["raw_text_length"] = len(text or "")
    _DEBUG["scheduled_text_length"] = len(scheduled_text or "")
    _DEBUG["text_preview"] = clean_text(scheduled_text[:3000])

    _DEBUG["tournament_markers_found"] = find_tournament_markers_in_text(
        scheduled_text,
    )[:50]

    matches = []
    seen = set()

    pattern = re.compile(
        r"(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM)?)\s+"
        r"(?:TBD\s+)?"
        r"(?P<p1>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+vs\s+"
        r"(?P<p2>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+(?P<odds1>\d+\.\d+|-)\s+(?P<odds2>\d+\.\d+|-)",
        re.IGNORECASE,
    )

    now = datetime.now(LOCAL_TZ)
    start = bet_window_start()
    end = bet_window_end()

    _DEBUG["now_local"] = now.isoformat()
    _DEBUG["bet_window_start"] = start.isoformat()
    _DEBUG["bet_window_end"] = end.isoformat()

    print("NOW LOCAL:", now.isoformat())
    print("BET WINDOW START LOCAL:", start.isoformat())
    print("BET WINDOW END LOCAL:", end.isoformat())
    print("SPORTSCORE RAW TIME ASSUMPTION: UTC")
    print("LOCAL_TZ_OFFSET_HOURS:", LOCAL_TZ_OFFSET_HOURS)

    for match in pattern.finditer(scheduled_text):
        time_text = clean_text(match.group("time"))

        p1 = clean_player_name(match.group("p1"))
        p2 = clean_player_name(match.group("p2"))

        odds1 = parse_odd(match.group("odds1"))
        odds2 = parse_odd(match.group("odds2"))

        match_start = parse_match_time(time_text)

        tournament = infer_tournament_from_context(
            scheduled_text,
            match.start(),
        )

        gender = infer_gender(tournament)
        best_of = infer_best_of(tournament)
        tournament_surface = infer_surface_from_tournament(tournament)

        debug_entry = {
            "time_raw": time_text,
            "player1": p1,
            "player2": p2,
            "match": f"{p1} vs {p2}",
            "tournament": tournament,
            "gender": gender,
            "best_of": best_of,
            "surface": tournament_surface,
            "odds_player1": odds1,
            "odds_player2": odds2,
            "parsed_local": match_start.isoformat() if match_start else None,
            "context_before_match": get_context_before_match(
                scheduled_text,
                match.start(),
            ),
        }

        if not is_within_bet_window(match_start):
            print(
                "SKIP OUTSIDE WINDOW:",
                time_text,
                p1,
                "vs",
                p2,
                "parsed_local:",
                match_start.isoformat() if match_start else None,
            )

            if len(_DEBUG["examples_skipped"]) < 30:
                skipped = dict(debug_entry)
                skipped["reason"] = "outside_bet_window"
                _DEBUG["examples_skipped"].append(skipped)

            continue

        if not is_valid_player(p1) or not is_valid_player(p2):
            print("SKIP INVALID PLAYER:", p1, "vs", p2)

            if len(_DEBUG["examples_skipped"]) < 30:
                skipped = dict(debug_entry)
                skipped["reason"] = "invalid_player"
                _DEBUG["examples_skipped"].append(skipped)

            continue

        if p1.lower() == p2.lower():
            print("SKIP SAME PLAYER:", p1, p2)

            if len(_DEBUG["examples_skipped"]) < 30:
                skipped = dict(debug_entry)
                skipped["reason"] = "same_player"
                _DEBUG["examples_skipped"].append(skipped)

            continue

        key = f"{p1.lower()}::{p2.lower()}::{match_start.isoformat()}"

        if key in seen:
            continue

        seen.add(key)

        match_record = {
            "player1": p1,
            "player2": p2,

            "tournament": tournament,
            "gender": gender,
            "best_of": best_of,
            "surface": tournament_surface,

            "data_source": "SportScore",
            "odds_player1": odds1,
            "odds_player2": odds2,
            "odds_source": "SportScore" if odds1 and odds2 else "missing",

            "match_time_raw": time_text,
            "match_time_raw_timezone_assumption": "UTC",
            "match_start": match_start.isoformat(),

            "bet_window_start": start.isoformat(),
            "bet_window_end": end.isoformat(),
            "bet_window_start_hour": BET_WINDOW_START_HOUR,
            "bet_window_end_next_day_hour": BET_WINDOW_END_NEXT_DAY_HOUR,
        }

        matches.append(match_record)

        if len(_DEBUG["examples_matches"]) < 30:
            _DEBUG["examples_matches"].append(debug_entry)

    _DEBUG["matches_found"] = len(matches)

    return matches


def get_today_matches():
    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=20,
        )

        _DEBUG["http_status"] = response.status_code

        print("SPORTSCORE HTTP:", response.status_code)

        if response.status_code != 200:
            _DEBUG["fetch_error"] = f"HTTP {response.status_code}"
            print("SPORTSCORE RAW ERROR:", response.text[:500])
            write_debug()
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        text = soup.get_text(
            " ",
            strip=True,
        )

        matches = extract_matches_from_text(text)

        limited_matches = matches[:40]

        _DEBUG["matches_returned"] = len(limited_matches)

        print(
            "REAL TENNIS MATCHES IN 06-06 LOCAL WINDOW:",
            len(matches),
        )

        print(
            "MATCH SAMPLE:",
            limited_matches[:10],
        )

        write_debug()

        return limited_matches

    except Exception as e:
        _DEBUG["fetch_error"] = str(e)

        print("SPORTSCORE FETCH ERROR:", str(e))

        write_debug()

        return []
