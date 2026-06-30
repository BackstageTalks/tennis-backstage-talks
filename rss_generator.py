from datetime import datetime


def generate_rss(data):
    now = datetime.utcnow()

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Tennis Picks</title>
<link>https://backstagetalks.github.io/tennis-backstage-talks/</link>
"""

    for p in data:
        xml += f"""
<item>
<title>{p['pick']} vs {p['player2']}</title>
<description>Prob: {p['probability']} | Odds: {p['odds']}</description>
<pubDate>{now}</pubDate>
</item>
"""

    xml += "</channel></rss>"
    return xml
