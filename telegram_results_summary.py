import json
import os
from datetime import datetime
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
RESULTS_DATA_PATH = "public/results_data.json"
SENT_DIR = Path("data/results/telegram_summary_sent")


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def fmt_units(value):
    try:
        number = float(value)
        if number > 0:
            return f"+{number:.2f}u"
        if number < 0:
            return f"{number:.2f}u"
        return "0.00u"
    except Exception:
        return "0.00u"


def result_icon(status):
    status = str(status or "PENDING").upper()
    if status == "WON":
        return "✅"
    if status == "LOST":
        return "❌"
    if status == "VOID":
        return "🟣"
    if status == "UNKNOWN":
        return "❔"
    return "⏳"


def load_top5_today_items():
    data = load_json(RESULTS_DATA_PATH, {})
    top5 = data.get("top5") or data.get("datasets", {}).get("top5") or {}
    day = top5.get("betting_day") or data.get("betting_day") or datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    items = top5.get("items") or []
    today_items = [item for item in items if str(item.get("date") or "") == str(day)]
    return day, today_items


def already_sent(day):
    return (SENT_DIR / f"{day}.json").exists()


def mark_sent(day, message):
    SENT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SENT_DIR / f"{day}.json", "w", encoding="utf-8") as file:
        json.dump({"date": day, "sent_at": datetime.now(LOCAL_TZ).isoformat(), "message": message}, file, ensure_ascii=False, indent=2)


def build_message(day, items):
    won = lost = void = pending = 0
    total_units = 0.0
    for item in items:
        status = str(item.get("result_status") or "PENDING").upper()
        if status == "WON":
            won += 1
        elif status == "LOST":
            lost += 1
        elif status == "VOID":
            void += 1
        else:
            pending += 1
        try:
            total_units += float(item.get("units") or 0)
        except Exception:
            pass
    settled = won + lost
    win_rate = f"{(won / settled) * 100:.1f}%" if settled else "-"
    message = (
        f"📊 Results | {day}\n\n"
        f"TOP5 snapshot\n"
        f"Picks: {len(items)}\n"
        f"W-L-V: {won}-{lost}-{void}\n"
        f"Pending: {pending}\n"
        f"Units: {fmt_units(total_units)}\n"
        f"Win rate: {win_rate}\n\n"
    )
    for item in items:
        status = str(item.get("result_status") or "PENDING").upper()
        message += f"{result_icon(status)} {item.get('pick') or '-'} | {item.get('odds') or '-'} | {status} | {item.get('score') or '-'} | {fmt_units(item.get('units'))}\n"
    message += "\nThis data is provided for informational and analytical purposes only\nPowered by BackstageTalks Statistical Engine"
    return message


def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": True},
        timeout=30,
    )
    response.raise_for_status()


def main():
    day, items = load_top5_today_items()
    if not items:
        print("No TOP5 items for today. No Telegram summary sent.")
        return
    unsettled = [item for item in items if str(item.get("result_status") or "PENDING").upper() in ["PENDING", "UNKNOWN"]]
    if unsettled:
        print("TOP5 not fully settled. No Telegram summary sent. Unsettled:", len(unsettled))
        return
    if already_sent(day):
        print("Telegram results summary already sent for", day)
        return
    message = build_message(day, items)
    send_telegram_message(message)
    mark_sent(day, message)
    print(message)
    print("Telegram results summary sent.")


if __name__ == "__main__":
    main()
