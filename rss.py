import os
import json
import datetime

BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks/"

def get_latest_predictions():
    if not os.path.exists("public"):
        return []

    files = [f for f in os.listdir("public") if f.startswith("predictions_")]

    if not files:
        return []

    latest = sorted(files)[-1]
    path = os.path.join("public", latest)

    print("Using:", path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_rss():
    predictions = get_latest_predictions()

    items = ""

    for i, p in enumerate(predictions):
        # 🔥 LABEL LOGIKA
        if p["probability_player1"] > 0.65 and p["confidence"] > 0.12:
            label = "🔥 ELITE PICK"
        elif p["probability_player1"] > 0.58:
            label = "✅ SAFE PICK"
        else:
            label = "⚖️ LEAN"

        # ✅ ONE-LINE DESCRIPTION (FeedFlow kompatibilné)
        desc = f"{label} | {p['tournament']} | Prob: {p['probability_player1']} | Conf: {p['confidence']}"

        guid = f"{p['player1']}-{p['player2']}-{i}"

        items += f"""
<item>
<title>{p['player1']} vs {p['player2']}</title>
<link>{BASE_URL}</link>
<guid isPermaLink="false">{guid}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{desc}</description>
</item>
"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Picks</title>
<link>{BASE_URL}</link>
<description>Daily tennis predictions (Top + Elite Picks)</description>
{items}
</channel>
</rss>
"""

    os.makedirs("public", exist_ok=True)

    with open("public/tennis.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("✅ RSS GENERATED:", len(predictions), "items")


if __name__ == "__main__":
    generate_rss()
