
import html
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests

BOT_TOKEN = os.getenv("TG_BOT_BTLKR")
CHAT_ID = os.getenv("TG_CHAT_ID")
if not BOT_TOKEN:
    raise ValueError("Missing GitHub secret: TG_BOT_BTLKR")
if not CHAT_ID:
    raise ValueError("Missing GitHub secret: TG_CHAT_ID")

LOCAL_TZ = ZoneInfo("Europe/Bratislava")
FEED_LIMIT = int(os.getenv("TG_FEED_LIMIT", "5"))
SELECTED_FEED = os.getenv("TG_FEED", "all").strip().lower()

RSS_FEEDS = [
    {"key": "corq", "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y185.xml", "title": "TOP BETS | Corq Model"},
    {"key": "thinq", "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y186.xml", "title": "TOP BETS | Thinq Model"},
    {"key": "blenq", "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y187.xml", "title": "TOP BETS | Blenq Model"},
]

BLENQ_MIN_ODDS = 1.70
BLENQ_MAX_ODDS = 2.65
BLENQ_MAX_GAP = 10.0
BLENQ_MIN_WR = 60.0
BLENQ_MIN_EDGE = 3.0
BANNED_MARKETS = {"CAUTION", "BEARISH"}


def clean(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def clean_one_line(value):
    return re.sub(r"\s+", " ", clean(value)).strip()


def extract_player(title):
    title = clean_one_line(title)
    if " to win vs " in title:
        return title.split(" to win vs ", 1)[0].strip()
    return title


def extract_opponent(title):
    title = clean_one_line(title)
    if " to win vs " in title:
        return title.split(" to win vs ", 1)[1].strip()
    return ""


def number(label, description, percent=False):
    text = clean(description)
    suffix = "%" if percent else ""
    match = re.search(re.escape(label) + r":\s*([+-]?[0-9]+(?:\.[0-9]+)?)" + suffix, text, re.IGNORECASE)
    return match.group(1) if match else None


def parse_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def market_signal(description):
    text = clean(description)
    match = re.search(r"Market Signal:\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        return clean_one_line(match.group(1)).upper()
    return ""


def blenq_allowed(description):
    wr = parse_float(number("Win probability", description, True))
    odd = parse_float(number("Odds", description, False))
    edge = parse_float(number("Edge", description, True))
    gap = parse_float(number("Market gap", description, True))
    signal = market_signal(description)
    if wr is None or odd is None or edge is None or gap is None:
        return False
    if odd < BLENQ_MIN_ODDS or odd > BLENQ_MAX_ODDS:
        return False
    if gap > BLENQ_MAX_GAP:
        return False
    if wr < BLENQ_MIN_WR:
        return False
    if edge < BLENQ_MIN_EDGE:
        return False
    if signal in BANNED_MARKETS:
        return False
    return True


def short_name(player):
    parts = clean_one_line(player).split()
    return parts[-1] if parts else "-"


def selected_feeds():
    if SELECTED_FEED in ("", "all", "*all"):
        return RSS_FEEDS
    feeds = [feed for feed in RSS_FEEDS if feed["key"] == SELECTED_FEED]
    if not feeds:
        valid = ", ".join(feed["key"] for feed in RSS_FEEDS)
        raise ValueError(f"Invalid TG_FEED={SELECTED_FEED}. Valid values: all, {valid}")
    return feeds


def build_message(feed):
    parsed = feedparser.parse(feed["url"])
    if parsed.bozo:
        raise ValueError(f"RSS parsing error for {feed['url']}: {parsed.bozo_exception}")
    today = datetime.now(LOCAL_TZ).strftime("%d.%m.%Y")
    message = f"📅 {today}\n\n🎾 {feed['title']}\n\n"
    icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    added = 0
    for item in parsed.entries:
        if added >= FEED_LIMIT:
            break
        title = item.get("title", "")
        description = item.get("description", "")
        if feed["key"] == "blenq" and not blenq_allowed(description):
            continue
        player = extract_player(title)
        opponent = extract_opponent(title)
        win_rate = number("Win probability", description, True)
        odd = number("Odds", description, False)
        edge = number("Edge", description, True)
        if not player or not win_rate or not odd:
            continue
        icon = icons[added] if added < len(icons) else f"{added + 1}."
        # Telegram output keeps the win-rate value, but removes only the literal "WR" label.
        # Example: Player | 61.4% | 1.92
        line = f"{icon} {short_name(player)} | {win_rate}% | {odd}"
        if feed["key"] == "blenq" and edge:
            edge_value = edge if str(edge).startswith("-") else f"+{edge}"
            line += f" | Edge {edge_value}%"
        if opponent:
            line += f"\n   vs {opponent}"
        message += line + "\n"
        added += 1
    if added == 0:
        message += "No valid picks found in RSS feed.\n"
    message += "\nThis data is provided for informational and analytical purposes only\nPowered by BackstageTalks Statistical Engine"
    return message, added


def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": True},
        timeout=30,
    )
    response.raise_for_status()


def main():
    print("TELEGRAM RSS FEED START")
    print("TG_FEED:", SELECTED_FEED)
    print("TG_FEED_LIMIT:", FEED_LIMIT)
    for feed in selected_feeds():
        message, count = build_message(feed)
        send_telegram_message(message)
        print("SENT FEED:", feed["key"], feed["url"])
        print("PICKS SENT:", count)
        print(message)
    print("TELEGRAM RSS FEED DONE")


if __name__ == "__main__":
    main()
