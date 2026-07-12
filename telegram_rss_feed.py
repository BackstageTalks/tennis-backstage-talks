# -*- coding: utf-8 -*-

import os
import re
import html
from datetime import datetime

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
# RSS FEEDS
# ============================================================

CORQ_FEED_URL = "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y185.xml"
THINQ_FEED_URL = "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y186.xml"

RSS_FEEDS = [
    {
        "url": CORQ_FEED_URL,
        "title": "TOP 7 | Corq Model",
        "pick_limit": 7
    },
    {
        "url": THINQ_FEED_URL,
        "title": "TOP 7 | Thinq Model",
        "pick_limit": 7
    },
    {
        "url": CORQ_FEED_URL,
        "title": "FREE",
        "pick_limit": 1
    }
]


# ============================================================
# FUNCTIONS
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_player(title):
    title = clean_text(title)

    if " to win vs " in title:
        return title.split(" to win vs ")[0].strip()

    return title.strip()


def extract_probability(description):
    description = clean_text(description)

    match = re.search(
        r"Win probability:\s*([0-9.]+)%",
        description,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def extract_odds(description):
    description = clean_text(description)

    match = re.search(
        r"Odds:\s*([0-9.]+)",
        description,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def build_message(feed_url, feed_title, pick_limit):
    feed = feedparser.parse(feed_url)

    if feed.bozo:
        raise ValueError(f"RSS parsing error for {feed_url}: {feed.bozo_exception}")

    if not feed.entries:
        raise ValueError(f"No RSS entries found for {feed_url}")

    today = datetime.now().strftime("%d.%m.%Y")

    message = (
        f"📅 {today}\n\n"
        f"🎾 {feed_title}\n\n"
    )

    icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]

    added = 0

    for item in feed.entries:
        if added >= pick_limit:
            break

        title = item.get("title", "")
        description = item.get("description", "")

        player = extract_player(title)
        probability = extract_probability(description)
        odds = extract_odds(description)

        if not player or not probability or not odds:
            continue

        surname = player.split()[-1]

        if added < len(icons):
            icon = icons[added]
        else:
            icon = f"{added + 1}."

        message += f"{icon} {surname} | {probability}% | {odds}\n"

        added += 1

    if added == 0:
        raise ValueError(f"No valid items parsed from {feed_url}")

    message += (
        "\n"
        "ℹ️ Analytical preview only\n"
        "🧠 by BackstageTalks AI Engine"
    )

    return message


def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()


# ============================================================
# MAIN
# ============================================================

for rss_feed in RSS_FEEDS:
    message = build_message(
        feed_url=rss_feed["url"],
        feed_title=rss_feed["title"],
        pick_limit=rss_feed["pick_limit"]
    )

    send_telegram_message(message)

    print(message)
    print("Telegram message sent successfully.")
