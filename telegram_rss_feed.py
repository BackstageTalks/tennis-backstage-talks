import html
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
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

FEED_LIMIT = int(os.getenv("TG_FEED_LIMIT", "5"))
SELECTED_FEED = os.getenv("TG_FEED", "all").strip().lower()

RSS_FEEDS = [
    {
        "key": "corq",
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y185.xml",
        "title": "TOP BETS | Corq Model",
    },
    {
        "key": "thinq",
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y186.xml",
        "title": "TOP BETS | Thinq Model",
    },
    {
        "key": "blend",
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y187.xml",
        "title": "TOP BETS | Blend Model",
    },
]


# ============================================================
# TEXT HELPERS
# ============================================================


def clean_text(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_multiline(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


# ============================================================
# PARSING HELPERS
# ============================================================


def extract_player(title):
    title = clean_text(title)

    if " to win vs " in title:
        return title.split(" to win vs ", 1)[0].strip()

    return title.strip()


def extract_opponent(title):
    title = clean_text(title)

    if " to win vs " in title:
        return title.split(" to win vs ", 1)[1].strip()

    return ""


def extract_probability(description):
    text = clean_multiline(description)

    match = re.search(
        r"Win probability:\s*([0-9]+(?:\.[0-9]+)?)%",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def extract_odds(description):
    text = clean_multiline(description)

    match = re.search(
        r"Odds:\s*([0-9]+(?:\.[0-9]+)?)",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def extract_ai_match(description):
    text = clean_multiline(description)

    match = re.search(
        r"AI Match:\s*([0-9]+(?:\.[0-9]+)?)%",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def short_name(player):
    parts = clean_text(player).split()

    if not parts:
        return "-"

    return parts[-1]


# ============================================================
# RSS + TELEGRAM
# ============================================================


def parse_feed_entries(feed_url):
    feed = feedparser.parse(feed_url)

    if feed.bozo:
        raise ValueError(f"RSS parsing error for {feed_url}: {feed.bozo_exception}")

    return feed.entries or []


def build_message(feed_url, feed_title, limit):
    entries = parse_feed_entries(feed_url)
    today = datetime.now(LOCAL_TZ).strftime("%d.%m.%Y")

    message = (
        f"📅 {today}\n\n"
        f"🎾 {feed_title}\n\n"
    )

    icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    added = 0

    for item in entries:
        if added >= limit:
            break

        title = item.get("title", "")
        description = item.get("description", "")

        player = extract_player(title)
        opponent = extract_opponent(title)
        probability = extract_probability(description)
        odd = extract_odds(description)
        ai_match = extract_ai_match(description)

        if not player or not probability or not odd:
            continue

        icon = icons[added] if added < len(icons) else f"{added + 1}."
        name = short_name(player)

        line = f"{icon} {name} | {probability}% | {odd}"

        if ai_match:
            line += f" | AI {ai_match}%"

        if opponent:
            line += f"\n   vs {opponent}"

        message += line + "\n"
        added += 1

    if added == 0:
        message += "No valid picks found in RSS feed.\n"

    message += (
        "\n"
        "This data is provided for informational and analytical purposes only\n"
        "Powered by BackstageTalks Statistical Engine"
    )

    return message, added


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


def selected_feeds():
    if SELECTED_FEED in ("", "all", "*all"):
        return RSS_FEEDS

    output = [feed for feed in RSS_FEEDS if feed["key"] == SELECTED_FEED]

    if not output:
        valid = ", ".join(feed["key"] for feed in RSS_FEEDS)
        raise ValueError(f"Invalid TG_FEED={SELECTED_FEED}. Valid values: all, {valid}")

    return output


def main():
    print("TELEGRAM RSS FEED START")
    print("TG_FEED:", SELECTED_FEED)
    print("TG_FEED_LIMIT:", FEED_LIMIT)

    for rss_feed in selected_feeds():
        message, count = build_message(
            feed_url=rss_feed["url"],
            feed_title=rss_feed["title"],
            limit=FEED_LIMIT,
        )

        send_telegram_message(message)

        print("")
        print("SENT FEED:", rss_feed["key"], rss_feed["url"])
        print("PICKS SENT:", count)
        print(message)
        print("Telegram message sent successfully.")

    print("TELEGRAM RSS FEED DONE")


if __name__ == "__main__":
    main()
