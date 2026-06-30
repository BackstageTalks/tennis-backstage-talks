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

MODEL_VERSION = "TA_ELO_V3"
CACHE_MAX_AGE_HOURS = 6


# --------------------------
# HELPERS
# --------------------------

def safe_float(x):
    try:
        return float(str(x).replace(",", "").strip())
    except:
        return None


def normalize_text(t):
    if not t:
        return ""
    t = str(t)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9\s\-']", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def normalize_player_name(n):
    return normalize_text(n)


# 🔥 lepší matching
def name_variants(name):
    key = normalize_player_name(name)
    parts = key.split()

    variants = {key}

    if len(parts) >= 2:
        variants.add(" ".join(reversed(parts)))
        variants.add(parts[0] + " " + parts[-1])

    if len(parts) >= 1:
        variants.add(parts[-1])

    return variants


def elo_probability(a, b):
    if a is None or b is None:
        return None
    return 1 / (1 + 10 ** ((b - a) / 400))


def infer_surface(surface):
    s = normalize_text(surface)
    if "grass" in s:
        return "gElo"
    if "clay" in s:
        return "cElo"
    if "hard" in s:
        return "hElo"
    return "Elo"


# --------------------------
# FETCH + PARSE
# --------------------------

def fetch(url):
    r = requests.get(url, headers={"User-Agent": "TA Bot"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse(html, tour):
    soup = BeautifulSoup(html, "html.parser")
    out = []

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            vals = [c.get_text(" ", strip=True) for c in cells]

            if len(vals) < 10:
                continue

            if vals[0].lower() in ["rank", "elo rank"]:
                continue

            player = vals[1]

            out.append({
                "tour": tour,
                "player": player,
                "normalized_name": normalize_player_name(player),
                "Elo": safe_float(vals[3]),
                "hElo": safe_float(vals[5]),
                "cElo": safe_float(vals[7]),
                "gElo": safe_float(vals[9]),
            })

    print(tour, "records:", len(out))
    return out


# --------------------------
# CACHE
# --------------------------

def load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        return json.load(open(CACHE_PATH))
    except:
        return None


def save_cache(d):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(d, open(CACHE_PATH, "w"), indent=2)


def fresh(c):
    try:
        t = datetime.fromisoformat(c["fetched_at"])
        return (datetime.now(timezone.utc) - t) < timedelta(hours=CACHE_MAX_AGE_HOURS)
    except:
        return False


# --------------------------
# LOAD
# --------------------------

def load_tennis_abstract_elo():
    cache = load_cache()

    if cache and fresh(cache):
        print("Using cache:", len(cache["records"]))
        return cache

    records = []

    for tour, url in [("ATP", ATP_ELO_URL), ("WTA", WTA_ELO_URL)]:
        try:
            html = fetch(url)
            records += parse(html, tour)
        except Exception as e:
            print("ERROR:", e)

    if not records and cache:
        print("Fallback cache")
        return cache

    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "records": records
    }

    save_cache(data)
    return data


# --------------------------
# LOOKUP
# --------------------------

def build_lookup(records):
    d = {}
    for r in records:
        d[r["normalized_name"]] = r
    return d


def find_player(name, data):
    lookup = build_lookup(data["records"])

    for v in name_variants(name):
        if v in lookup:
            return lookup[v]

    return None


def get_elo(record, surface):
    if not record:
        return None

    k = infer_surface(surface)
    return record.get(k) or record.get("Elo")


# --------------------------
# PREDICT
# --------------------------

def predict_match_with_tennis_abstract(p1, p2, surface, data):
    r1 = find_player(p1, data)
    r2 = find_player(p2, data)

    if not r1 or not r2:
        return {"available": False}

    e1 = get_elo(r1, surface)
    e2 = get_elo(r2, surface)

    if e1 is None or e2 is None:
        return {"available": False}

    prob = elo_probability(e1, e2)

    return {
        "available": True,
        "probability_player1": prob,
        "probability_player2": 1 - prob,
        "elo_player1": e1,
        "elo_player2": e2,
    }
