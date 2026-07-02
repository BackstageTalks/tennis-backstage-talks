import os
import csv
import json
import unicodedata
from difflib import SequenceMatcher


DEFAULT_ELO = 1500.0

ALIASES_PATH = "data/player_aliases.json"
ELO_DEBUG_PATH = "public/elo_debug.json"


ELO_CANDIDATE_FILES = [
    "data/elo/elo_store.json",
    "data/elo/elo.json",
    "data/elo/atp_elo_latest.csv",
    "data/elo/wta_elo_latest.csv",
    "data/elo/latest_elo.csv",
    "data/elo/elo_latest.csv",
    "elo_store.json",
    "elo.json",
]


_DEBUG = {
    "provider": "elo_engine_v2_safe_matcher",
    "loaded_files": [],
    "players_loaded": 0,

    "lookup_count": 0,
    "found_count": 0,
    "missing_count": 0,

    "examples_found": [],
    "examples_missing": [],
}


def write_debug():
    os.makedirs(
        "public",
        exist_ok=True,
    )

    with open(
        ELO_DEBUG_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            _DEBUG,
            file,
            indent=2,
            ensure_ascii=False,
        )


def normalize_name(name):
    if not name:
        return ""

    value = str(name)

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()

    value = value.replace("-", " ")
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = value.replace("'", "")
    value = value.replace("’", "")
    value = value.replace("`", "")

    return " ".join(value.split())


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize_name(a),
        normalize_name(b),
    ).ratio()


def last_name(name):
    normalized = normalize_name(name)

    if not normalized:
        return ""

    parts = normalized.split()

    return parts[-1]


def first_token(name):
    normalized = normalize_name(name)

    if not normalized:
        return ""

    parts = normalized.split()

    return parts[0]


