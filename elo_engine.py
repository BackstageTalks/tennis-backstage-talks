import json
import math
import os
import re
import unicodedata
from datetime import datetime


DATA_PATH = "data/elo_store.json"

START_ELO = 1500.0
BASE_K = 28.0

SURFACE_WEIGHT_BASE = 0.60
OVERALL_WEIGHT_BASE = 0.40

CALIBRATION_SHRINK = 0.86

MAX_RATING_DIFF_FOR_PROB = 420.0


def normalize(name):
    if not name:
        return ""

    text = str(name)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def surface_key(surface):
    s = normalize(surface)

    if "grass" in s:
        return "grass"

    if "clay" in s:
        return "clay"

    if "carpet" in s:
        return "carpet"

    if "hard" in s:
        return "hard"

    return "hard"


def parse_date(value):
    text = str(value or "")

    if not text or text == "0":
        return None

    for fmt in ["%Y%m%d", "%Y-%m-%d"]:
        try:
            return datetime.strptime(text[:10], fmt)
        except Exception:
            continue

    return None


def ensure_player(store, player):
    key = normalize(player)

    if key not in store:
        store[key] = {
            "player": player,
            "overall_elo": START_ELO,
            "overall_matches": 0,
            "surface_elo": {
                "hard": START_ELO,
                "clay": START_ELO,
                "grass": START_ELO,
                "carpet": START_ELO,
            },
            "surface_matches": {
                "hard": 0,
                "clay": 0,
                "grass": 0,
                "carpet": 0,
            },
            "last_match_date": None,
        }

    return key


def find_player_key(store, player):
    key = normalize(player)

    if key in store:
        return key

    parts = key.split()

    if not parts:
        return None

    last_name = parts[-1]

    candidates = []

    for existing_key in store.keys():
        e_parts = existing_key.split()

        if not e_parts:
            continue

        score = 0

        if e_parts[-1] == last_name:
            score += 3

        overlap = len(set(parts).intersection(set(e_parts)))
        score += overlap

        if score >= 3:
            candidates.append((score, existing_key))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][1]


def expected_score(rating_a, rating_b):
    diff = max(-MAX_RATING_DIFF_FOR_PROB, min(MAX_RATING_DIFF_FOR_PROB, rating_a - rating_b))
    return 1.0 / (1.0 + math.pow(10.0, -diff / 400.0))


def calibrated_probability(raw_probability):
    """
    ELO often becomes overconfident.
    This shrinks probabilities mildly toward 50%.
    """
    p = max(0.03, min(0.97, float(raw_probability)))
    calibrated = 0.5 + (p - 0.5) * CALIBRATION_SHRINK
    return max(0.05, min(0.95, calibrated))


def latest_match_date(matches):
    dates = []

    for match in matches:
        dt = parse_date(match.get("date"))

        if dt:
            dates.append(dt)

    if not dates:
        return None

    return max(dates)


def time_decay_multiplier(match_date, reference_date):
    """
    Recent matches update ratings more.
    Old matches still count, but less.
    """
    if not match_date or not reference_date:
        return 1.0

    age_days = max(0, (reference_date - match_date).days)

    if age_days <= 180:
        return 1.00

    if age_days <= 365:
        return 0.82

    if age_days <= 730:
        return 0.62

    return 0.45


def reliability_from_matches(matches_count):
    try:
        n = max(0, float(matches_count))
    except Exception:
        n = 0

    return round(1.0 - math.exp(-n / 45.0), 3)


def surface_reliability_from_matches(matches_count):
    try:
        n = max(0, float(matches_count))
    except Exception:
        n = 0

    return round(1.0 - math.exp(-n / 18.0), 3)


def dynamic_k_factor(player_matches, opponent_matches, match_date, reference_date):
    """
    Higher K for low-sample players.
    Lower K for stable known players.
    Time decay reduces impact of old matches.
    """
    min_matches = min(player_matches, opponent_matches)

    if min_matches < 10:
        sample_multiplier = 1.35
    elif min_matches < 25:
        sample_multiplier = 1.18
    elif min_matches < 60:
        sample_multiplier = 1.00
    else:
        sample_multiplier = 0.82

    decay = time_decay_multiplier(match_date, reference_date)

    return BASE_K * sample_multiplier * decay


