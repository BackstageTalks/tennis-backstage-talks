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

MODEL_VERSION = "TENNIS_ABSTRACT_ELO_V2"


def safe_float(value):
    try:
        if value is None:
            return None

        text = str(value)
        text = text.replace(",", "")
        text = text.replace("\u00a0", " ")
        text = text.strip()

        if text in ["", "-", "None", "nan", "NaN"]:
            return None

        return float(text)
    except Exception:
        return None


def normalize_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\u00a0", " ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()

    text = re.sub(r"[^a-z0-9\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_player_name(value):
    return normalize_text(value)


def name_variants(value):
    """
    Vytvorí základné varianty mena pre párovanie:
    - "alex de minaur"
    - "minaur alex de" / reversed fallback
    """
    key = normalize_player_name(value)

    if not key:
        return set()

    parts = key.split()

    variants = {key}

    if len(parts) >= 2:
        variants.add(" ".join(reversed(parts)))

    return variants


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
        "User-Agent": "BackstageTalksTennisBot/1.0 (+https://backstagetalks.github.io/tennis-backstage-talks/)"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response.text


def parse_elo_html(html_text, tour_label):
    """
    Robustný parser pre Tennis Abstract Elo stránky.

    Skúša:
    1. parsovať HTML tabuľky cez td/th bunky
    2. fallback parsovanie textových riadkov

    Očakávaný layout Tennis Abstract:
    Elo Rank | Player | Age | Elo | hElo Rank | hElo | cElo Rank | cElo | gElo Rank | gElo | ...
    """
    records = []

    table_records = parse_elo_tables(html_text, tour_label)
    records.extend(table_records)

    if len(records) < 20:
        text_records = parse_elo_text(html_text, tour_label)

        existing = {r["normalized_name"] for r in records}

        for record in text_records:
            if record["normalized_name"] not in existing:
                records.append(record)
                existing.add(record["normalized_name"])

    deduped = {}

    for record in records:
        key = record["normalized_name"]

        if key:
            deduped[key] = record

    output = list(deduped.values())

    print(f"{tour_label} parser output records:", len(output))

    return output


def parse_elo_tables(html_text, tour_label):
    soup = BeautifulSoup(html_text, "html.parser")

    records = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")

        for tr in rows:
            cells = tr.find_all(["td", "th"])

            values = [
                c.get_text(" ", strip=True).replace("\u00a0", " ")
                for c in cells
            ]

            values = [re.sub(r"\s+", " ", v).strip() for v in values]

            if not values:
                continue

            record = parse_positional_row(values, tour_label)

            if record:
                records.append(record)

    return records


def parse_positional_row(values, tour_label):
    """
    Positional parser for normal TA table rows.

    Expected:
    [rank, player, age, Elo, hRank, hElo, cRank, cElo, gRank, gElo, ...]
    """
    if len(values) < 10:
        return None

    if values[0].lower() in ["elo rank", "rank"]:
        return None

    rank = safe_float(values[0])

    if rank is None:
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


def parse_elo_text(html_text, tour_label):
    """
    Text fallback.

