import os
import re
from datetime import datetime

import feedparser
import requests

# RSS FEED
RSS_URL = "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y186.xml"

# GITHUB SECRETS
BOT_TOKEN = os.getenv("TG_BOT_BTLKR")
CHAT_ID = os.getenv("TG_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("TG_BOT_BTLKR secret not found")

if not CHAT_ID:
    raise ValueError("TG_CHAT_ID secret not found")

# LOAD RSS
feed = feedparser.parse(RSS_URL)

if not feed.entries:
    raise ValueError("No RSS entries found")

# HEADER
today = datetime.now().strftime("%d.%m.%Y")

message = (
    f"📅 {today}\n\n"
    f"🎾 TOP 5 | Thinq Model\n\n"
)

# TOP 5
for idx, item in enumerate(feed.entries[:5], start=1):

    title = item.title

    player = title.split(" to win vs ")[0]

    prob_match = re.search(
        r"Win probability:\s*([0-9.]+)%",
        item.description,
        re.IGNORECASE
    )

    odds_match = re.search(
        r"Odds:\s*([0-9.]+)",
        item.description,
        re.IGNORECASE
    )

    if not prob_match or not odds_match:
        continue

    probability = prob_match.group(1)
    odds = odds_match.group(1)

    surname = player.split()[-1]

    message += f"{idx}️⃣ {surname} | {probability}% | {odds}\n"

# FOOTER
message += (
    "\n"
    "This data is provided for informational and analytical purposes only\n"
    "Powered by BackstageTalks Statistical Engine"
)

# SEND TO TELEGRAM
response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=30
)

response.raise_for_status()

print(message)
print("Telegram TOP5 message sent successfully")