def surface_weight(surface_matches_1, surface_matches_2, surface):
    """
    Grass has fewer matches, so do not overtrust grass ELO too early.
    """
    min_surface_matches = min(surface_matches_1, surface_matches_2)

    if surface_key(surface) == "grass":
        if min_surface_matches < 4:
            return 0.25
        if min_surface_matches < 10:
            return 0.42
        return 0.55

    if min_surface_matches < 5:
        return 0.30

    if min_surface_matches < 15:
        return 0.48

    return SURFACE_WEIGHT_BASE


def blended_rating(record, surface):
    s_key = surface_key(surface)

    s_matches = record.get("surface_matches", {}).get(s_key, 0)

    if s_key == "grass":
        if s_matches < 4:
            w_surface = 0.25
        elif s_matches < 10:
            w_surface = 0.42
        else:
            w_surface = 0.55
    else:
        if s_matches < 5:
            w_surface = 0.30
        elif s_matches < 15:
            w_surface = 0.48
        else:
            w_surface = SURFACE_WEIGHT_BASE

    w_overall = 1.0 - w_surface

    overall = float(record.get("overall_elo", START_ELO))
    surface_elo = float(record.get("surface_elo", {}).get(s_key, START_ELO))

    return overall * w_overall + surface_elo * w_surface


def update_pair(store, p1_key, p2_key, surface, winner_key, match_date, reference_date):
    s_key = surface_key(surface)

    p1 = store[p1_key]
    p2 = store[p2_key]

    p1_overall = float(p1.get("overall_elo", START_ELO))
    p2_overall = float(p2.get("overall_elo", START_ELO))

    p1_surface = float(p1.get("surface_elo", {}).get(s_key, START_ELO))
    p2_surface = float(p2.get("surface_elo", {}).get(s_key, START_ELO))

    p1_result = 1.0 if p1_key == winner_key else 0.0
    p2_result = 1.0 - p1_result

    p1_matches = int(p1.get("overall_matches", 0))
    p2_matches = int(p2.get("overall_matches", 0))

    k = dynamic_k_factor(p1_matches, p2_matches, match_date, reference_date)

    expected_p1_overall = expected_score(p1_overall, p2_overall)
    expected_p2_overall = 1.0 - expected_p1_overall

    p1["overall_elo"] = p1_overall + k * (p1_result - expected_p1_overall)
    p2["overall_elo"] = p2_overall + k * (p2_result - expected_p2_overall)

    surface_k = k * 0.92

    expected_p1_surface = expected_score(p1_surface, p2_surface)
    expected_p2_surface = 1.0 - expected_p1_surface

    p1["surface_elo"][s_key] = p1_surface + surface_k * (p1_result - expected_p1_surface)
    p2["surface_elo"][s_key] = p2_surface + surface_k * (p2_result - expected_p2_surface)

    p1["overall_matches"] = p1_matches + 1
    p2["overall_matches"] = p2_matches + 1

    p1["surface_matches"][s_key] = int(p1["surface_matches"].get(s_key, 0)) + 1
    p2["surface_matches"][s_key] = int(p2["surface_matches"].get(s_key, 0)) + 1

    if match_date:
        date_text = match_date.strftime("%Y%m%d")
        p1["last_match_date"] = date_text
        p2["last_match_date"] = date_text


def build_elo(matches):
    store = {}

    sorted_matches = sorted(
        matches,
        key=lambda x: str(x.get("date") or "0")
    )

    reference_date = latest_match_date(sorted_matches)

    for match in sorted_matches:
        try:
            player1 = match.get("player1")
            player2 = match.get("player2")
            winner = match.get("winner")
            surface = match.get("surface", "Hard")
            match_date = parse_date(match.get("date"))

            if not player1 or not player2 or not winner:
                continue

            p1_key = ensure_player(store, player1)
            p2_key = ensure_player(store, player2)

            winner_key = normalize(winner)

            if winner_key not in [p1_key, p2_key]:
                continue

            update_pair(
                store=store,
                p1_key=p1_key,
                p2_key=p2_key,
                surface=surface,
                winner_key=winner_key,
                match_date=match_date,
                reference_date=reference_date,
            )

        except Exception:
            continue

    return store


