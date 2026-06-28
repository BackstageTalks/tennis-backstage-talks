import os
import json
import datetime
import html

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"


def latest_predictions():
    if not os.path.exists("public"):
        return []

    files = [
        f for f in os.listdir("public")
        if f.startswith("predictions_") and f.endswith(".json")
    ]

    if not files:
        print("NO prediction files found")
        return []

    latest = sorted(files)[-1]
    path = os.path.join("public", latest)

    print("RSS using prediction file:", path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def label_for_pick(p):
    probability = float(p.get("probability", 0))

    if probability >= 0.65:
        return "🔥 STRONG"
    elif probability >= 0.58:
        return "✅ SAFE"
    else:
        return "⚖️ LEAN"


def generate_rss():
    predictions = latest_predictions()

    items = ""

    for i, p in enumerate(predictions):
        player1 = html.escape(str(p.get("player1", "Unknown")))
        player2 = html.escape(str(p.get("player2", "Unknown")))
        tournament = html.escape(str(p.get("tournament", "Tennis")))

        probability = p.get("probability", "")
        confidence = p.get("confidence", "")
        value = p.get("value", "")
        odds = p.get("odds", "")

        label = label_for_pick(p)

        title = f"{player1} vs {player2}"
        desc = (
            f"{label} | {tournament} | "
            f"Prob: {probability} | "
            f"Conf: {confidence} | "
            f"Odds: {odds} | "
            f"Value: {value}"
        )

        guid = f"{player1}-{player2}-{datetime.date.today().isoformat()}-{i}"

        items += f"""
<item>
<title>{title}</title>
<link>{BASE}</link>
<guid isPermaLink="false">{guid}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{html.escape(desc)}</description>
</item>
"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Predictions</title>
<link>{BASE}</link>
<description>Daily tennis predictions from real match data</description>
{items}
</channel>
</rss>
"""

    os.makedirs("public", exist_ok=True)

    with open("public/tennis.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RSS GENERATED:", len(predictions), "items")

    print("RSS PREVIEW:")
    print(rss[:1000])


if __name__ == "__main__":
    generate_rss()
