import json
import os
import re
import unicodedata
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

DATA_DIR = "data"
CACHE_PATH = os.path.join(DATA_DIR, "tennis_abstract_elo_cache.json")

ATP_URL = "https://tennisabstract.com/reports/atp_elo_ratings.html"
WTA_URL = "https://tennisabstract.com/reports/wta_elo_ratings.html"


def normalize(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_float(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return None


def fetch(url):
    return requests.get(url, timeout=30).text


# ✅ NOVÝ PARSER (funguje na TA layout)
def parse_text(html, tour):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    records = []

    for line in lines:
        parts = line.split()

        # typická TA row:
        # 1 Jannik Sinner 24.7 2319.8 ...
        if len(parts) < 10:
            continue

        if not parts[0].isdigit():
            continue

        try:
            rank = int(parts[0])
        except:
            continue

        # meno = všetko medzi rank a age
        name_parts = []
        for p in parts[1:]:
            if re.match(r"\d+\.\d", p):
                break
            name_parts.append(p)

        name = " ".join(name_parts)

        # potom čísla
        numbers = [x for x in parts[len(name_parts)+1:] if re.match(r"\d+\.\d", x)]

        if len(numbers) < 4:
            continue

        elo = safe_float(numbers[0])
        helo = safe_float(numbers[1])
        celo = safe_float(numbers[2])
        gelo = safe_float(numbers[3])

        records.append({
            "player": name,
            "normalized": normalize(name),
            "Elo": elo,
            "hElo": helo,
            "cElo": celo,
            "gElo": gelo,
            "tour": tour
        })

    return records


def load_cache():
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH))
    return None


def save_cache(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(data, open(CACHE_PATH, "w"), indent=2)


def load_tennis_abstract_elo(force=False):
    cached = load_cache()

    if cached and not force:
        print("Using cached ELO:", len(cached["records"]))
        if len(cached["records"]) > 50:
            return cached

    all_records = []

    for tour, url in [("ATP", ATP_URL), ("WTA", WTA_URL)]:
        try:
            html = fetch(url)
            rec = parse_text(html, tour)
            print(f"{tour} parsed:", len(rec))
            all_records += rec
        except Exception as e:
            print("ERROR:", e)

    data = {
        "records": all_records,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

    save_cache(data)

    print("TOTAL ELO:", len(all_records))

    return data


def similarity(a, b):
    a = set(normalize(a).split())
    b = set(normalize(b).split())

    if not a or not b:
        return 0

    return len(a & b) / max(len(a), len(b))


def find_player(name, data):
    records = data["records"]

    key = normalize(name)

    for r in records:
        if r["normalized"] == key:
            return r

    best = None
    best_score = 0

    for r in records:
        s = similarity(name, r["player"])
        if s > best_score:
            best_score = s
            best = r

    if best_score >= 0.6:
        return best

    return None


def get_surface_elo(record, surface):
    s = normalize(surface)

    if "grass" in s:
        return record.get("gElo")
    if "clay" in s:
        return record.get("cElo")
    if "hard" in s:
        return record.get("hElo")

    return record.get("Elo")


def prob(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))


def predict_match_with_tennis_abstract(p1, p2, surface, elo_data):
    r1 = find_player(p1, elo_data)
    r2 = find_player(p2, elo_data)

    if not r1 or not r2:
        return {
            "available": False,
            "missing_players": [
                x for x, r in [(p1, r1), (p2, r2)] if not r
            ]
        }

    e1 = get_surface_elo(r1, surface)
    e2 = get_surface_elo(r2, surface)

    if e1 is None or e2 is None:
        return {"available": False, "missing_players": []}

    p = prob(e1, e2)

    return {
        "available": True,
        "probability_player1": p,
        "probability_player2": 1 - p,
    }
