import os, json, datetime

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"

def latest():
    files = [f for f in os.listdir("public") if f.startswith("predictions_")]
    if not files:
        return []
    last = sorted(files)[-1]
    return json.load(open("public/" + last))

def gen():
    preds = latest()

    items = ""

    for i, p in enumerate(preds):
        if p["probability"] > 0.65:
            label = "🔥 STRONG"
        elif p["probability"] > 0.58:
            label = "✅ SAFE"
        else:
            label = "⚖️ RISK"

        desc = f"{label} | Prob {p['probability']} | Conf {p['confidence']} | Value {p['value']}"

        items += f"""
<item>
<title>{p['player1']} vs {p['player2']}</title>
<link>{BASE}</link>
<guid>{i}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{desc}</description>
</item>
"""

    rss = f"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>Tennis Picks</title>
<link>{BASE}</link>
<description>Filtered high-probability predictions</description>
{items}
</channel>
</rss>
"""

    open("public/tennis.xml", "w").write(rss)

if __name__ == "__main__":
    gen()
