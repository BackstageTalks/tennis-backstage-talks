import os, json, datetime
from tracker import stats

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"

def latest():
    files = [f for f in os.listdir("public") if f.startswith("predictions_")]
    if not files:
        return []
    last = sorted(files)[-1]
    return json.load(open("public/" + last))

def gen():
    preds = latest()
    s = stats()

    items = ""

    for i, p in enumerate(preds):
        if p["value"] > 0.05:
            label = "🔥 VALUE"
        elif p["probability"] > 0.6:
            label = "✅ SAFE"
        else:
            label = "⚖️"

        desc = f"{label} | Prob {p['probability']} | Odds {p['odds']} | ROI edge {p['value']}"

        items += f"""
<item>
<title>{p['player1']} vs {p['player2']}</title>
<link>{BASE}</link>
<guid>{p['player1']}-{i}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{desc}</description>
</item>
"""

    rss = f"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>Tennis Picks</title>
<link>{BASE}</link>
<description>Accuracy {s['acc']}% | ROI {s['roi']}% | Bets {s['n']}</description>
{items}
</channel>
</rss>
"""

    open("public/tennis.xml", "w").write(rss)

if __name__ == "__main__":
    gen()
