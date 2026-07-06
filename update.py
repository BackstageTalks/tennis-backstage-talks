import glob
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from play_history import (
    betting_day,
    save_all_snapshot,
    save_top5_snapshot,
)

from prediction_engine_top import (
    build_all_predictions,
    get_top_predictions,
)

from src.bst_ai.service import (
    build_bst_ai_comparison,
)

from src.marq_ai import (
    build_marq_from_match,
)


ALL_SNAPSHOT_DIR = "data/pick_history/all"
TOP5_SNAPSHOT_DIR = "data/pick_history/top5"
LOCAL_TZ = ZoneInfo("Europe/Bratislava")


# -----------------------------------------------------------------------------
# Generic JSON helpers
# -----------------------------------------------------------------------------


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_json(path, default):
    try:
        if not path:
            return default

        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as exc:
        print(
            "UPDATE JSON LOAD ERROR:",
            path,
            str(exc),
        )

        return default


def is_non_empty_list(data):
    return isinstance(data, list) and len(data) > 0


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


# -----------------------------------------------------------------------------
# Snapshot helpers
# -----------------------------------------------------------------------------


def snapshot_path(kind, date):
    if kind == "all":
        return os.path.join(
            ALL_SNAPSHOT_DIR,
            f"{date}.json",
        )

    if kind == "top5":
        return os.path.join(
            TOP5_SNAPSHOT_DIR,
            f"{date}.json",
        )

    raise ValueError(
        f"Unsupported snapshot kind: {kind}"
    )


def extract_date_from_filename(path):
    filename = os.path.basename(path or "")

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})",
        filename,
    )

    if not match:
        return ""

    return match.group(1)


def latest_non_empty_snapshot(kind):
    if kind == "all":
        pattern = os.path.join(
            ALL_SNAPSHOT_DIR,
            "*.json",
        )

    elif kind == "top5":
        pattern = os.path.join(
            TOP5_SNAPSHOT_DIR,
            "*.json",
        )

    else:
        raise ValueError(
            f"Unsupported snapshot kind: {kind}"
        )

    files = glob.glob(pattern)

    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )

    for path in files:
        data = load_json(
            path,
            [],
        )

        if is_non_empty_list(data):
            print(
                "LATEST NON-EMPTY SNAPSHOT:",
                kind,
                path,
                len(data),
            )

            return data

    print(
        "LATEST NON-EMPTY SNAPSHOT:",
        kind,
        None,
    )

    return []


def load_today_snapshot(kind, date):
    path = snapshot_path(
        kind,
        date,
    )

    data = load_json(
        path,
        [],
    )

    if is_non_empty_list(data):
        print(
            "TODAY SNAPSHOT FOUND:",
            kind,
            path,
            len(data),
        )

        return data

    if os.path.exists(path):
        print(
            "TODAY SNAPSHOT EXISTS BUT IS EMPTY - IGNORING:",
            kind,
            path,
        )

    return []


def save_non_empty_all_snapshot(date, all_predictions):
    if not is_non_empty_list(all_predictions):
        print(
            "SKIP ALL SNAPSHOT SAVE:",
            "generated ALL is empty",
        )

        return load_today_snapshot(
            "all",
            date,
        )

    snapshot = save_all_snapshot(
        date=date,
        all_predictions=all_predictions,
    )

    if is_non_empty_list(snapshot):
        return snapshot

    path = snapshot_path(
        "all",
        date,
    )

    print(
        "REPAIR EMPTY ALL SNAPSHOT WITH NON-EMPTY GENERATED DATA:",
        path,
        len(all_predictions),
    )

    save_json(
        path,
        all_predictions,
    )

    return all_predictions


