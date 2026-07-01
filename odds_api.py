import json
import os
import re
import unicodedata
from datetime import datetime, timezone

import requests

from ts import fetch_ts_public_odds


ODDS_API_KEY = os.getenv("ODDS_API_KEY")
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY") or ODDS_API_KEY

ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY")
ODDS_API_NET_KEY = os.getenv("ODDS_API_NET_KEY")

REGIONS = os.getenv("ODDS_API_REGIONS", "eu,uk")
MARKETS = os.getenv("ODDS_API_MARKETS", "h2h")
ODDS_FORMAT = "decimal"

DEBUG_PATH = "public/odds_debug.json"
SNAPSHOT_PATH = "public/odds_snapshot.json"


THE_ODDS_API_SPORT_KEYS = [
    "tennis_atp_wimbledon",
    "tennis_atp_french_open",
    "tennis_atp_us_open",
    "tennis_atp_aus_open_singles",
    "tennis_atp_halle_open",
    "tennis_atp_queens_club_champ",
    "tennis_atp_mallorca_open",
    "tennis_atp_eastbourne",
    "tennis_atp_hamburg_open",
    "tennis_atp_munich",
    "tennis_atp_dubai",
    "tennis_atp_qatar_open",
    "tennis_atp_monte_carlo_masters",
    "tennis_atp_madrid_open",
    "tennis_atp_italian_open",
    "tennis_atp_canadian_open",
    "tennis_atp_cincinnati_open",
    "tennis_atp_shanghai_masters",
    "tennis_atp_paris_masters",

    "tennis_wta_wimbledon",
    "tennis_wta_french_open",
    "tennis_wta_us_open",
    "tennis_wta_aus_open_singles",
    "tennis_wta_bad_homburg_open",
    "tennis_wta_berlin_open",
    "tennis_wta_eastbourne",
    "tennis_wta_nottingham_open",
    "tennis_wta_canadian_open",
    "tennis_wta_cincinnati_open",
    "tennis_wta_madrid_open",
    "tennis_wta_italian_open",
]


def ensure_public_dir():
    os.makedirs("public", exist_ok=True)


def normalize_name(name):
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


def tokens(name):
    text = normalize_name(name)

    if not text:
        return set()

    return set(text.split())


def similarity(a, b):
    a_tokens = tokens(a)
    b_tokens = tokens(b)

    if not a_tokens or not b_tokens:
        return 0.0

    overlap = len(a_tokens.intersection(b_tokens))
    total = max(len(a_tokens), len(b_tokens))

    score = overlap / total

    a_parts = normalize_name(a).split()
    b_parts = normalize_name(b).split()

    if a_parts and b_parts and a_parts[-1] == b_parts[-1]:
        score += 0.35

    return min(score, 1.0)


def match_score(player1, player2, home, away):
    direct = min(
        similarity(player1, home),
        similarity(player2, away),
    )

    reverse = min(
        similarity(player1, away),
        similarity(player2, home),
    )

    return max(direct, reverse), direct >= reverse


def decimal_from_american(price):
    try:
        p = float(price)
    except Exception:
        return None

    if p <= 0:
        return round(1 + (100 / abs(p)), 3)

    return round(1 + (p / 100), 3)


def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)
    except Exception:
        return None


def fetch_json(url, headers=None, params=None, timeout=25):
    try:
        response = requests.get(
            url,
            headers=headers or {},
            params=params or {},
            timeout=timeout,
        )

        info = {
            "url": response.url,
            "status_code": response.status_code,
            "ok": response.status_code == 200,
            "headers": {
                "x-requests-remaining": response.headers.get("x-requests-remaining"),
                "x-requests-used": response.headers.get("x-requests-used"),
                "x-requests-last": response.headers.get("x-requests-last"),
            },
        }

        if response.status_code != 200:
            info["text_preview"] = response.text[:300]
            return None, info

        try:
            return response.json(), info
        except Exception as e:
            info["json_error"] = str(e)
            info["text_preview"] = response.text[:300]
            return None, info

    except Exception as e:
        return None, {
            "url": url,
            "ok": False,
            "error": str(e),
        }


def normalize_the_odds_api_event(event, sport_key):
    home = event.get("home_team")
    away = event.get("away_team")

    if not home or not away:
        return None

    best_home = None
    best_away = None
    bookmaker_key = None

    for bookmaker in event.get("bookmakers", []) or []:
        bookmaker_key = bookmaker.get("key") or bookmaker.get("title")

        for market in bookmaker.get("markets", []) or []:
            if market.get("key") != "h2h":
                continue

            for outcome in market.get("outcomes", []) or []:
                name = outcome.get("name")
                price = outcome.get("price")

                odd = safe_float(price)

                if odd is None:
                    odd = decimal_from_american(price)

                if not name or odd is None:
                    continue

                if normalize_name(name) == normalize_name(home):
                    best_home = odd

                if normalize_name(name) == normalize_name(away):
                    best_away = odd

            if best_home and best_away:
                return {
                    "provider": "the_odds_api",
                    "bookmaker": bookmaker_key,
                    "sport_key": sport_key,
                    "event_id": event.get("id"),
                    "home_team": home,
                    "away_team": away,
                    "player1": home,
                    "player2": away,
                    "odds_player1": best_home,
                    "odds_player2": best_away,
                    "commence_time": event.get("commence_time"),
                }

    return None


