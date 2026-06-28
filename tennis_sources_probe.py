import os
import re
import json
import datetime
import requests
from bs4 import BeautifulSoup

TODAY = datetime.date.today().isoformat()

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def header(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def is_bad_name(name):
    if not name:
        return True

    name = clean_text(name)

    if len(name) < 3 or len(name) > 50:
        return True

    bad_words = [
        "tennis",
        "live",
        "scores",
        "fixtures",
        "results",
        "rankings",
        "scheduled",
        "finished",
        "upcoming",
        "advertisement",
        "favorites",
        "privacy",
        "terms",
        "login",
        "register",
        "wimbledon",
        "atp",
        "wta",
        "challenger",
        "singles",
        "doubles",
        "draw",
        "final",
        "semi",
        "quarter",
        "court",
        "odds",
        "today",
        "tomorrow",
        "yesterday",
    ]

    lower = name.lower()

    if any(word in lower for word in bad_words):
        return True

    if not re.search(r"[A-Za-z]", name):
        return True

    return False


def add_match(matches, seen, source, p1, p2, tournament="Tennis"):
    p1 = clean_text(p1)
    p2 = clean_text(p2)

    if is_bad_name(p1) or is_bad_name(p2):
        return

    if p1.lower() == p2.lower():
        return

    key = f"{source}:{p1.lower()}:{p2.lower()}"

    if key in seen:
        return

    seen.add(key)

    matches.append({
        "source": source,
        "player1": p1,
        "player2": p2,
        "tournament": tournament
    })


def parse_vs_text(source, text, tournament="Tennis"):
    matches = []
    seen = set()

    text = clean_text(text)

    # formát: Player A vs Player B
    patterns = [
        r"([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})\s+vs\s+([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})",
        r"([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})\s+v\s+([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text):
            p1 = m.group(1)
            p2 = m.group(2)
            add_match(matches, seen, source, p1, p2, tournament)

    return matches


# ============================================================
# SPORTScore