def save_non_empty_top5_snapshot(date, top_predictions):
    if not is_non_empty_list(top_predictions):
        print(
            "SKIP TOP5 SNAPSHOT SAVE:",
            "generated TOP5 is empty",
        )

        return load_today_snapshot(
            "top5",
            date,
        )

    snapshot = save_top5_snapshot(
        date=date,
        top5_predictions=top_predictions,
    )

    if is_non_empty_list(snapshot):
        return snapshot

    path = snapshot_path(
        "top5",
        date,
    )

    print(
        "REPAIR EMPTY TOP5 SNAPSHOT WITH NON-EMPTY GENERATED DATA:",
        path,
        len(top_predictions),
    )

    save_json(
        path,
        top_predictions,
    )

    return top_predictions


# -----------------------------------------------------------------------------
# Public output source selection
# -----------------------------------------------------------------------------


def choose_public_all_predictions(
    generated_all_predictions,
    all_snapshot,
):
    if is_non_empty_list(all_snapshot):
        print(
            "PUBLIC ALL SOURCE:",
            "today immutable snapshot",
            len(all_snapshot),
        )

        return all_snapshot

    if is_non_empty_list(generated_all_predictions):
        print(
            "PUBLIC ALL SOURCE:",
            "generated predictions",
            len(generated_all_predictions),
        )

        return generated_all_predictions

    restored_all = latest_non_empty_snapshot(
        "all"
    )

    if is_non_empty_list(restored_all):
        print(
            "PUBLIC ALL SOURCE:",
            "latest non-empty snapshot fallback",
            len(restored_all),
        )

        return restored_all

    raise RuntimeError(
        "No ALL predictions available. "
        "Generated ALL is empty and no non-empty immutable ALL snapshot exists. "
        "Refusing to write empty public ALL JSON."
    )


def choose_public_top_predictions(
    generated_top_predictions,
    top5_snapshot,
    public_all_predictions,
):
    if is_non_empty_list(top5_snapshot):
        print(
            "PUBLIC TOP5 SOURCE:",
            "today immutable snapshot",
            len(top5_snapshot),
        )

        return top5_snapshot

    if is_non_empty_list(generated_top_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "generated predictions",
            len(generated_top_predictions),
        )

        return generated_top_predictions

    restored_top5 = latest_non_empty_snapshot(
        "top5"
    )

    if is_non_empty_list(restored_top5):
        print(
            "PUBLIC TOP5 SOURCE:",
            "latest non-empty snapshot fallback",
            len(restored_top5),
        )

        return restored_top5

    if is_non_empty_list(public_all_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "derived from public ALL predictions",
        )

        derived_top = get_top_predictions(
            public_all_predictions,
        )

        if is_non_empty_list(derived_top):
            print(
                "PUBLIC TOP5 DERIVED COUNT:",
                len(derived_top),
            )

            return derived_top

    print(
        "PUBLIC TOP5 WARNING:",
        "No generated TOP5, no TOP5 snapshot, no historical TOP5, "
        "and no derived TOP5. Writing empty TOP5 public JSON. "
        "build_pages.py can derive TOP5 from ALL."
    )

    return []


# -----------------------------------------------------------------------------
# Match keys / field normalization / enrichment helpers
# -----------------------------------------------------------------------------


def normalize_text(value):
    return str(value or "").strip().lower()


def split_match_players(match_text):
    text = str(match_text or "").strip()

    if not text:
        return None, None

    separators = [
        " vs ",
        " v ",
        " - ",
    ]

    for separator in separators:
        if separator in text:
            parts = text.split(separator, 1)

            if len(parts) == 2:
                player1 = parts[0].strip()
                player2 = parts[1].strip()

                if player1 and player2:
                    return player1, player2

    return None, None


def ensure_player_fields(prediction):
    player1 = prediction.get("player1")
    player2 = prediction.get("player2")

    if player1 and player2:
        return prediction

    derived_player1, derived_player2 = split_match_players(
        prediction.get("match")
    )

    changed = False

    if not player1 and derived_player1:
        prediction["player1"] = derived_player1
        changed = True

    if not player2 and derived_player2:
        prediction["player2"] = derived_player2
        changed = True

    if changed:
        print(
            "ENRICH PLAYER FIELDS:",
            prediction.get("match"),
            "player1=",
            prediction.get("player1"),
            "player2=",
            prediction.get("player2"),
        )

    return prediction


