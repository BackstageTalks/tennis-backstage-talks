import json
import os
import re
import unicodedata
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup


DATA_DIR = "data"
CACHE_PATH = os.path.join(DATA_DIR, "tennis_abstract_elo_cache.json")

ATP_ELO_URL = "https://tennisabstract.com/reports/atp_elo_ratings.html"
WTA_ELO_URL = "https://tennisabstract.com/reports/wta_elo_ratings.html"

MODEL_VERSION = "TENNIS_ABSTRACT_ELO_V2"

CACHE_MAX_AGE_HOURS = 6


# -------------------------
# HELPERS
# -------------------------

def safe_float(value):
    try:
        if value is None:
            return None

        text = str(value).replace(",", "").strip()

        if text in ["", "-", "None", "nan"]:
            return None

        return float(text)
    except Exception:
        return None


def normalize_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\u00a0", " ")
    text = text.strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    text = re.sub(r"[^a-z0-9\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_player_name(value):
    return normalize_text(value)


def elo_probability(elo_a, elo_b):
    if elo_a is None or elo_b is None:
        return None

    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def infer_surface_key(surface):
    surface_text = normalize_text(surface)

    if "grass" in surface_text:
        return "gElo"

    if "clay" in surface_text:
        return "cElo"

    if "hard" in surface_text:
        return "hElo"

    return "Elo"


# -------------------------
# FETCH
# -------------------------

def fetch_url(url):
    headers = {
        "User-Agent": "BackstageTalksTennisBot/1.0"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response.text


# -------------------------
# PARSER
# -------------------------

def parse_elo_html(html_text, tour_label):
    soup = BeautifulSoup(html_text, "html.parser")

    rows = []

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            values = [
                c.get_text(" ", strip=True).replace("\u00a0", " ")
                for c in cells
            ]

            values = [re.sub(r"\s+", " ", v).strip() for v in values]

            record = parse_positional_row(values, tour_label)

            if record:
                rows.append(record)

    print(f"{tour_label} parser output:", len(rows))
    return rows


def parse_positional_row(values, tour_label):
    if len(values) < 10:
        return None

    if values[0].lower() in ["elo rank", "rank"]:
        return None

    player = values[1].strip()

    if not player or player.lower() == "player":
        return None

    elo = safe_float(values[3])
    helo = safe_float(values[5])
    celo = safe_float(values[7])
    gelo = safe_float(values[9])

    if elo is None and helo is None and celo is None and gelo is None:
        return None

    return {
        "tour": tour_label,
        "player": player,
        "normalized_name": normalize_player_name(player),
        "Elo": elo,
        "hElo": helo,
        "cElo": celo,
        "gElo": gelo,
    }


# -------------------------
# CACHE
# -------------------------

def load_cache():
    if not os.path.exists(CACHE_PATH):
        return None

    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cache(data):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_cache_fresh(cache_data):
    if not cache_data:
        return False

    fetched_at = cache_data.get("fetched_at")

    if not fetched_at:
        return False

    try:
        fetched_time = datetime.fromisoformat(fetched_at)
    except Exception:
        return False

    age = datetime.now(timezone.utc) - fetched_time

    return age < timedelta(hours=CACHE_MAX_AGE_HOURS)


# -------------------------
# LOAD
# -------------------------

def load_tennis_abstract_elo(force_refresh=False):
    cached = load_cache()

    if cached and cached.get("records"):
        if not force_refresh and is_cache_fresh(cached):
            print("Using fresh cache:", len(cached["records"]))
            return cached
        else:
            print("Cache stale → refreshing Elo...")

    all_records = []

    for tour_label, url in [("ATP", ATP_ELO_URL), ("WTA", WTA_ELO_URL)]:
        try:
            print(f"Fetching {tour_label} Elo...")
            html = fetch_url(url)
            records = parse_elo_html(html, tour_label)
            print(f"{tour_label} records:", len(records))
            all_records.extend(records)
        except Exception as e:
            print(f"ERROR {tour_label}:", e)

    # fallback
    if not all_records and cached:
        print("WARNING: using old cache")
        return cached

    data = {
        "model_version": MODEL_VERSION,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "records": all_records,
    }

    save_cache(data)

    print("Saved cache:", len(all_records))

    return data


# -------------------------
# LOOKUP
# -------------------------

def build_lookup(records):
    lookup = {}
    for r in records:
        key = r.get("normalized_name")
        if key:
            lookup[key] = r
    return lookup


def find_player_record(player_name, elo_data):
    if not player_name or not elo_data:
        return None

    records = elo_data.get("records", [])
    lookup = build_lookup(records)

    key = normalize_player_name(player_name)

    if key in lookup:
        return lookup[key]

    return None


def get_elo_value(record, surface):
    if not record:
        return None, None

    key = infer_surface_key(surface)

    if record.get(key) is not None:
        return record.get(key), key

    return record.get("Elo"), "Elo"


# -------------------------
# PREDICTION
# -------------------------

def predict_match_with_tennis_abstract(player1, player2, surface, elo_data):

    r1 = find_player_record(player1, elo_data)
    r2 = find_player_record(player2, elo_data)

    if not r1 or not r2:
        return {
            "available": False,
            "missing_players": [player1, player2]
        }

    elo1, _ = get_elo_value(r1, surface)
    elo2, _ = get_elo_value(r2, surface)

    if elo1 is None or elo2 is None:
        return {"available": False, "missing_players": []}

    prob1 = elo_probability(elo1, elo2)

    return {
        "available": True,
        "probability_player1": prob1,
        "probability_player2": 1 - prob1,
        "elo_player1": elo1,
        "elo_player2": elo2,
        "model_source": "TENNIS_ABSTRACT_ELO",
        "model_version": MODEL_VERSION,
    }