def fetch_the_odds_api():
    debug = {
        "provider": "the_odds_api",
        "enabled": bool(THE_ODDS_API_KEY),
        "sport_keys_attempted": [],
        "events_raw": 0,
        "odds_records": 0,
        "errors": [],
    }

    if not THE_ODDS_API_KEY:
        return [], debug

    records = []

    for sport_key in THE_ODDS_API_SPORT_KEYS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"

        params = {
            "apiKey": THE_ODDS_API_KEY,
            "regions": REGIONS,
            "markets": MARKETS,
            "oddsFormat": ODDS_FORMAT,
        }

        data, info = fetch_json(url, params=params)

        debug["sport_keys_attempted"].append({
            "sport_key": sport_key,
            "status": info.get("status_code"),
            "ok": info.get("ok"),
            "remaining": info.get("headers", {}).get("x-requests-remaining"),
            "used": info.get("headers", {}).get("x-requests-used"),
            "last": info.get("headers", {}).get("x-requests-last"),
        })

        if data is None:
            continue

        if not isinstance(data, list):
            continue

        debug["events_raw"] += len(data)

        for event in data:
            record = normalize_the_odds_api_event(event, sport_key)

            if record:
                records.append(record)

    debug["odds_records"] = len(records)
    return records, debug


def normalize_generic_event(event):
    home = (
        event.get("home")
        or event.get("home_team")
        or event.get("homeTeam")
        or event.get("participant1")
        or event.get("player1")
    )

    away = (
        event.get("away")
        or event.get("away_team")
        or event.get("awayTeam")
        or event.get("participant2")
        or event.get("player2")
    )

    if not home or not away:
        return None

    odds_home = None
    odds_away = None
    bookmaker = None

    bookmakers = event.get("bookmakers") or event.get("books") or {}

    if isinstance(bookmakers, dict):
        for book_name, markets in bookmakers.items():
            bookmaker = book_name

            if isinstance(markets, list):
                for market in markets:
                    name = str(market.get("name") or market.get("key") or "").lower()

                    if name not in ["ml", "moneyline", "h2h", "match winner", "winner"]:
                        continue

                    odds_obj = market.get("odds") or market.get("outcomes")

                    if isinstance(odds_obj, list):
                        for outcome in odds_obj:
                            if "home" in outcome and "away" in outcome:
                                odds_home = safe_float(outcome.get("home"))
                                odds_away = safe_float(outcome.get("away"))
                                break

                            out_name = outcome.get("name")
                            price = outcome.get("price") or outcome.get("odd")

                            if out_name and normalize_name(out_name) == normalize_name(home):
                                odds_home = safe_float(price)

                            if out_name and normalize_name(out_name) == normalize_name(away):
                                odds_away = safe_float(price)

                    elif isinstance(odds_obj, dict):
                        odds_home = safe_float(
                            odds_obj.get("home")
                            or odds_obj.get(home)
                        )
                        odds_away = safe_float(
                            odds_obj.get("away")
                            or odds_obj.get(away)
                        )

                    if odds_home and odds_away:
                        break

            if odds_home and odds_away:
                break

    if odds_home is None:
        odds_home = safe_float(
            event.get("odds_home")
            or event.get("home_odds")
            or event.get("odds1")
        )

    if odds_away is None:
        odds_away = safe_float(
            event.get("odds_away")
            or event.get("away_odds")
            or event.get("odds2")
        )

    if odds_home is None or odds_away is None:
        return None

    return {
        "provider": "generic_odds_api",
        "bookmaker": bookmaker,
        "event_id": event.get("id") or event.get("eventId"),
        "home_team": home,
        "away_team": away,
        "player1": home,
        "player2": away,
        "odds_player1": odds_home,
        "odds_player2": odds_away,
        "commence_time": event.get("date") or event.get("commence_time") or event.get("startTime"),
    }