def prediction_key(prediction):
    prediction = ensure_player_fields(
        dict(prediction)
    )

    player1 = normalize_text(
        prediction.get("player1")
    )

    player2 = normalize_text(
        prediction.get("player2")
    )

    pick = normalize_text(
        prediction.get("pick")
    )

    match_start = normalize_text(
        prediction.get("match_start")
    )

    if player1 and player2 and pick and match_start:
        return (
            player1,
            player2,
            pick,
            match_start,
        )

    if player1 and player2 and pick:
        return (
            player1,
            player2,
            pick,
        )

    return (
        normalize_text(prediction.get("match")),
        pick,
    )


def build_fresh_index(fresh_predictions):
    index = {}

    for prediction in fresh_predictions or []:
        key = prediction_key(
            prediction
        )

        index[key] = prediction

    return index


def find_fresh_prediction(prediction, fresh_index):
    key = prediction_key(
        prediction
    )

    fresh = fresh_index.get(key)

    if fresh:
        return fresh

    normalized = ensure_player_fields(
        dict(prediction)
    )

    fallback_key = (
        normalize_text(normalized.get("player1")),
        normalize_text(normalized.get("player2")),
        normalize_text(normalized.get("pick")),
    )

    return fresh_index.get(fallback_key)


def extract_match_date(prediction):
    start_value = prediction.get("match_start")

    if not start_value:
        return None

    try:
        text = str(start_value)

        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            return text[:10]

        local_dt = dt.astimezone(
            LOCAL_TZ,
        )

        return local_dt.strftime("%Y-%m-%d")

    except Exception:
        text = str(start_value)

        if len(text) >= 10:
            return text[:10]

    return None


def refresh_bst_fields(prediction):
    prediction = ensure_player_fields(
        prediction
    )

    player1 = prediction.get("player1")
    player2 = prediction.get("player2")
    pick = prediction.get("pick")
    surface = prediction.get("surface")
    corq_probability = safe_float(
        prediction.get("corq_ai_probability")
        or prediction.get("probability")
    )

    if not player1 or not player2 or not pick:
        print(
            "ENRICH BST SKIP - missing players/pick:",
            prediction.get("match"),
            "player1=",
            player1,
            "player2=",
            player2,
            "pick=",
            pick,
        )

        return prediction

    if corq_probability is None:
        print(
            "ENRICH BST SKIP - missing corq probability:",
            prediction.get("match"),
        )

        return prediction

    try:
        bst_ai = build_bst_ai_comparison(
            player1=player1,
            player2=player2,
            pick=pick,
            surface=surface,
            corq_probability=corq_probability,
            tour=prediction.get("gender"),
        )

        fields = [
            "corq_ai_probability",
            "bst_ai_probability",
            "ai_match",
            "ai_gap",
            "ai_signed_gap",
            "ai_lean",
            "ai_direction_match",
            "ai_match_color",
            "bst_ai_status",
            "bst_ai_reason",
            "bst_ai_rating_type",
            "bst_player1_found",
            "bst_player2_found",
        ]

        for field in fields:
            prediction[field] = bst_ai.get(field)

        print(
            "ENRICH BST:",
            prediction.get("match"),
            "player1=",
            player1,
            "player2=",
            player2,
            "pick=",
            pick,
            "status=",
            prediction.get("bst_ai_status"),
            "bst=",
            prediction.get("bst_ai_probability"),
        )

    except Exception as exc:
        print(
            "ENRICH BST ERROR:",
            prediction.get("match"),
            str(exc),
        )

    return prediction


