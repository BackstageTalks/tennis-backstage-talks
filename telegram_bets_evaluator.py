# -*- coding: utf-8 -*-
"""Evaluate Telegram bet snapshots and optionally send a Telegram results message.

Manual/scheduled flow:
1) telegram_rss_feed.py sends the original TG picks and saves a snapshot in data/telegram_snapshots.
2) This script reads the exact saved snapshot, reads public/results_data.json, matches results, and assigns:
   winner == pick        => ✅
   winner != pick        => ❌
   match not finished    => ⏳
   delayed/postponed     => 🕒
   walkover/void         => ➖
3) By default it sends only when all picks are settled. Set TG_EVAL_SEND_PENDING=1 for interim message.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BOT_TOKEN = os.getenv("TG_BOT_BTLKR")
CHAT_ID = os.getenv("TG_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("Missing GitHub secret: TG_BOT_BTLKR")
if not CHAT_ID:
    raise ValueError("Missing GitHub secret: TG_CHAT_ID")

LOCAL_TZ = ZoneInfo("Europe/Bratislava")
SNAPSHOT_DIR = Path(os.getenv("TG_SNAPSHOT_DIR", "data/telegram_snapshots"))
RESULTS_DATA_PATH = os.getenv("RESULTS_DATA_PATH", "public/results_data.json")
EVALUATED_DIR = Path(os.getenv("TG_EVALUATED_DIR", "data/telegram_snapshots/evaluated"))
SENT_DIR = Path(os.getenv("TG_EVAL_SENT_DIR", "data/results/telegram_bets_eval_sent"))

TG_EVAL_DATE = os.getenv("TG_EVAL_DATE", "").strip()
TG_EVAL_MODEL = os.getenv("TG_EVAL_MODEL", "thinq").strip().lower() or "thinq"
SEND_PENDING = os.getenv("TG_EVAL_SEND_PENDING", "0").strip().lower() in {"1", "true", "yes", "y"}
ALLOW_RESEND = os.getenv("TG_EVAL_ALLOW_RESEND", "0").strip().lower() in {"1", "true", "yes", "y"}
# If a snapshot remains pending for too long, convert pending/unknown matches to void (➖)
# so one postponed/unmapped match cannot block final TG evaluation indefinitely.
# Set to 0 to disable. Default: 48 hours after snapshot created_at/date.
STALE_PENDING_AFTER_HOURS = int(os.getenv("TG_STALE_PENDING_AFTER_HOURS", "48"))


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def normalize_name(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9áäčďéíĺľňóôŕšťúýžąćęłńóśźżüößñç]+", "", text, flags=re.IGNORECASE)
    return text


def pair_key(a, b):
    return "|".join(sorted([normalize_name(a), normalize_name(b)]))


def display_date(day):
    try:
        return datetime.strptime(str(day), "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return str(day)


def rank_icon(index):
    icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    return icons[index - 1] if 1 <= index <= len(icons) else f"#{index}"


def as_percent(value):
    if value is None or value == "":
        return "-"
    try:
        number = float(value)
        if number <= 1.0:
            number *= 100.0
        return f"{number:.1f}%"
    except Exception:
        text = str(value).strip()
        return text if text.endswith("%") else f"{text}%"


def as_odds(value):
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def first_value(item, keys, default=None):
    if not isinstance(item, dict):
        return default
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default


def parse_datetime_value(value):
    if not value:
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        # date-only snapshot day means beginning of that local betting day
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=LOCAL_TZ)
        return dt.astimezone(LOCAL_TZ)
    except Exception:
        return None


def snapshot_reference_time(snapshot):
    # Prefer exact snapshot creation/send time, fallback to betting day.
    for key in ["created_at", "sent_at", "date", "betting_day"]:
        dt = parse_datetime_value(snapshot.get(key)) if isinstance(snapshot, dict) else None
        if dt is not None:
            return dt
    return None


def snapshot_is_stale(snapshot):
    if STALE_PENDING_AFTER_HOURS <= 0:
        return False
    ref = snapshot_reference_time(snapshot)
    if ref is None:
        return False
    return datetime.now(LOCAL_TZ) >= ref + timedelta(hours=STALE_PENDING_AFTER_HOURS)


def flatten_items(value):
    items = []
    if isinstance(value, list):
        for entry in value:
            items.extend(flatten_items(entry))
    elif isinstance(value, dict):
        match_like_keys = {
            "pick", "winner", "match_winner", "result_winner", "player1", "player2",
            "opponent", "result_status", "match_status", "event_id", "id", "score"
        }
        if any(key in value for key in match_like_keys):
            items.append(value)
        for nested in value.values():
            if isinstance(nested, (list, dict)):
                items.extend(flatten_items(nested))
    return items


def item_event_ids(item):
    ids = []
    for key in ["event_id", "eventId", "match_id", "matchId", "id", "entry_id", "rss_entry_id"]:
        value = item.get(key) if isinstance(item, dict) else None
        if value not in (None, ""):
            ids.append(str(value))
    return ids


def item_names(item):
    pick = first_value(item, ["pick_full", "pick", "selected_player", "player"], "")
    opponent = first_value(item, ["opponent", "opponent_display", "player2", "against", "vs"], "")
    p1 = first_value(item, ["player1", "home", "home_player"], "")
    p2 = first_value(item, ["player2", "away", "away_player"], "")
    if p1 and p2:
        return p1, p2
    return pick, opponent


def build_results_index(results_data):
    result_items = flatten_items(results_data)
    by_id = {}
    by_pair = {}
    for item in result_items:
        for event_id in item_event_ids(item):
            by_id[event_id] = item
        p1, p2 = item_names(item)
        if p1 and p2:
            by_pair[pair_key(p1, p2)] = item
    return by_id, by_pair, result_items


def find_result_for_snapshot_item(snapshot_item, by_id, by_pair):
    for event_id in item_event_ids(snapshot_item):
        if event_id in by_id:
            return by_id[event_id]
    p1 = first_value(snapshot_item, ["pick_full", "pick"], "")
    p2 = first_value(snapshot_item, ["opponent", "opponent_display"], "")
    if p1 and p2:
        return by_pair.get(pair_key(p1, p2))
    return None


def result_icon(snapshot_item, result_item):
    if not result_item:
        return "⏳"

    status = str(first_value(result_item, ["result_status", "status", "match_status"], "PENDING") or "PENDING").upper()

    void_statuses = {"VOID", "WALKOVER", "W/O", "WO", "CANCELLED", "CANCELED", "ABANDONED", "RETIRED_VOID"}
    delayed_statuses = {"DELAYED", "POSTPONED"}
    pending_statuses = {"PENDING", "UNKNOWN", "SCHEDULED", "NOT_STARTED", "NOT STARTED", "LIVE", "IN_PROGRESS", "IN PROGRESS"}
    finished_statuses = {"FINISHED", "COMPLETED", "ENDED", "FINAL", "FT", "DONE", "WON", "LOST"}

    if status in void_statuses:
        return "➖"
    if status in delayed_statuses:
        return "🕒"
    if status == "WON":
        return "✅"
    if status == "LOST":
        return "❌"
    if status in pending_statuses:
        return "⏳"

    pick = first_value(snapshot_item, ["pick_full", "pick"], "")
    winner = first_value(result_item, ["winner", "winner_name", "match_winner", "result_winner"], "")

    if status not in finished_statuses and not winner:
        return "⏳"
    if not winner or not pick:
        return "⏳"
    return "✅" if normalize_name(winner) == normalize_name(pick) else "❌"


def evaluate_snapshot(snapshot, by_id, by_pair):
    evaluated_items = []
    stale_snapshot = snapshot_is_stale(snapshot)

    for item in snapshot.get("items", []):
        result = find_result_for_snapshot_item(item, by_id, by_pair)
        icon = result_icon(item, result)
        stale_pending = False

        # Stale cutoff: delayed/postponed/unmapped/pending after N hours becomes void.
        # This prevents one old pending match from blocking the final evaluation forever.
        if icon in {"⏳", "🕒"} and stale_snapshot:
            icon = "➖"
            stale_pending = True

        enriched = dict(item)
        enriched["result_icon"] = icon
        enriched["result_status"] = {"✅": "WON", "❌": "LOST", "⏳": "PENDING", "🕒": "DELAYED", "➖": "VOID"}.get(icon, "PENDING")
        if stale_pending:
            enriched["result_status"] = "STALE_VOID"
            enriched["stale_pending_void"] = True
            enriched["stale_pending_after_hours"] = STALE_PENDING_AFTER_HOURS
            enriched["stale_pending_reason"] = "Pending/postponed too long, treated as void."
        if result:
            enriched["matched_result"] = {
                "winner": first_value(result, ["winner", "winner_name", "match_winner", "result_winner"], None),
                "status": first_value(result, ["result_status", "status", "match_status"], None),
                "score": first_value(result, ["score", "result_score", "final_score"], None),
            }
        evaluated_items.append(enriched)

    evaluated = dict(snapshot)
    evaluated["evaluated_at"] = datetime.now(LOCAL_TZ).isoformat()
    evaluated["stale_pending_after_hours"] = STALE_PENDING_AFTER_HOURS
    evaluated["stale_snapshot"] = stale_snapshot
    evaluated["items"] = evaluated_items
    evaluated["pending_count"] = sum(1 for item in evaluated_items if item.get("result_icon") == "⏳")
    evaluated["delayed_count"] = sum(1 for item in evaluated_items if item.get("result_icon") == "🕒")
    evaluated["stale_void_count"] = sum(1 for item in evaluated_items if item.get("stale_pending_void"))
    return evaluated


def snapshot_files():
    day = TG_EVAL_DATE or datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    pattern = f"{day}_*_topbets.json" if TG_EVAL_MODEL in ("", "all") else f"{day}_{TG_EVAL_MODEL}_topbets.json"
    return sorted(SNAPSHOT_DIR.glob(pattern))


def evaluation_signature(evaluated):
    parts = []
    for item in evaluated.get("items", []):
        parts.append(
            "|".join(
                [
                    str(item.get("rank") or ""),
                    str(item.get("pick") or item.get("pick_full") or ""),
                    str(item.get("opponent") or item.get("opponent_display") or ""),
                    str(item.get("result_icon") or ""),
                    str(item.get("result_status") or ""),
                ]
            )
        )
    raw = "\n".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def evaluation_marker_name(snapshot_path, evaluated):
    pending_count = int(evaluated.get("pending_count") or 0)
    delayed_count = int(evaluated.get("delayed_count") or 0)
    if pending_count == 0 and delayed_count == 0:
        suffix = "final"
    else:
        suffix = f"interim_{evaluation_signature(evaluated)}"
    return f"{snapshot_path.stem}_{suffix}.json"


def sent_marker(snapshot_path, evaluated):
    return SENT_DIR / evaluation_marker_name(snapshot_path, evaluated)


def already_sent(snapshot_path, evaluated):
    return sent_marker(snapshot_path, evaluated).exists()


def mark_sent(snapshot_path, evaluated, message):
    SENT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(
        sent_marker(snapshot_path, evaluated),
        {
            "snapshot": str(snapshot_path),
            "sent_at": datetime.now(LOCAL_TZ).isoformat(),
            "pending_count": evaluated.get("pending_count"),
            "delayed_count": evaluated.get("delayed_count"),
            "stale_void_count": evaluated.get("stale_void_count"),
            "message": message,
        },
    )


def build_message(evaluated):
    day = evaluated.get("date") or datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    model_title = evaluated.get("model_title") or "TOP BETS | Thinq Model"

    lines = ["AI Betting by Backstage Talks", f"🗓️ {display_date(day)}", "", f"🎾 {model_title}", ""]
    for idx, item in enumerate(evaluated.get("items", []), start=1):
        rank = int(item.get("rank") or idx)
        pick = first_value(item, ["pick", "pick_display", "pick_full"], "-")
        opponent = first_value(item, ["opponent_display", "opponent"], "-")
        probability = first_value(item, ["probability", "win_probability"], None)
        odds = first_value(item, ["odds", "selected_odds", "pick_odds"], None)
        icon = item.get("result_icon") or "⏳"
        lines.append(f"{rank_icon(rank)} {pick} | {as_percent(probability)} | {as_odds(odds)}")
        lines.append(f"   vs {opponent} {icon}")

    lines.extend(["", "This data is provided for informational and analytical purposes only", "Powered by BackstageTalks Statistical Engine"])
    return "\n".join(lines)


def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": True},
        timeout=30,
    )
    response.raise_for_status()
    try:
        return response.json()
    except Exception:
        return {}


def main():
    files = snapshot_files()
    if not files:
        print("No Telegram snapshots found for evaluation.")
        return

    results_data = load_json(RESULTS_DATA_PATH, {})
    by_id, by_pair, result_items = build_results_index(results_data)
    print("Loaded result items:", len(result_items))

    for path in files:
        snapshot = load_json(path, {})
        if not snapshot.get("items"):
            print("Snapshot has no items:", path)
            continue

        evaluated = evaluate_snapshot(snapshot, by_id, by_pair)
        evaluated_path = EVALUATED_DIR / path.name
        write_json(evaluated_path, evaluated)
        print("Saved evaluated snapshot:", evaluated_path)

        pending_count = evaluated.get("pending_count", 0)
        delayed_count = evaluated.get("delayed_count", 0)
        if pending_count and not SEND_PENDING:
            print("Snapshot still has non-delayed pending matches. No Telegram result sent. Pending:", pending_count, "Delayed:", delayed_count, path)
            continue

        if already_sent(path, evaluated) and not ALLOW_RESEND:
            print("Evaluation message already sent for this state:", path)
            continue

        message = build_message(evaluated)
        send_telegram_message(message)
        mark_sent(path, evaluated, message)
        print(message)
        print("Telegram evaluation message sent for snapshot:", path)


if __name__ == "__main__":
    main()
