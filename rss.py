import datetime
import json
import os

def generate_rss():
    today = datetime.date.today().isoformat()
    path = f"data/predictions_{today}.json"

    if not os.path.exists(path):
        print("No predictions for RSS")
        return

    with open(path, "r", encoding="utf-8") as f:
        preds = json.load(f)

    items = ""
    for p in preds:
        items += f"""
        <item>
            <title>{p['player1']} vs {p['player2']}</title>
            <description>Value bet: {p['value_player1']['value']:.3f} / {p['value_player2']['value']:.3f}</description>
        </item>
        """

    rss = f"""
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

    print("RSS generated")
