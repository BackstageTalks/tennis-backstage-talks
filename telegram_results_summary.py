import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ============================================================
# TELEGRAM SECRETS
# ============================================================

BOT_TOKEN = os.getenv("TG_BOT_BTLKR")
CHAT_ID = os.getenv("TG_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("Missing GitHub secret: TG_BOT_BTLKR")
if not CHAT_ID:
    raise ValueError("Missing GitHub secret: TG_CHAT_ID")

# ============================================================
# CONFIG
# ============================================================

LOCAL_TZ = ZoneInfo("Europe/Bratislava")

RESULTS_DATA_PATH = os.getenv("RESULTS_DATA_PATH", "public/results_data.json")
SENT_DIR = Path(os.getenv("TG_RESULTS_SENT_DIR", "data/results/telegram_summary_sent"))

# Model/title used in the Telegram result message.
TG_RESULTS_MODEL = os.getenv("TG_RESULTS_MODEL", "Thinq").strip() or "Thinq"
TG_RESULTS_DATASET = os.getenv("TG_RESULTS_DATASET", "top5").strip().lower() or "top5"

# Default: wait until all TG picks are settled before sending result message.
# Set TG_RESULTS_SEND_PENDING=1 if you want to send also with pending matches shown as ⏳.
SEND_WITH_PENDING = os.getenv("TG_RESULTS_SEND_PENDING", "0").strip().lower() in {"1", "true", "yes", "y"}

# Optional: avoid duplicate send per day/model/dataset.
ALLOW_RESEND = os.getenv("TG_RESULTS_ALLOW_RESEND", "0").strip().lower() in {"1", "true", "yes", "y"}

# ============================================================
# HELPERS
# ============================================================

def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def normalize_name(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9áäčďéíĺľňóôŕšťúýžąćęłńóśźżüößñç]+", "", text, flags=re.IGNORECASE)
    return text


def display_date(day):
    """Convert YYYY-MM-DD to DD.MM.YYYY. If conversion fails, return original text."""
    try:
        return datetime.strptime(str(day), "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return str(day)


def rank_icon(index):
    icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    if 1 <= index <= len(icons):
        return icons[index - 1]
    return f"#{index}"


def as_percent(value):
    if value is None or value == "":
        return "-"
    try:
        number = float(value)
        # Accept both 0.734 and 73.4 formats.
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
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default


def result_icon_for_item(item):
    """Evaluate one TG bet using the agreed rules.

    Rules:
    - winner == pick        => ✅
    - winner != pick        => ❌
    - match not finished    => ⏳
    - walkover/void         => ➖
    """
    status = str(first_value(item, ["result_status", "status", "match_status"], "PENDING") or "PENDING").upper()

    void_statuses = {
        "VOID",
        "WALKOVER",
        "W/O",
        "WO",
        "CANCELLED",
        "CANCELED",
        "ABANDONED",
        "RETIRED_VOID",
    }
    pending_statuses = {
        "PENDING",
        "UNKNOWN",
        "SCHEDULED",
        "NOT_STARTED",
        "NOT STARTED",
        "LIVE",
        "IN_PROGRESS",
        "IN PROGRESS",
        "DELAYED",
        "POSTPONED",
    }
    finished_statuses = {
        "FINISHED",
        "COMPLETED",
        "ENDED",
        "FINAL",
        "FT",
        "DONE",
        "WON",
        "LOST",
    }

    if status in void_statuses:
        return "➖"
    if status == "WON":
        return "✅"
    if status == "LOST":
        return "❌"
    if status in pending_statuses:
        return "⏳"

    pick = first_value(item, ["pick", "selected_player", "player", "winner_pick"], "")
    winner = first_value(item, ["winner", "match_winner", "result_winner"], "")

    if status not in finished_statuses and not winner:
        return "⏳"
    if not winner or not pick:
        return "⏳"

    if normalize_name(winner) == normalize_name(pick):
        return "✅"
    return "❌"


def is_unsettled_icon(icon):
    return icon == "⏳"

# ============================================================
# DATA LOADING
# ============================================================

def load_dataset_items(data):
    """Load items from public/results_data.json.

    Supports both:
    - data["top5"]
    - data["datasets"]["top5"]
    - data["top7"] / data["datasets"]["top7"]
    - fallback to flat data["items"]
    """
    dataset = data.get(TG_RESULTS_DATASET) or data.get("datasets", {}).get(TG_RESULTS_DATASET) or {}

    if not dataset and TG_RESULTS_DATASET == "top5":
        dataset = data.get("top7") or data.get("datasets", {}).get("top7") or {}

    day = (
        dataset.get("betting_day")
        or dataset.get("date")
        or data.get("betting_day")
        or data.get("date")
        or datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    )

    items = dataset.get("items") or data.get("items") or []

    # Prefer only today's/snapshot day items, but do not drop all items if date is missing.
    filtered = []
    for item in items:
        item_date = str(item.get("date") or item.get("betting_day") or day)
        if item_date == str(day):
            filtered.append(item)

    return day, filtered if filtered else items


def already_sent(day):
    sent_file = SENT_DIR / f"{day}_{TG_RESULTS_MODEL.lower()}_{TG_RESULTS_DATASET}.json"
    return sent_file.exists()


def mark_sent(day, message):
    SENT_DIR.mkdir(parents=True, exist_ok=True)
    sent_file = SENT_DIR / f"{day}_{TG_RESULTS_MODEL.lower()}_{TG_RESULTS_DATASET}.json"
    with open(sent_file, "w", encoding="utf-8") as file:
        json.dump(
            {
                "date": day,
                "model": TG_RESULTS_MODEL,
                "dataset": TG_RESULTS_DATASET,
                "sent_at": datetime.now(LOCAL_TZ).isoformat(),
                "message": message,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

# ============================================================
# MESSAGE BUILDER
# ============================================================

def build_message(day, items):
    lines = []
    lines.append("AI Betting by Backstage Talks")
    lines.append(f"🗓️ {display_date(day)}")
    lines.append("")
    lines.append(f"🎾 TOP BETS | {TG_RESULTS_MODEL} Model")
    lines.append("")

    for idx, item in enumerate(items, start=1):
        pick = first_value(item, ["pick", "selected_player", "player", "winner_pick"], "-")
        opponent = first_value(item, ["opponent", "player2", "against", "vs"], "-")
        probability = first_value(item, ["probability", "win_probability", "thinq_probability", "bst_ai_probability", "corq_ai_probability"], None)
        odds = first_value(item, ["odds", "selected_odds", "pick_odds"], None)
        icon = result_icon_for_item(item)

        lines.append(f"{rank_icon(idx)} {pick} | {as_percent(probability)} | {as_odds(odds)}")
        lines.append(f"   vs {opponent} {icon}")

    lines.append("")
    lines.append("This data is provided for informational and analytical purposes only")
    lines.append("Powered by BackstageTalks Statistical Engine")
    return "\n".join(lines)

# ============================================================
# TELEGRAM
# ============================================================

def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()

# ============================================================
# MAIN
# ============================================================

def main():
    data = load_json(RESULTS_DATA_PATH, {})
    day, items = load_dataset_items(data)

    if not items:
        print("No Telegram result items found. No message sent.")
        return

    icons = [result_icon_for_item(item) for item in items]
    pending_count = sum(1 for icon in icons if is_unsettled_icon(icon))

    if pending_count and not SEND_WITH_PENDING:
        print("Telegram bets are not fully settled. No result message sent. Pending:", pending_count)
        return

    if already_sent(day) and not ALLOW_RESEND:
        print("Telegram result message already sent for", day, TG_RESULTS_MODEL, TG_RESULTS_DATASET)
        return

    message = build_message(day, items)
    send_telegram_message(message)
    mark_sent(day, message)

    print(message)
    print("Telegram result message sent.")


if __name__ == "__main__":
    main()