def fetch_odds_api_io():
    debug = {
        "provider": "odds_api_io",
        "enabled": bool(ODDS_API_IO_KEY),
        "events_raw": 0,
        "odds_records": 0,
        "status": None,
        "errors": [],
    }

    if not ODDS_API_IO_KEY:
        return [], debug

    url = "https://api.odds-api.io/v3/events"

    params = {
        "apiKey": ODDS_API_IO_KEY,
        "sport": "tennis",
    }

    data, info = fetch_json(url, params=params)

    debug["status"] = info.get("status_code")
    debug["ok"] = info.get("ok")

    if data is None:
        return [], debug

    if isinstance(data, dict):
        events = data.get("events") or data.get("data") or data.get("results") or []
    elif isinstance(data, list):
        events = data
    else:
        events = []

    debug["events_raw"] = len(events)

    records = []

    for event in events:
        record = normalize_generic_event(event)

        if record:
            record["provider"] = "odds_api_io"
            records.append(record)

    debug["odds_records"] = len(records)
    return records, debug


def fetch_odds_api_net():
    debug = {
        "provider": "odds_api_net",
        "enabled": bool(ODDS_API_NET_KEY),
        "events_raw": 0,
        "odds_records": 0,
        "errors": [],
    }

    if not ODDS_API_NET_KEY:
        return [], debug

    base_url = os.getenv("ODDS_API_NET_BASE_URL", "https://api.odds-api.net/v1")
    headers = {
        "X-API-Key": ODDS_API_NET_KEY,
    }

    sports_url = base_url.rstrip("/") + "/sports"
    sports_data, sports_info = fetch_json(sports_url, headers=headers)

    debug["sports_status"] = sports_info.get("status_code")
    debug["sports_ok"] = sports_info.get("ok")

    events_url = base_url.rstrip("/") + "/events"
    events_data, events_info = fetch_json(
        events_url,
        headers=headers,
        params={"sport": "tennis"},
    )

    debug["events_status"] = events_info.get("status_code")
    debug["events_ok"] = events_info.get("ok")

    if events_data is None:
        return [], debug

    if isinstance(events_data, dict):
        events = events_data.get("events") or events_data.get("data") or events_data.get("results") or []
    elif isinstance(events_data, list):
        events = events_data
    else:
        events = []

    debug["events_raw"] = len(events)

    records = []

    for event in events:
        record = normalize_generic_event(event)

        if record:
            record["provider"] = "odds_api_net"
            records.append(record)

    debug["odds_records"] = len(records)
    return records, debug


def dedupe_records(records):
    output = {}

    for record in records:
        key = "::".join([
            normalize_name(record.get("home_team")),
            normalize_name(record.get("away_team")),
            str(record.get("odds_player1")),
            str(record.get("odds_player2")),
            str(record.get("provider")),
        ])

        output[key] = record

    return list(output.values())


def fetch_odds():
    ensure_public_dir()

    all_records = []
    debug = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "providers": {},
    }

    provider_functions = [
        ("the_odds_api", fetch_the_odds_api),
        ("odds_api_io", fetch_odds_api_io),
        ("odds_api_net", fetch_odds_api_net),
        ("ts", fetch_ts_public_odds),
    ]

    for provider_name, fn in provider_functions:
        try:
            records, provider_debug = fn()
            debug["providers"][provider_name] = provider_debug
            all_records.extend(records or [])
        except Exception as e:
            debug["providers"][provider_name] = {
                "provider": provider_name,
                "enabled": True,
                "error": str(e),
                "odds_records": 0,
            }

    all_records = dedupe_records(all_records)

    debug["total_odds_records"] = len(all_records)

    with open(DEBUG_PATH, "w", encoding="utf-8") as f:
        json.dump(debug, f, ensure_ascii=False, indent=2)

    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print("ODDS RECORDS TOTAL:", len(all_records))
    print("ODDS DEBUG:", debug)

    return all_records


def find_match_odds(player1, player2, odds_matches):
    best = None
    best_score = 0.0
    best_direct = True

    for record in odds_matches or []:
        home = record.get("home_team") or record.get("player1")
        away = record.get("away_team") or record.get("player2")

        if not home or not away:
            continue

        score, direct = match_score(player1, player2, home, away)

        if score > best_score:
            best_score = score
            best = record
            best_direct = direct

    if not best or best_score < 0.55:
        return {
            "odds_player1": None,
            "odds_player2": None,
            "odds_source": None,
            "bookmaker": None,
            "event_id": None,
            "match_score": round(best_score, 3),
        }

    if best_direct:
        odds_player1 = best.get("odds_player1")
        odds_player2 = best.get("odds_player2")
    else:
        odds_player1 = best.get("odds_player2")
        odds_player2 = best.get("odds_player1")

    return {
        "odds_player1": safe_float(odds_player1),
        "odds_player2": safe_float(odds_player2),
        "odds_source": best.get("provider"),
        "bookmaker": best.get("bookmaker"),
        "event_id": best.get("event_id"),
        "match_score": round(best_score, 3),
    }
