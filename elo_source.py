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

