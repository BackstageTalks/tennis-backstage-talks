import re
import requests
from bs4 import BeautifulSoup


URL = "https://sportscore.com/tennis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_player_name(name):
    name = clean_text(name)

    # odstráň čas na začiatku
    name = re.sub(r"^\d{1,2}:\d{2}\s*(AM|PM)?\s+", "", name, flags=re.IGNORECASE)

    # ak regex zachytil "AM Player", odstráň AM/PM
    name = re.sub(r"^(AM|PM)\s+", "", name, flags=re.IGNORECASE)

    # ak je vnútri čas, zober časť za posledným časom
    name = re.split(r"\d{1,2}:\d{2}\s*(?:AM|PM)?\s+", name, flags=re.IGNORECASE)[-1]

    # odstráň odds na konci: "1.80 2.00" alebo "- -"
    name = re.sub(r"\s+(\d+\.\d+|-)\s+(\d+\.\d+|-)$", "", name)

    # odstráň samostatné pomlčky na konci
    name = re.sub(r"\s+[-–]+$", "", name)

    # odstráň bracket/seed noise
    name = re.sub(r"\(\d+\)", "", name)

    # finálne čistenie
    name = clean_text(name)

    return name


def is_valid_player(name):
    if not name:
        return False

    if len(name) < 3 or len(name) > 45:
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
        "wta",
        "atp",
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

    if not re.search(r"[A-Za-z]", name):
        return False

    # zatiaľ nechceme doubles páry
    if "/" in name:
        return False

    return True


def extract_matches_from_text(text):
    text = clean_text(text)

    matches = []
    seen = set()

    # zachytáva hlavne formáty:
    # 1:00 AM Raul Brancaccio vs Nikoloz Basilashvili - -
    # Player A vs Player B 1.80 2.00
    pattern = re.compile(
        r"(?:\d{1,2}:\d{2}\s*(?:AM|PM)?\s+)?"
        r"([A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,60}?)"
        r"\s+vs\s+"
        r"([A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,60}?)"
        r"(?=\s+(?:\d+\.\d+|-)\s+(?:\d+\.\d+|-)|\s+\d{1,2}:\d{2}\s*(?:AM|PM)?|$)",
        re.IGNORECASE,
    )

    for match in pattern.finditer(text):
        p1 = clean_player_name(match.group(1))
        p2 = clean_player_name(match.group(2))

        if not is_valid_player(p1) or not is_valid_player(p2):
            continue

        if p1.lower() == p2.lower():
            continue

        key = f"{p1.lower()}::{p2.lower()}"

        if key in seen:
            continue

        seen.add(key)

        matches.append((p1, p2, "SportScore Tennis"))

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

        print("REAL TENNIS MATCHES:", len(matches))
        print("MATCH SAMPLE:", matches[:10])

        return matches[:20]

    except Exception as e:
        print("SPORTSCORE FETCH ERROR:", str(e))
        return []