def predict(player1, player2, surface, store):
    p1_key = find_player_key(store, player1)
    p2_key = find_player_key(store, player2)

    p1_found = p1_key is not None
    p2_found = p2_key is not None

    if p1_found:
        p1_record = store[p1_key]
    else:
        p1_record = {
            "overall_elo": START_ELO,
            "overall_matches": 0,
            "surface_elo": {
                "hard": START_ELO,
                "clay": START_ELO,
                "grass": START_ELO,
                "carpet": START_ELO,
            },
            "surface_matches": {
                "hard": 0,
                "clay": 0,
                "grass": 0,
                "carpet": 0,
            },
        }

    if p2_found:
        p2_record = store[p2_key]
    else:
        p2_record = {
            "overall_elo": START_ELO,
            "overall_matches": 0,
            "surface_elo": {
                "hard": START_ELO,
                "clay": START_ELO,
                "grass": START_ELO,
                "carpet": START_ELO,
            },
            "surface_matches": {
                "hard": 0,
                "clay": 0,
                "grass": 0,
                "carpet": 0,
            },
        }

    s_key = surface_key(surface)

    p1_rating = blended_rating(p1_record, surface)
    p2_rating = blended_rating(p2_record, surface)

    raw_p1 = expected_score(p1_rating, p2_rating)
    calibrated_p1 = calibrated_probability(raw_p1)

    p1_matches = int(p1_record.get("overall_matches", 0))
    p2_matches = int(p2_record.get("overall_matches", 0))

    p1_surface_matches = int(p1_record.get("surface_matches", {}).get(s_key, 0))
    p2_surface_matches = int(p2_record.get("surface_matches", {}).get(s_key, 0))

    p1_rel = reliability_from_matches(p1_matches)
    p2_rel = reliability_from_matches(p2_matches)

    p1_surface_rel = surface_reliability_from_matches(p1_surface_matches)
    p2_surface_rel = surface_reliability_from_matches(p2_surface_matches)

    min_rel = min(p1_rel, p2_rel)

    if min_rel < 0.25:
        calibrated_p1 = 0.5 + (calibrated_p1 - 0.5) * 0.80
    elif min_rel < 0.40:
        calibrated_p1 = 0.5 + (calibrated_p1 - 0.5) * 0.90

    calibrated_p1 = max(0.05, min(0.95, calibrated_p1))

    return {
        "probability_player1": round(calibrated_p1, 4),
        "probability_player2": round(1.0 - calibrated_p1, 4),

        "elo_player1": round(p1_rating, 2),
        "elo_player2": round(p2_rating, 2),

        "overall_elo_player1": round(float(p1_record.get("overall_elo", START_ELO)), 2),
        "overall_elo_player2": round(float(p2_record.get("overall_elo", START_ELO)), 2),

        "surface_elo_player1": round(float(p1_record.get("surface_elo", {}).get(s_key, START_ELO)), 2),
        "surface_elo_player2": round(float(p2_record.get("surface_elo", {}).get(s_key, START_ELO)), 2),

        "elo_found_player1": p1_found,
        "elo_found_player2": p2_found,

        "elo_matched_key_player1": p1_key,
        "elo_matched_key_player2": p2_key,

        "elo_matches_player1": p1_matches,
        "elo_matches_player2": p2_matches,

        "surface_matches_player1": p1_surface_matches,
        "surface_matches_player2": p2_surface_matches,

        "elo_reliability_player1": p1_rel,
        "elo_reliability_player2": p2_rel,

        "surface_reliability_player1": p1_surface_rel,
        "surface_reliability_player2": p2_surface_rel,

        "surface": s_key,
        "raw_probability_player1": round(raw_p1, 4),
        "model": "SURFACE_ELO_DECAY_DYNAMIC_K_CALIBRATED_V1",
    }


def save(store):
    os.makedirs("data", exist_ok=True)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def load():
    if not os.path.exists(DATA_PATH):
        return {}

    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_and_save(matches):
    store = build_elo(matches)
    save(store)
    return store