def refresh_marq_fields(prediction):
    prediction = ensure_player_fields(
        prediction
    )

    player1 = prediction.get("player1")
    player2 = prediction.get("player2")
    pick = prediction.get("pick")
    match_date = extract_match_date(
        prediction
    )

    if not player1 or not player2 or not pick or not match_date:
        print(
            "ENRICH MARQ SKIP:",
            prediction.get("match"),
            "player1=",
            player1,
            "player2=",
            player2,
            "pick=",
            pick,
            "date=",
            match_date,
        )

        return prediction

    try:
        marq_ai = build_marq_from_match(
            player1=player1,
            player2=player2,
            date_only=match_date,
            pick=pick,
        )

        prediction["marq_ai_score"] = getattr(
            marq_ai,
            "score",
            None,
        )

        prediction["marq_ai_signal"] = getattr(
            marq_ai,
            "signal",
            None,
        )

        prediction["marq_ai_direction"] = getattr(
            marq_ai,
            "direction",
            None,
        )

        prediction["marq_ai_strength"] = getattr(
            marq_ai,
            "strength",
            None,
        )

        prediction["marq_ai_consistency"] = getattr(
            marq_ai,
            "consistency",
            None,
        )

        print(
            "ENRICH MARQ:",
            prediction.get("match"),
            "score=",
            prediction.get("marq_ai_score"),
            "signal=",
            prediction.get("marq_ai_signal"),
        )

    except Exception as exc:
        print(
            "ENRICH MARQ ERROR:",
            prediction.get("match"),
            str(exc),
        )

    return prediction


def merge_refreshable_fields(base_prediction, fresh_prediction):
    if not isinstance(fresh_prediction, dict):
        return base_prediction

    refreshable_fields = [
        "player1",
        "player2",
        "bst_ai_probability",
        "ai_match",
        "ai_gap",
        "ai_signed_gap",
        "ai_lean",
        "ai_direction_match",
        "ai_match_color",
        "bst_ai_status",
        "bst_ai_reason",
        "bst_ai_rating_type",
        "bst_player1_found",
        "bst_player2_found",
        "marq_ai_score",
        "marq_ai_signal",
        "marq_ai_direction",
        "marq_ai_strength",
        "marq_ai_consistency",
    ]

    for field in refreshable_fields:
        if field in fresh_prediction:
            base_prediction[field] = fresh_prediction.get(field)

    return base_prediction


def enrich_public_predictions(public_predictions, fresh_predictions, label):
    if not is_non_empty_list(public_predictions):
        return public_predictions

    fresh_index = build_fresh_index(
        fresh_predictions
    )

    enriched = []

    print(
        "ENRICH PUBLIC PREDICTIONS:",
        label,
        "count=",
        len(public_predictions),
    )

    for prediction in public_predictions:
        updated = ensure_player_fields(
            dict(prediction)
        )

        fresh = find_fresh_prediction(
            updated,
            fresh_index,
        )

        if fresh:
            updated = merge_refreshable_fields(
                updated,
                fresh,
            )

            print(
                "ENRICH FROM FRESH:",
                label,
                updated.get("match"),
                "bst=",
                updated.get("bst_ai_probability"),
                "status=",
                updated.get("bst_ai_status"),
            )

            # If the fresh match did not have usable BsT for any reason,
            # still try recomputing from the snapshot fields.
            if updated.get("bst_ai_status") != "OK":
                updated = refresh_bst_fields(
                    updated
                )

            if updated.get("marq_ai_score") is None:
                updated = refresh_marq_fields(
                    updated
                )

        else:
            print(
                "ENRICH FROM RECOMPUTE:",
                label,
                updated.get("match"),
            )

            updated = refresh_bst_fields(
                updated
            )

            updated = refresh_marq_fields(
                updated
            )

        enriched.append(updated)

    return enriched


# -----------------------------------------------------------------------------
# Main workflow entry
# -----------------------------------------------------------------------------