def load_aliases():
    if not os.path.exists(ALIASES_PATH):
        return {}

    try:
        with open(
            ALIASES_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            raw_aliases = json.load(file)

    except Exception:
        return {}

    aliases = {}

    for alias, canonical in raw_aliases.items():
        aliases[
            normalize_name(alias)
        ] = canonical

    return aliases


def safe_float(value, default=None):
    try:
        if value is None:
            return default

        if value == "":
            return default

        return float(value)

    except Exception:
        return default


def detect_name(row):
    for key in [
        "player",
        "Player",
        "name",
        "Name",
        "player_name",
        "Player Name",
    ]:
        if key in row and row.get(key):
            return row.get(key)

    return None


def detect_elo(row):
    candidates = [
        "elo",
        "Elo",
        "ELO",
        "rating",
        "Rating",
        "overall_elo",
        "overall",
        "Overall",
    ]

    for key in candidates:
        if key in row:
            value = safe_float(row.get(key))

            if value is not None:
                return value

    return None


def detect_yelo(row):
    candidates = [
        "yelo",
        "Yelo",
        "YELO",
        "year_elo",
        "season_elo",
    ]

    for key in candidates:
        if key in row:
            value = safe_float(row.get(key))

            if value is not None:
                return value

    return None


def detect_surface_elos(row):
    surfaces = {}

    mapping = {
        "hard": [
            "hard_elo",
            "Hard Elo",
            "hard",
            "Hard",
        ],
        "clay": [
            "clay_elo",
            "Clay Elo",
            "clay",
            "Clay",
        ],
        "grass": [
            "grass_elo",
            "Grass Elo",
            "grass",
            "Grass",
        ],
        "indoor": [
            "indoor_elo",
            "Indoor Elo",
            "indoor",
            "Indoor",
        ],
    }

    for surface, keys in mapping.items():
        for key in keys:
            if key in row:
                value = safe_float(row.get(key))

                if value is not None:
                    surfaces[surface] = value
                    break

    return surfaces


def add_record(store, name, record):
    if not name:
        return

    normalized = normalize_name(name)

    if not normalized:
        return

    record["name"] = name
    record["normalized_name"] = normalized

    store[normalized] = record


def load_json_file(path):
    store = {}

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if isinstance(data, dict):

        if "players" in data:
            players = data.get("players")

            if isinstance(players, dict):
                iterable = players.items()

                for name, value in iterable:
                    if isinstance(value, dict):
                        elo = safe_float(
                            value.get("elo")
                            or value.get("rating")
                            or value.get("overall_elo"),
                            DEFAULT_ELO,
                        )

                        yelo = safe_float(
                            value.get("yelo")
                            or value.get("year_elo")
                            or value.get("season_elo"),
                            elo,
                        )

                        surfaces = value.get("surfaces") or {}

                        record = {
                            "elo": elo,
                            "yelo": yelo,
                            "surfaces": surfaces,
                            "source": path,
                            "raw": value,
                        }

                        add_record(
                            store,
                            name,
                            record,
                        )

            elif isinstance(players, list):
                for value in players:
                    if not isinstance(value, dict):
                        continue

                    name = detect_name(value)

                    if not name:
                        continue

                    elo = detect_elo(value)

                    if elo is None:
                        elo = DEFAULT_ELO

                    yelo = detect_yelo(value)

                    if yelo is None:
                        yelo = elo

                    record = {
                        "elo": elo,
                        "yelo": yelo,
                        "surfaces": detect_surface_elos(value),
                        "source": path,
                        "raw": value,
                    }

                    add_record(
                        store,
                        name,
                        record,
                    )

        else:
            for name, value in data.items():
                if isinstance(value, dict):
                    elo = safe_float(
                        value.get("elo")
                        or value.get("rating")
                        or value.get("overall_elo"),
                        DEFAULT_ELO,
                    )

                    yelo = safe_float(
                        value.get("yelo")
                        or value.get("year_elo")
                        or value.get("season_elo"),
                        elo,
                    )

                    record = {
                        "elo": elo,
                        "yelo": yelo,
                        "surfaces": value.get("surfaces") or {},
                        "source": path,
                        "raw": value,
                    }

                    add_record(
                        store,
                        name,
                        record,
                    )

                else:
                    elo = safe_float(value)

                    if elo is not None:
                        record = {
                            "elo": elo,
                            "yelo": elo,
                            "surfaces": {},
                            "source": path,
                            "raw": value,
                        }

                        add_record(
                            store,
                            name,
                            record,
                        )

    elif isinstance(data, list):
        for value in data:
            if not isinstance(value, dict):
                continue

            name = detect_name(value)

            if not name:
                continue

            elo = detect_elo(value)

            if elo is None:
                elo = DEFAULT_ELO

            yelo = detect_yelo(value)

            if yelo is None:
                yelo = elo

            record = {
                "elo": elo,
                "yelo": yelo,
                "surfaces": detect_surface_elos(value),
                "source": path,
                "raw": value,
            }

            add_record(
                store,
                name,
                record,
            )

    return store


def load_csv_file(path):
    store = {}

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            name = detect_name(row)

            if not name:
                continue

            elo = detect_elo(row)

            if elo is None:
                elo = DEFAULT_ELO

            yelo = detect_yelo(row)

            if yelo is None:
                yelo = elo

            record = {
                "elo": elo,
                "yelo": yelo,
                "surfaces": detect_surface_elos(row),
                "source": path,
                "raw": row,
            }

            add_record(
                store,
                name,
                record,
            )

    return store


def load():
    """
    Existing prediction engines call this function.

    Returns:
        dict normalized_name -> player ELO record
    """

    store = {}

    for path in ELO_CANDIDATE_FILES:
        if not os.path.exists(path):
            continue

        try:
            if path.endswith(".json"):
                loaded = load_json_file(path)

            elif path.endswith(".csv"):
                loaded = load_csv_file(path)

            else:
                loaded = {}

            if loaded:
                store.update(loaded)

                _DEBUG["loaded_files"].append({
                    "path": path,
                    "players": len(loaded),
                })

        except Exception as exc:
            _DEBUG["loaded_files"].append({
                "path": path,
                "error": str(exc),
            })

    _DEBUG["players_loaded"] = len(store)

    write_debug()

    return store


def candidate_matches_by_initial(player_name, store):
    normalized = normalize_name(player_name)
    parts = normalized.split()

    if len(parts) < 2:
        return []

    first = parts[0]
    last = parts[-1]

    if len(first) != 1:
        return []

    matches = []

    for key, record in store.items():
        rec_name = record.get("name", key)
        rec_first = first_token(rec_name)
        rec_last = last_name(rec_name)

        if rec_last == last and rec_first.startswith(first):
            matches.append((key, record, 1.0))

    return matches


def find_player_record(player_name, store):
    """
    Safe player lookup.

    Order:
    1. exact normalized match
    2. alias match
    3. initial + last name match
    4. conservative fuzzy match
    """

    _DEBUG["lookup_count"] += 1

    aliases = load_aliases()
    normalized = normalize_name(player_name)

    if not normalized:
        _DEBUG["missing_count"] += 1

        return {
            "found": False,
            "record": None,
            "matched_name": None,
            "match_method": "empty",
            "match_score": 0.0,
        }

    # 1. exact normalized
    if normalized in store:
        record = store[normalized]

        _DEBUG["found_count"] += 1

        if len(_DEBUG["examples_found"]) < 30:
            _DEBUG["examples_found"].append({
                "input": player_name,
                "matched": record.get("name"),
                "method": "exact",
                "score": 1.0,
            })

        return {
            "found": True,
            "record": record,
            "matched_name": record.get("name"),
            "match_method": "exact",
            "match_score": 1.0,
        }

    # 2. alias
    alias_target = aliases.get(normalized)

    if alias_target:
        alias_normalized = normalize_name(alias_target)

        if alias_normalized in store:
            record = store[alias_normalized]

            _DEBUG["found_count"] += 1

            if len(_DEBUG["examples_found"]) < 30:
                _DEBUG["examples_found"].append({
                    "input": player_name,
                    "matched": record.get("name"),
                    "method": "alias",
                    "score": 1.0,
                })

            return {
                "found": True,
                "record": record,
                "matched_name": record.get("name"),
                "match_method": "alias",
                "match_score": 1.0,
            }

    # 3. initial + last name
    initial_matches = candidate_matches_by_initial(
        player_name,
        store,
    )

    if len(initial_matches) == 1:
        key, record, score = initial_matches[0]

        _DEBUG["found_count"] += 1

        if len(_DEBUG["examples_found"]) < 30:
            _DEBUG["examples_found"].append({
                "input": player_name,
                "matched": record.get("name"),
                "method": "initial_last_name",
                "score": score,
            })

        return {
            "found": True,
            "record": record,
            "matched_name": record.get("name"),
            "match_method": "initial_last_name",
            "match_score": score,
        }

    # 4. conservative fuzzy
    input_last = last_name(player_name)

    candidates = []

    for key, record in store.items():
        rec_name = record.get("name", key)
        rec_last = last_name(rec_name)

        last_score = similarity(
            input_last,
            rec_last,
        )

        if last_score < 0.92:
            continue

        full_score = similarity(
            player_name,
            rec_name,
        )

        if full_score >= 0.90:
            candidates.append({
                "key": key,
                "record": record,
                "score": full_score,
                "last_score": last_score,
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if candidates:
        best = candidates[0]

        ambiguous = False

        if len(candidates) > 1:
            second = candidates[1]

            if (
                best["score"] - second["score"]
            ) < 0.03:
                ambiguous = True

        if not ambiguous:
            record = best["record"]

            _DEBUG["found_count"] += 1

            if len(_DEBUG["examples_found"]) < 30:
                _DEBUG["examples_found"].append({
                    "input": player_name,
                    "matched": record.get("name"),
                    "method": "fuzzy_safe",
                    "score": round(
                        best["score"],
                        3,
                    ),
                })

            return {
                "found": True,
                "record": record,
                "matched_name": record.get("name"),
                "match_method": "fuzzy_safe",
                "match_score": round(
                    best["score"],
                    3,
                ),
            }

    _DEBUG["missing_count"] += 1

    if len(_DEBUG["examples_missing"]) < 50:
        _DEBUG["examples_missing"].append({
            "input": player_name,
            "normalized": normalized,
            "reason": "no_safe_match",
        })

    return {
        "found": False,
        "record": None,
        "matched_name": None,
        "match_method": "missing",
        "match_score": 0.0,
    }


def get_rating_from_record(record, surface=None):
    if not record:
        return DEFAULT_ELO

    if surface:
        surface_key = normalize_name(surface)

        surfaces = record.get("surfaces") or {}

        if isinstance(surfaces, dict):
            for key, value in surfaces.items():
                if normalize_name(key) == surface_key:
                    detected = safe_float(value)

                    if detected is not None:
                        return detected

    elo = safe_float(
        record.get("elo"),
        DEFAULT_ELO,
    )

    return elo


def get_yelo_from_record(record):
    if not record:
        return DEFAULT_ELO

    yelo = safe_float(
        record.get("yelo"),
        None,
    )

    if yelo is not None:
        return yelo

    return safe_float(
        record.get("elo"),
        DEFAULT_ELO,
    )


def win_probability(rating_a, rating_b):
    return 1 / (
        1 + 10 ** (
            (rating_b - rating_a) / 400
        )
    )


def predict(
    player1,
    player2,
    surface=None,
    elo_store=None,
):
    """
    Existing prediction engines call this function.

    Returns:
    {
        "probability_player1": ...,
        "probability_player2": ...
    }

    Plus debug metadata.
    """

    if elo_store is None:
        elo_store = load()

    lookup1 = find_player_record(
        player1,
        elo_store,
    )

    lookup2 = find_player_record(
        player2,
        elo_store,
    )

    rating1 = get_rating_from_record(
        lookup1.get("record"),
        surface=surface,
    )

    rating2 = get_rating_from_record(
        lookup2.get("record"),
        surface=surface,
    )

    yelo1 = get_yelo_from_record(
        lookup1.get("record"),
    )

    yelo2 = get_yelo_from_record(
        lookup2.get("record"),
    )

    probability1 = win_probability(
        rating1,
        rating2,
    )

    probability2 = 1 - probability1

    write_debug()

    return {
        "probability_player1": probability1,
        "probability_player2": probability2,

        "elo_player1": rating1,
        "elo_player2": rating2,

        "yelo_player1": yelo1,
        "yelo_player2": yelo2,

        "elo_found_player1": lookup1.get("found"),
        "elo_found_player2": lookup2.get("found"),

        "elo_match_player1": lookup1.get("matched_name"),
        "elo_match_player2": lookup2.get("matched_name"),

        "elo_match_method_player1": lookup1.get("match_method"),
        "elo_match_method_player2": lookup2.get("match_method"),

        "elo_match_score_player1": lookup1.get("match_score"),
        "elo_match_score_player2": lookup2.get("match_score"),
    }
