import json
import os
import re
import unicodedata
from datetime import datetime, timezone

import requests


DEBUG_PATH = "public/ts_debug.json"
SNAPSHOT_PATH = "public/ts_odds_snapshot.json"


TS_BASES = [
    "https://www.tipsport.cz",
    "https://www.tipsport.sk",
]


TS_ENDPOINT_CANDIDATES = [
    "/rest/offer/v4/offer",
    "/rest/offer/v3/offer",
    "/rest/offer/offer",
    "/api/rest/offer/v4/offer",
    "/api/rest/offer/v3/offer",

    "/rest/offer/v4/eventTables",
    "/rest/offer/v3/eventTables",
    "/rest/offer/eventTables",
    "/api/rest/offer/v4/eventTables",
    "/api/rest/offer/v3/eventTables",

    "/rest/offer/v4/search",
    "/rest/offer/v3/search",
]


USER_AGENT = (
    "Mozilla/5.0 (compatible; tennis-backstage-talks/1.0; "
    "+https://backstagetalks.github.io/tennis-backstage-talks/)"
)


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


def request_json(url, params=None):
    try:
        response = requests.get(
            url,
            params=params or {},
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://www.tipsport.cz/",
            },
            timeout=20,
        )

        info = {
            "url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "ok": response.status_code == 200,
        }

        if response.status_code != 200:
            info["text_preview"] = response.text[:300]
            return None, info

        text = response.text.strip()

        if not text:
            info["empty_response"] = True
            return None, info

        try:
            return response.json(), info
        except Exception:
            info["json_error"] = "response_not_json"
            info["text_preview"] = text[:300]
            return None, info

    except Exception as e:
        return None, {
            "url": url,
            "params": params or {},
            "ok": False,
            "error": str(e),
        }


