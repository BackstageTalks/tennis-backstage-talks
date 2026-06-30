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

MODEL_VERSION = "TENNIS_ABSTRACT_ELO_V1"


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


def fetch_url(url):
    headers = {
        "User-Agent": "BackstageTalksTennisBot/1.0"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response.text


def parse_elo_html(html_text, tour_label):
    soup = BeautifulSoup(html_text, "html.parser")

    rows = []

    tables = soup.find_all("table")

    for table in tables:
        trs = table.find_all("tr")

        if len(trs) < 2:
            continue

        headers = []
        data_started = False

        for tr in trs:
            cells = tr.find_all(["th", "td"])
            values = [
                c.get_text(" ", strip=True).replace("\u00a0", " ")
                for c in cells
            ]

            values = [re.sub(r"\s+", " ", v).strip() for v in values]

            if not values:
                continue

            lower_values = [v.lower() for v in values]

            if "player" in lower_values:
                headers = values
                data_started = True
                continue

            if not data_started and len(values) >= 10:
                # Tennis Abstract can have compact tables;
                # fallback positional parsing if no header row detected.
                pass

            record = parse_elo_row(values, headers, tour_label)

            if record:
                rows.append(record)

    # Extra fallback: sometimes table parsing can be odd, but rows above should usually work.
    return rows


def find_header_index(headers, candidates):
    if not headers:
        return None

    normalized_headers = [h.replace("\u00a0", " ").strip().lower() for h in headers]

    for candidate in candidates:
        candidate = candidate.lower()

        for i, header in enumerate(normalized_headers):
            if header == candidate:
                return i

    return None


def parse_elo_row(values, headers, tour_label):
    if len(values) < 4:
        return None

    player_idx = find_header_index(headers, ["Player"])
    elo_idx = find_header_index(headers, ["Elo"])
    helo_idx = find_header_index(headers, ["hElo"])
    celo_idx = find_header_index(headers, ["cElo"])
    gelo_idx = find_header_index(headers, ["gElo"])

    # Positional fallback based on Tennis Abstract layout:
    # Elo Rank, Player, Age, Elo, hElo Rank, hElo, cElo Rank, cElo, gElo Rank, gElo, ...
    if player_idx is None:
        player_idx = 1

    if elo_idx is None:
        elo_idx = 3

    if helo_idx is None:
        helo_idx = 5

    if celo_idx is None:
        celo_idx = 7

    if gelo_idx is None:
        gelo_idx = 9

    if player_idx >= len(values):
        return None

    player = values[player_idx].strip()

    if not player or player.lower() == "player":
        return None

    elo = safe_float(values[elo_idx]) if elo_idx < len(values) else None
    helo = safe_float(values[helo_idx]) if helo_idx < len(values) else None
    celo = safe_float(values[celo_idx]) if celo_idx < len(values) else None
    gelo = safe_float(values[gelo_idx]) if gelo_idx < len(values) else None

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


def build_lookup(records):
    lookup = {}

    for record in records:
        key = record["normalized_name"]

        if key:
            lookup[key] = record

    return lookup


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


def load_tennis_abstract_elo(force_refresh=False):
    if not force_refresh:
        cached = load_cache()

        if cached and cached.get("records"):
            return cached

    all_records = []

    sources = [
        ("ATP", ATP_ELO_URL),
        ("WTA", WTA_ELO_URL),
    ]

    for tour_label, url in sources:
        try:
            print(f"Fetching Tennis Abstract Elo: {tour_label} {url}")
            html_text = fetch_url(url)
            records = parse_elo_html(html_text, tour_label)
            print(f"Parsed {tour_label} Elo records:", len(records))
            all_records.extend(records)
        except Exception as e:
            print(f"ERROR fetching/parsing {tour_label} Elo:", e)

    data = {
        "model_version": MODEL_VERSION,
        "source": "Tennis Abstract Elo Ratings",
        "atp_url": ATP_ELO_URL,
        "wta_url": WTA_ELO_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "records": all_records,
    }

    save_cache(data)

    return data


def find_player_record(player_name, elo_data):
    if not player_name or not elo_data:
        return None

    records = elo_data.get("records", [])

    if not records:
        return None

    lookup = build_lookup(records)

    key = normalize_player_name(player_name)

    if key in lookup:
        return lookup[key]

    # Simple loose matching fallback.
    key_parts = set(key.split())

    if not key_parts:
        return None

    best_record = None
    best_overlap = 0

    for record in records:
        candidate_key = record.get("normalized_name", "")
        candidate_parts = set(candidate_key.split())

        overlap = len(key_parts.intersection(candidate_parts))

        if overlap > best_overlap and overlap >= 2:
            best_overlap = overlap
            best_record = record

    return best_record


def get_elo_value(record, surface):
    if not record:
        return None, None

    surface_key = infer_surface_key(surface)

    value = record.get(surface_key)

    if value is not None:
        return value, surface_key

    # fallback within Tennis Abstract only
    if record.get("Elo") is not None:
        return record.get("Elo"), "Elo"

    return None, None


def predict_match_with_tennis_abstract(player1, player2, surface, elo_data):
    record1 = find_player_record(player1, elo_data)
    record2 = find_player_record(player2, elo_data)

    if not record1 or not record2:
        return None

    elo1, elo_type1 = get_elo_value(record1, surface)
    elo2, elo_type2 = get_elo_value(record2, surface)

    if elo1 is None or elo2 is None:
        return None

    prob1 = elo_probability(elo1, elo2)

    if prob1 is None:
        return None

    return {
        "player1": player1,
        "player2": player2,
        "probability_player1": prob1,
        "probability_player2": 1 - prob1,
        "elo_player1": elo1,
        "elo_player2": elo2,
        "elo_type_player1": elo_type1,
        "elo_type_player2": elo_type2,
        "elo_record_player1": record1,
        "elo_record_player2": record2,
        "model_source": "TENNIS_ABSTRACT_ELO",
        "model_version": MODEL_VERSION,
    }