def run():
    today = betting_day()

    print("BETTING DAY:", today)
    print("BUILDING ALL PREDICTIONS...")

    all_predictions = build_all_predictions()

    print(
        "GENERATED ALL COUNT:",
        len(all_predictions)
        if isinstance(all_predictions, list)
        else "invalid",
    )

    print("BUILDING TOP5 PREDICTIONS...")

    if is_non_empty_list(all_predictions):
        top_predictions = get_top_predictions(
            all_predictions
        )
    else:
        top_predictions = []

    print(
        "GENERATED TOP5 COUNT:",
        len(top_predictions)
        if isinstance(top_predictions, list)
        else "invalid",
    )

    os.makedirs("public", exist_ok=True)
    os.makedirs(ALL_SNAPSHOT_DIR, exist_ok=True)
    os.makedirs(TOP5_SNAPSHOT_DIR, exist_ok=True)

    print("LOADING TODAY IMMUTABLE SNAPSHOTS...")

    existing_all_snapshot = load_today_snapshot(
        "all",
        today,
    )

    existing_top5_snapshot = load_today_snapshot(
        "top5",
        today,
    )

    print("SAVING IMMUTABLE ALL SNAPSHOT IF NON-EMPTY...")

    if is_non_empty_list(existing_all_snapshot):
        all_snapshot = existing_all_snapshot
        print(
            "KEEPING EXISTING NON-EMPTY ALL SNAPSHOT:",
            len(all_snapshot),
        )
    else:
        all_snapshot = save_non_empty_all_snapshot(
            date=today,
            all_predictions=all_predictions,
        )

    print("SAVING IMMUTABLE TOP5 SNAPSHOT IF NON-EMPTY...")

    if is_non_empty_list(existing_top5_snapshot):
        top5_snapshot = existing_top5_snapshot
        print(
            "KEEPING EXISTING NON-EMPTY TOP5 SNAPSHOT:",
            len(top5_snapshot),
        )
    else:
        top5_snapshot = save_non_empty_top5_snapshot(
            date=today,
            top_predictions=top_predictions,
        )

    print(
        "IMMUTABLE ALL SNAPSHOT COUNT:",
        len(all_snapshot)
        if isinstance(all_snapshot, list)
        else "invalid",
    )

    print(
        "IMMUTABLE TOP5 SNAPSHOT COUNT:",
        len(top5_snapshot)
        if isinstance(top5_snapshot, list)
        else "invalid",
    )

    public_all_predictions = choose_public_all_predictions(
        generated_all_predictions=all_predictions,
        all_snapshot=all_snapshot,
    )

    public_top_predictions = choose_public_top_predictions(
        generated_top_predictions=top_predictions,
        top5_snapshot=top5_snapshot,
        public_all_predictions=public_all_predictions,
    )

    public_all_predictions = enrich_public_predictions(
        public_predictions=public_all_predictions,
        fresh_predictions=all_predictions,
        label="ALL",
    )

    public_top_predictions = enrich_public_predictions(
        public_predictions=public_top_predictions,
        fresh_predictions=all_predictions,
        label="TOP5",
    )

    top_path = f"public/predictions_{today}.json"
    all_path = f"public/all_predictions_{today}.json"

    save_json(
        top_path,
        public_top_predictions,
    )

    save_json(
        all_path,
        public_all_predictions,
    )

    print(
        "SAVED TOP PUBLIC JSON:",
        top_path,
        len(public_top_predictions),
    )

    print(
        "SAVED ALL PUBLIC JSON:",
        all_path,
        len(public_all_predictions),
    )

    print(
        "SAVED TOP5 SNAPSHOT:",
        len(top5_snapshot)
        if isinstance(top5_snapshot, list)
        else "invalid",
    )

    print(
        "SAVED ALL SNAPSHOT:",
        len(all_snapshot)
        if isinstance(all_snapshot, list)
        else "invalid",
    )


if __name__ == "__main__":
    run()
