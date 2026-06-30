import json
import os
import re
import unicodedata
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

DATA_DIR = "data"
CACHE_PATH = os.path.join(DATA_DIR, "tennis_abstract_elo_cache.json")

ATP_ELO_URL = "https://tennisabstract.com/reports/atp_elo_ratings.html"
WTA_ELO_URL = "https://tennisabstract.com/reports/wta_elo_ratings.html"

MODEL_VERSION = "TENNIS_ABSTRACT_ELO_V3"

PLAYER_ALIASES = {
    "alex de minaur": "alexander de minaur",
}

def safe_float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return None

def normalize_text(value):
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_player_name(value):
    key = normalize_text(value)
    return PLAYER_ALIASES.get(key, key)

def token_similarity(a, b):
    a_parts = set(normalize_player_name(a).split())
    b_parts = set(normalize_player_name(b).split())

    if not a_parts or not b_parts:
        return 0.0

    overlap = len(a_parts & b_parts)
    total = max(len(a_parts), len(b_parts))
    return overlap / total

def elo_probability(elo_a, elo_b):
    if elo_a is None or elo_b is None:
        return None
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def infer_surface_key(surface):
    s = normalize_text(surface)
    if "grass" in s:
        return "gElo"
    if "clay" in s:
        return "cElo"
    if "hard" in s:
        return "hElo"
    return "Elo"

def fetch_url(url):
    return requests.get(url, timeout=30).text

def parse_table(html, tour):
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            values = [c.get_text(strip=True) for c in cells]

            if len(values) < 10:
                continue

            rank = safe_float(values[0])
            if rank is None:
                continue

            player = values[1]
            elo = safe_float(values[3])
            helo = safe_float(values[5])
            celo = safe_float(values[7])
            gelo = safe_float(values[9])

            records.append({
                "tour": tour,
                "player": player,
                "normalized_name": normalize_player_name(player),
                "Elo": elo,
                "hElo": helo,
                "cElo": celo,
                "gElo": gelo,
            })

    return records

def is_cache_valid(cached, hours=6):
    try:
        t = datetime.fromisoformat(cached["fetched_at"])
        return (datetime.now(timezone.utc) - t).total_seconds() < hours * 3600
    except:
        return False

def load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    return json.load(open(CACHE_PATH, encoding="utf-8"))

def save_cache(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(data, open(CACHE_PATH, "w", encoding="utf-8"), indent=2)

def load_tennis_abstract_elo(force_refresh=False):
    cached = load_cache()

    if cached and not force_refresh and is_cache_valid(cached):
        print("Using cached ELO:", len(cached["records"]))
        return cached

    all_records = []

    for label, url in [("ATP", ATP_ELO_URL), ("WTA", WTA_ELO_URL)]:
        try:
            html = fetch_url(url)
            parsed = parse_table(html, label)
            print(f"{label} parsed:", len(parsed))
            all_records.extend(parsed)
        except Exception as e:
            print("ERROR:", e)

    data = {
        "records": all_records,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

    save_cache(data)
    print("TOTAL ELO:", len(all_records))

    return data

def find_player_record(name, elo_data):
    records = elo_data.get("records", [])

    key = normalize_player_name(name)

    for r in records:
        if r["normalized_name"] == key:
            return r

    best = None
    best_score = 0

    for r in records:
        score = token_similarity(name, r["player"])
        if score > best_score:
            best_score = score
            best = r

    if best_score >= 0.6:
        return best

    return None

def get_elo(record, surface):
    if not record:
        return None

    k = infer_surface_key(surface)
    return record.get(k) or record.get("Elo")

def predict_match_with_tennis_abstract(p1, p2, surface, elo_data):
    r1 = find_player_record(p1, elo_data)
    r2 = find_player_record(p2, elo_data)

    if not r1 or not r2:
        return {
            "available": False,
            "missing_players": [p for p, r in [(p1, r1), (p2, r2)] if r is None]
        }

    e1 = get_elo(r1, surface)
    e2 = get_elo(r2, surface)

    if e1 is None or e2 is None:
        return {"available": False, "missing_players": []}

    p = elo_probability(e1, e2)

    return {
        "available": True,
        "probability_player1": p,
        "probability_player2": 1 - p,
        "elo_player1": e1,
        "elo_player2": e2,
    }
