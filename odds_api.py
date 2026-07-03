if left_initials[0] == right_initials```

---

```python
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher

import requests


ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4/sports"

DEFAULT_SPORT_KEYS = [
    "tennis_atp_wimbledon",
    "tennis_wta_wimbledon",
    "tennis_atp",
    "tennis_wta",
]

DEFAULT_REGIONS = "eu,uk,us,au"
DEFAULT_MARKETS = "h2h"
DEFAULT_ODDS_FORMAT = "decimal"

REQUEST_TIMEOUT_SECONDS = 25

MATCH_SCORE_THRESHOLD = 0.82
OUTCOME_SCORE_THRESHOLD = 0.84

DEBUG_PATH = "public/odds_debug.json"


def get_api_key():
    return os.getenv("ODDS_API_KEY")


def get_sport_keys():
    value = os.getenv("ODDS_SPORT_KEYS")

    if not value:
        return DEFAULT_SPORT_KEYS

    keys = []

    for item in value.split(","):
        item = item.strip()

        if item:
            keys.append(item)

    if not keys:
        return DEFAULT_SPORT_KEYS

    return keys


def get_regions():
    return os.getenv(
        "ODDS_REGIONS",
        DEFAULT_REGIONS,
    )


def normalize_name(name):
    if name is None:
        return ""

    text = str(name).strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    replacements = {
        "-": " ",
        "_": " ",
        ".": " ",
        ",": " ",
        "'": " ",
        "’": " ",
        "`": " ",
        "´": " ",
        "(": " ",
        ")": " ",
        "[": " ",
        "]": " ",
        "{": " ",
        "}": " ",
        "/": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def name_tokens(name):
    normalized = normalize_name(name)

    if not normalized:
        return []

    return [
        token
        for token in normalized.split(" ")
        if token
    ]


def sorted_token_key(name):
    tokens = name_tokens(name)

    return " ".join(
        sorted(tokens)
    )


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def sequence_score(left, right):
    left_normalized = normalize_name(left)
    right_normalized = normalize_name(right)

    if not left_normalized or not right_normalized:
        return 0.0

    if left_normalized == right_normalized:
        return 1.0

    if sorted_token_key(left_normalized) == sorted_token_key(right_normalized):
        return 0.98

    return SequenceMatcher(
        None,
        left_normalized,
        right_normalized,
    ).ratio()


def token_overlap_score(left, right):
    left_tokens = set(
        name_tokens(left)
    )

    right_tokens = set(
        name_tokens(right)
    )

    if not left_tokens or not right_tokens:
        return 0.0

    intersection = left_tokens.intersection(
        right_tokens
    )

    union = left_tokens.union(
        right_tokens
    )

    if not union:
        return 0.0

    return len(intersection) / len(union)


def last_name_score(left, right):
    left_tokens = name_tokens(left)
    right_tokens = name_tokens(right)

    if not left_tokens or not right_tokens:
        return 0.0

    left_last = left_tokens[-1]
    right_last = right_tokens[-1]

    if left_last != right_last:
        return 0.0

    if len(left_tokens) == 1 or len(right_tokens) == 1:
        return 0.82

    left_initials = "".join(
        token[0]
        for token in left_tokens[:-1]
        if token
    )

    right_initials = "".join(
        token[0]
        for token in right_tokens[:-1]
        if token
    )


if left_initials and right_initials:
        if left_initials == right_initials:
            return 0.95

        if left_initials[0] == right_initialsreturn 0.88

    return 0.86



def name_match_score(left, right):
    scores = [
        sequence_score(left, right),
        token_overlap_score(left, right),
        last_name_score(left, right),
    ]

    return max(scores)


def event_match_score(player1, player2, event):
    home_team = event.get("home_team")
    away_team = event.get("away_team")

    if not home_team or not away_team:
        return 0.0

    direct_score = (
        name_match_score(player1, home_team)
        + name_match_score(player2, away_team)
    ) / 2.0

    reverse_score = (
        name_match_score(player1, away_team)
        + name_match_score(player2, home_team)
    ) / 2.0

    return max(
        direct_score,
        reverse_score,
    )


def confidence_label(score):
    if score >= 0.97:
        return "exact"

    if score >= 0.90:
        return "strong"

    if score >= MATCH_SCORE_THRESHOLD:
        return "fuzzy"

    return "low"


def is_h2h_market(market):
    return market.get("key") == "h2h"


def iter_h2h_outcomes(event):
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if not is_h2h_market(market):
                continue

            for outcome in market.get("outcomes", []):
                name = outcome.get("name")
                price = safe_float(
                    outcome.get("price")
                )

                if not name:
                    continue

