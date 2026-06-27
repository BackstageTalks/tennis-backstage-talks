import datetime
import json
import os

def generate_rss():
    today = datetime.date.today().isoformat()
    path = f"data/predictions_{today}.json"

    # Ak predikcie neexistujú, RSS aj tak vytvoríme (prázdny feed)
    predictions = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            predictions = json.load(f)
    else:
        print("No predictions found, generating empty RSS feed")

    items = ""
    for p in predictions:
        items += f"""
        <item>
            <title>{p['player1']} vs {p['player2']} – {p['tournament']}</title>
            <description>
                Player1 value: {p['value_player1']['value']:.3f}
                Player2 value: {p['value_player2']['value']:.3f}
            </description>
        </item>
        """

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Backstage Talks Tennis Predictions</title>
            <link>https://backstagetalks.github.io/BackstageTalks/</link>
            <description>Daily tennis predictions and value bets</description>
            {items}
        </channel>
    </rss>
    """

    os.makedirs("public", exist_ok=True)

    with open("public/tennis.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RSS generated → public/tennis.xml")
