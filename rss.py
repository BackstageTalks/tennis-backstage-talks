import os
import json
import datetime

def get_latest_predictions():
    if not os.path.exists("public"):
        return []

    files = [f for f in os.listdir("public") if f.startswith("predictions_")]

    if not files:
        return []

    latest = sorted(files)[-1]
    path = os.path.join("public", latest)

    print("Using file:", path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_rss():
    predictions = get_latest_predictions()

    items = ""

    for p in predictions:
        items += f"""
<item>
<title>{p['player1']} vs {p['player2']}</title>
<link>https://backstagetalks.github.io/tennis-backstage-talks/</link>
<guid>{p['player1']}-{p['player2']}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>
Tournament: {p['tournament']}
Value1: {p['value_player1']['value']:.3f}
Value2: {p['value_player2']['value']:.3f}
</description>
</item>
"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Predictions</title>
<link>https://backstagetalks.github.io/tennis-backstage-talks/</link>
<description>Daily tennis predictions</description>
{items}
</channel>
</rss>
"""

    os.makedirs("public", exist_ok=True)

    with open("public/tennis.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RSS generated with", len(predictions), "items")


if __name__ == "__main__":
    generate_rss()