def flatten(obj):
    if isinstance(obj, dict):
        yield obj

        for value in obj.values():
            yield from flatten(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from flatten(item)


def looks_like_tennis_text(value):
    text = normalize_name(value)

    tennis_terms = [
        "tenis",
        "tennis",
        "atp",
        "wta",
        "challenger",
        "itf",
        "wimbledon",
        "australian open",
        "french open",
        "us open",
    ]

    return any(term in text for term in tennis_terms)


def record_contains_tennis_hint(record):
    if not isinstance(record, dict):
        return False

    for value in record.values():
        if isinstance(value, str) and looks_like_tennis_text(value):
            return True

        if isinstance(value, dict):
            if record_contains_tennis_hint(value):
                return True

        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and looks_like_tennis_text(item):
                    return True
                if isinstance(item, dict) and record_contains_tennis_hint(item):
                    return True

    return False


def extract_event_id(record):
    for key in [
        "eventId",
        "event_id",
        "matchId",
        "match_id",
        "id",
    ]:
        value = record.get(key)

        if value is not None:
            return str(value)

    return None


def extract_odd_value(record):
    for key in [
        "odd",
        "currentOdd",
        "price",
        "odds",
        "value",
    ]:
        value = record.get(key)

        if value is None:
            continue

        try:
            odd = float(value)

            if 1.01 <= odd <= 100:
                return odd
        except Exception:
            continue

    return None


def extract_cell_name(record):
    for key in [
        "name",
        "opportunityName",
        "selectionName",
        "participantName",
        "title",
    ]:
        value = record.get(key)

        if value:
            return str(value)

    return ""


def extract_event_name(record):
    for key in [
        "eventName",
        "matchName",
        "fullName",
        "name",
        "title",
        "competitionName",
    ]:
        value = record.get(key)

        if value:
            return str(value)

    return ""


def is_active(record):
    if "active" in record:
        return bool(record.get("active"))

    return True


def parse_records_to_raw_cells(data):
    rows = []

    for record in flatten(data):
        if not isinstance(record, dict):
            continue

        odd = extract_odd_value(record)

        if odd is None:
            continue

        if not is_active(record):
            continue

        event_id = extract_event_id(record)
        cell_name = extract_cell_name(record)
        event_name = extract_event_name(record)

        rows.append({
            "provider": "ts",
            "event_id": event_id,
            "event_name": event_name,
            "cell_name": cell_name,
            "odd": odd,
            "raw_keys": list(record.keys())[:30],
            "raw": {
                k: record.get(k)
                for k in record.keys()
                if k in [
                    "name",
                    "id",
                    "eventId",
                    "odd",
                    "currentOdd",
                    "active",
                    "winning",
                    "oppNumber",
                    "opportunityName",
                    "selectionName",
                ]
            },
        })

    return rows


def dedupe_raw_cells(raw_cells):
    deduped = {}

    for cell in raw_cells:
        key = "::".join([
            str(cell.get("event_id")),
            normalize_name(cell.get("cell_name")),
            str(cell.get("odd")),
        ])

        deduped[key] = cell

    return list(deduped.values())


def group_cells_to_match_odds(raw_cells):
    grouped = {}

    for cell in raw_cells:
        event_id = cell.get("event_id")

        if not event_id:
            continue

        grouped.setdefault(event_id, []).append(cell)

    matches = []

    for event_id, cells in grouped.items():
        clean_cells = [
            c for c in cells
            if c.get("cell_name") and c.get("odd")
        ]

        if len(clean_cells) < 2:
            continue

        first_two = clean_cells[:2]

        player1 = first_two[0]["cell_name"]
        player2 = first_two[1]["cell_name"]

        if normalize_name(player1) == normalize_name(player2):
            continue

        matches.append({
            "provider": "ts",
            "bookmaker": "TS",
            "event_id": event_id,
            "home_team": player1,
            "away_team": player2,
            "player1": player1,
            "player2": player2,
            "odds_player1": first_two[0]["odd"],
            "odds_player2": first_two[1]["odd"],
            "commence_time": None,
            "raw_market_size": len(clean_cells),
        })

    return matches


def fetch_ts_endpoint_candidates():
    debug = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "ts",
        "endpoint_attempts": [],
        "raw_cells_count": 0,
        "match_odds_count": 0,
        "errors": [],
    }

    all_raw_cells = []

    params_candidates = [
        {},
        {"sport": "tenis"},
        {"sport": "tennis"},
        {"lang": "cz"},
    ]

    for base in TS_BASES:
        for endpoint in TS_ENDPOINT_CANDIDATES:
            url = base.rstrip("/") + endpoint

            for params in params_candidates:
                data, info = request_json(url, params=params)
                info["params"] = params
                debug["endpoint_attempts"].append(info)

                if data is None:
                    continue

                raw_cells = parse_records_to_raw_cells(data)

                if raw_cells:
                    all_raw_cells.extend(raw_cells)

    raw_cells_output = dedupe_raw_cells(all_raw_cells)
    match_odds = group_cells_to_match_odds(raw_cells_output)

    debug["raw_cells_count"] = len(raw_cells_output)
    debug["match_odds_count"] = len(match_odds)

    ensure_public_dir()

    with open(DEBUG_PATH, "w", encoding="utf-8") as f:
        json.dump(debug, f, ensure_ascii=False, indent=2)

    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(match_odds, f, ensure_ascii=False, indent=2)

    print("TS RAW CELLS:", len(raw_cells_output))
    print("TS MATCH ODDS:", len(match_odds))

    return match_odds, debug


def fetch_ts_public_odds():
    try:
        match_odds, debug = fetch_ts_endpoint_candidates()
        return match_odds, debug

    except Exception as e:
        debug = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": "ts",
            "error": str(e),
            "raw_cells_count": 0,
            "match_odds_count": 0,
        }

        ensure_public_dir()

        with open(DEBUG_PATH, "w", encoding="utf-8") as f:
            json.dump(debug, f, ensure_ascii=False, indent=2)

        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

        return [], debug


if __name__ == "__main__":
    odds, debug_data = fetch_ts_public_odds()

    print(json.dumps(debug_data, ensure_ascii=False, indent=2))
    print("TS ODDS SAMPLE:")
    print(json.dumps(odds[:10], ensure_ascii=False, indent=2))
