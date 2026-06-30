from datetime import datetime


def generate_rss(top_preds):
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Picks</title>
<link>https://backstagetalks.github.io/tennis-backstage-talks/</link>
<description>Daily picks</description>
<lastBuildDate>{now}</lastBuildDate>
"""

    for p in top_preds:
        pick = p["pick"]
        opp = p["player2"] if pick == p["player1"] else p["player1"]
        prob = round(p["probability"] * 100, 1)
        odds = p["odds"] if p["odds"] else "-"
        time = p.get("time", "TBD")

        rss += f"""
<item>
<title>{pick} vs {opp}</title>
<description>
Pick: {pick}
Win%: {prob}
Odds: {odds}
Time: {time}
</description>
<pubDate>{now}</pubDate>
</item>
"""

    rss += "</channel></rss>"
    return rss
